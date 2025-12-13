# ⚡ latency-audit

[![PyPI version](https://img.shields.io/pypi/v/latency-audit.svg)](https://pypi.org/project/latency-audit/)
[![Python Versions](https://img.shields.io/pypi/pyversions/latency-audit.svg)](https://pypi.org/project/latency-audit/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit)
[![CI](https://github.com/nikhilpadala/latency-audit/actions/workflows/test.yml/badge.svg)](https://github.com/nikhilpadala/latency-audit/actions)

**The HFT Validator.**
A ruthless CLI tool that audits Linux infrastructure against Tier 1 High-Frequency Trading standards.

---

## 🚨 The Problem

Default Linux kernels are tuned for **throughput** (web servers), not **latency** (trading).

A single misconfigured setting can cost you:

| Misconfiguration | Latency Penalty |
|------------------|-----------------|
| `swappiness > 0` | **+100µs** (page fault) |
| `transparent_hugepages=always` | **+50µs** (compaction stalls) |
| GRO/LRO enabled | **+30µs** per packet |
| Wrong CPU governor | **+200µs** (frequency scaling) |
| C-States enabled | **+500µs** (wake-up latency) |

**In HFT, 1 microsecond = $1M/year.** These defaults are silent killers.

---

## 🛠 What It Checks

### Kernel
- [x] Swappiness (should be 0)
- [x] Transparent Hugepages (should be `never`)
- [x] Kernel preemption model

### CPU
- [x] Frequency Governor (should be `performance`)
- [x] C-States (should be disabled)
- [x] Core Isolation (`isolcpus` configuration)
- [x] NUMA topology awareness

### Network
- [x] NIC Offloads (GRO/LRO/TSO should be OFF for latency-critical paths)
- [x] IRQ affinity
- [x] Ring buffer sizes

### Clock
- [x] TSC reliability (`constant_tsc`, `nonstop_tsc`)
- [x] Clocksource configuration

---

## 📦 Installation

```bash
pip install latency-audit
```

Or install from source for the latest:

```bash
pip install git+https://github.com/nikhilpadala/latency-audit.git
```

---

## ⚡ Usage

### Quick Audit (Read-Only)

```bash
latency-audit
```

Example output:

```
⚡ latency-audit v0.1.0

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                           KERNEL CONFIGURATION                            ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
  ✅ swappiness = 0
  ❌ transparent_hugepages = always (should be: never)
  ✅ kernel.sched_min_granularity_ns = 100000

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                            CPU CONFIGURATION                              ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
  ✅ governor = performance (all cores)
  ❌ C-States enabled (max_cstate = 9, should be: 0)
```

### JSON Output (for CI/CD)

```bash
latency-audit --json
```

```json
{
  "score": 72,
  "checks": [
    {"name": "swappiness", "status": "pass", "value": 0},
    {"name": "thp", "status": "fail", "value": "always", "expected": "never"}
  ]
}
```

### Check Specific Categories

```bash
latency-audit --category kernel
latency-audit --category cpu
latency-audit --category network
```

---

## 🔒 Security

This tool is **read-only by design**. It:

- ✅ Reads `/proc` and `/sys` filesystem
- ✅ Reads `sysctl` values
- ✅ Inspects NIC settings via `ethtool`
- ❌ Never modifies any settings
- ❌ Never requires root (though some checks are more complete with it)

---

## 🤝 Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

```bash
# Clone and install dev dependencies
git clone https://github.com/nikhilpadala/latency-audit.git
cd latency-audit
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Run tests
pytest
```

---

## 📈 Roadmap

- [ ] `--fix` mode with guided remediation
- [ ] Benchmark mode (measure actual latency)
- [ ] Docker container for isolated testing
- [ ] Ansible playbook generation
- [ ] Integration with Prometheus/Grafana

---

## 📄 License

MIT © [Nikhil Padala](https://nikhilpadala.com)

---

<p align="center">
  <sub>Built with obsessive attention to microseconds.</sub>
</p>
