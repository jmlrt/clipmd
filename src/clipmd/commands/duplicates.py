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
@click.option(
    "--auto-resolve",
    is_flag=True,
    help="Automatically resolve duplicates by trashing losers",
)
@click.option(
    "--strategy",
    type=click.Choice(["oldest-wins"]),
    default="oldest-wins",
    help="Resolution strategy (default: oldest-wins)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be done without trashing",
)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="Skip confirmation prompt",
)
@click.pass_context
def duplicates_command(
    ctx: click.Context,
    by_url: bool,
    by_hash: bool,
    by_filename: bool,
    output: Path | None,
    output_format: str,
    auto_resolve: bool,
    strategy: str,
    dry_run: bool,
    yes: bool,
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

    # Handle auto-resolve if requested
    if auto_resolve:
        # Restrict --auto-resolve to a single detection method to avoid overlapping groups
        methods_enabled = sum([by_url, by_hash, by_filename])
        if methods_enabled > 1:
            console.print(
                "[red]Error:[/red] --auto-resolve can only be used with one detection "
                "method (--by-url, --by-hash, or --by-filename), not multiple"
            )
            raise SystemExit(1)

        total_groups = len(result.by_url) + len(result.by_hash) + len(result.by_filename)
        if total_groups > 0:
            # Use the appropriate groups based on the single enabled method
            if result.by_url:
                combined_groups = result.by_url
            elif result.by_hash:
                combined_groups = result.by_hash
            else:
                combined_groups = result.by_filename

            # Show confirmation unless --yes was passed
            if not yes:
                console.print(
                    f"\n[yellow]Found {total_groups} duplicate groups to resolve:[/yellow]"
                )
                for group in combined_groups:
                    for file_path in group.files:
                        console.print(f"  - {file_path.relative_to(root_dir)}")
                if not click.confirm("\nResolve duplicates?"):
                    return

            # Resolve the duplicates
            resolve_stats = duplicates.resolve_duplicates(
                combined_groups,
                config,
                strategy=strategy,
                dry_run=dry_run,
            )

            # Print resolution summary
            console.print("")
            for _key, kept_path in resolve_stats.kept:
                rel_path = (
                    kept_path.relative_to(root_dir)
                    if kept_path.is_relative_to(root_dir)
                    else kept_path
                )
                console.print(f"  Kept: {rel_path}")

            if resolve_stats.trashed:
                console.print(f"\nTrashed {len(resolve_stats.trashed)} files")

            if resolve_stats.errors:
                console.print(f"\n[red]Errors ({len(resolve_stats.errors)}):[/red]")
                for path, error in resolve_stats.errors:
                    console.print(f"  ✗ {path}: {error}")

            if dry_run:
                console.print("\n[yellow](dry-run) No files were actually trashed[/yellow]")

            return

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
        click.echo(output_text)

    # Summary
    total_groups = len(result.by_url) + len(result.by_hash) + len(result.by_filename)
    if total_groups > 0:
        console.print(f"\n[yellow]Found {total_groups} duplicate groups[/yellow]")
