"""Stats command for clipmd."""

from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console

from clipmd.context import Context
from clipmd.core import stats

console = Console()


@click.command("stats")
@click.argument(
    "path",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    required=False,
    default=None,
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["table", "json", "yaml"]),
    default="table",
    help="Output format (default: table)",
)
@click.option(
    "--warnings-only",
    is_flag=True,
    help="Only show folders outside thresholds",
)
@click.option(
    "--include-special",
    is_flag=True,
    help="Include special folders (0-*, etc.)",
)
@click.pass_context
def stats_command(
    ctx: click.Context,
    path: Path | None,
    output_format: str,
    warnings_only: bool,
    include_special: bool,
) -> None:
    """Display folder statistics for PATH (default: vault root).

    Shows article counts per folder with warnings for folders
    outside the configured min/max thresholds.
    """
    cli_ctx: Context = ctx.find_object(Context)  # type: ignore[assignment]
    config = cli_ctx.config

    if config is None:
        console.print("[red]Error:[/red] No configuration loaded")
        raise SystemExit(1)

    target_path = path or config.paths.root
    folder_stats = stats.collect_folder_stats(target_path, config, include_special)

    if warnings_only:
        folder_stats.folders = [f for f in folder_stats.folders if f.warning]

    if output_format == "json":
        console.print(stats.format_stats_json(folder_stats))
    elif output_format == "yaml":
        console.print(stats.format_stats_yaml(folder_stats))
    else:
        # Table format
        console.print(
            f"Folder Statistics ({folder_stats.total_articles} articles in "
            f"{folder_stats.total_folders} folders)\n"
        )
        console.print(stats.format_stats_table(folder_stats))

        if folder_stats.warnings:
            console.print(
                f"\nWarnings: {len(folder_stats.warnings)} folders outside "
                f"{config.folders.warn_below}-{config.folders.warn_above} range"
            )
