"""File discovery utilities for clipmd."""

from __future__ import annotations

import fnmatch
from collections.abc import Iterator
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from clipmd.config import Config


def should_ignore_file(path: Path, config: Config) -> bool:
    """Check if a file should be ignored based on configuration.

    Criteria for ignoring:
    1. Hidden files (name starts with .)
    2. Files in the ignore_files list (e.g., README.md, CLAUDE.md)

    Args:
        path: Path to the file.
        config: Application configuration.

    Returns:
        True if the file should be ignored.
    """
    # Check if hidden file
    if path.name.startswith("."):
        return True

    # Check if in ignore list
    return path.name in config.special_folders.ignore_files


def should_exclude_folder(name: str, config: Config) -> bool:
    """Check if a folder should be excluded based on configuration.

    Args:
        name: Folder name.
        config: Application configuration.

    Returns:
        True if the folder should be excluded.
    """
    return any(
        fnmatch.fnmatch(name, pattern) for pattern in config.special_folders.exclude_patterns
    )


def is_in_excluded_folder(path: Path, root: Path, config: Config) -> bool:
    """Check if a file is inside an excluded folder.

    Args:
        path: Path to the file.
        root: Root directory.
        config: Application configuration.

    Returns:
        True if the file is in an excluded folder.
    """
    try:
        relative = path.relative_to(root)
        for part in relative.parts[:-1]:  # Exclude the filename itself
            if should_exclude_folder(part, config):
                return True
    except ValueError:
        # path is not relative to root
        pass
    return False


def discover_markdown_files(
    root: Path,
    config: Config,
    *,
    recursive: bool = True,
    include_special_folders: bool = False,
) -> Iterator[Path]:
    """Discover markdown files in a directory.

    Args:
        root: Root directory to search.
        config: Application configuration.
        recursive: Whether to search recursively.
        include_special_folders: Whether to include files in special folders.

    Yields:
        Paths to markdown files.
    """
    pattern = "**/*.md" if recursive else "*.md"

    for path in root.glob(pattern):
        # Skip ignored files
        if should_ignore_file(path, config):
            continue

        # Skip files in hidden directories
        try:
            relative = path.relative_to(root)
            if any(part.startswith(".") for part in relative.parts[:-1]):
                continue
        except ValueError:
            continue

        # Skip files in excluded folders (unless include_special_folders is True)
        if not include_special_folders and is_in_excluded_folder(path, root, config):
            continue

        yield path
