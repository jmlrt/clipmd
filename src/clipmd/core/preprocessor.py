"""Core logic for preprocessing markdown files."""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

from clipmd.core.cache import Cache
from clipmd.core.dates import add_date_prefix, get_date_for_prefix, has_date_prefix
from clipmd.core.discovery import discover_markdown_files
from clipmd.core.frontmatter import (
    fix_frontmatter,
    get_source_url,
    parse_frontmatter,
    serialize_frontmatter,
)
from clipmd.core.hasher import hash_content
from clipmd.core.sanitizer import clean_url, sanitize_filename

if TYPE_CHECKING:
    from clipmd.config import Config


@dataclass
class PreprocessStats:
    """Statistics from preprocessing."""

    scanned: int = 0
    frontmatter_fixed: int = 0
    frontmatter_fixes: dict[str, int] = field(default_factory=dict)
    urls_cleaned: int = 0
    filenames_renamed: int = 0
    date_prefixes_added: int = 0
    date_prefixes_from_frontmatter: int = 0
    date_prefixes_from_content: int = 0
    duplicates_found: int = 0
    duplicate_groups: list[list[tuple[str, Path]]] = field(default_factory=list)
    errors: list[tuple[Path, str]] = field(default_factory=list)


@dataclass
class PreprocessResult:
    """Result of preprocessing a single file."""

    path: Path
    new_path: Path | None = None
    frontmatter_fixed: bool = False
    frontmatter_fix_types: list[str] = field(default_factory=list)
    url_cleaned: bool = False
    filename_renamed: bool = False
    date_prefix_added: bool = False
    date_source: str | None = None
    content_hash: str | None = None
    source_url: str | None = None
    error: str | None = None


def preprocess_file(
    path: Path,
    config: Config,
    dry_run: bool = False,
    no_url_clean: bool = False,
    no_filename_clean: bool = False,
    no_date_prefix: bool = False,
    no_frontmatter_fix: bool = False,
) -> PreprocessResult:
    """Preprocess a single markdown file.

    Args:
        path: Path to the markdown file.
        config: Application configuration.
        dry_run: If True, don't modify files.
        no_url_clean: Skip URL cleaning.
        no_filename_clean: Skip filename sanitization.
        no_date_prefix: Skip date prefix addition.
        no_frontmatter_fix: Skip frontmatter fixing.

    Returns:
        PreprocessResult with changes made.
    """
    result = PreprocessResult(path=path)

    try:
        content = path.read_text(encoding="utf-8")
    except OSError as e:
        result.error = f"Could not read file: {e}"
        return result

    # Parse frontmatter
    try:
        parsed = parse_frontmatter(content)
    except Exception as e:
        result.error = f"Could not parse frontmatter: {e}"
        return result

    modified = False
    new_frontmatter = dict(parsed.data)

    # Fix frontmatter issues
    if not no_frontmatter_fix and parsed.has_frontmatter and parsed.raw_frontmatter:
        fix_result = fix_frontmatter(parsed.raw_frontmatter)
        if fix_result.fixes:
            result.frontmatter_fixed = True
            result.frontmatter_fix_types = [f.fix_type for f in fix_result.fixes]
            # Re-parse the fixed frontmatter
            try:
                new_frontmatter = yaml.safe_load(fix_result.fixed_frontmatter) or {}
                modified = True
            except yaml.YAMLError:
                pass

    # Clean source URL
    source_url = get_source_url(new_frontmatter, config.frontmatter)
    if source_url:
        result.source_url = source_url
        if not no_url_clean:
            cleaned_url = clean_url(source_url, config.url_cleaning)
            if cleaned_url != source_url:
                # Update the URL in frontmatter
                for field_name in config.frontmatter.source_url:
                    if field_name in new_frontmatter:
                        new_frontmatter[field_name] = cleaned_url
                        break
                result.url_cleaned = True
                result.source_url = cleaned_url
                modified = True

    # Compute content hash
    result.content_hash = hash_content(parsed.content, config.cache.hash_length)

    # Check if filename needs date prefix
    filename = path.name
    new_filename = filename

    if not no_date_prefix and not has_date_prefix(filename):
        date_result = get_date_for_prefix(
            new_frontmatter,
            parsed.content,
            filename,
            config.dates,
        )
        if date_result.date:
            new_filename = add_date_prefix(
                filename,
                date_result.date,
                config.dates.output_format,
            )
            result.date_prefix_added = True
            result.date_source = date_result.source
            modified = True

    # Sanitize filename
    if not no_filename_clean:
        sanitized = sanitize_filename(new_filename, config.filenames)
        if sanitized != new_filename:
            new_filename = sanitized
            result.filename_renamed = True
            modified = True
        elif sanitize_filename(filename, config.filenames) != filename:
            # Original filename needed sanitization
            result.filename_renamed = True
            modified = True

    # Determine new path
    if new_filename != filename:
        result.new_path = path.parent / new_filename
    else:
        result.new_path = path

    # Apply changes if not dry run
    if not dry_run and modified:
        # Reconstruct file content
        new_content = serialize_frontmatter(new_frontmatter) + parsed.content

        # Write updated content
        try:
            path.write_text(new_content, encoding="utf-8")
        except OSError as e:
            result.error = f"Could not write file: {e}"
            return result

        # Rename file if needed
        if result.new_path and result.new_path != path:
            try:
                shutil.move(str(path), str(result.new_path))
            except OSError as e:
                result.error = f"Could not rename file: {e}"
                return result

    return result


