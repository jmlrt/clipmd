"""Core logic for moving and organizing article files."""

from __future__ import annotations

import contextlib
import hashlib
import json
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from send2trash import send2trash

from clipmd.core.cache import load_cache
from clipmd.core.frontmatter import get_source_url, get_title, parse_frontmatter
from clipmd.core.rules import match_domain
from clipmd.core.sanitizer import extract_domain

if TYPE_CHECKING:
    from clipmd.config import Config


def _are_files_identical(source_path: Path, dest_path: Path) -> bool | None:
    """Compare two files by SHA256 hash. Returns True if identical, False if different, None on error."""
    try:

        def file_hash(path: Path) -> str:
            """Compute SHA256 hash of file content (chunked for memory efficiency)."""
            hash_obj = hashlib.sha256()
            with open(path, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    hash_obj.update(chunk)
            return hash_obj.hexdigest()

        return file_hash(source_path) == file_hash(dest_path)
    except OSError:
        return None


@dataclass
class MoveInstruction:
    """A single move instruction from the categorization file."""

    index: int
    category: str
    filename: str
    line_number: int
    is_trash: bool = False


@dataclass
class MoveResult:
    """Result of a single move operation."""

    filename: str
    source: Path
    destination: Path | None = None
    success: bool = False
    error: str | None = None
    trashed: bool = False
    folder_created: bool = False
    removed_duplicate: bool = False


@dataclass
class MoveStats:
    """Statistics from move operations."""

    total: int = 0
    moved: int = 0
    trashed: int = 0
    folders_created: list[str] = field(default_factory=list)
    errors: list[tuple[str, str]] = field(default_factory=list)
    skipped: int = 0
    skipped_files: list[str] = field(default_factory=list)


def parse_categorization_file(content: str) -> list[MoveInstruction]:
    """Parse a categorization file into move instructions.

    Supported formats:
    - "1. Category - filename.md"
    - "1. Category - filename.md  # comment"
    - "Category - filename.md"
    - "TRASH - filename.md"

    Args:
        content: Content of the categorization file.

    Returns:
        List of MoveInstruction objects.
    """
    instructions = []

    # Pattern: optional index, category, dash, filename
    # Examples:
    #   1. Tech - 20240115-Article.md
    #   Tech - article.md
    #   TRASH - duplicate.md
    pattern = re.compile(r"^\s*(?:(\d+)\.\s+)?([A-Za-z0-9_-]+)\s*-\s*(\S+\.md)\s*(?:#.*)?$")

    for line_num, line in enumerate(content.splitlines(), start=1):
        # Skip comments and empty lines
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        match = pattern.match(line)
        if match:
            index_str, category, filename = match.groups()
            index = int(index_str) if index_str else line_num
            is_trash = category.upper() == "TRASH"

            instructions.append(
                MoveInstruction(
                    index=index,
                    category=category,
                    filename=filename,
                    line_number=line_num,
                    is_trash=is_trash,
                )
            )

    return instructions


def apply_domain_rules_fallback(
    source_dir: Path,
    config: Config,
    mapped_files: set[str],
) -> list[MoveInstruction]:
    """Apply domain rules to unmapped articles as a fallback.

    Scans for articles in source_dir that aren't in the categorization file,
    extracts their URLs, and applies domain rules from config. Creates
    MoveInstructions for articles that match a domain rule.

    Args:
        source_dir: Source directory containing articles.
        config: Application configuration with domain rules.
        mapped_files: Set of filenames already in the categorization file.

    Returns:
        List of MoveInstructions for articles with matching domain rules.
    """
    if not config.domain_rules:
        return []

    fallback_instructions: list[MoveInstruction] = []
    index_offset = 10000  # Use high index numbers for fallback

    # Find all markdown files in source_dir
    for md_file in sorted(source_dir.glob("*.md")):
        if md_file.name in mapped_files:
            continue  # Skip already mapped files

        # Skip configured ignored files
        ignore_files = getattr(getattr(config, "special_folders", None), "ignore_files", [])
        if md_file.name in ignore_files:
            continue

        # Extract URL from frontmatter
        try:
            content = md_file.read_text(encoding="utf-8")
            parsed = parse_frontmatter(content)
            url = get_source_url(parsed.data, config.frontmatter)

            if not url:
                continue

            # Extract domain and apply rules
            domain = extract_domain(url)
            folder = match_domain(domain, config.domain_rules)

            if folder:
                # Validate folder using same constraints as categorization parser
                # to prevent path traversal or invalid paths
                if not re.fullmatch(r"[A-Za-z0-9_-]+", folder):
                    continue  # Skip invalid rule outputs

                instruction = MoveInstruction(
                    index=index_offset,
                    category=folder,
                    filename=md_file.name,
                    line_number=-1,  # Negative to indicate fallback
                    is_trash=False,
                )
                fallback_instructions.append(instruction)
                index_offset += 1
        except (OSError, UnicodeDecodeError):
            # Skip files that can't be read or decoded
            pass

    return fallback_instructions


def parse_json_categorization(content: str) -> list[MoveInstruction]:
    """Parse a JSON categorization into move instructions.

    Expected format:
        [{"file": "filename.md", "folder": "Category"}, ...]

    Use "TRASH" as folder to send files to trash.

    Raises:
        ValueError: If JSON is invalid, missing required keys, or values contain
                    path separators or traversal sequences.
    """
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}") from e

    if not isinstance(data, list):
        raise ValueError("JSON must be a list of objects")

    instructions = []
    for i, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Item {i} must be an object, got {type(item).__name__}")
        if "file" not in item or "folder" not in item:
            raise ValueError(f"Item {i} missing required keys: 'file' and 'folder'")

        filename = str(item["file"]).strip()
        category = str(item["folder"]).strip()

        # Validate filename: must be basename (no path separators)
        if "/" in filename or "\\" in filename:
            raise ValueError(
                f"Item {i}: 'file' must be a basename (no path separators): {filename}"
            )

        # Validate folder: must match same pattern as plain-text parser (unless TRASH)
        # Pattern: [A-Za-z0-9_-]+ — letters, digits, underscores, hyphens only
        if category.upper() != "TRASH" and not re.fullmatch(r"[A-Za-z0-9_-]+", category):
            raise ValueError(
                f"Item {i}: 'folder' must contain only letters, digits, underscores, "
                f"and hyphens (got: {category!r})"
            )

        instructions.append(
            MoveInstruction(
                index=i,
                category=category,
                filename=filename,
                line_number=i,
                is_trash=category.upper() == "TRASH",
            )
        )

    return instructions


