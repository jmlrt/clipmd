"""Core orchestration logic for the triage workflow."""

from __future__ import annotations

import asyncio
import contextlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from clipmd.core import fetcher, mover, preprocessor, stats
from clipmd.core.mover import MoveInstruction

if TYPE_CHECKING:
    from clipmd.config import Config


@dataclass
class FetchStepResult:
    """Result from the fetch step."""

    rss_fetched: int = 0
    inbox_fetched: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)


@dataclass
class PreprocessStepResult:
    """Result from the preprocess step."""

    processed: int = 0
    duplicates_removed: int = 0
    errors: list[str] = field(default_factory=list)


@dataclass
class MoveStepResult:
    """Result from the move step."""

    domain_matched: int = 0
    staged: int = 0
    trashed: int = 0
    errors: list[str] = field(default_factory=list)
    folders_created: list[str] = field(default_factory=list)


@dataclass
class TriageResult:
    """Overall result from triage workflow."""

    fetch: FetchStepResult = field(default_factory=FetchStepResult)
    preprocess: PreprocessStepResult = field(default_factory=PreprocessStepResult)
    move: MoveStepResult = field(default_factory=MoveStepResult)
    stats_result: stats.Stats | None = None
    dry_run: bool = False


def run_triage(
    config: Config,
    vault: Path,
    dry_run: bool = False,
    no_domain_rules: bool = False,
    staging_folder: str | None = None,
) -> TriageResult:
    """Run the triage workflow: fetch → preprocess → move → stats.

    Best-effort execution: errors are logged and stored in results, but the
    workflow continues through all steps when possible (partial failures).

    Args:
        config: Configuration object
        vault: Vault root directory
        dry_run: If True, show what would happen without moving files
        no_domain_rules: If True, skip domain rule matching (move all to staging)
        staging_folder: Override staging folder name (default from config)

    Returns:
        TriageResult with stats from each step
    """
    result = TriageResult(dry_run=dry_run)
    effective_staging = staging_folder or config.triage.staging_folder

    # Fetch RSS sources
    for rss_url in config.triage.rss_sources:
        try:
            orch_result = asyncio.run(
                fetcher.orchestrate_fetch(
                    (rss_url,),
                    None,
                    config,
                    vault,
                    rss=True,
                    rss_limit=config.triage.rss_limit,
                    check_duplicates=True,
                    use_readability=True,
                    dry_run=dry_run,
                )
            )
            if orch_result.rss_error:
                result.fetch.errors.append(
                    f"RSS fetch failed for {rss_url}: {orch_result.rss_error}"
                )
            else:
                stats_obj = orch_result.process_result.stats
                result.fetch.rss_fetched += stats_obj.saved
                result.fetch.skipped += stats_obj.skipped
                # Capture individual fetch errors
                for url, error in stats_obj.errors:
                    result.fetch.errors.append(f"{url}: {error}")
        except Exception as exc:
            result.fetch.errors.append(f"RSS fetch failed for {rss_url}: {exc}")

    # Fetch INBOX.md if configured
    if config.triage.inbox_file:
        inbox_path = vault / config.triage.inbox_file
        if inbox_path.exists():
            try:
                orch_result = asyncio.run(
                    fetcher.orchestrate_fetch(
                        (),
                        inbox_path,
                        config,
                        vault,
                        rss=False,
                        check_duplicates=True,
                        use_readability=True,
                        dry_run=dry_run,
                    )
                )
                stats_obj = orch_result.process_result.stats
                result.fetch.inbox_fetched += stats_obj.saved
                result.fetch.skipped += stats_obj.skipped
                # Capture individual fetch errors from INBOX
                for url, error in stats_obj.errors:
                    result.fetch.errors.append(f"{url}: {error}")

                # Clear inbox file on success
                if not dry_run and (stats_obj.saved > 0 or stats_obj.errors):
                    if stats_obj.errors:
                        ko_lines = "\n".join(
                            f"{url} # [KO] - {error}" for url, error in stats_obj.errors
                        )
                        inbox_path.write_text(ko_lines + "\n" if ko_lines else "", encoding="utf-8")
                    else:
                        inbox_path.write_text("", encoding="utf-8")
            except Exception as exc:
                result.fetch.errors.append(f"INBOX fetch failed: {exc}")

    # Preprocess
    try:
        preprocess_stats = preprocessor.preprocess_directory(vault, config, dry_run=dry_run)
        result.preprocess.processed = preprocess_stats.scanned
        result.preprocess.duplicates_removed = preprocess_stats.duplicates_found
        result.preprocess.errors = [f"{path}: {error}" for path, error in preprocess_stats.errors]
    except Exception as exc:
        result.preprocess.errors.append(f"Preprocess failed: {exc}")

    # Move with domain rules
    # Filter out special files (INBOX.md, README.md, etc.) from move candidates
    special_files = set(config.special_folders.ignore_files)
    if config.triage.inbox_file:
        special_files.add(config.triage.inbox_file)

    all_md_files = {
        f.name for f in vault.glob("*.md") if f.is_file() and f.name not in special_files
    }
    domain_instructions = []
    if not no_domain_rules and config.domain_rules:
        domain_instructions = mover.apply_domain_rules_fallback(vault, config, set())
        result.move.domain_matched = len(domain_instructions)

    matched_files = {instr.filename for instr in domain_instructions}
    unmatched_files = all_md_files - matched_files
    staging_instructions = []
    for idx, filename in enumerate(sorted(unmatched_files), start=len(domain_instructions)):
        staging_instructions.append(
            MoveInstruction(
                index=idx,
                category=effective_staging,
                filename=filename,
                line_number=-1,
            )
        )

    result.move.staged = len(staging_instructions)

    # Execute moves
    all_instructions = domain_instructions + staging_instructions
    if all_instructions:
        try:
            move_stats = mover.execute_moves(
                all_instructions,
                vault,
                config,
                dry_run=dry_run,
                create_folders=True,
                update_cache=True,
                dest_root=vault,
                skip_missing=True,
            )
            result.move.trashed = move_stats.trashed
            result.move.folders_created = move_stats.folders_created
            result.move.errors = [f"{file}: {error}" for file, error in move_stats.errors]
        except Exception as exc:
            result.move.errors.append(f"Move operation failed: {exc}")

    # Collect stats (non-critical; suppress errors to avoid breaking the workflow)
    with contextlib.suppress(Exception):
        result.stats_result = stats.collect_folder_stats(vault, config, include_special=False)

    return result


