"""
Tests for process hygiene checks.

These tests mock the /proc filesystem reads to verify
check logic works correctly for various scenarios.
"""

from unittest.mock import patch

from latency_audit.checks.process import (
    check_context_switches,
    check_page_faults,
    set_target_pid,
)
from latency_audit.models import CheckStatus


class TestContextSwitches:
    """Tests for the involuntary context switch check."""

    def test_no_pid_skips(self) -> None:
        """No PID specified should skip."""
        set_target_pid(None)
        result = check_context_switches()
        assert result.status == CheckStatus.SKIP
        assert "no PID" in result.current_value

    def test_zero_switches_passes(self) -> None:
        """Zero involuntary context switches should pass."""
        set_target_pid(1234)

        status_content = """
Name:   trading_app
State:  S (sleeping)
Pid:    1234
voluntary_ctxt_switches:    500
nonvoluntary_ctxt_switches: 0
"""
        with patch(
            "latency_audit.checks.process._read_proc_file",
            return_value=status_content,
        ):
            result = check_context_switches()
            assert result.status == CheckStatus.PASS
            assert "0 involuntary" in result.current_value

    def test_few_switches_warns(self) -> None:
        """Less than 10 involuntary switches should warn."""
        set_target_pid(1234)

        status_content = """
Name:   trading_app
nonvoluntary_ctxt_switches: 5
"""
        with patch(
            "latency_audit.checks.process._read_proc_file",
            return_value=status_content,
        ):
            result = check_context_switches()
            assert result.status == CheckStatus.WARN
            assert "5 involuntary" in result.current_value

    def test_many_switches_fails(self) -> None:
        """10 or more involuntary switches should fail."""
        set_target_pid(1234)

        status_content = """
Name:   trading_app
nonvoluntary_ctxt_switches: 50
"""
        with patch(
            "latency_audit.checks.process._read_proc_file",
            return_value=status_content,
        ):
            result = check_context_switches()
            assert result.status == CheckStatus.FAIL
            assert "50 involuntary" in result.current_value

    def test_pid_not_found_skips(self) -> None:
        """Non-existent PID should skip."""
        set_target_pid(99999)

        with patch(
            "latency_audit.checks.process._read_proc_file",
            return_value=None,
        ):
            result = check_context_switches()
            assert result.status == CheckStatus.SKIP


class TestPageFaults:
    """Tests for the major page fault check."""

    def test_no_pid_skips(self) -> None:
        """No PID specified should skip."""
        set_target_pid(None)
        result = check_page_faults()
        assert result.status == CheckStatus.SKIP
        assert "no PID" in result.current_value

    def test_zero_faults_passes(self) -> None:
        """Zero major page faults should pass."""
        set_target_pid(1234)

        # /proc/<pid>/stat format:
        # pid (comm) state ppid pgrp session tty tpgid flags minflt cminflt majflt ...
        # Fields after ')': state ppid pgrp session tty tpgid flags minflt cminflt majflt
        #                   [0]   [1]  [2]   [3]    [4]  [5]   [6]    [7]     [8]    [9]
        stat_content = (
            "1234 (trading_app) S 1 1234 1234 0 -1 4194304 1000 0 0 0 0 0 0 0"
        )

        with patch(
            "latency_audit.checks.process._read_proc_file",
            return_value=stat_content,
        ):
            result = check_page_faults()
            assert result.status == CheckStatus.PASS
            assert "0 major" in result.current_value

    def test_faults_detected_fails(self) -> None:
        """Non-zero major page faults should fail."""
        set_target_pid(1234)

        # majflt is field 9 after the last ')'
        # state ppid pgrp session tty tpgid flags minflt cminflt majflt
        stat_content = "1234 (trading_app) S 1 1234 1234 0 -1 4194304 1000 0 5 0 0 0 0"

        with patch(
            "latency_audit.checks.process._read_proc_file",
            return_value=stat_content,
        ):
            result = check_page_faults()
            assert result.status == CheckStatus.FAIL
            assert "5 major" in result.current_value

    def test_pid_not_found_skips(self) -> None:
        """Non-existent PID should skip."""
        set_target_pid(99999)

        with patch(
            "latency_audit.checks.process._read_proc_file",
            return_value=None,
        ):
            result = check_page_faults()
            assert result.status == CheckStatus.SKIP

    def test_process_name_with_spaces(self) -> None:
        """Process name with spaces should parse correctly."""
        set_target_pid(1234)

        # Process name with spaces in parentheses
        stat_content = (
            "1234 (my trading app) S 1 1234 1234 0 -1 4194304 1000 0 0 0 0 0 0"
        )

        with patch(
            "latency_audit.checks.process._read_proc_file",
            return_value=stat_content,
        ):
            result = check_page_faults()
            assert result.status == CheckStatus.PASS
