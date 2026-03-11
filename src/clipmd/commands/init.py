"""Init command for clipmd."""

from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console

from clipmd.config import get_xdg_config_home
from clipmd.core import initializer

console = Console()


@click.command("init")
@click.option(
    "--minimal",
    is_flag=True,
    help="Create minimal config (with defaults)",
)
@click.option(
    "--force",
    is_flag=True,
    help="Overwrite existing config file",
)
def init_command(
    minimal: bool,
    force: bool,
) -> None:
    """Initialize clipmd configuration.

    Creates the config file at ~/.config/clipmd/config.yaml and creates
    the .clipmd directory in the current directory for cache storage.

    The config file specifies:
    - vault: Path to your articles directory
    - cache: Path to the cache file
    - domain_rules: Optional domain-to-folder mappings
    """
    # Vault is the current directory
    vault_path = Path.cwd()

    # Config goes to ~/.config/clipmd/config.yaml
    xdg_config_home = get_xdg_config_home()
    config_path = xdg_config_home / "clipmd" / "config.yaml"

    # Initialize vault
    try:
        result = initializer.initialize_vault(
            vault_path=vault_path,
            config_path=config_path,
            minimal=minimal,
            force=force,
        )
    except FileExistsError as e:
        console.print(f"[yellow]{e}[/yellow]")
        console.print("Use --force to overwrite.")
        raise SystemExit(1) from e

    console.print(f"[green]✓ Created config file:[/green] {result.config_path}")
    console.print(f"[green]✓ Created vault directory:[/green] {result.clipmd_dir}/")

    # Show file count if found
    if result.markdown_file_count > 0:
        console.print(f"[dim]Found {result.markdown_file_count} markdown files in directory.[/dim]")

    console.print("\n[bold]Next steps:[/bold]")
    console.print("  1. Edit config file to customize:")
    console.print(f"     {config_path}")
    console.print("  2. Run: clipmd preprocess")
    console.print("  3. Run: clipmd extract --folders > articles-metadata.txt")
    console.print(f"\n[dim]Config file location: {config_path}[/dim]")
