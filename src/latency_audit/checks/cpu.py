"""
CPU configuration checks for latency-audit.

These checks validate CPU settings that impact latency:
- Frequency Governor (performance vs power-saving)
- C-States (deep sleep states)
- Core Isolation (isolcpus)
- NUMA topology awareness
"""

from pathlib import Path

from latency_audit.models import CheckCategory, CheckResult, CheckStatus
from latency_audit.runner import runner


def _read_sysfs(path: str) -> str | None:
    """Read a value from /proc or /sys filesystem."""
    try:
        return Path(path).read_text().strip()
    except (FileNotFoundError, PermissionError, OSError):
        return None


def _list_cpus() -> list[int]:
    """Get list of CPU IDs from /sys/devices/system/cpu/."""
    cpu_path = Path("/sys/devices/system/cpu")
    if not cpu_path.exists():
        return []

    cpus = []
    for entry in cpu_path.iterdir():
        if entry.name.startswith("cpu") and entry.name[3:].isdigit():
            cpus.append(int(entry.name[3:]))
    return sorted(cpus)


def check_cpu_governor() -> CheckResult:
    """
    Check CPU frequency scaling governor.

    For HFT: Should be 'performance' to prevent frequency scaling.
    Power-saving governors can add 200µs+ latency during scale-up.
    """
    cpus = _list_cpus()
    if not cpus:
        return CheckResult(
            name="cpu_governor",
            category=CheckCategory.CPU,
            status=CheckStatus.SKIP,
            current_value="unknown",
            expected_value="performance",
            description="Could not enumerate CPUs",
        )

    governors: dict[str, list[int]] = {}
    for cpu in cpus:
        gov = _read_sysfs(f"/sys/devices/system/cpu/cpu{cpu}/cpufreq/scaling_governor")
        if gov:
            governors.setdefault(gov, []).append(cpu)

    if not governors:
        return CheckResult(
            name="cpu_governor",
            category=CheckCategory.CPU,
            status=CheckStatus.SKIP,
            current_value="unknown",
            expected_value="performance",
            description="Could not read CPU governors (cpufreq may not be available)",
        )

    # Check if all CPUs are on 'performance'
    if list(governors.keys()) == ["performance"]:
        status = CheckStatus.PASS
        current = "performance (all cores)"
    else:
        status = CheckStatus.FAIL
        current = ", ".join(f"{g}: {len(cpus)} cores" for g, cpus in governors.items())

    return CheckResult(
        name="cpu_governor",
        category=CheckCategory.CPU,
        status=status,
        current_value=current,
        expected_value="performance (all cores)",
        latency_impact="+200µs (frequency scaling)"
        if status == CheckStatus.FAIL
        else None,
        description="CPU frequency scaling governor",
        fix_hint="cpupower frequency-set -g performance",
    )


def check_cstates() -> CheckResult:
    """
    Check CPU C-State configuration.

    For HFT: C-States should be disabled (max_cstate=0 or 1).
    Deep C-States can add 100-500µs wake-up latency.
    """
    # Check kernel boot parameter
    cmdline = _read_sysfs("/proc/cmdline")
    if cmdline and "processor.max_cstate=0" in cmdline:
        return CheckResult(
            name="cstates",
            category=CheckCategory.CPU,
            status=CheckStatus.PASS,
            current_value="disabled (kernel param)",
            expected_value="max_cstate=0",
            description="CPU C-States (deep sleep) disabled via kernel parameter",
        )

    if cmdline and "processor.max_cstate=1" in cmdline:
        return CheckResult(
            name="cstates",
            category=CheckCategory.CPU,
            status=CheckStatus.PASS,
            current_value="C1 only (kernel param)",
            expected_value="max_cstate=0 or 1",
            description="CPU C-States limited to C1 (halt only)",
        )

    # Try to read from /sys
    # This is a heuristic - actual C-state control varies by system
    idle_driver = _read_sysfs("/sys/devices/system/cpu/cpuidle/current_driver")

    if idle_driver is None:
        return CheckResult(
            name="cstates",
            category=CheckCategory.CPU,
            status=CheckStatus.SKIP,
            current_value="unknown",
            expected_value="max_cstate=0",
            description="Could not determine C-State configuration",
        )

    # If intel_idle or acpi_idle is active, C-States are likely enabled
    if idle_driver in ("intel_idle", "acpi_idle"):
        return CheckResult(
            name="cstates",
            category=CheckCategory.CPU,
            status=CheckStatus.FAIL,
            current_value=f"enabled ({idle_driver})",
            expected_value="disabled",
            latency_impact="+100-500µs (wake-up)",
            description="CPU C-States can cause wake-up latency spikes",
            fix_hint="Add 'processor.max_cstate=0 intel_idle.max_cstate=0' to kernel cmdline",
        )

    return CheckResult(
        name="cstates",
        category=CheckCategory.CPU,
        status=CheckStatus.WARN,
        current_value=idle_driver,
        expected_value="disabled",
        description="Unknown idle driver - verify C-State configuration manually",
    )