def format_triage_summary(result: TriageResult) -> list[str]:
    """Format triage result as Rich markup lines.

    Args:
        result: TriageResult object

    Returns:
        List of Rich markup strings
    """
    lines = []

    # Fetch summary
    if result.fetch.rss_fetched or result.fetch.inbox_fetched or result.fetch.skipped:
        lines.append("✅ Fetched:")
        if result.fetch.rss_fetched:
            lines.append(f"   {result.fetch.rss_fetched} from RSS")
        if result.fetch.inbox_fetched:
            lines.append(f"   {result.fetch.inbox_fetched} from INBOX.md")
        if result.fetch.skipped:
            lines.append(f"   {result.fetch.skipped} skipped (duplicates/cached)")

    if result.fetch.errors:
        lines.append("[yellow]⚠️  Fetch warnings:[/yellow]")
        for error in result.fetch.errors[:3]:
            lines.append(f"  {error}")

    # Move summary
    if result.move.domain_matched or result.move.staged or result.move.trashed:
        lines.append("📁 Organized:")
        if result.move.domain_matched:
            lines.append(f"   {result.move.domain_matched} to folders (domain rules)")
        if result.move.staged:
            lines.append(f"   {result.move.staged} to staging")
        if result.move.trashed:
            lines.append(f"   {result.move.trashed} to trash")

    # Final summary
    lines.append("✅ Triage complete!")

    return lines
