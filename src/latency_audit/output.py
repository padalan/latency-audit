"""
Rich console output formatting for latency-audit.

This module handles beautiful terminal output using the Rich library.
"""

import json
from typing import TYPE_CHECKING

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from latency_audit.models import CheckCategory, CheckStatus

if TYPE_CHECKING:
    from latency_audit.models import AuditReport, CheckResult

# Status indicators and colors
STATUS_ICONS: dict[CheckStatus, tuple[str, str]] = {
    CheckStatus.PASS: ("[PASS]", "green"),
    CheckStatus.FAIL: ("[FAIL]", "red"),
    CheckStatus.WARN: ("[WARN]", "yellow"),
    CheckStatus.SKIP: ("[SKIP]", "dim"),
}

CATEGORY_TITLES: dict[CheckCategory, str] = {
    CheckCategory.KERNEL: "KERNEL CONFIGURATION",
    CheckCategory.CPU: "CPU CONFIGURATION",
    CheckCategory.NETWORK: "NETWORK CONFIGURATION",
    CheckCategory.CLOCK: "CLOCK CONFIGURATION",
}


def print_header(console: Console, version: str) -> None:
    """Print the tool header."""
    console.print()
    console.print(
        Panel.fit(
            f"[bold cyan]latency-audit[/bold cyan] [dim]v{version}[/dim]\n"
            "[dim]HFT-grade Linux infrastructure validator[/dim]",
            border_style="cyan",
        )
    )
    console.print()


def print_check(console: Console, check: "CheckResult") -> None:
    """Print a single check result."""
    icon, color = STATUS_ICONS[check.status]
    value_text = str(check.current_value)

    # Build the output line
    line = Text()
    line.append(f"  {icon} ")
    line.append(check.name, style="bold")
    line.append(f" = {value_text}", style=color)

    if check.status == CheckStatus.FAIL and check.expected_value is not None:
        line.append(f" (should be: {check.expected_value})", style="dim")

    if check.latency_impact:
        line.append(f" [{check.latency_impact}]", style="red dim")

    console.print(line)


def print_category(
    console: Console, category: CheckCategory, checks: list["CheckResult"]
) -> None:
    """Print a category section with all its checks."""
    if not checks:
        return

    title = CATEGORY_TITLES.get(category, category.value.upper())
    console.print(Panel(title, style="bold white on blue", expand=True))

    for check in checks:
        print_check(console, check)

    console.print()


def print_summary(console: Console, report: "AuditReport") -> None:
    """Print the summary table."""
    table = Table(title="Audit Summary", expand=True, show_header=False)
    table.add_column("Metric", style="bold")
    table.add_column("Value", justify="right")

    # Score with color based on value
    score = report.score
    if score >= 80:
        score_style = "bold green"
    elif score >= 60:
        score_style = "bold yellow"
    else:
        score_style = "bold red"

    table.add_row("Score", f"[{score_style}]{score}/100[/{score_style}]")
    table.add_row("Passed", f"[green]{len(report.passed)}[/green]")
    table.add_row("Failed", f"[red]{len(report.failed)}[/red]")
    table.add_row("Warnings", f"[yellow]{len(report.warnings)}[/yellow]")

    console.print(table)
    console.print()


def print_report(console: Console, report: "AuditReport") -> None:
    """Print the full audit report in human-readable format."""
    print_header(console, report.version)

    # Group checks by category
    by_category: dict[CheckCategory, list[CheckResult]] = {}
    for check in report.checks:
        by_category.setdefault(check.category, []).append(check)

    # Print each category in order
    for category in CheckCategory:
        if category in by_category:
            print_category(console, category, by_category[category])

    print_summary(console, report)


def print_json(console: Console, report: "AuditReport") -> None:
    """Print the report as JSON."""
    console.print_json(json.dumps(report.to_dict(), indent=2))