def suggest_source_dir(missing_filenames: list[str], vault_root: Path) -> list[str]:
    """Find subdirectories that contain files reported as missing in source_dir.

    Used to suggest a `--source-dir` value when all or most files in a
    categorization file are not found at the vault root.

    Args:
        missing_filenames: Filenames that were not found in source_dir.
        vault_root: Root of the vault to search under.

    Returns:
        Sorted list of relative subdirectory names (e.g. ["Inbox", "Clippings"])
        that contain at least one of the missing files.
    """
    found_dirs: set[str] = set()
    for filename in missing_filenames:
        for match in vault_root.rglob(filename):
            # Only consider direct children of vault_root (one level deep)
            try:
                rel = match.relative_to(vault_root)
                if len(rel.parts) == 2:  # subdir/filename
                    found_dirs.add(rel.parts[0])
            except ValueError:
                pass
    return sorted(found_dirs)


def _levenshtein_distance(s1: str, s2: str) -> int:
    """Compute Levenshtein edit distance between two strings.

    Args:
        s1: First string.
        s2: Second string.

    Returns:
        Number of single-character edits (insert/delete/replace) to transform s1 into s2.
    """
    m, n = len(s1), len(s2)
    dp = list(range(n + 1))
    for i in range(1, m + 1):
        prev = dp[0]
        dp[0] = i
        for j in range(1, n + 1):
            temp = dp[j]
            if s1[i - 1] == s2[j - 1]:
                dp[j] = prev
            else:
                dp[j] = 1 + min(prev, dp[j], dp[j - 1])
            prev = temp
    return dp[n]


