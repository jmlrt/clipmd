"""Core logic for moving and organizing article files."""

from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from send2trash import send2trash

from clipmd.core.cache import load_cache
from clipmd.core.frontmatter import get_source_url, parse_frontmatter

if TYPE_CHECKING:
    from clipmd.config import Config


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


def parse_json_categorization(content: str) -> list[MoveInstruction]:
    """Parse a JSON categorization into move instructions.

    Expected format:
        [{"file": "filename.md", "folder": "Category"}, ...]

    Use "TRASH" as folder to send files to trash.

    Validates:
    - file: must be basename (no path separators), end with .md, no path traversal
    - folder: no path separators, no path traversal, no absolute paths

    Raises:
        ValueError: If JSON is invalid, missing required keys, fields have wrong types,
                    or contain invalid values (path traversal, separators, etc.).
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

        filename = item["file"]
        category = item["folder"]

        # Validate field types
        if not isinstance(filename, str):
            raise ValueError(f"Item {i}: 'file' must be a string, got {type(filename).__name__}")
        if not isinstance(category, str):
            raise ValueError(f"Item {i}: 'folder' must be a string, got {type(category).__name__}")

        # Validate filename: must be basename, end with .md, no path traversal
        if "/" in filename or "\\" in filename or ".." in filename:
            raise ValueError(
                f"Item {i}: 'file' must be a basename (no path separators or traversal): {filename}"
            )
        if not filename.endswith(".md"):
            raise ValueError(f"Item {i}: 'file' must end with .md: {filename}")

        # Validate folder: no path separators, no path traversal (unless TRASH)
        if category.upper() != "TRASH" and (
            "/" in category or "\\" in category or ".." in category
        ):
            raise ValueError(
                f"Item {i}: 'folder' must not contain path separators or traversal: {category}"
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
) -> MoveResult:
    """Execute a single move instruction.

    Args:
        instruction: The move instruction to execute.
        source_dir: Source directory containing the files.
        create_folders: Whether to create folders if they don't exist.
        dest_root: Root directory for destination (defaults to source_dir).

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
        result.error = "Destination file already exists"
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
                    stats.errors.append(
                        (instruction.filename, f"Destination already exists: {dest_path}")
                    )
                    continue
                stats.moved += 1
            continue

        # Execute the move
        result = execute_move(instruction, source_dir, create_folders, dest_root=dest_root)

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
                continue  # Move failed

            # Read frontmatter to get URL
            try:
                content = dest_file.read_text(encoding="utf-8")
                parsed = parse_frontmatter(content)
                url = get_source_url(parsed.data, config.frontmatter)
                if url:
                    cache.update_location(url, folder=instruction.category)
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
