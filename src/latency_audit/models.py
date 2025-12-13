"""
Data models for latency-audit check results.

This module defines the core data structures used throughout the tool.
Using dataclasses for immutability and clean typing.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class CheckStatus(Enum):
    """Result status for a single check."""

    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"  # Suboptimal but not critical
    SKIP = "skip"  # Could not determine (e.g., missing permissions)


class CheckCategory(Enum):
    """Categories of checks for grouping and filtering."""

    KERNEL = "kernel"
    CPU = "cpu"
    NETWORK = "network"
    CLOCK = "clock"


@dataclass(frozen=True)
class CheckResult:
    """
    Immutable result from a single audit check.

    Attributes:
        name: Human-readable name of the check (e.g., "swappiness")
        category: Which category this check belongs to
        status: Pass/Fail/Warn/Skip
        current_value: What the system currently has
        expected_value: What HFT best practices recommend
        latency_impact: Estimated latency penalty in microseconds (if known)
        description: Brief explanation for humans
        fix_hint: Optional hint on how to fix (for --fix mode later)
    """

    name: str
    category: CheckCategory
    status: CheckStatus
    current_value: Any
    expected_value: Any
    latency_impact: str | None = None
    description: str = ""
    fix_hint: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "category": self.category.value,
            "status": self.status.value,
            "current_value": str(self.current_value),
            "expected_value": str(self.expected_value),
            "latency_impact": self.latency_impact,
            "description": self.description,
            "fix_hint": self.fix_hint,
        }


@dataclass
class AuditReport:
    """
    Complete audit report containing all check results.

    Attributes:
        checks: List of all CheckResult objects
        score: Overall score (0-100)
        version: Version of latency-audit that ran
    """

    checks: list[CheckResult]
    version: str

    @property
    def score(self) -> int:
        """Calculate score based on pass/fail ratio."""
        if not self.checks:
            return 100

        # Only count checks that aren't skipped
        countable = [c for c in self.checks if c.status != CheckStatus.SKIP]
        if not countable:
            return 100

        passed = sum(1 for c in countable if c.status == CheckStatus.PASS)
        return int((passed / len(countable)) * 100)

    @property
    def passed(self) -> list[CheckResult]:
        """Get all passed checks."""
        return [c for c in self.checks if c.status == CheckStatus.PASS]

    @property
    def failed(self) -> list[CheckResult]:
        """Get all failed checks."""
        return [c for c in self.checks if c.status == CheckStatus.FAIL]

    @property
    def warnings(self) -> list[CheckResult]:
        """Get all warning checks."""
        return [c for c in self.checks if c.status == CheckStatus.WARN]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "version": self.version,
            "score": self.score,
            "summary": {
                "total": len(self.checks),
                "passed": len(self.passed),
                "failed": len(self.failed),
                "warnings": len(self.warnings),
            },
            "checks": [c.to_dict() for c in self.checks],
        }
