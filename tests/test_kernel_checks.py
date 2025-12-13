"""
Tests for kernel configuration checks.

These tests mock the /proc and /sys filesystem reads to verify
check logic works correctly for various scenarios.
"""

from unittest.mock import patch

from latency_audit.checks.kernel import (
    check_sched_min_granularity,
    check_swappiness,
    check_transparent_hugepages,
)
from latency_audit.models import CheckStatus


class TestSwappiness:
    """Tests for the swappiness check."""

    def test_swappiness_zero_passes(self) -> None:
        """Swappiness of 0 should pass."""
        with patch("latency_audit.checks.kernel._read_sysctl", return_value="0"):
            result = check_swappiness()
            assert result.status == CheckStatus.PASS
            assert result.current_value == "0"

    def test_swappiness_nonzero_fails(self) -> None:
        """Swappiness > 0 should fail."""
        with patch("latency_audit.checks.kernel._read_sysctl", return_value="60"):
            result = check_swappiness()
            assert result.status == CheckStatus.FAIL
            assert result.current_value == "60"
            assert result.latency_impact is not None

    def test_swappiness_unreadable_skips(self) -> None:
        """Unreadable swappiness should skip."""
        with patch("latency_audit.checks.kernel._read_sysctl", return_value=None):
            result = check_swappiness()
            assert result.status == CheckStatus.SKIP


class TestTransparentHugepages:
    """Tests for the transparent hugepages check."""

    def test_thp_never_passes(self) -> None:
        """THP set to never should pass."""
        with patch(
            "latency_audit.checks.kernel._read_sysfs",
            return_value="always madvise [never]",
        ):
            result = check_transparent_hugepages()
            assert result.status == CheckStatus.PASS
            assert result.current_value == "never"

    def test_thp_always_fails(self) -> None:
        """THP set to always should fail."""
        with patch(
            "latency_audit.checks.kernel._read_sysfs",
            return_value="[always] madvise never",
        ):
            result = check_transparent_hugepages()
            assert result.status == CheckStatus.FAIL
            assert result.current_value == "always"
            assert result.latency_impact is not None

    def test_thp_madvise_warns(self) -> None:
        """THP set to madvise should warn."""
        with patch(
            "latency_audit.checks.kernel._read_sysfs",
            return_value="always [madvise] never",
        ):
            result = check_transparent_hugepages()
            assert result.status == CheckStatus.WARN
            assert result.current_value == "madvise"

    def test_thp_unreadable_skips(self) -> None:
        """Unreadable THP should skip."""
        with patch("latency_audit.checks.kernel._read_sysfs", return_value=None):
            result = check_transparent_hugepages()
            assert result.status == CheckStatus.SKIP


class TestSchedMinGranularity:
    """Tests for the scheduler granularity check."""

    def test_low_granularity_passes(self) -> None:
        """Low granularity (<=1ms) should pass."""
        with patch("latency_audit.checks.kernel._read_sysctl", return_value="100000"):
            result = check_sched_min_granularity()
            assert result.status == CheckStatus.PASS

    def test_medium_granularity_warns(self) -> None:
        """Medium granularity (1-3ms) should warn."""
        with patch("latency_audit.checks.kernel._read_sysctl", return_value="2000000"):
            result = check_sched_min_granularity()
            assert result.status == CheckStatus.WARN

    def test_high_granularity_fails(self) -> None:
        """High granularity (>3ms) should fail."""
        with patch("latency_audit.checks.kernel._read_sysctl", return_value="5000000"):
            result = check_sched_min_granularity()
            assert result.status == CheckStatus.FAIL

    def test_unreadable_skips(self) -> None:
        """Unreadable granularity should skip."""
        with patch("latency_audit.checks.kernel._read_sysctl", return_value=None):
            result = check_sched_min_granularity()
            assert result.status == CheckStatus.SKIP