def find_suspicious_categories(
    instructions: list[MoveInstruction],
    source_dir: Path,
    max_distance: int = 2,
    dest_root: Path | None = None,
) -> dict[str, str]:
    """Find new category names that closely resemble existing folder names.

    Args:
        instructions: List of move instructions.
        source_dir: Source directory to check for existing folders.
        max_distance: Maximum Levenshtein distance to consider suspicious.
        dest_root: Root directory to check for existing folders (defaults to source_dir).

    Returns:
        Dict mapping suspicious new category name → closest existing folder name.
    """
    check_dir = dest_root or source_dir
    existing_folders = {d.name for d in check_dir.iterdir() if d.is_dir()}
    suspicious: dict[str, str] = {}

    unique_categories = {i.category for i in instructions if not i.is_trash}
    for category in unique_categories:
        if category in existing_folders:
            continue  # Exact match — not suspicious
        best_match: str | None = None
        best_dist = max_distance + 1
        for folder in existing_folders:
            dist = _levenshtein_distance(category, folder)
            if dist <= max_distance and dist < best_dist:
                best_dist = dist
                best_match = folder
        if best_match is not None:
            suspicious[category] = best_match

    return suspicious


def execute_move(
    instruction: MoveInstruction,
    source_dir: Path,
    create_folders: bool = True,
    dest_root: Path | None = None,
    dry_run: bool = False,
) -> MoveResult:
    """Execute a single move instruction.

    Args:
        instruction: The move instruction to execute.
        source_dir: Source directory containing the files.
        create_folders: Whether to create folders if they don't exist.
        dest_root: Root directory for destination (defaults to source_dir).
        dry_run: If True, don't actually move/delete files.

    Returns:
        MoveResult with the outcome.
    """
    result = MoveResult(
        filename=instruction.filename,
        source=source_dir / instruction.filename,
    )

    # Check if source file exists
    if not result.source.exists():
        result.error = "File not found"
        return result

    if instruction.is_trash:
        # Move to system trash
        try:
            send2trash(str(result.source))
            result.success = True
            result.trashed = True
        except ImportError:
            result.error = "send2trash not installed"
        except Exception as e:
            result.error = f"Failed to trash: {e}"
        return result

    # Move to category folder
    dest_folder = (dest_root or source_dir) / instruction.category

    # Create folder if needed
    if not dest_folder.exists():
        if create_folders:
            try:
                dest_folder.mkdir(parents=True)
                result.folder_created = True
            except OSError as e:
                result.error = f"Failed to create folder: {e}"
                return result
        else:
            result.error = f"Folder does not exist: {instruction.category}"
            return result

    # Move the file
    result.destination = dest_folder / instruction.filename

    # Check if destination already exists
    if result.destination.exists():
        # Compare files to see if they're duplicates
        identical = _are_files_identical(result.source, result.destination)

        if identical is None:
            # Error comparing files
            result.error = "Failed to compare files"
            return result
        elif identical:
            # Files are identical - send source to trash (not permanent delete)
            if not dry_run:
                send2trash(str(result.source))
            result.success = True
            result.removed_duplicate = True
            return result
        else:
            # Files differ - this is a real conflict
            result.error = "Destination file already exists (content differs)"
            return result

    try:
        shutil.move(str(result.source), str(result.destination))
        result.success = True
    except OSError as e:
        result.error = f"Failed to move: {e}"

    return result


