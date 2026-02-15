"""Output formatting for fetch results."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from clipmd.core.fetcher import FetchOrchestrationResult


@dataclass
class FetchDisplayOptions:
    """Options for formatting fetch results."""

    output_format: str  # "text" or "json"
    dry_run: bool
    show_feed_info: bool = True
    show_skipped: bool = True


def format_fetch_text_output(
    orch_result: FetchOrchestrationResult,
    options: FetchDisplayOptions,
) -> list[str]:
    """Format fetch results as text output lines.

    Args:
        orch_result: Orchestration result with fetch data.
        options: Display options.

    Returns:
        List of formatted output lines for console.
    """
    lines = []
    process_result = orch_result.process_result
    stats = process_result.stats

    # Feed info
    if options.show_feed_info and orch_result.feed_entry_count is not None:
        lines.append(f"Found {orch_result.feed_entry_count} entries in feed")

    # Skipped URLs
    if options.show_skipped and orch_result.skipped_urls:
        for url in orch_result.skipped_urls:
            lines.append(f"[dim]Skipping (already saved): {url}[/dim]")

    # Early exit if nothing to fetch
    if not stats.total:
        if orch_result.skipped_urls:
            lines.append("[yellow]All URLs already saved[/yellow]")
        else:
            lines.append("[yellow]No URLs to fetch[/yellow]")
        return lines

    lines.append(f"Fetching {stats.total} URL(s)...\n")

    # Display saved files
    for saved_file in process_result.saved_files:
        if options.dry_run:
            lines.append(f"Would save: {saved_file.url}")
            lines.append(f"  Title: {saved_file.title or 'Unknown'}")
            lines.append(f"  Filename: {saved_file.filename}")
            lines.append("")
        else:
            lines.append(f"[green]✓[/green] {saved_file.url}")
            if saved_file.title:
                lines.append(f"  Title: {saved_file.title}")

            # Get additional info from fetch results
            fetch_result = next(
                (r for r in orch_result.fetch_results if r.url == saved_file.url),
                None,
            )
            if fetch_result:
                if fetch_result.author:
                    lines.append(f"  Author: {fetch_result.author}")
                if fetch_result.published:
                    lines.append(f"  Published: {fetch_result.published}")
            lines.append(f"  Saved: {saved_file.filename}")
            lines.append("")

    # Display errors
    for url, error in stats.errors:
        lines.append(f"[red]✗[/red] {url}: {error}")

    # Summary
    summary_parts = []
    if stats.saved > 0:
        summary_parts.append(f"{stats.saved} saved")
    if stats.errors:
        summary_parts.append(f"{len(stats.errors)} failed")

    if summary_parts:
        lines.append(f"\nSummary: {', '.join(summary_parts)}")

    return lines


def format_fetch_json_output(orch_result: FetchOrchestrationResult) -> str:
    """Format fetch results as JSON.

    Args:
        orch_result: Orchestration result with fetch data.

    Returns:
        JSON string.
    """
    stats = orch_result.process_result.stats
    output_data = {
        "total": stats.total,
        "saved": stats.saved,
        "errors": [{"url": url, "error": err} for url, err in stats.errors],
    }
    return json.dumps(output_data, indent=2)
