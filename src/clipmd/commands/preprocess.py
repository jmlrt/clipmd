"""Preprocess command for clipmd."""

from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console

from clipmd.context import Context
from clipmd.core import preprocessor

console = Console()


@click.command("preprocess")
@click.argument(
    "path",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=".",
)
@click.option("--dry-run", is_flag=True, help="Show what would be done")
@click.option("--no-url-clean", is_flag=True, help="Skip URL cleaning")
@click.option("--no-filename-clean", is_flag=True, help="Skip filename sanitization")
@click.option("--no-date-prefix", is_flag=True, help="Skip date prefix addition")
@click.option("--no-frontmatter-fix", is_flag=True, help="Skip frontmatter fixing")
@click.option("--no-dedupe", is_flag=True, help="Skip duplicate detection")
@click.pass_context
def preprocess_command(
    ctx: click.Context,
    path: Path,
    dry_run: bool,
    no_url_clean: bool,
    no_filename_clean: bool,
    no_date_prefix: bool,
    no_frontmatter_fix: bool,
    no_dedupe: bool,
) -> None:
    """Preprocess markdown articles.

    Cleans URLs, sanitizes filenames, adds date prefixes, and fixes frontmatter.
    """
    cli_ctx: Context = ctx.find_object(Context)  # type: ignore[assignment]
    config = cli_ctx.config

    if config is None:
        console.print("[red]Error:[/red] No configuration loaded")
        raise SystemExit(1)

    if dry_run:
        console.print("[yellow]Dry run - no files will be modified[/yellow]\n")

    stats = preprocessor.preprocess_directory(
        path,
        config,
        dry_run=dry_run,
        no_url_clean=no_url_clean,
        no_filename_clean=no_filename_clean,
        no_date_prefix=no_date_prefix,
        no_frontmatter_fix=no_frontmatter_fix,
        no_dedupe=no_dedupe,
    )

    # Display summary
    summary_lines = preprocessor.format_preprocess_summary(
        stats,
        no_frontmatter_fix=no_frontmatter_fix,
        no_url_clean=no_url_clean,
        no_filename_clean=no_filename_clean,
        no_date_prefix=no_date_prefix,
        no_dedupe=no_dedupe,
    )
    for line in summary_lines:
        console.print(line)
