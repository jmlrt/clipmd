"""Core logic for finding and reporting duplicate articles."""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING

from clipmd.core.dates import has_date_prefix, parse_date_string
from clipmd.core.discovery import discover_markdown_files
from clipmd.core.frontmatter import get_source_url, parse_frontmatter
from clipmd.core.hasher import hash_content
from clipmd.core.sanitizer import clean_url

if TYPE_CHECKING:
    from clipmd.config import Config


@dataclass
class DuplicateGroup:
    """A group of duplicate articles."""

    key: str
    files: list[Path] = field(default_factory=list)


@dataclass
class DuplicateResult:
    """Results of duplicate detection."""

    by_url: list[DuplicateGroup] = field(default_factory=list)
    by_hash: list[DuplicateGroup] = field(default_factory=list)
    by_filename: list[DuplicateGroup] = field(default_factory=list)


@dataclass
class ResolveStats:
    """Statistics from resolving duplicates."""

    total_groups: int = 0
    kept: list[tuple[str, Path]] = field(default_factory=list)  # (key, kept_path)
    trashed: list[Path] = field(default_factory=list)
    errors: list[tuple[Path, str]] = field(default_factory=list)


def _extract_date_from_filename(path: Path) -> date | None:
    """Extract date from filename using date prefix pattern.

    Args:
        path: Path to check.

    Returns:
        Extracted date or None if not found.
    """
    filename = path.stem
    if has_date_prefix(filename):
        # YYYYMMDD- prefix format
        date_str = filename[:8]
        try:
            return parse_date_string(date_str)
        except Exception:
            pass
    return None


def _get_file_date(path: Path, config: Config | None = None) -> date | None:
    """Extract date from filename, then frontmatter clipped field.

    Args:
        path: Path to the file.
        config: Application configuration (used for frontmatter field mapping).

    Returns:
        Extracted date or None if not found.
    """
    # First try filename
    result = _extract_date_from_filename(path)
    if result:
        return result

    # Then try frontmatter clipped field
    try:
        content = path.read_text(encoding="utf-8")
        parsed = parse_frontmatter(content)
        # Use configured field names or defaults
        clipped_fields = ["clipped"]
        if (
            config
            and hasattr(config, "frontmatter")
            and hasattr(config.frontmatter, "clipped_date")
        ):
            clipped_fields = list(config.frontmatter.clipped_date) or ["clipped"]
        # Try each configured field name
        for field in clipped_fields:
            clipped = parsed.data.get(field)
            if clipped:
                return parse_date_string(str(clipped))
    except Exception:
        pass

    return None


def pick_winner(paths: list[Path], config: Config | None = None) -> Path:
    """Return the path to keep (oldest by date, then shortest stem for ties).

    Args:
        paths: List of paths to choose from.
        config: Application configuration (optional, used for frontmatter field mapping).

    Returns:
        Path to the winner (file to keep).
    """
    if len(paths) == 1:
        return paths[0]

    def sort_key(p: Path) -> tuple:
        d = _get_file_date(p, config)
        # Sort by: (has_no_date, date, stem_length, normalized_path_string)
        # Files with dates come first (has_no_date=False < True)
        # Earlier dates come first
        # Shorter stems break ties
        # Normalized path string breaks final ties deterministically
        return (0 if d else 1, d or date.max, len(p.stem), str(p))

    return min(paths, key=sort_key)


def resolve_duplicates(
    groups: list[DuplicateGroup],
    config: Config,
    strategy: str = "oldest-wins",  # noqa: ARG001
    dry_run: bool = False,
) -> ResolveStats:
    """Resolve duplicate groups by trashing losers.

    Args:
        groups: List of duplicate groups to resolve.
        config: Application configuration.
        strategy: Resolution strategy (currently only "oldest-wins").
        dry_run: If True, don't actually trash files.

    Returns:
        ResolveStats with summary of operations.
    """
    from clipmd.core import trash

    stats = ResolveStats(total_groups=len(groups))
    to_trash_set: set[Path] = set()

    for group in groups:
        winner = pick_winner(group.files, config)
        losers = [f for f in group.files if f != winner]
        stats.kept.append((group.key, winner))
        to_trash_set.update(losers)

    # Trash the loser files (deduplicated)
    if to_trash_set:
        to_trash = sorted(to_trash_set)  # Deterministic ordering
        trash_stats = trash.trash_files(to_trash, config, dry_run=dry_run)
        # Track successfully trashed files by excluding error paths
        error_paths = {p for p, _ in trash_stats.errors}
        stats.trashed = [p for p in to_trash if p not in error_paths]
        stats.errors = list(trash_stats.errors)

    return stats


