"""Duplicates command for clipmd."""

from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console

from clipmd.context import Context
from clipmd.core import duplicates

console = Console()


@click.command("duplicates")
@click.option(
    "--by-url",
    is_flag=True,
    help="Find by matching source URL",
)
@click.option(
    "--by-hash",
    is_flag=True,
    help="Find by content hash",
)
@click.option(
    "--by-filename",
    is_flag=True,
    help="Find by similar filename",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(dir_okay=False, path_type=Path),
    help="Output file",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["markdown", "json"]),
    default="markdown",
    help="Output format (default: markdown)",
)
@click.pass_context
def duplicates_command(
    ctx: click.Context,
    by_url: bool,
    by_hash: bool,
    by_filename: bool,
    output: Path | None,
    output_format: str,
) -> None:
    """Find duplicate articles.

    By default, searches by URL. Use flags to enable other detection methods.
    """
    cli_ctx: Context = ctx.find_object(Context)  # type: ignore[assignment]
    config = cli_ctx.config

    if config is None:
        console.print("[red]Error:[/red] No configuration loaded")
        raise SystemExit(1)

    root_dir = config.paths.root

    # Default to by-url if no method specified
    if not by_url and not by_hash and not by_filename:
        by_url = True

    result = duplicates.DuplicateResult()

    if by_url:
        console.print("[dim]Scanning for URL duplicates...[/dim]")
        result.by_url = duplicates.find_duplicates_by_url(root_dir, config)

    if by_hash:
        console.print("[dim]Scanning for content duplicates...[/dim]")
        result.by_hash = duplicates.find_duplicates_by_hash(root_dir, config)

    if by_filename:
        console.print("[dim]Scanning for filename duplicates...[/dim]")
        result.by_filename = duplicates.find_duplicates_by_filename(root_dir, config)

    # Format output
    if output_format == "json":
        output_text = duplicates.format_duplicates_json(result, root_dir)
    else:
        output_text = duplicates.format_duplicates_markdown(result, root_dir)

    # Write or print
    if output:
        output.write_text(output_text, encoding="utf-8")
        console.print(f"Duplicates saved to: {output}")
    else:
        console.print(output_text)

    # Summary
    total_groups = len(result.by_url) + len(result.by_hash) + len(result.by_filename)
    if total_groups > 0:
        console.print(f"\n[yellow]Found {total_groups} duplicate groups[/yellow]")
