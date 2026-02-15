"""Core trash operations and file management logic."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from send2trash import send2trash

from clipmd.core.cache import load_cache

if TYPE_CHECKING:
    from clipmd.config import Config


@dataclass
class TrashResult:
    """Result of a single trash operation."""

    path: Path
    success: bool = False
    error: str | None = None


@dataclass
class TrashStats:
    """Statistics from trash operations."""

    total: int = 0
    trashed: int = 0
    errors: list[tuple[Path, str]] = field(default_factory=list)


def trash_file(path: Path) -> TrashResult:
    """Move a single file to system trash.

    Args:
        path: Path to the file to trash.

    Returns:
        TrashResult with the outcome.
    """
    result = TrashResult(path=path)

    if not path.exists():
        result.error = "File not found"
        return result

    try:
        send2trash(str(path))
        result.success = True
    except ImportError:
        result.error = "send2trash not installed"
    except Exception as e:
        result.error = f"Failed to trash: {e}"

    return result


def trash_files(
    paths: list[Path],
    config: Config,
    dry_run: bool = False,
    update_cache: bool = True,
) -> TrashStats:
    """Move multiple files to system trash.

    Args:
        paths: List of paths to trash.
        config: Application configuration.
        dry_run: If True, don't actually trash files.
        update_cache: Whether to update the cache.

    Returns:
        TrashStats with summary of operations.
    """
    stats = TrashStats(total=len(paths))
    successfully_trashed: list[Path] = []

    for path in paths:
        if dry_run:
            if path.exists():
                stats.trashed += 1
            else:
                stats.errors.append((path, "File not found"))
            continue

        result = trash_file(path)
        if result.success:
            stats.trashed += 1
            successfully_trashed.append(path)
        else:
            stats.errors.append((path, result.error or "Unknown error"))

    # Update cache only for successfully trashed files
    if update_cache and not dry_run and successfully_trashed:
        _update_cache_after_trash(successfully_trashed, config)

    return stats


def _update_cache_after_trash(paths: list[Path], config: Config) -> None:
    """Update cache after trashing files.

    Args:
        paths: List of paths that were trashed.
        config: Application configuration.
    """
    cache_path = config.paths.cache
    if not cache_path.is_absolute():
        cache_path = config.paths.root / cache_path

    cache = load_cache(cache_path)

    for path in paths:
        # Find by filename
        result = cache.find_by_filename(path.name)
        if result:
            url, entry = result
            cache.mark_removed(url)

    cache.save()


def expand_glob_patterns(patterns: list[str], base_dir: Path) -> list[Path]:
    """Expand glob patterns to file paths.

    Args:
        patterns: List of file patterns (may include globs).
        base_dir: Base directory for relative patterns.

    Returns:
        List of expanded file paths.
    """
    paths: list[Path] = []

    for pattern in patterns:
        # Check if it's a glob pattern
        if "*" in pattern or "?" in pattern:
            # Expand glob
            pat_path = Path(pattern)
            if pat_path.is_absolute():
                # For absolute patterns, glob relative to their own parent directory
                parent = pat_path.parent
                name_pattern = pat_path.name
                matches = list(parent.glob(name_pattern))
            else:
                # Relative patterns are interpreted relative to base_dir
                matches = list(base_dir.glob(pattern))
            # Filter to only files
            paths.extend(p for p in matches if p.is_file())
        else:
            # Regular file path
            path = Path(pattern)
            if not path.is_absolute():
                path = base_dir / path
            if path.is_file():
                paths.append(path)
            elif path.exists():
                # Skip directories
                continue
            else:
                # Include even if doesn't exist (will error later)
                paths.append(path)

    return paths
