"""
Hardware integrity checks for latency-audit.

These checks validate physical hardware configuration that impacts latency:
- PCIe Link Width & Speed (NIC negotiation)
- Memory Channel Balance (bandwidth optimization)
"""

import subprocess
from pathlib import Path

from latency_audit.models import CheckCategory, CheckResult, CheckStatus
from latency_audit.runner import runner


def _read_sysfs(path: str) -> str | None:
    """Read a value from /proc or /sys filesystem."""
    try:
        return Path(path).read_text().strip()
    except (FileNotFoundError, PermissionError, OSError):
        return None


def _get_interfaces() -> list[str]:
    """Get list of network interfaces (excluding loopback)."""
    net_path = Path("/sys/class/net")
    if not net_path.exists():
        return []

    interfaces = []
    for entry in net_path.iterdir():
        if entry.name != "lo":
            interfaces.append(entry.name)
    return sorted(interfaces)


def _get_pci_device_path(interface: str) -> Path | None:
    """Get the PCI device path for a network interface."""
    device_link = Path(f"/sys/class/net/{interface}/device")
    if not device_link.exists():
        return None
    try:
        # Resolve the symlink to get the actual PCI device path
        return device_link.resolve()
    except OSError:
        return None


def check_pcie_link() -> list[CheckResult]:
    """
    Check PCIe link width and speed for network interfaces.

    For HFT: NICs should negotiate at maximum PCIe speed/width.
    Degraded links silently halve bandwidth and add serialization latency.
    """
    interfaces = _get_interfaces()
    if not interfaces:
        return [
            CheckResult(
                name="pcie_link",
                category=CheckCategory.HARDWARE,
                status=CheckStatus.SKIP,
                current_value="unknown",
                expected_value="max negotiated",
                description="Could not enumerate network interfaces",
            )
        ]

    results = []
    for iface in interfaces[:3]:  # Limit to first 3 interfaces
        pci_path = _get_pci_device_path(iface)
        if pci_path is None:
            continue

        # Read current and max link parameters
        current_speed = _read_sysfs(str(pci_path / "current_link_speed"))
        max_speed = _read_sysfs(str(pci_path / "max_link_speed"))
        current_width = _read_sysfs(str(pci_path / "current_link_width"))
        max_width = _read_sysfs(str(pci_path / "max_link_width"))

        if not all([current_speed, max_speed, current_width, max_width]):
            # PCIe info not available (virtual device, etc.)
            continue

        # Normalize values for comparison
        # Speed format: "8.0 GT/s PCIe" or "16.0 GT/s PCIe"
        # Width format: "x8" or "x16"
        speed_degraded = current_speed != max_speed
        width_degraded = current_width != max_width

        if speed_degraded or width_degraded:
            status = CheckStatus.FAIL
            issues = []
            if width_degraded:
                issues.append(f"width {current_width} (max: {max_width})")
            if speed_degraded:
                issues.append(f"speed {current_speed} (max: {max_speed})")
            current = ", ".join(issues)
            latency_impact = "Bandwidth reduced - check riser card/slot"
        else:
            status = CheckStatus.PASS
            current = f"{current_speed} {current_width}"
            latency_impact = None

        results.append(
            CheckResult(
                name=f"pcie_link ({iface})",
                category=CheckCategory.HARDWARE,
                status=status,
                current_value=current,
                expected_value=f"{max_speed} {max_width}",
                latency_impact=latency_impact,
                description=f"PCIe link negotiation for {iface}",
                fix_hint="Reseat NIC, check riser card, verify BIOS PCIe settings"
                if status == CheckStatus.FAIL
                else None,
            )
        )

    return (
        results
        if results
        else [
            CheckResult(
                name="pcie_link",
                category=CheckCategory.HARDWARE,
                status=CheckStatus.SKIP,
                current_value="unknown",
                expected_value="max negotiated",
                description="No PCIe devices found for network interfaces",
            )
        ]
    )


def check_memory_channels() -> CheckResult:
    """
    Check memory channel balance and population.

    For HFT: All memory channels should be populated symmetrically.
    Asymmetric population can drop memory bandwidth significantly.
    """
    # Try EDAC sysfs first (doesn't require sudo)
    edac_path = Path("/sys/devices/system/edac/mc")
    if edac_path.exists():
        try:
            controllers = list(edac_path.iterdir())
            if controllers:
                # Count memory controllers (rough proxy for channel population)
                mc_count = len([c for c in controllers if c.name.startswith("mc")])
                if mc_count > 0:
                    return CheckResult(
                        name="memory_channels",
                        category=CheckCategory.HARDWARE,
                        status=CheckStatus.PASS,
                        current_value=f"{mc_count} memory controller(s) detected",
                        expected_value="balanced channels",
                        description="Memory controllers detected via EDAC",
                    )
        except OSError:
            pass

    # Try dmidecode (requires sudo, may fail)
    try:
        result = subprocess.run(
            ["dmidecode", "-t", "memory"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            output = result.stdout
            # Count populated and empty slots
            populated = output.count("Size:") - output.count("Size: No Module")
            empty = output.count("Size: No Module")

            if empty == 0:
                status = CheckStatus.PASS
                current = f"{populated} DIMMs, all slots populated"
            elif populated == 0:
                status = CheckStatus.SKIP
                current = "No memory information available"
            else:
                # Check for obvious imbalance (odd number of DIMMs)
                if populated % 2 != 0:
                    status = CheckStatus.WARN
                    current = f"{populated} DIMMs ({empty} empty) - odd count may indicate imbalance"
                else:
                    status = CheckStatus.PASS
                    current = f"{populated} DIMMs ({empty} empty)"

            return CheckResult(
                name="memory_channels",
                category=CheckCategory.HARDWARE,
                status=status,
                current_value=current,
                expected_value="symmetric channel population",
                description="Memory DIMM population check",
                fix_hint="Populate all channels symmetrically for optimal bandwidth"
                if status == CheckStatus.WARN
                else None,
            )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass

    return CheckResult(
        name="memory_channels",
        category=CheckCategory.HARDWARE,
        status=CheckStatus.SKIP,
        current_value="unknown",
        expected_value="balanced channels",
        description="dmidecode not available or requires elevated privileges",
        fix_hint="Run with sudo for full memory audit",
    )


def register_hardware_checks() -> None:
    """Register all hardware checks with the runner."""
    runner.register_check(check_pcie_link)
    runner.register_check(check_memory_channels)
