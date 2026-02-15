"""Extract command for clipmd."""

from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console

from clipmd.context import Context
from clipmd.core import extractor

console = Console()


@click.command("extract")
@click.argument(
    "path",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=".",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Output file (default: stdout)",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["markdown", "json", "yaml"]),
    default="markdown",
    help="Output format",
)
@click.option(
    "--max-chars",
    type=int,
    default=150,
    help="Max description/content chars",
)
@click.option(
    "--include-content/--no-content",
    default=True,
    help="Include content preview",
)
@click.option(
    "--include-stats",
    is_flag=True,
    help="Include word count and language",
)
@click.option(
    "--folders",
    is_flag=True,
    help="Include list of existing folders",
)
@click.pass_context
def extract_command(
    ctx: click.Context,
    path: Path,
    output: Path | None,
    output_format: str,
    max_chars: int,
    include_content: bool,
    include_stats: bool,
    folders: bool,
) -> None:
    """Extract metadata from articles into LLM-optimized format.

    Generates a compact metadata file for LLM consumption, reducing
    token usage by 95%+ compared to reading full articles.
    """
    cli_ctx: Context = ctx.find_object(Context)  # type: ignore[assignment]
    config = cli_ctx.config

    if config is None:
        console.print("[red]Error:[/red] No configuration loaded")
        raise SystemExit(1)

    # Extract metadata
    result = extractor.extract_metadata(
        path,
        config,
        max_chars=max_chars,
        include_content=include_content,
        include_stats=include_stats,
        include_folders=folders,
    )

    # Format output
    if output_format == "markdown":
        formatted = extractor.format_markdown(result, include_stats=include_stats)
    elif output_format == "json":
        formatted = extractor.format_json(result)
    else:
        formatted = extractor.format_yaml_output(result)

    # Write output
    if output:
        output.write_text(formatted, encoding="utf-8")
        console.print(f"Metadata written to {output}")
    else:
        console.print(formatted)
