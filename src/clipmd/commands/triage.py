"""Triage command for clipmd."""

from __future__ import annotations

import click
from rich.console import Console

from clipmd.context import Context
from clipmd.core import triager

console = Console()


@click.command("triage")
@click.option(
    "--staging",
    metavar="FOLDER",
    help="Override staging folder (default: from config)",
)
@click.option(
    "--no-domain-rules",
    is_flag=True,
    help="Skip domain rule matching (move everything to staging)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would happen without moving files",
)
@click.pass_context
def triage_command(
    ctx: click.Context, staging: str | None, no_domain_rules: bool, dry_run: bool
) -> None:
    """Run fully automated article triage: fetch, preprocess, organize.

    Fetches RSS sources and INBOX.md, preprocesses articles, applies domain
    rules to organize them into folders, and moves unmatched articles to the
    staging folder for later LLM categorization.

    Examples:

        clipmd triage

        clipmd triage --no-domain-rules --dry-run

        clipmd triage --staging my-staging-folder
    """
    cli_ctx: Context = ctx.find_object(Context)  # type: ignore[assignment]
    config = cli_ctx.require_config()
    vault = cli_ctx.require_vault()

    effective_staging = staging or config.triage.staging_folder

    if dry_run:
        console.print("[yellow]Dry run - no files will be modified[/yellow]\n")

    result = triager.run_triage(
        config,
        vault,
        dry_run=dry_run,
        no_domain_rules=no_domain_rules,
        staging_folder=effective_staging,
    )

    for line in triager.format_triage_summary(result):
        console.print(line)

    if result.move.errors:
        console.print("\n[red]Move errors:[/red]")
        for error in result.move.errors[:5]:
            console.print(f"  - {error}")
        if len(result.move.errors) > 5:
            console.print(f"  ... and {len(result.move.errors) - 5} more")
        raise SystemExit(2)
