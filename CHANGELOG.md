# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.4] - 2024-12-14

### Added

- **Hardware Integrity Checks**
  - PCIe Link Width & Speed validator (detects degraded NIC negotiation)
  - Memory Channel Balance audit (EDAC sysfs + dmidecode fallback)
- **Process Hygiene Checks** (requires `--pid` flag)
  - Involuntary Context Switch rate monitoring
  - Major Page Fault detection (disk I/O events)
- **Network Enhancements**
  - UDP socket buffer drops check (`RcvbufErrors`)
  - NIC hardware discard counters (`rx_missed_errors`)
- New CLI option: `--pid` for process-specific monitoring
- New categories: `hardware`, `process`

### Changed

- Updated CLI help text with new categories
- Enhanced README with Tier 1-3 feature documentation

## [0.1.3] - 2024-12-14

### Added

- **Hardware Integrity Checks**
  - PCIe Link Width & Speed validator (detects degraded NIC negotiation)
  - Memory Channel Balance audit (EDAC sysfs + dmidecode fallback)
- **Process Hygiene Checks** (requires `--pid` flag)
  - Involuntary Context Switch rate monitoring
  - Major Page Fault detection (disk I/O events)
- **Network Enhancements**
  - UDP socket buffer drops check (`RcvbufErrors`)
  - NIC hardware discard counters (`rx_missed_errors`)
- New CLI option: `--pid` for process-specific monitoring
- New categories: `hardware`, `process`

### Changed

- Updated CLI help text with new categories
- Enhanced README with Tier 1-3 feature documentation

## [0.1.0] - 2024-12-13

### Added

- Initial release with CLI skeleton
- `latency-audit` CLI command with `--version` and `--json` flags
- Pre-commit hooks (Ruff, typos, security checks)
- GitHub Actions CI/CD (lint, type-check, test, PyPI publish)
- Comprehensive documentation (README, CONTRIBUTING, LICENSE)

[Unreleased]: https://github.com/padalan/latency-audit/compare/v0.1.4...HEAD
[0.1.4]: https://github.com/padalan/latency-audit/compare/v0.1.3...v0.1.4
[0.1.3]: https://github.com/padalan/latency-audit/compare/v0.1.0...v0.1.3
[0.1.0]: https://github.com/padalan/latency-audit/releases/tag/v0.1.0