def execute_moves(
    instructions: list[MoveInstruction],
    source_dir: Path,
    config: Config,
    dry_run: bool = False,
    create_folders: bool = True,
    update_cache: bool = True,
    dest_root: Path | None = None,
    skip_missing: bool = False,
) -> MoveStats:
    """Execute all move instructions.

    Args:
        instructions: List of move instructions.
        source_dir: Source directory containing the files.
        config: Application configuration.
        dry_run: If True, don't actually move files.
        create_folders: Whether to create folders if they don't exist.
        update_cache: Whether to update the cache after moving.
        dest_root: Root directory for destination (defaults to source_dir).
        skip_missing: If True, skip missing files with a warning instead of error.

    Returns:
        MoveStats with summary of operations.
    """
    stats = MoveStats(total=len(instructions))

    # Track created folders
    created_folders: set[str] = set()

    for instruction in instructions:
        if dry_run:
            # Just check if the move would succeed
            source = source_dir / instruction.filename
            if not source.exists():
                if skip_missing:
                    stats.skipped += 1
                    stats.skipped_files.append(instruction.filename)
                else:
                    stats.errors.append((instruction.filename, "File not found"))
                continue

            if instruction.is_trash:
                stats.trashed += 1
            else:
                dest_folder = (dest_root or source_dir) / instruction.category
                if not dest_folder.exists() and instruction.category not in created_folders:
                    if create_folders:
                        created_folders.add(instruction.category)
                        stats.folders_created.append(instruction.category)
                    else:
                        stats.errors.append(
                            (instruction.filename, f"Folder does not exist: {instruction.category}")
                        )
                        continue
                # Mirror execute_move() validations
                if dest_folder.exists() and not dest_folder.is_dir():
                    stats.errors.append(
                        (instruction.filename, f"Destination is not a directory: {dest_folder}")
                    )
                    continue
                dest_path = dest_folder / instruction.filename
                if dest_path.exists():
                    # Check if it's a duplicate (same content) - if so, it will succeed
                    identical = _are_files_identical(source, dest_path)
                    if identical is None:
                        # Error comparing files - report it
                        stats.errors.append((instruction.filename, "Failed to compare files"))
                        continue
                    elif not identical:
                        # Files differ - this is a real conflict
                        stats.errors.append(
                            (instruction.filename, "Destination already exists (content differs)")
                        )
                        continue
                    # If identical, dry-run succeeds (source gets removed)
                    stats.moved += 1
                    continue
                stats.moved += 1
            continue

        # Execute the move
        result = execute_move(
            instruction, source_dir, create_folders, dest_root=dest_root, dry_run=dry_run
        )

        if result.success:
            if result.trashed:
                stats.trashed += 1
            else:
                stats.moved += 1
                if result.folder_created and instruction.category not in created_folders:
                    created_folders.add(instruction.category)
                    stats.folders_created.append(instruction.category)
        else:
            if skip_missing and result.error == "File not found":
                stats.skipped += 1
                stats.skipped_files.append(instruction.filename)
            else:
                stats.errors.append((instruction.filename, result.error or "Unknown error"))

    # Update cache if requested
    if update_cache and not dry_run:
        _update_cache_after_moves(instructions, source_dir, config, dest_root=dest_root)

    return stats


def _update_cache_after_moves(
    instructions: list[MoveInstruction],
    source_dir: Path,
    config: Config,
    dest_root: Path | None = None,
) -> None:
    """Update cache after moves.

    Args:
        instructions: List of move instructions that were executed.
        source_dir: Source directory.
        config: Application configuration.
        dest_root: Root directory for destination (defaults to source_dir).
    """
    cache_path = config.cache
    cache = load_cache(cache_path)

    for instruction in instructions:
        if instruction.is_trash:
            # Find URL and mark as removed
            source_file = source_dir / instruction.filename
            if source_file.exists():
                continue  # File wasn't actually trashed

            # Try to find in cache by filename
            result = cache.find_by_filename(instruction.filename)
            if result:
                url, _entry = result
                cache.mark_removed(url)
        else:
            # Update location in cache
            dest_file = (dest_root or source_dir) / instruction.category / instruction.filename
            if not dest_file.exists():
                continue  # Move truly failed (dest doesn't exist)

            # Read frontmatter to get URL. If dest file is unreadable/corrupt, skip
            # both the cache update and the source trash (conservative: prefer not
            # losing data over cleaning up the stale source).
            try:
                content = dest_file.read_text(encoding="utf-8")
                parsed = parse_frontmatter(content)
                url = get_source_url(parsed.data, config.frontmatter)
                if url:
                    updated = cache.update_location(url)
                    if updated is None:
                        # URL not in cache: article was organized outside clipmd or before
                        # caching was implemented. Add it now to prevent re-fetching.
                        title = get_title(parsed.data, config.frontmatter) or dest_file.stem
                        cache.add(
                            url=url,
                            filename=dest_file.name,
                            title=title,
                        )

                # If source file still exists, the move was blocked by an existing destination.
                # Trash the source — the organized destination is the canonical version.
                source_file = source_dir / instruction.filename
                if source_file.exists():
                    with contextlib.suppress(Exception):
                        send2trash(str(source_file))
            except Exception:
                pass

    cache.save()


