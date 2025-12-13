"""
Kernel configuration checks for latency-audit.

These checks validate Linux kernel settings that impact latency:
- Swappiness (memory management)
- Transparent Hugepages (memory compaction)
- Kernel preemption model
"""

from pathlib import Path

from latency_audit.models import CheckCategory, CheckResult, CheckStatus
from latency_audit.runner import runner


def _read_sysfs(path: str) -> str | None:
    """
    Read a value from /proc or /sys filesystem.

    Returns None if file doesn't exist or can't be read.
    """
    try:
        return Path(path).read_text().strip()
    except (FileNotFoundError, PermissionError, OSError):
        return None


def _read_sysctl(key: str) -> str | None:
    """
    Read a sysctl value by key (e.g., 'vm.swappiness').

    Converts key to path: vm.swappiness -> /proc/sys/vm/swappiness
    """
    path = f"/proc/sys/{key.replace('.', '/')}"
    return _read_sysfs(path)


def check_swappiness() -> CheckResult:
    """
    Check vm.swappiness setting.

    For HFT: Should be 0 to prevent swapping under memory pressure.
    Swapping can cause 100µs+ page fault latency.
    """
    value = _read_sysctl("vm.swappiness")

    if value is None:
        return CheckResult(
            name="swappiness",
            category=CheckCategory.KERNEL,
            status=CheckStatus.SKIP,
            current_value="unknown",
            expected_value="0",
            description="Could not read vm.swappiness",
        )

    status = CheckStatus.PASS if value == "0" else CheckStatus.FAIL
    return CheckResult(
        name="swappiness",
        category=CheckCategory.KERNEL,
        status=status,
        current_value=value,
        expected_value="0",
        latency_impact="+100µs (page fault)" if status == CheckStatus.FAIL else None,
        description="Memory swapping aggressiveness (0 = disabled)",
        fix_hint="sysctl -w vm.swappiness=0",
    )


def check_transparent_hugepages() -> CheckResult:
    """
    Check Transparent Hugepages (THP) setting.

    For HFT: Should be 'never' to avoid memory compaction stalls.
    THP can cause unpredictable 50µs+ latency spikes.
    """
    path = "/sys/kernel/mm/transparent_hugepage/enabled"
    value = _read_sysfs(path)

    if value is None:
        return CheckResult(
            name="transparent_hugepages",
            category=CheckCategory.KERNEL,
            status=CheckStatus.SKIP,
            current_value="unknown",
            expected_value="never",
            description="Could not read THP setting",
        )

    # Value looks like: "always madvise [never]" - bracketed is active
    if "[never]" in value:
        current = "never"
        status = CheckStatus.PASS
    elif "[madvise]" in value:
        current = "madvise"
        status = CheckStatus.WARN  # Acceptable but not ideal
    else:
        current = "always"
        status = CheckStatus.FAIL

    return CheckResult(
        name="transparent_hugepages",
        category=CheckCategory.KERNEL,
        status=status,
        current_value=current,
        expected_value="never",
        latency_impact="+50µs (compaction)" if status == CheckStatus.FAIL else None,
        description="Transparent Hugepages can cause compaction stalls",
        fix_hint="echo never > /sys/kernel/mm/transparent_hugepage/enabled",
    )


def check_sched_min_granularity() -> CheckResult:
    """
    Check kernel.sched_min_granularity_ns.

    Lower values = more responsive scheduling but more overhead.
    Default is 3000000 (3ms). HFT often uses 100000 (100µs).
    """
    value = _read_sysctl("kernel.sched_min_granularity_ns")

    if value is None:
        return CheckResult(
            name="sched_min_granularity_ns",
            category=CheckCategory.KERNEL,
            status=CheckStatus.SKIP,
            current_value="unknown",
            expected_value="≤1000000",
            description="Could not read scheduler granularity",
        )

    try:
        ns_value = int(value)
    except ValueError:
        ns_value = 0

    # 1ms or less is good for latency-sensitive workloads
    if ns_value <= 1_000_000:
        status = CheckStatus.PASS
    elif ns_value <= 3_000_000:
        status = CheckStatus.WARN
    else:
        status = CheckStatus.FAIL

    return CheckResult(
        name="sched_min_granularity_ns",
        category=CheckCategory.KERNEL,
        status=status,
        current_value=f"{ns_value:,}",
        expected_value="≤1,000,000",
        description="Minimum scheduler time slice in nanoseconds",
        fix_hint="sysctl -w kernel.sched_min_granularity_ns=100000",
    )


def register_kernel_checks() -> None:
    """Register all kernel checks with the runner."""
    runner.register_check(check_swappiness)
    runner.register_check(check_transparent_hugepages)
    runner.register_check(check_sched_min_granularity)
