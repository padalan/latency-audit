"""
CLI entry point for latency-audit.

This module provides the command-line interface using Click.
"""

import click

from latency_audit import __version__


@click.command()
@click.version_option(version=__version__, prog_name="latency-audit")
@click.option("--json", "output_json", is_flag=True, help="Output results as JSON")
def main(output_json: bool) -> None:
    """
    🔬 latency-audit: HFT-grade Linux infrastructure validator.

    Audits your Linux system against Tier 1 High-Frequency Trading
    latency standards. Read-only by default.
    """
    click.echo("⚡ latency-audit v" + __version__)
    click.echo("🚧 Audit logic coming soon...")

    if output_json:
        click.echo('{"status": "not_implemented"}')


if __name__ == "__main__":
    main()
