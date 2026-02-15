"""Trash command for clipmd."""

from __future__ import annotations

import click
from rich.console import Console

from clipmd.context import Context
from clipmd.core import trash

console = Console()


@click.command("trash")
@click.argument("files", nargs=-1, required=True)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be trashed without trashing",
)
@click.option(
    "--no-cache-update",
    is_flag=True,
    help="Skip cache update",
)
@click.pass_context
def trash_command(
    ctx: click.Context,
    files: tuple[str, ...],
    dry_run: bool,
    no_cache_update: bool,
) -> None:
    """Move files to system trash.

    Files can be specified as paths or glob patterns.

    Examples:
        clipmd trash article.md
        clipmd trash "Folder/*.md"
        clipmd trash file1.md file2.md file3.md
    """
    cli_ctx: Context = ctx.find_object(Context)  # type: ignore[assignment]
    config = cli_ctx.config

    if config is None:
        console.print("[red]Error:[/red] No configuration loaded")
        raise SystemExit(1)

    # Expand glob patterns
    paths = trash.expand_glob_patterns(list(files), config.paths.root)

    if not paths:
        console.print("[yellow]No files match the specified patterns[/yellow]")
        return

    if dry_run:
        console.print("[yellow]Dry run - no files will be trashed[/yellow]\n")

    # Execute trash
    stats = trash.trash_files(
        paths,
        config,
        dry_run=dry_run,
        update_cache=not no_cache_update,
    )

    # Print results
    if stats.trashed > 0:
        if dry_run:
            console.print("Would trash:")
        else:
            console.print("Trashed:")

        error_paths = {p for p, _ in stats.errors}
        for path in paths:
            if path not in error_paths:
                console.print(f"  ✓ {path.name}")

    if stats.errors:
        console.print(f"\n[red]Errors ({len(stats.errors)}):[/red]")
        for path, error in stats.errors:
            console.print(f"  ✗ {path.name}: {error}")

    # Summary
    console.print(f"\nSummary: {stats.trashed} trashed")

    if not no_cache_update and not dry_run and stats.trashed > 0:
        console.print("Cache updated.")
