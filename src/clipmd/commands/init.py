"""Init command for clipmd."""

from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console

from clipmd.config import get_xdg_config_path
from clipmd.core import initializer

console = Console()


@click.command("init")
@click.option(
    "--config",
    "config_path",
    type=click.Path(dir_okay=False, path_type=Path),
    help="Custom config location (default: config.yaml)",
)
@click.option(
    "--minimal",
    is_flag=True,
    help="Create minimal config only",
)
@click.option(
    "--force",
    is_flag=True,
    help="Overwrite existing config file",
)
@click.option(
    "--set-default/--no-set-default",
    default=True,
    help="Set this vault as the default (saved to ~/.config/clipmd/)",
)
def init_command(
    config_path: Path | None,
    minimal: bool,
    force: bool,
    set_default: bool,
) -> None:
    """Initialize clipmd in a directory.

    Creates a config file and .clipmd directory for cache and rules.
    By default, sets this vault as the default for all clipmd commands.
    """
    # Determine config path
    if config_path is None:
        config_path = Path("config.yaml")

    # Initialize vault
    try:
        result = initializer.initialize_vault(config_path, minimal, force, set_default)
    except FileExistsError as e:
        console.print(f"[yellow]{e}[/yellow]")
        console.print("Use --force to overwrite.")
        raise SystemExit(1) from e

    console.print(f"[green]Created config file:[/green] {result.config_path}")
    console.print(f"[green]Created directory:[/green] {result.clipmd_dir}/")

    # Show default vault message if set
    if result.vault_path:
        xdg_path = get_xdg_config_path()
        console.print(f"[green]Set as default vault:[/green] {result.vault_path}")
        console.print(f"[dim]  (saved to {xdg_path})[/dim]")

    # Show file count if found
    if result.markdown_file_count > 0:
        console.print(
            f"\n[dim]Found {result.markdown_file_count} markdown files in directory.[/dim]"
        )

    console.print("\n[bold]Next steps:[/bold]")
    console.print("  1. Review and customize config.yaml")
    console.print("  2. Run: clipmd preprocess")
    console.print("  3. Run: clipmd extract > articles-metadata.txt")
