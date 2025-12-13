"""
Clock configuration checks for latency-audit.

These checks validate clock/timing settings that impact latency:
- TSC (Time Stamp Counter) reliability
- Clocksource configuration
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


def check_tsc_reliable() -> CheckResult:
    """
    Check if TSC (Time Stamp Counter) is reliable.

    For HFT: TSC should have constant_tsc and nonstop_tsc flags.
    An unreliable TSC causes timing jitter and wrong measurements.
    """
    cpuinfo = _read_sysfs("/proc/cpuinfo")

    if cpuinfo is None:
        return CheckResult(
            name="tsc_reliable",
            category=CheckCategory.CLOCK,
            status=CheckStatus.SKIP,
            current_value="unknown",
            expected_value="constant_tsc nonstop_tsc",
            description="Could not read CPU information",
        )

    # Look for TSC-related flags
    flags_line = ""
    for line in cpuinfo.splitlines():
        if line.startswith("flags"):
            flags_line = line
            break

    if not flags_line:
        return CheckResult(
            name="tsc_reliable",
            category=CheckCategory.CLOCK,
            status=CheckStatus.SKIP,
            current_value="unknown",
            expected_value="constant_tsc nonstop_tsc",
            description="Could not parse CPU flags",
        )

    flags = flags_line.split(":")[1].split() if ":" in flags_line else []

    has_constant = "constant_tsc" in flags
    has_nonstop = "nonstop_tsc" in flags
    has_tsc = "tsc" in flags

    if has_constant and has_nonstop:
        return CheckResult(
            name="tsc_reliable",
            category=CheckCategory.CLOCK,
            status=CheckStatus.PASS,
            current_value="constant_tsc, nonstop_tsc",
            expected_value="constant_tsc nonstop_tsc",
            description="TSC is reliable for high-precision timing",
        )

    if has_tsc and (has_constant or has_nonstop):
        return CheckResult(
            name="tsc_reliable",
            category=CheckCategory.CLOCK,
            status=CheckStatus.WARN,
            current_value="partial TSC support",
            expected_value="constant_tsc nonstop_tsc",
            description="TSC may have reliability issues",
        )

    return CheckResult(
        name="tsc_reliable",
        category=CheckCategory.CLOCK,
        status=CheckStatus.FAIL,
        current_value="not reliable",
        expected_value="constant_tsc nonstop_tsc",
        latency_impact="timing jitter",
        description="TSC is not reliable - timing measurements may be inaccurate",
        fix_hint="Use hardware with modern Intel/AMD CPU that supports constant_tsc",
    )


def check_clocksource() -> CheckResult:
    """
    Check current clocksource.

    For HFT: Should be 'tsc' for lowest latency.
    HPET and other sources have higher read overhead.
    """
    current = _read_sysfs(
        "/sys/devices/system/clocksource/clocksource0/current_clocksource"
    )
    available = _read_sysfs(
        "/sys/devices/system/clocksource/clocksource0/available_clocksource"
    )

    if current is None:
        return CheckResult(
            name="clocksource",
            category=CheckCategory.CLOCK,
            status=CheckStatus.SKIP,
            current_value="unknown",
            expected_value="tsc",
            description="Could not read clocksource configuration",
        )

    if current == "tsc":
        return CheckResult(
            name="clocksource",
            category=CheckCategory.CLOCK,
            status=CheckStatus.PASS,
            current_value="tsc",
            expected_value="tsc",
            description="Using TSC for lowest latency clock reads",
        )

    # Not using TSC
    available_sources = available.split() if available else []
    if "tsc" in available_sources:
        return CheckResult(
            name="clocksource",
            category=CheckCategory.CLOCK,
            status=CheckStatus.FAIL,
            current_value=current,
            expected_value="tsc",
            latency_impact="+50-500ns per read",
            description=f"Using {current} instead of tsc (tsc is available)",
            fix_hint="echo tsc > /sys/devices/system/clocksource/clocksource0/current_clocksource",
        )

    return CheckResult(
        name="clocksource",
        category=CheckCategory.CLOCK,
        status=CheckStatus.WARN,
        current_value=current,
        expected_value="tsc",
        description=f"Using {current} - TSC not available on this system",
    )


def register_clock_checks() -> None:
    """Register all clock checks with the runner."""
    runner.register_check(check_tsc_reliable)
    runner.register_check(check_clocksource)
