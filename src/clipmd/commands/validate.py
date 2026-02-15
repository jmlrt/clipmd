"""Validate command for clipmd."""

from __future__ import annotations

import click
from rich.console import Console

from clipmd.context import Context
from clipmd.core import validator

console = Console()


@click.command("validate")
@click.option(
    "--fix",
    is_flag=True,
    help="Attempt to fix issues",
)
@click.pass_context
def validate_command(ctx: click.Context, fix: bool) -> None:  # noqa: ARG001
    """Validate configuration and setup.

    Checks that clipmd is properly configured and ready to use.
    """
    cli_ctx: Context = ctx.find_object(Context)  # type: ignore[assignment]

    # Get config path and loaded config from context if available
    config_path = None
    loaded_config = None
    if cli_ctx:
        if cli_ctx.config_path:
            # Config was loaded with explicit path, use that
            config_path = cli_ctx.config_path
        if cli_ctx.config:
            # Use already-loaded config (with resolved vault root)
            loaded_config = cli_ctx.config

    console.print("Validating clipmd setup...\n")

    report = validator.run_validation(config_path, loaded_config)

    # Display results
    for check in report.checks:
        icon = "[green]\u2713[/green]" if check.passed else "[red]\u2717[/red]"
        console.print(f"{icon} {check.message}")

        if check.details:
            if check.passed:
                console.print(f"  [yellow]\u26a0[/yellow] {check.details}")
            else:
                console.print(f"    {check.details}")

    # Summary
    console.print()
    if report.passed:
        warning_count = len(report.warnings)
        if warning_count > 0:
            console.print(f"[green]Validation passed[/green] with {warning_count} warning(s).")
        else:
            console.print("[green]Validation passed.[/green]")
    else:
        failure_count = len(report.failures)
        console.print(f"[red]Validation failed[/red] with {failure_count} error(s).")

        if fix:
            console.print("\n[dim]Attempting to fix issues...[/dim]")
            # For now, just suggest running init
            console.print("Run 'clipmd init' to create missing configuration.")

        raise SystemExit(1)