def find_duplicates(
    results: list[PreprocessResult],
    cache: Cache | None = None,
) -> list[list[tuple[str, Path]]]:
    """Find duplicate articles by URL.

    Args:
        results: List of preprocess results.
        cache: Optional cache with existing entries.

    Returns:
        List of duplicate groups, each containing (url, path) tuples.
    """
    url_to_files: dict[str, list[Path]] = {}

    for result in results:
        if result.source_url and result.error is None:
            url = result.source_url
            path = result.new_path or result.path
            if url not in url_to_files:
                url_to_files[url] = []
            url_to_files[url].append(path)

    # Also check cache
    if cache:
        for url, paths in url_to_files.items():
            if cache.has_active_url(url):
                entry = cache.get(url)
                if entry:
                    # Check if cached file is different from current files
                    cached_path = Path(entry.folder or ".") / entry.filename
                    if cached_path not in paths:
                        paths.append(cached_path)

    # Find groups with more than one file
    duplicates = []
    for url, paths in url_to_files.items():
        if len(paths) > 1:
            duplicates.append([(url, p) for p in paths])

    return duplicates


def preprocess_directory(
    path: Path,
    config: Config,
    dry_run: bool = False,
    no_url_clean: bool = False,
    no_filename_clean: bool = False,
    no_date_prefix: bool = False,
    no_frontmatter_fix: bool = False,
    no_dedupe: bool = False,
) -> PreprocessStats:
    """Preprocess all markdown files in a directory.

    Args:
        path: Directory to process.
        config: Application configuration.
        dry_run: If True, don't modify files.
        no_url_clean: Skip URL cleaning.
        no_filename_clean: Skip filename sanitization.
        no_date_prefix: Skip date prefix addition.
        no_frontmatter_fix: Skip frontmatter fixing.
        no_dedupe: Skip duplicate detection.

    Returns:
        PreprocessStats with summary of changes.
    """
    stats = PreprocessStats()
    results: list[PreprocessResult] = []

    # Find all markdown files (excludes hidden, ignored files, and special folders)
    filtered_files = list(discover_markdown_files(path, config))
    stats.scanned = len(filtered_files)

    for md_file in filtered_files:
        result = preprocess_file(
            md_file,
            config,
            dry_run=dry_run,
            no_url_clean=no_url_clean,
            no_filename_clean=no_filename_clean,
            no_date_prefix=no_date_prefix,
            no_frontmatter_fix=no_frontmatter_fix,
        )
        results.append(result)

        if result.error:
            stats.errors.append((md_file, result.error))
            continue

        if result.frontmatter_fixed and not no_frontmatter_fix:
            stats.frontmatter_fixed += 1
            for fix_type in result.frontmatter_fix_types:
                stats.frontmatter_fixes[fix_type] = stats.frontmatter_fixes.get(fix_type, 0) + 1

        if result.url_cleaned and not no_url_clean:
            stats.urls_cleaned += 1

        if result.filename_renamed and not no_filename_clean:
            stats.filenames_renamed += 1

        if result.date_prefix_added and not no_date_prefix:
            stats.date_prefixes_added += 1
            if result.date_source == "frontmatter":
                stats.date_prefixes_from_frontmatter += 1
            elif result.date_source == "content":
                stats.date_prefixes_from_content += 1

    # Find duplicates
    if not no_dedupe:
        duplicates = find_duplicates(results)
        stats.duplicates_found = sum(len(group) for group in duplicates)
        stats.duplicate_groups = duplicates

    return stats


