"""
Tests for data models.

Tests for CheckResult, AuditReport, and their serialization.
"""

import pytest

from latency_audit.models import (
    AuditReport,
    CheckCategory,
    CheckResult,
    CheckStatus,
)


class TestCheckResult:
    """Tests for CheckResult dataclass."""

    def test_to_dict_serialization(self) -> None:
        """CheckResult should serialize to dict correctly."""
        result = CheckResult(
            name="test_check",
            category=CheckCategory.KERNEL,
            status=CheckStatus.PASS,
            current_value="0",
            expected_value="0",
            latency_impact="+100µs",
            description="Test description",
            fix_hint="sysctl -w test=0",
        )
        data = result.to_dict()

        assert data["name"] == "test_check"
        assert data["category"] == "kernel"
        assert data["status"] == "pass"
        assert data["current_value"] == "0"
        assert data["latency_impact"] == "+100µs"
        assert data["fix_hint"] == "sysctl -w test=0"

    def test_frozen_dataclass(self) -> None:
        """CheckResult should be immutable."""
        result = CheckResult(
            name="test",
            category=CheckCategory.CPU,
            status=CheckStatus.FAIL,
            current_value="bad",
            expected_value="good",
        )
        with pytest.raises(AttributeError):
            result.name = "changed"  # type: ignore[misc]


class TestAuditReport:
    """Tests for AuditReport dataclass."""

    def test_score_all_pass(self) -> None:
        """Score should be 100 when all checks pass."""
        checks = [
            CheckResult(
                name=f"check{i}",
                category=CheckCategory.KERNEL,
                status=CheckStatus.PASS,
                current_value="ok",
                expected_value="ok",
            )
            for i in range(5)
        ]
        report = AuditReport(checks=checks, version="0.1.0")
        assert report.score == 100

    def test_score_all_fail(self) -> None:
        """Score should be 0 when all checks fail."""
        checks = [
            CheckResult(
                name=f"check{i}",
                category=CheckCategory.CPU,
                status=CheckStatus.FAIL,
                current_value="bad",
                expected_value="good",
            )
            for i in range(5)
        ]
        report = AuditReport(checks=checks, version="0.1.0")
        assert report.score == 0

    def test_score_mixed(self) -> None:
        """Score should be proportional to pass rate."""
        checks = [
            CheckResult(
                name="pass1",
                category=CheckCategory.KERNEL,
                status=CheckStatus.PASS,
                current_value="ok",
                expected_value="ok",
            ),
            CheckResult(
                name="fail1",
                category=CheckCategory.KERNEL,
                status=CheckStatus.FAIL,
                current_value="bad",
                expected_value="good",
            ),
        ]
        report = AuditReport(checks=checks, version="0.1.0")
        assert report.score == 50

    def test_score_ignores_skipped(self) -> None:
        """Skipped checks should not affect score."""
        checks = [
            CheckResult(
                name="pass",
                category=CheckCategory.KERNEL,
                status=CheckStatus.PASS,
                current_value="ok",
                expected_value="ok",
            ),
            CheckResult(
                name="skip",
                category=CheckCategory.KERNEL,
                status=CheckStatus.SKIP,
                current_value="unknown",
                expected_value="ok",
            ),
        ]
        report = AuditReport(checks=checks, version="0.1.0")
        assert report.score == 100  # Only 1 countable check, and it passed

    def test_filter_properties(self) -> None:
        """Filter properties should work correctly."""
        checks = [
            CheckResult(
                name="pass",
                category=CheckCategory.KERNEL,
                status=CheckStatus.PASS,
                current_value="ok",
                expected_value="ok",
            ),
            CheckResult(
                name="fail",
                category=CheckCategory.CPU,
                status=CheckStatus.FAIL,
                current_value="bad",
                expected_value="good",
            ),
            CheckResult(
                name="warn",
                category=CheckCategory.NETWORK,
                status=CheckStatus.WARN,
                current_value="meh",
                expected_value="good",
            ),
        ]
        report = AuditReport(checks=checks, version="0.1.0")

        assert len(report.passed) == 1
        assert len(report.failed) == 1
        assert len(report.warnings) == 1

    def test_to_dict_serialization(self) -> None:
        """AuditReport should serialize to dict correctly."""
        checks = [
            CheckResult(
                name="test",
                category=CheckCategory.CLOCK,
                status=CheckStatus.PASS,
                current_value="tsc",
                expected_value="tsc",
            )
        ]
        report = AuditReport(checks=checks, version="0.1.0")
        data = report.to_dict()

        assert data["version"] == "0.1.0"
        assert data["score"] == 100
        assert data["summary"]["total"] == 1
        assert data["summary"]["passed"] == 1
        assert len(data["checks"]) == 1

    def test_empty_report(self) -> None:
        """Empty report should have score of 100."""
        report = AuditReport(checks=[], version="0.1.0")
        assert report.score == 100
