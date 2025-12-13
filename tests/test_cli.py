"""
Tests for latency-audit CLI.

These are smoke tests to verify the CLI is installable and runnable.
More comprehensive tests will be added as we implement audit logic.
"""

from click.testing import CliRunner

from latency_audit import __version__
from latency_audit.cli import main


def test_version():
    """Test that version is defined and follows semver."""
    assert __version__ is not None
    parts = __version__.split(".")
    assert len(parts) == 3, "Version should be in semver format (X.Y.Z)"


def test_cli_runs():
    """Test that CLI runs without error."""
    runner = CliRunner()
    result = runner.invoke(main)
    assert result.exit_code == 0
    assert "latency-audit" in result.output


def test_cli_version_flag():
    """Test --version flag."""
    runner = CliRunner()
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_cli_json_flag():
    """Test --json flag is accepted."""
    runner = CliRunner()
    result = runner.invoke(main, ["--json"])
    assert result.exit_code == 0
    # Should contain JSON-like output (will be more structured later)
    assert "status" in result.output or "latency-audit" in result.output
