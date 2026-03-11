"""Preprocess command for clipmd."""

from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console

from clipmd.context import Context
from clipmd.core import preprocessor

console = Console()


@click.command("preprocess")
@click.argument(
    "path",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=".",
)
@click.option("--dry-run", is_flag=True, help="Show what would be done")
@click.option("--no-url-clean", is_flag=True, help="Skip URL cleaning")
@click.option("--no-filename-clean", is_flag=True, help="Skip filename sanitization")
@click.option("--no-date-prefix", is_flag=True, help="Skip date prefix addition")
@click.option("--no-frontmatter-fix", is_flag=True, help="Skip frontmatter fixing")
@click.option("--no-dedupe", is_flag=True, help="Skip duplicate detection")
@click.option(
    "--auto-remove-dupes",
    is_flag=True,
    help="Automatically remove duplicate files detected during preprocessing (skips confirmation)",
)
@click.pass_context
def preprocess_command(
    ctx: click.Context,
    path: Path,
    dry_run: bool,
    no_url_clean: bool,
    no_filename_clean: bool,
    no_date_prefix: bool,
    no_frontmatter_fix: bool,
    no_dedupe: bool,
    auto_remove_dupes: bool,
) -> None:
    """Preprocess markdown articles.

    Cleans URLs, sanitizes filenames, adds date prefixes, and fixes frontmatter.
    """
    cli_ctx: Context = ctx.find_object(Context)  # type: ignore[assignment]
    config = cli_ctx.config

    if config is None:
        console.print("[red]Error:[/red] No configuration loaded")
        raise SystemExit(1)

    if config.vault is None:
        console.print("[red]Error:[/red] Vault path not configured in ~/.config/clipmd/config.yaml")
        raise SystemExit(1)

    if dry_run:
        console.print("[yellow]Dry run - no files will be modified[/yellow]\n")

    stats = preprocessor.preprocess_directory(
        path,
        config,
        dry_run=dry_run,
        no_url_clean=no_url_clean,
        no_filename_clean=no_filename_clean,
        no_date_prefix=no_date_prefix,
        no_frontmatter_fix=no_frontmatter_fix,
        no_dedupe=no_dedupe,
    )

    # Handle auto-remove-dupes if requested
    if auto_remove_dupes and stats.duplicate_groups:
        from clipmd.core import trash
        from clipmd.core.duplicates import pick_winner

        to_trash: set[Path] = set()
        for group in stats.duplicate_groups:
            # Extract and normalize paths (may be relative from cache)
            paths = []
            for _, p in group:
                # Normalize to absolute path under vault
                if not p.is_absolute():
                    p = config.vault / p
                paths.append(p)

            winner = pick_winner(paths, config)
            losers = [p for p in paths if p != winner]
            to_trash.update(losers)  # Use set to deduplicate

        if to_trash:
            # Filter to only files under the processed path (safety: don't trash files outside scope)
            to_trash_list = [p for p in to_trash if p.resolve().is_relative_to(path.resolve())]

            if to_trash_list:
                # Sort for deterministic display
                to_trash_list = sorted(to_trash_list)
                # --auto-remove-dupes implies automatic removal (no confirmation)
                if not dry_run:
                    console.print(f"Removing {len(to_trash_list)} duplicate files (oldest kept)")
                    for p in to_trash_list:
                        console.print(f"  - {p.name}")

                if not dry_run:
                    trash_stats = trash.trash_files(to_trash_list, config, dry_run=False)
                    console.print(f"Removed {trash_stats.trashed} duplicate files")
                    # Surface any trash errors
                    if trash_stats.errors:
                        console.print("\n[red]Errors while removing duplicates:[/red]")
                        for path, error in trash_stats.errors:
                            console.print(f"  ✗ {path.name}: {error}")
                else:
                    console.print(f"[dry-run] Would remove {len(to_trash_list)} duplicate files")

    # Display summary
    summary_lines = preprocessor.format_preprocess_summary(
        stats,
        no_frontmatter_fix=no_frontmatter_fix,
        no_url_clean=no_url_clean,
        no_filename_clean=no_filename_clean,
        no_date_prefix=no_date_prefix,
        no_dedupe=no_dedupe,
    )
    for line in summary_lines:
        console.print(line)
