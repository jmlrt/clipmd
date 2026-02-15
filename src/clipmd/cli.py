"""Click CLI entry point for clipmd."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.logging import RichHandler

from clipmd import __version__
from clipmd.context import Context
from clipmd.exceptions import ClipmdError

# Global console for user output
console = Console()
error_console = Console(stderr=True)


def setup_logging(verbosity: int) -> None:
    """Configure logging based on verbosity level.

    Args:
        verbosity: 0=WARNING, 1=INFO, 2+=DEBUG
    """
    level = {0: logging.WARNING, 1: logging.INFO, 2: logging.DEBUG}.get(verbosity, logging.DEBUG)
    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=[RichHandler(console=Console(stderr=True), show_time=False)],
    )


pass_context = click.make_pass_decorator(Context, ensure=True)


@click.group()
@click.option(
    "-v",
    "--verbose",
    count=True,
    help="Increase output verbosity (can be repeated: -vv)",
)
@click.option(
    "-q",
    "--quiet",
    is_flag=True,
    help="Suppress non-essential output",
)
@click.option(
    "--config",
    "config_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Use custom config file",
)
@click.option(
    "--vault",
    "vault_path",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Use specific vault directory (overrides default)",
)
@click.option(
    "--no-color",
    is_flag=True,
    help="Disable colored output",
)
@click.version_option(version=__version__, prog_name="clipmd")
@pass_context
def main(
    ctx: Context,
    verbose: int,
    quiet: bool,
    config_path: Path | None,
    vault_path: Path | None,
    no_color: bool,
) -> None:
    """clipmd - Clip, organize, and manage markdown articles.

    A CLI tool for saving, organizing, and managing markdown articles
    with YAML frontmatter. Designed to assist LLM-based workflows.
    """
    ctx.verbose = verbose
    ctx.quiet = quiet
    ctx.no_color = no_color
    ctx.vault_override = vault_path

    # Configure console colors
    if no_color:
        console.no_color = True
        error_console.no_color = True

    # Setup logging based on verbosity
    if not quiet:
        setup_logging(verbose)

    # Load config (will be used by subcommands)
    try:
        ctx.load_config(config_path)
        # Update paths.root to the resolved vault root
        if ctx.config is not None:
            ctx.config.paths.root = ctx.get_vault_root()
    except ClipmdError as e:
        error_console.print(f"[red]Error:[/red] {e}")
        sys.exit(e.exit_code)


@main.command()
@pass_context
def version(_ctx: Context) -> None:
    """Show version and exit."""
    console.print(f"clipmd {__version__}")


def register_commands() -> None:
    """Register all subcommands."""
    from clipmd.commands.duplicates import duplicates_command
    from clipmd.commands.extract import extract_command
    from clipmd.commands.fetch import fetch_command
    from clipmd.commands.init import init_command
    from clipmd.commands.move import move_command
    from clipmd.commands.preprocess import preprocess_command
    from clipmd.commands.stats import stats_command
    from clipmd.commands.trash import trash_command
    from clipmd.commands.validate import validate_command

    main.add_command(init_command)
    main.add_command(preprocess_command)
    main.add_command(extract_command)
    main.add_command(move_command)
    main.add_command(trash_command)
    main.add_command(fetch_command)
    main.add_command(stats_command)
    main.add_command(duplicates_command)
    main.add_command(validate_command)


# Register commands on import
register_commands()


if __name__ == "__main__":
    main()
