"""
Tests for clock configuration checks.

These tests mock the /proc and /sys filesystem reads to verify
check logic works correctly for various scenarios.
"""

from unittest.mock import patch

from latency_audit.checks.clock import check_clocksource, check_tsc_reliable
from latency_audit.models import CheckStatus


class TestTscReliable:
    """Tests for the TSC reliability check."""

    def test_full_tsc_support_passes(self) -> None:
        """Full TSC support (constant_tsc + nonstop_tsc) should pass."""
        cpuinfo = """
processor       : 0
vendor_id       : GenuineIntel
model name      : Intel(R) Core(TM) i7-10700K
flags           : fpu vme de pse tsc msr pae mce cx8 apic sep mtrr pge constant_tsc nonstop_tsc
"""
        with patch("latency_audit.checks.clock._read_sysfs", return_value=cpuinfo):
            result = check_tsc_reliable()
            assert result.status == CheckStatus.PASS

    def test_partial_tsc_support_warns(self) -> None:
        """Partial TSC support should warn."""
        cpuinfo = """
processor       : 0
flags           : fpu vme tsc constant_tsc
"""
        with patch("latency_audit.checks.clock._read_sysfs", return_value=cpuinfo):
            result = check_tsc_reliable()
            assert result.status == CheckStatus.WARN

    def test_no_tsc_support_fails(self) -> None:
        """No TSC support should fail."""
        cpuinfo = """
processor       : 0
flags           : fpu vme de pse
"""
        with patch("latency_audit.checks.clock._read_sysfs", return_value=cpuinfo):
            result = check_tsc_reliable()
            assert result.status == CheckStatus.FAIL

    def test_unreadable_skips(self) -> None:
        """Unreadable cpuinfo should skip."""
        with patch("latency_audit.checks.clock._read_sysfs", return_value=None):
            result = check_tsc_reliable()
            assert result.status == CheckStatus.SKIP


class TestClocksource:
    """Tests for the clocksource check."""

    def test_tsc_clocksource_passes(self) -> None:
        """TSC clocksource should pass."""

        def mock_read_sysfs(path: str) -> str:
            if "current" in path:
                return "tsc"
            return "tsc hpet acpi_pm"

        with patch(
            "latency_audit.checks.clock._read_sysfs", side_effect=mock_read_sysfs
        ):
            result = check_clocksource()
            assert result.status == CheckStatus.PASS
            assert result.current_value == "tsc"

    def test_hpet_clocksource_fails(self) -> None:
        """HPET clocksource when TSC available should fail."""

        def mock_read_sysfs(path: str) -> str:
            if "current" in path:
                return "hpet"
            return "tsc hpet acpi_pm"

        with patch(
            "latency_audit.checks.clock._read_sysfs", side_effect=mock_read_sysfs
        ):
            result = check_clocksource()
            assert result.status == CheckStatus.FAIL
            assert result.latency_impact is not None

    def test_hpet_only_warns(self) -> None:
        """HPET clocksource when TSC not available should warn."""

        def mock_read_sysfs(path: str) -> str:
            if "current" in path:
                return "hpet"
            return "hpet acpi_pm"

        with patch(
            "latency_audit.checks.clock._read_sysfs", side_effect=mock_read_sysfs
        ):
            result = check_clocksource()
            assert result.status == CheckStatus.WARN

    def test_unreadable_skips(self) -> None:
        """Unreadable clocksource should skip."""
        with patch("latency_audit.checks.clock._read_sysfs", return_value=None):
            result = check_clocksource()
            assert result.status == CheckStatus.SKIP
