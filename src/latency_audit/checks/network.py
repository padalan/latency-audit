"""
Network configuration checks for latency-audit.

These checks validate network settings that impact latency:
- NIC Offloads (GRO/LRO/TSO)
- IRQ Affinity
- Ring Buffer sizes
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


def _run_ethtool(interface: str, *args: str) -> str | None:
    """Run ethtool command and return output."""
    try:
        cmd = ["ethtool", *args, interface]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout
        return None
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None


def _get_interfaces() -> list[str]:
    """Get list of network interfaces (excluding loopback)."""
    net_path = Path("/sys/class/net")
    if not net_path.exists():
        return []

    interfaces = []
    for entry in net_path.iterdir():
        if entry.name != "lo":  # Exclude loopback
            interfaces.append(entry.name)
    return sorted(interfaces)


def check_nic_offloads() -> list[CheckResult]:
    """
    Check NIC offload settings (GRO, LRO, TSO).

    For HFT: Offloads should typically be OFF for latency-critical paths.
    They add batching delays that increase tail latency.
    """
    interfaces = _get_interfaces()
    if not interfaces:
        return [
            CheckResult(
                name="nic_offloads",
                category=CheckCategory.NETWORK,
                status=CheckStatus.SKIP,
                current_value="unknown",
                expected_value="off",
                description="Could not enumerate network interfaces",
            )
        ]

    results = []
    for iface in interfaces[:3]:  # Limit to first 3 interfaces
        output = _run_ethtool(iface, "-k")
        if output is None:
            results.append(
                CheckResult(
                    name=f"nic_offloads ({iface})",
                    category=CheckCategory.NETWORK,
                    status=CheckStatus.SKIP,
                    current_value="unknown",
                    expected_value="off",
                    description=f"Could not read offload settings for {iface}",
                )
            )
            continue

        # Parse offload status
        offloads = {}
        for line in output.splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                key = key.strip().lower()
                value = value.strip()
                if key in (
                    "generic-receive-offload",
                    "large-receive-offload",
                    "tcp-segmentation-offload",
                ):
                    short_name = {
                        "generic-receive-offload": "GRO",
                        "large-receive-offload": "LRO",
                        "tcp-segmentation-offload": "TSO",
                    }[key]
                    offloads[short_name] = value.split()[0]  # "on" or "off"

        if not offloads:
            continue

        # Check if any latency-impacting offloads are on
        bad_offloads = [k for k, v in offloads.items() if v == "on"]

        if bad_offloads:
            status = CheckStatus.WARN  # Warn, not fail - depends on use case
            current = ", ".join(f"{k}=on" for k in bad_offloads)
            latency_impact = "+30µs per packet (batching)"
        else:
            status = CheckStatus.PASS
            current = "all off"
            latency_impact = None

        results.append(
            CheckResult(
                name=f"nic_offloads ({iface})",
                category=CheckCategory.NETWORK,
                status=status,
                current_value=current,
                expected_value="GRO/LRO/TSO off",
                latency_impact=latency_impact,
                description=f"NIC offload settings for {iface}",
                fix_hint=f"ethtool -K {iface} gro off lro off tso off",
            )
        )

    return (
        results
        if results
        else [
            CheckResult(
                name="nic_offloads",
                category=CheckCategory.NETWORK,
                status=CheckStatus.SKIP,
                current_value="unknown",
                expected_value="off",
                description="ethtool not available or no interfaces found",
            )
        ]
    )


def check_ring_buffers() -> list[CheckResult]:
    """
    Check NIC ring buffer sizes.

    For HFT: Ring buffers should be maximized to prevent packet drops.
    Small buffers cause drops during traffic bursts.
    """
    interfaces = _get_interfaces()
    if not interfaces:
        return [
            CheckResult(
                name="ring_buffers",
                category=CheckCategory.NETWORK,
                status=CheckStatus.SKIP,
                current_value="unknown",
                expected_value="maximized",
                description="Could not enumerate network interfaces",
            )
        ]

    results = []
    for iface in interfaces[:3]:  # Limit to first 3 interfaces
        output = _run_ethtool(iface, "-g")
        if output is None:
            continue

        # Parse ring buffer info
        current_rx = None
        max_rx = None
        section = None

        for line in output.splitlines():
            if "Pre-set maximums" in line:
                section = "max"
            elif "Current hardware settings" in line:
                section = "current"
            elif "RX:" in line and section:
                try:
                    value = int(line.split(":")[1].strip())
                    if section == "max":
                        max_rx = value
                    else:
                        current_rx = value
                except (ValueError, IndexError):
                    pass

        if current_rx is not None and max_rx is not None:
            if current_rx >= max_rx * 0.9:  # Within 90% of max
                status = CheckStatus.PASS
            elif current_rx >= max_rx * 0.5:
                status = CheckStatus.WARN
            else:
                status = CheckStatus.FAIL

            results.append(
                CheckResult(
                    name=f"ring_buffer ({iface})",
                    category=CheckCategory.NETWORK,
                    status=status,
                    current_value=f"RX: {current_rx}/{max_rx}",
                    expected_value="maximized",
                    description=f"NIC ring buffer size for {iface}",
                    fix_hint=f"ethtool -G {iface} rx {max_rx}",
                )
            )

    return (
        results
        if results
        else [
            CheckResult(
                name="ring_buffers",
                category=CheckCategory.NETWORK,
                status=CheckStatus.SKIP,
                current_value="unknown",
                expected_value="maximized",
                description="Could not read ring buffer settings",
            )
        ]
    )


def check_irq_affinity() -> CheckResult:
    """
    Check IRQ affinity configuration.

    For HFT: Network IRQs should be pinned to specific cores.
    This prevents IRQ storms from affecting trading threads.
    """
    irq_path = Path("/proc/irq")
    if not irq_path.exists():
        return CheckResult(
            name="irq_affinity",
            category=CheckCategory.NETWORK,
            status=CheckStatus.SKIP,
            current_value="unknown",
            expected_value="configured",
            description="Could not read IRQ information",
        )

    # Check if irqbalance is running (it's usually not wanted for HFT)
    try:
        result = subprocess.run(
            ["pgrep", "irqbalance"],
            capture_output=True,
            timeout=2,
        )
        irqbalance_running = result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        irqbalance_running = False

    if irqbalance_running:
        return CheckResult(
            name="irq_affinity",
            category=CheckCategory.NETWORK,
            status=CheckStatus.WARN,
            current_value="irqbalance running",
            expected_value="manual affinity",
            description="irqbalance may move IRQs unpredictably",
            fix_hint="systemctl stop irqbalance && set manual IRQ affinity",
        )

    return CheckResult(
        name="irq_affinity",
        category=CheckCategory.NETWORK,
        status=CheckStatus.PASS,
        current_value="manual",
        expected_value="configured",
        description="irqbalance not running - manual affinity assumed",
    )


def check_udp_buffer_drops() -> CheckResult:
    """
    Check UDP socket buffer drops (RcvbufErrors).

    For HFT: This indicates packets the kernel received but the application
    couldn't read fast enough. The socket buffer overflowed.
    """
    snmp_content = _read_sysfs("/proc/net/snmp")
    if snmp_content is None:
        return CheckResult(
            name="udp_buffer_drops",
            category=CheckCategory.NETWORK,
            status=CheckStatus.SKIP,
            current_value="unknown",
            expected_value="0 drops",
            description="Could not read /proc/net/snmp",
        )

    # Parse UDP line from /proc/net/snmp
    # Format has header line then values line:
    # Udp: InDatagrams NoPorts InErrors OutDatagrams RcvbufErrors SndbufErrors ...
    # Udp: 12345 0 0 6789 0 0 ...
    udp_header = None
    udp_values = None
    for line in snmp_content.splitlines():
        if line.startswith("Udp:"):
            if udp_header is None:
                udp_header = line.split()
            else:
                udp_values = line.split()
                break

    if udp_header is None or udp_values is None:
        return CheckResult(
            name="udp_buffer_drops",
            category=CheckCategory.NETWORK,
            status=CheckStatus.SKIP,
            current_value="unknown",
            expected_value="0 drops",
            description="Could not parse UDP stats from /proc/net/snmp",
        )

    # Find RcvbufErrors column
    try:
        rcvbuf_idx = udp_header.index("RcvbufErrors")
        rcvbuf_errors = int(udp_values[rcvbuf_idx])
    except (ValueError, IndexError):
        return CheckResult(
            name="udp_buffer_drops",
            category=CheckCategory.NETWORK,
            status=CheckStatus.SKIP,
            current_value="unknown",
            expected_value="0 drops",
            description="RcvbufErrors not found in /proc/net/snmp",
        )

    if rcvbuf_errors == 0:
        status = CheckStatus.PASS
        current = "0 drops"
        latency_impact = None
    else:
        status = CheckStatus.FAIL
        current = f"{rcvbuf_errors} drops"
        latency_impact = "Packets lost - app too slow to drain socket"

    return CheckResult(
        name="udp_buffer_drops",
        category=CheckCategory.NETWORK,
        status=status,
        current_value=current,
        expected_value="0 drops",
        latency_impact=latency_impact,
        description="UDP socket buffer overflow drops",
        fix_hint="Increase SO_RCVBUF or optimize receive loop"
        if status != CheckStatus.PASS
        else None,
    )


def check_nic_hardware_drops() -> list[CheckResult]:
    """
    Check NIC hardware discard counters.

    For HFT: These indicate the NIC ran out of buffer space before
    the kernel could process packets. Often caused by PCIe congestion
    or CPU not keeping up with interrupt handling.
    """
    interfaces = _get_interfaces()
    if not interfaces:
        return [
            CheckResult(
                name="nic_hardware_drops",
                category=CheckCategory.NETWORK,
                status=CheckStatus.SKIP,
                current_value="unknown",
                expected_value="0 drops",
                description="Could not enumerate network interfaces",
            )
        ]

    results = []
    for iface in interfaces[:3]:  # Limit to first 3 interfaces
        stats_path = f"/sys/class/net/{iface}/statistics"

        rx_missed = _read_sysfs(f"{stats_path}/rx_missed_errors")
        rx_over = _read_sysfs(f"{stats_path}/rx_over_errors")

        if rx_missed is None and rx_over is None:
            continue

        try:
            missed = int(rx_missed) if rx_missed else 0
            over = int(rx_over) if rx_over else 0
            total_drops = missed + over
        except ValueError:
            continue

        if total_drops == 0:
            status = CheckStatus.PASS
            current = "0 hardware drops"
            latency_impact = None
        else:
            status = CheckStatus.WARN
            current = f"{total_drops} drops (missed={missed}, over={over})"
            latency_impact = "Packets dropped at NIC level - check PCIe/CPU load"

        results.append(
            CheckResult(
                name=f"nic_hardware_drops ({iface})",
                category=CheckCategory.NETWORK,
                status=status,
                current_value=current,
                expected_value="0 drops",
                latency_impact=latency_impact,
                description=f"NIC hardware discard counters for {iface}",
                fix_hint="Check PCIe link, increase ring buffers, verify CPU affinity"
                if status != CheckStatus.PASS
                else None,
            )
        )

    return (
        results
        if results
        else [
            CheckResult(
                name="nic_hardware_drops",
                category=CheckCategory.NETWORK,
                status=CheckStatus.SKIP,
                current_value="unknown",
                expected_value="0 drops",
                description="Could not read NIC hardware drop counters",
            )
        ]
    )


def register_network_checks() -> None:
    """Register all network checks with the runner."""
    runner.register_check(check_nic_offloads)
    runner.register_check(check_ring_buffers)
    runner.register_check(check_irq_affinity)
    runner.register_check(check_udp_buffer_drops)
    runner.register_check(check_nic_hardware_drops)
