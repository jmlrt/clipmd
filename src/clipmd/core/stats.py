"""Core statistics collection and formatting logic."""

from __future__ import annotations

import fnmatch
import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import yaml
from rich.table import Table

from clipmd.core.discovery import should_ignore_file

if TYPE_CHECKING:
    from clipmd.config import Config


@dataclass
class FolderStats:
    """Statistics for a single folder."""

    name: str
    count: int
    warning: str | None = None


@dataclass
class Stats:
    """Overall statistics."""

    total_articles: int = 0
    total_folders: int = 0
    folders: list[FolderStats] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def is_excluded_folder(name: str, exclude_patterns: list[str]) -> bool:
    """Check if folder matches any exclusion pattern.

    Args:
        name: Folder name.
        exclude_patterns: List of patterns.

    Returns:
        True if folder should be excluded.
    """
    return any(fnmatch.fnmatch(name, pattern) for pattern in exclude_patterns)


def collect_folder_stats(
    root_dir: Path,
    config: Config,
    include_special: bool = False,
) -> Stats:
    """Collect folder statistics.

    Args:
        root_dir: Root articles directory.
        config: Application configuration.
        include_special: Whether to include special folders.

    Returns:
        Stats object with folder counts.
    """
    stats = Stats()
    folder_counts: Counter[str] = Counter()

    # Get exclusion patterns
    exclude_patterns = config.special_folders.exclude_patterns

    # Count articles in root
    root_count = 0
    for item in root_dir.iterdir():
        if item.is_file() and item.suffix == ".md" and not should_ignore_file(item, config):
            root_count += 1

    if root_count > 0:
        folder_counts["(root)"] = root_count

    # Count articles in folders
    for item in root_dir.iterdir():
        if not item.is_dir():
            continue
        if item.name.startswith("."):
            continue

        # Check if special folder
        if not include_special and is_excluded_folder(item.name, exclude_patterns):
            continue

        count = sum(
            1
            for f in item.iterdir()
            if f.is_file() and f.suffix == ".md" and not should_ignore_file(f, config)
        )
        if count > 0:
            folder_counts[item.name] = count

    # Sort by count (descending)
    sorted_folders = sorted(folder_counts.items(), key=lambda x: (-x[1], x[0]))

    # Get thresholds from config
    min_threshold = config.folders.warn_below
    max_threshold = config.folders.warn_above

    for folder_name, count in sorted_folders:
        warning = None
        if min_threshold is not None and count < min_threshold:
            warning = f"below threshold ({min_threshold})"
            stats.warnings.append(f"{folder_name} has only {count} articles")
        elif max_threshold is not None and count > max_threshold:
            warning = f"above threshold ({max_threshold})"
            stats.warnings.append(f"{folder_name} has {count} articles")

        stats.folders.append(
            FolderStats(
                name=folder_name,
                count=count,
                warning=warning,
            )
        )
        stats.total_articles += count

    stats.total_folders = len(stats.folders)

    return stats


def format_stats_table(stats: Stats) -> Table:
    """Format statistics as a table.

    Args:
        stats: Statistics to format.

    Returns:
        Formatted table.
    """
    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("Count", justify="right", style="cyan")
    table.add_column("Folder", style="bold")
    table.add_column("Warning", style="yellow")

    for folder in stats.folders:
        table.add_row(
            str(folder.count),
            f"{folder.name}/",
            f"⚠️  {folder.warning}" if folder.warning else "",
        )

    return table


def format_stats_json(stats: Stats) -> str:
    """Format statistics as JSON.

    Args:
        stats: Statistics to format.

    Returns:
        JSON string.
    """
    data = {
        "total_articles": stats.total_articles,
        "total_folders": stats.total_folders,
        "folders": [
            {
                "name": f.name,
                "count": f.count,
                "warning": f.warning,
            }
            for f in stats.folders
        ],
        "warnings": stats.warnings,
    }
    return json.dumps(data, indent=2)


def format_stats_yaml(stats: Stats) -> str:
    """Format statistics as YAML.

    Args:
        stats: Statistics to format.

    Returns:
        YAML string.
    """
    data = {
        "total_articles": stats.total_articles,
        "total_folders": stats.total_folders,
        "folders": [
            {
                "name": f.name,
                "count": f.count,
                "warning": f.warning,
            }
            for f in stats.folders
        ],
        "warnings": stats.warnings,
    }
    return yaml.dump(data, default_flow_style=False, sort_keys=False)
