"""Fetch command for clipmd."""

from __future__ import annotations

import asyncio
from pathlib import Path

import click
from rich.console import Console

from clipmd.context import Context
from clipmd.core import cache, fetcher, url_utils
from clipmd.core.formatters import (
    FetchDisplayOptions,
    format_fetch_json_output,
    format_fetch_text_output,
)
from clipmd.core.rss import validate_rss_mode

console = Console()


@click.command("fetch")
@click.argument("urls", nargs=-1)
@click.option(
    "--output",
    "-o",
    type=click.Path(file_okay=False, path_type=Path),
    help="Output directory (default: config root)",
)
@click.option(
    "--file",
    "-f",
    "url_file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Read URLs from file (one per line)",
)
@click.option(
    "--rss",
    is_flag=True,
    help="Treat URL as RSS/Atom feed",
)
@click.option(
    "--rss-limit",
    type=int,
    default=10,
    help="Max entries to fetch from feed (default: 10)",
)
@click.option(
    "--check-duplicates/--no-check-duplicates",
    default=True,
    help="Skip URLs already in cache (default: true)",
)
@click.option(
    "--no-readability",
    is_flag=True,
    help="Keep full HTML, don't extract main content",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be fetched without saving",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output info format (default: text)",
)
@click.option(
    "--no-cache-update",
    is_flag=True,
    help="Skip cache update",
)
@click.pass_context
def fetch_command(
    ctx: click.Context,
    urls: tuple[str, ...],
    output: Path | None,
    url_file: Path | None,
    rss: bool,
    rss_limit: int,
    check_duplicates: bool,
    no_readability: bool,
    dry_run: bool,
    output_format: str,
    no_cache_update: bool,
) -> None:
    """Fetch URLs and convert to markdown with YAML frontmatter.

    Fetches web pages, extracts main content using readability,
    and saves as markdown files with proper frontmatter.

    Examples:

        clipmd fetch "https://example.com/article"

        clipmd fetch -f urls.txt

        clipmd fetch --rss "https://example.com/feed.xml"
    """
    cli_ctx: Context = ctx.find_object(Context)  # type: ignore[assignment]
    config = cli_ctx.config

    if config is None:
        console.print("[red]Error:[/red] No configuration loaded")
        raise SystemExit(1)

    # Determine output directory
    output_dir = output or config.paths.root

    # Quick checks
    if not urls and not url_file:
        console.print("[yellow]No URLs provided[/yellow]")
        return

    # Validate RSS mode (exactly one URL)
    if rss:
        all_urls_for_validation = list(urls)
        if url_file:
            all_urls_for_validation.extend(url_utils.read_urls_from_file(url_file))

        is_valid, error_msg = validate_rss_mode(all_urls_for_validation)
        if not is_valid:
            console.print(f"[red]Error:[/red] {error_msg}")
            raise SystemExit(1)

    # Show progress messages if text format
    if output_format == "text":
        if rss and urls:
            console.print(f"Fetching RSS feed: {urls[0]}")
        if dry_run:
            console.print("[yellow]Dry run - no files will be saved[/yellow]\n")

    # Orchestrate fetch workflow
    try:
        orch_result = asyncio.run(
            fetcher.orchestrate_fetch(
                urls,
                url_file,
                config,
                output_dir,
                rss=rss,
                rss_limit=rss_limit,
                check_duplicates=check_duplicates,
                use_readability=not no_readability,
                dry_run=dry_run,
            )
        )
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1) from e

    # Format and display output
    if output_format == "json":
        formatted = format_fetch_json_output(orch_result)
        console.print(formatted)
    else:
        display_options = FetchDisplayOptions(
            output_format=output_format,
            dry_run=dry_run,
        )
        lines = format_fetch_text_output(orch_result, display_options)
        for line in lines:
            console.print(line)

    # Update cache
    stats = orch_result.process_result.stats
    if not dry_run and not no_cache_update and stats.saved > 0:
        cache.update_cache_after_fetch(orch_result.fetch_results, config)
        if output_format == "text":
            console.print("Cache updated.")
