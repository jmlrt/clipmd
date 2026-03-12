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
    type=click.Path(file_okay=False, path_type=Path),
    help="Source directory (default: config root)",
)
@click.option(
    "--skip-missing",
    is_flag=True,
    help="Skip missing source files instead of halting on error",
)
@click.pass_context
def move_command(
    ctx: click.Context,
    categorization_file: Path,
    dry_run: bool,
    create_folders: bool,
    no_cache_update: bool,
    source_dir: Path | None,
    skip_missing: bool,
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
    assert config is not None
    assert config.vault is not None

    # Track whether --source-dir was explicitly passed
    source_dir_explicit = source_dir is not None
    source_dir_is_relative = source_dir is not None and not source_dir.is_absolute()

    if source_dir is None:
        source_dir = config.vault
    elif source_dir_is_relative:
        # Normalize relative paths against vault
        source_dir = config.vault / source_dir

    # Validate that source directory exists and is a directory after normalization
    if not source_dir.exists():
        raise click.BadParameter(
            f"Source directory not found: {source_dir}",
            param_hint="--source-dir",
        )
    if not source_dir.is_dir():
        raise click.BadParameter(
            f"Source path is not a directory: {source_dir}",
            param_hint="--source-dir",
        )

    # Resolve both paths after existence is confirmed so that any `..` components
    # are eliminated before the containment check (lexical relative_to() can be
    # bypassed with paths like `root/../outside`).
    source_dir = source_dir.resolve()
    vault_root = config.vault.resolve()

    # Determine destination root for moves
    # Use vault root as destination when source_dir is a subdirectory of it
    dest_root = None
    if source_dir_explicit and source_dir != vault_root:
        # Check if source_dir is within vault root (subdirectory)
        try:
            source_dir.relative_to(vault_root)
            # If we get here, source_dir is within vault root
            dest_root = vault_root
        except ValueError:
            # source_dir is not within vault root (e.g., absolute temp path in tests)
            pass

    # Display dry run message if applicable
    if dry_run:
        console.print("[yellow]Dry run - no files will be moved[/yellow]\n")

    # Read and parse the categorization file
    file_content = categorization_file.read_text(encoding="utf-8")
    instructions = mover.parse_categorization_file(file_content)

    if not instructions:
        console.print("[yellow]No valid move instructions found[/yellow]")
        return

    # Pre-flight fuzzy folder check (skip in dry-run — just warn)
    suspicious = mover.find_suspicious_categories(instructions, source_dir, dest_root=dest_root)
    if suspicious:
        for bad_category, similar_existing in suspicious.items():
            if dry_run:
                console.print(
                    f"[yellow]Warning:[/yellow] New folder [bold]{bad_category}/[/bold] "
                    f"closely resembles existing folder [bold]{similar_existing}/[/bold]"
                )
            else:
                console.print(f"\n[yellow]⚠️  About to create new folder:[/yellow] {bad_category}/")
                console.print(f"   Similar existing folder found: [bold]{similar_existing}/[/bold]")
                action = click.prompt(
                    "   Action?",
                    type=click.Choice(["use-existing", "skip", "create-anyway"]),
                    default="use-existing",
                )
                if action == "use-existing":
                    for instr in instructions:
                        if instr.category == bad_category:
                            instr.category = similar_existing
                elif action == "skip":
                    instructions = [i for i in instructions if i.category != bad_category]

    if not instructions:
        console.print("[yellow]No valid move instructions remain after review[/yellow]")
        return

    # Execute moves
    move_stats = mover.execute_moves(
        instructions,
        source_dir,
        config,
        dry_run=dry_run,
        create_folders=create_folders,
        update_cache=not no_cache_update,
        dest_root=dest_root,
        skip_missing=skip_missing,
    )

    # Display results
    result_lines = mover.format_move_results(instructions, move_stats, dry_run=dry_run)
    for line in result_lines:
        console.print(line)

    # Show cache update message
    if not no_cache_update and not dry_run:
        console.print("Cache updated.")

    # If files were not found and --source-dir was not explicitly set,
    # search the vault for those files and suggest the right --source-dir
    # (unless --skip-missing was explicitly set)
    if not source_dir_explicit and not dry_run and not skip_missing:
        missing = [f for f, e in move_stats.errors if e == "File not found"]
        if missing:
            suggestions = mover.suggest_source_dir(missing, config.vault)
            if suggestions:
                dirs = ", ".join(f"[bold]{d}[/bold]" for d in suggestions)
                console.print(
                    f"\n[yellow]Hint:[/yellow] missing files found in {dirs} — "
                    f"try [bold]--source-dir {suggestions[0]}[/bold]"
                )