def find_duplicates_by_url(root_dir: Path, config: Config) -> list[DuplicateGroup]:
    """Find articles with the same source URL.

    Args:
        root_dir: Root articles directory.
        config: Application configuration.

    Returns:
        List of duplicate groups.
    """
    url_to_files: dict[str, list[Path]] = defaultdict(list)

    # Scan all markdown files
    for md_file in discover_markdown_files(root_dir, config):
        try:
            content = md_file.read_text(encoding="utf-8")
            parsed = parse_frontmatter(content)
            url = get_source_url(parsed.data, config.frontmatter)
            if url:
                # Clean URL to remove tracking params before using as grouping key
                cleaned_url = clean_url(url)
                url_to_files[cleaned_url].append(md_file)
        except Exception:
            continue

    # Find groups with more than one file
    groups = []
    for url, files in sorted(url_to_files.items()):
        if len(files) > 1:
            groups.append(DuplicateGroup(key=url, files=sorted(files)))

    return groups


def find_duplicates_by_hash(root_dir: Path, config: Config) -> list[DuplicateGroup]:
    """Find articles with the same content hash.

    Args:
        root_dir: Root articles directory.
        config: Application configuration.

    Returns:
        List of duplicate groups.
    """
    hash_to_files: dict[str, list[Path]] = defaultdict(list)

    # Scan all markdown files
    for md_file in discover_markdown_files(root_dir, config):
        try:
            content = md_file.read_text(encoding="utf-8")
            parsed = parse_frontmatter(content)
            # Hash the content body, not frontmatter
            content_hash = hash_content(parsed.content)
            hash_to_files[content_hash].append(md_file)
        except Exception:
            continue

    # Find groups with more than one file
    groups = []
    for content_hash, files in sorted(hash_to_files.items()):
        if len(files) > 1:
            groups.append(DuplicateGroup(key=content_hash[:12], files=sorted(files)))

    return groups


def find_duplicates_by_filename(root_dir: Path, config: Config) -> list[DuplicateGroup]:
    """Find articles with similar filenames.

    This looks for files that have the same name after removing date prefix.

    Args:
        root_dir: Root articles directory.
        config: Application configuration.

    Returns:
        List of duplicate groups.
    """
    name_to_files: dict[str, list[Path]] = defaultdict(list)

    # Scan all markdown files
    for md_file in discover_markdown_files(root_dir, config):
        # Remove date prefix for comparison
        filename = md_file.stem
        if has_date_prefix(filename):
            # Remove YYYYMMDD- prefix
            filename = filename[9:]

        name_to_files[filename.lower()].append(md_file)

    # Find groups with more than one file
    groups = []
    for name, files in sorted(name_to_files.items()):
        if len(files) > 1:
            groups.append(DuplicateGroup(key=name, files=sorted(files)))

    return groups


def format_duplicates_markdown(result: DuplicateResult, root_dir: Path) -> str:
    """Format duplicates as markdown.

    Args:
        result: Duplicate detection result.
        root_dir: Root directory for relative paths.

    Returns:
        Markdown string.
    """
    lines = ["# Duplicate Articles\n"]

    if result.by_url:
        lines.append(f"## By URL ({len(result.by_url)} groups)\n")
        for i, group in enumerate(result.by_url, 1):
            lines.append(f"{i}. {group.key}")
            for f in group.files:
                rel_path = f.relative_to(root_dir) if f.is_relative_to(root_dir) else f
                lines.append(f"   - {rel_path}")
            lines.append("")

    if result.by_hash:
        lines.append(f"## By Content Hash ({len(result.by_hash)} groups)\n")
        for i, group in enumerate(result.by_hash, 1):
            lines.append(f"{i}. Hash: {group.key}...")
            for f in group.files:
                rel_path = f.relative_to(root_dir) if f.is_relative_to(root_dir) else f
                lines.append(f"   - {rel_path}")
            lines.append("")

    if result.by_filename:
        lines.append(f"## By Similar Filename ({len(result.by_filename)} groups)\n")
        for i, group in enumerate(result.by_filename, 1):
            lines.append(f"{i}. {group.key}")
            for f in group.files:
                rel_path = f.relative_to(root_dir) if f.is_relative_to(root_dir) else f
                lines.append(f"   - {rel_path}")
            lines.append("")

    if not result.by_url and not result.by_hash and not result.by_filename:
        lines.append("No duplicates found.\n")

    return "\n".join(lines)


def format_duplicates_json(result: DuplicateResult, root_dir: Path) -> str:
    """Format duplicates as JSON.

    Args:
        result: Duplicate detection result.
        root_dir: Root directory for relative paths.

    Returns:
        JSON string.
    """

    def group_to_dict(group: DuplicateGroup) -> dict:
        return {
            "key": group.key,
            "files": [
                str(f.relative_to(root_dir) if f.is_relative_to(root_dir) else f)
                for f in group.files
            ],
        }

    data = {
        "by_url": [group_to_dict(g) for g in result.by_url],
        "by_hash": [group_to_dict(g) for g in result.by_hash],
        "by_filename": [group_to_dict(g) for g in result.by_filename],
    }
    return json.dumps(data, indent=2)
