"""
Audit runner that orchestrates all checks.

This module is the central coordinator that:
1. Discovers and runs all checks
2. Collects results into an AuditReport
3. Handles category filtering
"""

from collections.abc import Callable

from latency_audit import __version__
from latency_audit.models import AuditReport, CheckCategory, CheckResult

# Type alias for check functions
CheckFunction = Callable[[], CheckResult | list[CheckResult]]


class AuditRunner:
    """
    Orchestrates the audit process.

    Usage:
        runner = AuditRunner()
        report = runner.run()
        # or filter by category:
        report = runner.run(categories=[CheckCategory.KERNEL])
    """

    def __init__(self) -> None:
        """Initialize the runner with available check modules."""
        # Will be populated as we add check modules
        self._check_functions: list[CheckFunction] = []

    def register_check(self, check_fn: CheckFunction) -> None:
        """Register a check function to be run during audit."""
        self._check_functions.append(check_fn)

    def run(self, categories: list[CheckCategory] | None = None) -> AuditReport:
        """
        Run all registered checks and return a report.

        Args:
            categories: Optional list of categories to filter by.
                       If None, runs all categories.

        Returns:
            AuditReport containing all check results.
        """
        results: list[CheckResult] = []

        for check_fn in self._check_functions:
            try:
                result = check_fn()
                # Handle functions that return multiple results
                if isinstance(result, list):
                    results.extend(result)
                else:
                    results.append(result)
            except Exception:
                # Don't crash on individual check failures
                # Could add logging here later
                pass

        # Filter by category if requested
        if categories:
            results = [r for r in results if r.category in categories]

        return AuditReport(checks=results, version=__version__)


# Global runner instance - check modules will register with this
runner = AuditRunner()


def run_audit(categories: list[CheckCategory] | None = None) -> AuditReport:
    """
    Convenience function to run the audit.

    Args:
        categories: Optional category filter.

    Returns:
        AuditReport with all results.
    """
    return runner.run(categories)
