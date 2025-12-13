"""
CLI entry point for latency-audit.

This module provides the command-line interface using Click.
"""

import click
from rich.console import Console

# Import checks to register them
import latency_audit.checks  # noqa: F401
from latency_audit import __version__
from latency_audit.checks.process import set_target_pid
from latency_audit.models import CheckCategory
from latency_audit.output import print_json, print_report
from latency_audit.runner import run_audit


@click.command()
@click.version_option(version=__version__, prog_name="latency-audit")
@click.option("--json", "output_json", is_flag=True, help="Output results as JSON")
@click.option(
    "--category",
    "-c",
    type=click.Choice(["kernel", "cpu", "network", "clock", "hardware", "process"]),
    multiple=True,
    help="Filter by category (can be used multiple times)",
)
@click.option(
    "--pid",
    type=int,
    default=None,
    help="Target PID for process-specific checks (context switches, page faults)",
)
def main(output_json: bool, category: tuple[str, ...], pid: int | None) -> None:
    """
    latency-audit: HFT-grade Linux infrastructure validator.

    Audits your Linux system against Tier 1 High-Frequency Trading
    latency standards. Read-only, non-invasive.
    """
    console = Console()

    # Set target PID for process checks
    if pid is not None:
        set_target_pid(pid)

    # Convert category strings to enums
    categories = None
    if category:
        categories = [CheckCategory(c) for c in category]

    # Run the audit
    report = run_audit(categories)

    # Output results
    if output_json:
        print_json(console, report)
    else:
        print_report(console, report)


if __name__ == "__main__":
    main()
