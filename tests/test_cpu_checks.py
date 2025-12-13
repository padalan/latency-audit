"""
Tests for CPU configuration checks.

These tests mock the /proc and /sys filesystem reads to verify
check logic works correctly for various scenarios.
"""

from unittest.mock import MagicMock, patch

from latency_audit.checks.cpu import (
    check_cpu_governor,
    check_cstates,
    check_isolcpus,
    check_numa,
)
from latency_audit.models import CheckStatus


class TestCpuGovernor:
    """Tests for the CPU governor check."""

    def test_all_performance_passes(self) -> None:
        """All CPUs on performance governor should pass."""
        with (
            patch("latency_audit.checks.cpu._list_cpus", return_value=[0, 1]),
            patch(
                "latency_audit.checks.cpu._read_sysfs",
                return_value="performance",
            ),
        ):
            result = check_cpu_governor()
            assert result.status == CheckStatus.PASS

    def test_mixed_governors_fails(self) -> None:
        """Mixed governors should fail."""

        def mock_read_sysfs(path: str) -> str:
            if "cpu0" in path:
                return "performance"
            return "powersave"

        with (
            patch("latency_audit.checks.cpu._list_cpus", return_value=[0, 1]),
            patch("latency_audit.checks.cpu._read_sysfs", side_effect=mock_read_sysfs),
        ):
            result = check_cpu_governor()
            assert result.status == CheckStatus.FAIL

    def test_no_cpus_skips(self) -> None:
        """No CPUs found should skip."""
        with patch("latency_audit.checks.cpu._list_cpus", return_value=[]):
            result = check_cpu_governor()
            assert result.status == CheckStatus.SKIP


class TestCStates:
    """Tests for the C-States check."""

    def test_max_cstate_zero_passes(self) -> None:
        """max_cstate=0 in kernel params should pass."""
        with patch(
            "latency_audit.checks.cpu._read_sysfs",
            return_value="BOOT_IMAGE=/vmlinuz processor.max_cstate=0 quiet",
        ):
            result = check_cstates()
            assert result.status == CheckStatus.PASS
            assert "disabled" in result.current_value

    def test_intel_idle_fails(self) -> None:
        """intel_idle driver active should fail."""

        def mock_read_sysfs(path: str) -> str | None:
            if "cmdline" in path:
                return "BOOT_IMAGE=/vmlinuz quiet"
            if "current_driver" in path:
                return "intel_idle"
            return None

        with patch("latency_audit.checks.cpu._read_sysfs", side_effect=mock_read_sysfs):
            result = check_cstates()
            assert result.status == CheckStatus.FAIL
            assert "intel_idle" in result.current_value


class TestIsolcpus:
    """Tests for the isolcpus check."""

    def test_isolcpus_configured_passes(self) -> None:
        """isolcpus in kernel params should pass."""
        with patch(
            "latency_audit.checks.cpu._read_sysfs",
            return_value="BOOT_IMAGE=/vmlinuz isolcpus=2,3 quiet",
        ):
            result = check_isolcpus()
            assert result.status == CheckStatus.PASS
            assert "2,3" in result.current_value

    def test_no_isolcpus_warns(self) -> None:
        """No isolcpus should warn (it's optional)."""
        with patch(
            "latency_audit.checks.cpu._read_sysfs",
            return_value="BOOT_IMAGE=/vmlinuz quiet",
        ):
            result = check_isolcpus()
            assert result.status == CheckStatus.WARN

    def test_unreadable_skips(self) -> None:
        """Unreadable cmdline should skip."""
        with patch("latency_audit.checks.cpu._read_sysfs", return_value=None):
            result = check_isolcpus()
            assert result.status == CheckStatus.SKIP


class TestNuma:
    """Tests for the NUMA topology check."""

    def test_single_node_passes(self) -> None:
        """Single NUMA node should pass."""
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_node0 = MagicMock()
        mock_node0.name = "node0"
        mock_path.iterdir.return_value = [mock_node0]

        with patch("latency_audit.checks.cpu.Path", return_value=mock_path):
            result = check_numa()
            assert result.status == CheckStatus.PASS
            assert "single" in result.current_value.lower()

    def test_multi_node_warns(self) -> None:
        """Multiple NUMA nodes should warn."""
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_node0 = MagicMock()
        mock_node0.name = "node0"
        mock_node1 = MagicMock()
        mock_node1.name = "node1"
        mock_path.iterdir.return_value = [mock_node0, mock_node1]

        with patch("latency_audit.checks.cpu.Path", return_value=mock_path):
            result = check_numa()
            assert result.status == CheckStatus.WARN
            assert "2 nodes" in result.current_value