def format_move_results(
    instructions: list[MoveInstruction],
    stats: MoveStats,
    dry_run: bool = False,
) -> list[str]:
    """Format move results for display.

    Args:
        instructions: List of move instructions that were executed.
        stats: Statistics from move operations.
        dry_run: If True, use "Would" phrasing instead of past tense.

    Returns:
        List of formatted output lines.
    """
    lines = []

    # Folders created
    if stats.folders_created:
        lines.append("Created folders:")
        for folder in stats.folders_created:
            lines.append(f"  - {folder}/")
        lines.append("")

    # Files moved or would be moved
    if stats.moved > 0 or stats.trashed > 0:
        if dry_run:
            lines.append("Would move:")
        else:
            lines.append("Moved:")

        error_filenames = {e[0] for e in stats.errors}
        skipped_filenames = set(stats.skipped_files)
        for instruction in instructions:
            if (
                instruction.filename not in error_filenames
                and instruction.filename not in skipped_filenames
            ):
                if instruction.is_trash:
                    lines.append(f"  ✓ {instruction.filename} → Trash")
                else:
                    lines.append(f"  ✓ {instruction.filename} → {instruction.category}/")

    # Errors
    if stats.errors:
        lines.append(f"\n[red]Errors ({len(stats.errors)}):[/red]")
        for filename, error in stats.errors:
            lines.append(f"  ✗ {filename}: {error}")

    # Skipped files
    if stats.skipped > 0:
        lines.append(f"\n[yellow]WARN: {stats.skipped} files skipped (not found)[/yellow]")

    # Summary
    summary_parts = []
    if stats.moved > 0:
        summary_parts.append(f"{stats.moved} moved")
    if stats.trashed > 0:
        summary_parts.append(f"{stats.trashed} trashed")
    if stats.folders_created:
        summary_parts.append(f"{len(stats.folders_created)} folders created")
    if stats.skipped > 0:
        summary_parts.append(f"{stats.skipped} skipped")

    if summary_parts:
        lines.append(f"\nSummary: {', '.join(summary_parts)}")

    return lines


def execute_move_workflow(
    categorization_file: Path,
    source_dir: Path,
    config: Config,
    dry_run: bool = False,
    create_folders: bool = True,
    update_cache: bool = True,
) -> tuple[list[MoveInstruction], MoveStats] | None:
    """Execute complete move workflow from categorization file.

    Reads file, parses instructions, executes moves, and updates cache.

    Args:
        categorization_file: Path to categorization file.
        source_dir: Source directory containing files.
        config: Application configuration.
        dry_run: If True, don't actually move files.
        create_folders: Whether to create folders if needed.
        update_cache: Whether to update cache after moves.

    Returns:
        Tuple of (instructions, stats) or None if no valid instructions.
    """
    # Read and parse categorization file
    content = categorization_file.read_text(encoding="utf-8")
    instructions = parse_categorization_file(content)

    if not instructions:
        return None

    # Execute moves
    stats = execute_moves(
        instructions,
        source_dir,
        config,
        dry_run=dry_run,
        create_folders=create_folders,
        update_cache=update_cache,
    )

    return instructions, stats
