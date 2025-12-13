"""
Checks package for latency-audit.

This package contains all the individual check modules organized by category:
- kernel.py: Kernel configuration checks
- cpu.py: CPU configuration checks
- network.py: Network configuration checks
- clock.py: Clock configuration checks
"""

from latency_audit.checks.clock import register_clock_checks
from latency_audit.checks.cpu import register_cpu_checks
from latency_audit.checks.kernel import register_kernel_checks
from latency_audit.checks.network import register_network_checks

# Register all checks when this package is imported
register_kernel_checks()
register_cpu_checks()
register_network_checks()
register_clock_checks()