def format_preprocess_summary(
    stats: PreprocessStats,
    no_frontmatter_fix: bool = False,
    no_url_clean: bool = False,
    no_filename_clean: bool = False,
    no_date_prefix: bool = False,
    no_dedupe: bool = False,
) -> list[str]:
    """Format preprocessing summary for display.

    Args:
        stats: Preprocessing statistics.
        no_frontmatter_fix: If True, skip frontmatter section.
        no_url_clean: If True, skip URL cleaning section.
        no_filename_clean: If True, skip filename section.
        no_date_prefix: If True, skip date prefix section.
        no_dedupe: If True, skip duplicates section.

    Returns:
        List of formatted output lines.
    """
    lines = []

    lines.append("Preprocessing Summary")
    lines.append("=" * 21)
    lines.append(f"Scanned: {stats.scanned} files\n")

    if not no_frontmatter_fix:
        lines.append("Frontmatter fixing:")
        lines.append(f"  - Fixed: {stats.frontmatter_fixed}")
        for fix_type, count in stats.frontmatter_fixes.items():
            lines.append(f"    - {fix_type}: {count}")
        lines.append(f"  - Already valid: {stats.scanned - stats.frontmatter_fixed}\n")

    if not no_url_clean:
        lines.append("URL cleaning:")
        lines.append(f"  - Cleaned: {stats.urls_cleaned}")
        lines.append(f"  - Already clean: {stats.scanned - stats.urls_cleaned}\n")

    if not no_filename_clean:
        lines.append("Filename sanitization:")
        lines.append(f"  - Renamed: {stats.filenames_renamed}")
        lines.append(f"  - Already clean: {stats.scanned - stats.filenames_renamed}\n")

    if not no_date_prefix:
        lines.append("Date prefixes:")
        lines.append(f"  - Added: {stats.date_prefixes_added}")
        if stats.date_prefixes_from_frontmatter:
            lines.append(f"    - from frontmatter: {stats.date_prefixes_from_frontmatter}")
        if stats.date_prefixes_from_content:
            lines.append(f"    - from content: {stats.date_prefixes_from_content}")
        lines.append(f"  - Already prefixed: {stats.scanned - stats.date_prefixes_added}\n")

    if not no_dedupe and stats.duplicate_groups:
        lines.append(f"Duplicates found: {len(stats.duplicate_groups)} groups")
        for group in stats.duplicate_groups:
            url = group[0][0]
            lines.append(f"  - {url}")
            for _, file_path in group:
                lines.append(f"    - {file_path}")
        lines.append("  [Use --auto-remove-dupes or manually resolve]\n")

    if stats.errors:
        lines.append(f"\n[red]Errors: {len(stats.errors)}[/red]")
        for file_path, error in stats.errors:
            lines.append(f"  - {file_path}: {error}")

    ready_count = stats.scanned - len(stats.errors)
    lines.append(f"\nReady for categorization: {ready_count} files")

    return lines
