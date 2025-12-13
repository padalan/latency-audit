"""
Process hygiene checks for latency-audit.

These checks validate process-level metrics that impact latency:
- Involuntary Context Switches (scheduler preemption)
- Major Page Faults (disk I/O during execution)
"""

from pathlib import Path

from latency_audit.models import CheckCategory, CheckResult, CheckStatus
from latency_audit.runner import runner

# Global PID storage - set via CLI before checks run
_target_pid: int | None = None


def set_target_pid(pid: int | None) -> None:
    """Set the target PID for process checks."""
    global _target_pid
    _target_pid = pid


def get_target_pid() -> int | None:
    """Get the current target PID."""
    return _target_pid


def _read_proc_file(path: str) -> str | None:
    """Read a file from /proc filesystem."""
    try:
        return Path(path).read_text().strip()
    except (FileNotFoundError, PermissionError, OSError):
        return None


def check_context_switches() -> CheckResult:
    """
    Check involuntary context switch count for target process.

    For HFT: Trading threads should NEVER be preempted by the scheduler.
    Any involuntary context switch indicates core isolation breach or
    noisy neighbors.
    """
    pid = get_target_pid()

    if pid is None:
        return CheckResult(
            name="context_switches",
            category=CheckCategory.PROCESS,
            status=CheckStatus.SKIP,
            current_value="no PID specified",
            expected_value="0 involuntary",
            description="Use --pid to specify target process",
            fix_hint="latency-audit --pid <PID> --category process",
        )

    # Read /proc/<pid>/status
    status_content = _read_proc_file(f"/proc/{pid}/status")
    if status_content is None:
        return CheckResult(
            name="context_switches",
            category=CheckCategory.PROCESS,
            status=CheckStatus.SKIP,
            current_value=f"PID {pid} not found",
            expected_value="0 involuntary",
            description=f"Could not read /proc/{pid}/status",
        )

    # Parse nonvoluntary_ctxt_switches
    involuntary = None
    for line in status_content.splitlines():
        if line.startswith("nonvoluntary_ctxt_switches:"):
            parts = line.split(":")
            if len(parts) >= 2:
                value_str = parts[1].strip()
                if value_str.isdigit():
                    involuntary = int(value_str)
            break

    if involuntary is None:
        return CheckResult(
            name="context_switches",
            category=CheckCategory.PROCESS,
            status=CheckStatus.SKIP,
            current_value="unknown",
            expected_value="0 involuntary",
            description="Could not parse context switch count",
        )

    # Determine status based on count
    if involuntary == 0:
        status = CheckStatus.PASS
        current = "0 involuntary switches"
        latency_impact = None
    elif involuntary < 10:
        status = CheckStatus.WARN
        current = f"{involuntary} involuntary switches"
        latency_impact = "+1-10µs per switch"
    else:
        status = CheckStatus.FAIL
        current = f"{involuntary} involuntary switches"
        latency_impact = "Core isolation likely breached"

    return CheckResult(
        name=f"context_switches (PID {pid})",
        category=CheckCategory.PROCESS,
        status=status,
        current_value=current,
        expected_value="0 involuntary",
        latency_impact=latency_impact,
        description="Involuntary context switch count",
        fix_hint="Check isolcpus config, taskset pinning, cgroup isolation"
        if status != CheckStatus.PASS
        else None,
    )


def check_page_faults() -> CheckResult:
    """
    Check major page fault count for target process.

    For HFT: Major page faults mean disk I/O occurred (catastrophic).
    After warmup, major fault count MUST be 0 during trading hours.
    """
    pid = get_target_pid()

    if pid is None:
        return CheckResult(
            name="page_faults",
            category=CheckCategory.PROCESS,
            status=CheckStatus.SKIP,
            current_value="no PID specified",
            expected_value="0 major faults",
            description="Use --pid to specify target process",
            fix_hint="latency-audit --pid <PID> --category process",
        )

    # Read /proc/<pid>/stat
    stat_content = _read_proc_file(f"/proc/{pid}/stat")
    if stat_content is None:
        return CheckResult(
            name="page_faults",
            category=CheckCategory.PROCESS,
            status=CheckStatus.SKIP,
            current_value=f"PID {pid} not found",
            expected_value="0 major faults",
            description=f"Could not read /proc/{pid}/stat",
        )

    # Parse stat fields (space-separated, but process name in parens may have spaces)
    # Format: pid (comm) state ppid pgrp session tty_nr tpgid flags minflt cminflt majflt ...
    # majflt is field 12 (0-indexed: 11) after the last ')'
    try:
        # Find the last ')' to skip the process name
        last_paren = stat_content.rfind(")")
        if last_paren == -1:
            raise ValueError("Invalid stat format")

        # Split the rest by spaces
        fields = stat_content[last_paren + 1 :].split()
        # fields[0] = state, fields[1] = ppid, ... fields[9] = majflt
        majflt = int(fields[9])
    except (ValueError, IndexError):
        return CheckResult(
            name="page_faults",
            category=CheckCategory.PROCESS,
            status=CheckStatus.SKIP,
            current_value="unknown",
            expected_value="0 major faults",
            description="Could not parse page fault count from /proc/stat",
        )

    if majflt == 0:
        status = CheckStatus.PASS
        current = "0 major faults"
        latency_impact = None
    else:
        status = CheckStatus.FAIL
        current = f"{majflt} major faults"
        latency_impact = "+100µs-10ms per fault (disk access)"

    return CheckResult(
        name=f"page_faults (PID {pid})",
        category=CheckCategory.PROCESS,
        status=status,
        current_value=current,
        expected_value="0 major faults",
        latency_impact=latency_impact,
        description="Major page fault count (disk I/O events)",
        fix_hint="Ensure memory is locked (mlockall), check swap usage"
        if status != CheckStatus.PASS
        else None,
    )


def register_process_checks() -> None:
    """Register all process checks with the runner."""
    runner.register_check(check_context_switches)
    runner.register_check(check_page_faults)
