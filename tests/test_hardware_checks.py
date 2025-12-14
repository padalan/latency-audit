"""
Tests for hardware integrity checks.

These tests mock the /sys filesystem reads to verify
check logic works correctly for various scenarios.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

from latency_audit.checks.hardware import (
    check_memory_channels,
    check_pcie_link,
)
from latency_audit.models import CheckStatus


class TestPcieLink:
    """Tests for the PCIe link validator check."""

    def test_pcie_at_max_speed_passes(self) -> None:
        """NIC negotiated at max speed/width should pass."""
        # Use a real Path so that / operator works correctly
        mock_pci_path = Path("/sys/bus/pci/devices/0000:01:00.0")

        def mock_read_sysfs(path: str) -> str | None:
            if "current_link_speed" in path:
                return "16.0 GT/s PCIe"
            if "max_link_speed" in path:
                return "16.0 GT/s PCIe"
            if "current_link_width" in path:
                return "x16"
            if "max_link_width" in path:
                return "x16"
            return None

        with (
            patch(
                "latency_audit.checks.hardware._get_interfaces",
                return_value=["eth0"],
            ),
            patch(
                "latency_audit.checks.hardware._get_pci_device_path",
                return_value=mock_pci_path,
            ),
            patch(
                "latency_audit.checks.hardware._read_sysfs",
                side_effect=mock_read_sysfs,
            ),
        ):
            results = check_pcie_link()
            assert len(results) == 1
            assert results[0].status == CheckStatus.PASS

    def test_pcie_width_degraded_fails(self) -> None:
        """NIC negotiated at lower width should fail."""
        mock_pci_path = Path("/sys/bus/pci/devices/0000:01:00.0")

        def mock_read_sysfs(path: str) -> str | None:
            if "current_link_speed" in path:
                return "16.0 GT/s PCIe"
            if "max_link_speed" in path:
                return "16.0 GT/s PCIe"
            if "current_link_width" in path:
                return "x8"  # Degraded!
            if "max_link_width" in path:
                return "x16"
            return None

        with (
            patch(
                "latency_audit.checks.hardware._get_interfaces",
                return_value=["eth0"],
            ),
            patch(
                "latency_audit.checks.hardware._get_pci_device_path",
                return_value=mock_pci_path,
            ),
            patch(
                "latency_audit.checks.hardware._read_sysfs",
                side_effect=mock_read_sysfs,
            ),
        ):
            results = check_pcie_link()
            assert len(results) == 1
            assert results[0].status == CheckStatus.FAIL
            assert "x8" in results[0].current_value

    def test_pcie_speed_degraded_fails(self) -> None:
        """NIC negotiated at lower speed should fail."""
        mock_pci_path = Path("/sys/bus/pci/devices/0000:01:00.0")

        def mock_read_sysfs(path: str) -> str | None:
            if "current_link_speed" in path:
                return "8.0 GT/s PCIe"  # Degraded!
            if "max_link_speed" in path:
                return "16.0 GT/s PCIe"
            if "current_link_width" in path:
                return "x16"
            if "max_link_width" in path:
                return "x16"
            return None

        with (
            patch(
                "latency_audit.checks.hardware._get_interfaces",
                return_value=["eth0"],
            ),
            patch(
                "latency_audit.checks.hardware._get_pci_device_path",
                return_value=mock_pci_path,
            ),
            patch(
                "latency_audit.checks.hardware._read_sysfs",
                side_effect=mock_read_sysfs,
            ),
        ):
            results = check_pcie_link()
            assert len(results) == 1
            assert results[0].status == CheckStatus.FAIL

    def test_no_interfaces_skips(self) -> None:
        """No network interfaces should skip."""
        with patch(
            "latency_audit.checks.hardware._get_interfaces",
            return_value=[],
        ):
            results = check_pcie_link()
            assert len(results) == 1
            assert results[0].status == CheckStatus.SKIP

    def test_no_pci_device_skips(self) -> None:
        """Virtual interface without PCI device should skip."""
        with (
            patch(
                "latency_audit.checks.hardware._get_interfaces",
                return_value=["veth0"],
            ),
            patch(
                "latency_audit.checks.hardware._get_pci_device_path",
                return_value=None,
            ),
        ):
            results = check_pcie_link()
            assert len(results) == 1
            assert results[0].status == CheckStatus.SKIP


class TestMemoryChannels:
    """Tests for the memory channel balance check."""

    def test_edac_available_passes(self) -> None:
        """EDAC sysfs available should pass."""
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_mc0 = MagicMock()
        mock_mc0.name = "mc0"
        mock_mc1 = MagicMock()
        mock_mc1.name = "mc1"
        mock_path.iterdir.return_value = [mock_mc0, mock_mc1]

        with patch("latency_audit.checks.hardware.Path", return_value=mock_path):
            result = check_memory_channels()
            assert result.status == CheckStatus.PASS
            assert "2 memory controller" in result.current_value

    def test_dmidecode_all_populated_passes(self) -> None:
        """All memory slots populated should pass."""
        mock_path = MagicMock()
        mock_path.exists.return_value = False  # No EDAC

        dmidecode_output = """
Memory Device
    Size: 32 GB
Memory Device
    Size: 32 GB
Memory Device
    Size: 32 GB
Memory Device
    Size: 32 GB
"""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = dmidecode_output

        with (
            patch("latency_audit.checks.hardware.Path", return_value=mock_path),
            patch("subprocess.run", return_value=mock_result),
        ):
            result = check_memory_channels()
            assert result.status == CheckStatus.PASS
            assert "4 DIMMs" in result.current_value

    def test_dmidecode_unbalanced_warns(self) -> None:
        """Odd number of DIMMs should warn."""
        mock_path = MagicMock()
        mock_path.exists.return_value = False  # No EDAC

        dmidecode_output = """
Memory Device
    Size: 32 GB
Memory Device
    Size: 32 GB
Memory Device
    Size: 32 GB
Memory Device
    Size: No Module Installed
"""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = dmidecode_output

        with (
            patch("latency_audit.checks.hardware.Path", return_value=mock_path),
            patch("subprocess.run", return_value=mock_result),
        ):
            result = check_memory_channels()
            assert result.status == CheckStatus.WARN
            assert "3 DIMMs" in result.current_value

    def test_dmidecode_not_available_skips(self) -> None:
        """dmidecode not installed should skip."""
        mock_path = MagicMock()
        mock_path.exists.return_value = False  # No EDAC

        with (
            patch("latency_audit.checks.hardware.Path", return_value=mock_path),
            patch("subprocess.run", side_effect=FileNotFoundError()),
        ):
            result = check_memory_channels()
            assert result.status == CheckStatus.SKIP