def check_isolcpus() -> CheckResult:
    """
    Check for isolated CPUs (isolcpus kernel parameter).

    For HFT: Critical cores should be isolated from scheduler.
    This prevents OS tasks from interrupting latency-critical threads.
    """
    cmdline = _read_sysfs("/proc/cmdline")

    if cmdline is None:
        return CheckResult(
            name="isolcpus",
            category=CheckCategory.CPU,
            status=CheckStatus.SKIP,
            current_value="unknown",
            expected_value="isolcpus=<cores>",
            description="Could not read kernel command line",
        )

    if "isolcpus=" in cmdline:
        # Extract the isolcpus value
        for param in cmdline.split():
            if param.startswith("isolcpus="):
                isolated = param.split("=", 1)[1]
                return CheckResult(
                    name="isolcpus",
                    category=CheckCategory.CPU,
                    status=CheckStatus.PASS,
                    current_value=f"cores {isolated}",
                    expected_value="isolcpus=<cores>",
                    description="Cores isolated from general scheduler",
                )

    return CheckResult(
        name="isolcpus",
        category=CheckCategory.CPU,
        status=CheckStatus.WARN,
        current_value="none",
        expected_value="isolcpus=<cores>",
        description="No CPU isolation configured (optional but recommended for HFT)",
        fix_hint="Add 'isolcpus=2,3' (adjust cores) to kernel cmdline",
    )


def check_numa() -> CheckResult:
    """
    Check NUMA topology.

    For HFT: Understanding NUMA topology is critical for memory placement.
    This check reports the topology for awareness.
    """
    numa_path = Path("/sys/devices/system/node")
    if not numa_path.exists():
        return CheckResult(
            name="numa_topology",
            category=CheckCategory.CPU,
            status=CheckStatus.SKIP,
            current_value="unknown",
            expected_value="aware",
            description="Could not read NUMA topology",
        )

    nodes = []
    for entry in numa_path.iterdir():
        if entry.name.startswith("node") and entry.name[4:].isdigit():
            nodes.append(int(entry.name[4:]))

    if len(nodes) <= 1:
        return CheckResult(
            name="numa_topology",
            category=CheckCategory.CPU,
            status=CheckStatus.PASS,
            current_value="single node (UMA)",
            expected_value="aware",
            description="Single NUMA node - no cross-node latency concerns",
        )

    # Multi-node NUMA - just informational
    return CheckResult(
        name="numa_topology",
        category=CheckCategory.CPU,
        status=CheckStatus.WARN,
        current_value=f"{len(nodes)} nodes",
        expected_value="aware",
        description="Multi-node NUMA - ensure memory affinity is configured",
        fix_hint="Use numactl --membind=<node> for latency-critical processes",
    )


def register_cpu_checks() -> None:
    """Register all CPU checks with the runner."""
    runner.register_check(check_cpu_governor)
    runner.register_check(check_cstates)
    runner.register_check(check_isolcpus)
    runner.register_check(check_numa)
