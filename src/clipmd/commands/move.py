"""Move command for clipmd."""

from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console

from clipmd.context import Context
from clipmd.core import mover

console = Console()


@click.command("move")
@click.argument(
    "categorization_file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be moved without moving",
)
@click.option(
    "--create-folders/--no-create-folders",
    default=True,
    help="Create folders if needed (default: true)",
)
@click.option(
    "--no-cache-update",
    is_flag=True,
    help="Skip cache update",
)
@click.option(
    "--source-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Source directory (default: config root)",
)
@click.pass_context
def move_command(
    ctx: click.Context,
    categorization_file: Path,
    dry_run: bool,
    create_folders: bool,
    no_cache_update: bool,
    source_dir: Path | None,
) -> None:
    """Move files based on a categorization file.

    The categorization file format is:
    1. Category - filename.md
    2. Another-Category - another-file.md
    3. TRASH - duplicate.md

    Use TRASH to move files to system trash.
    """
    cli_ctx: Context = ctx.find_object(Context)  # type: ignore[assignment]
    config = cli_ctx.config

    if config is None:
        console.print("[red]Error:[/red] No configuration loaded")
        raise SystemExit(1)

    # Use config root if source_dir not specified
    if source_dir is None:
        source_dir = config.paths.root

    # Display dry run message if applicable
    if dry_run:
        console.print("[yellow]Dry run - no files will be moved[/yellow]\n")

    # Execute move workflow
    result = mover.execute_move_workflow(
        categorization_file,
        source_dir,
        config,
        dry_run=dry_run,
        create_folders=create_folders,
        update_cache=not no_cache_update,
    )

    # Handle empty categorization file
    if result is None:
        console.print("[yellow]No valid move instructions found[/yellow]")
        return

    instructions, stats = result

    # Display results
    result_lines = mover.format_move_results(instructions, stats, dry_run=dry_run)
    for line in result_lines:
        console.print(line)

    # Show cache update message
    if not no_cache_update and not dry_run:
        console.print("Cache updated.")
