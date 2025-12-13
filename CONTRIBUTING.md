# Contributing to latency-audit

First off, thanks for taking the time to contribute! 🎉

This document provides guidelines and best practices for contributing to latency-audit.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Pull Request Process](#pull-request-process)
- [Style Guide](#style-guide)
- [Testing](#testing)

---

## Code of Conduct

This project adheres to a code of conduct. By participating, you are expected to uphold this code:

- **Be respectful** of differing viewpoints and experiences
- **Accept constructive criticism** gracefully
- **Focus on what's best** for the community and project
- **Show empathy** towards other community members

---

## Getting Started

### Prerequisites

- Python 3.10 or higher
- Git
- A Linux system (for running actual audits) or macOS/WSL (for development)

### Fork and Clone

1. Fork the repository on GitHub
2. Clone your fork:

```bash
git clone https://github.com/YOUR_USERNAME/latency-audit.git
cd latency-audit
```

---

## Development Setup

### 1. Create a Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 2. Install in Editable Mode with Dev Dependencies

```bash
pip install -e ".[dev]"
```

### 3. Install Pre-commit Hooks

```bash
pre-commit install
```

This ensures code quality checks run automatically before each commit.

### 4. Verify Setup

```bash
# Run tests
pytest

# Run linting
ruff check src/

# Run type checking
mypy src/
```

---

## Making Changes

### Branch Naming

Use descriptive branch names:

- `feat/add-numa-check` - New features
- `fix/swappiness-detection` - Bug fixes
- `docs/improve-readme` - Documentation
- `refactor/cli-structure` - Code refactoring

### Commit Messages

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Code style (formatting, no logic change)
- `refactor`: Code restructuring
- `test`: Adding or updating tests
- `chore`: Maintenance (deps, CI, etc.)

**Examples:**

```bash
feat(kernel): add transparent hugepages check
fix(cpu): correct c-state detection on AMD processors
docs(readme): add benchmark results table
```

---

## Pull Request Process

### Before Submitting

1. **Ensure all tests pass:**
   ```bash
   pytest
   ```

2. **Run the full pre-commit suite:**
   ```bash
   pre-commit run --all-files
   ```

3. **Update documentation** if you've changed behavior

4. **Add tests** for new functionality

### PR Description

Include in your PR description:

- **What** does this PR do?
- **Why** is this change needed?
- **How** was it tested?
- **Screenshots** (if UI/output changes)

### Review Process

1. A maintainer will review your PR
2. Address any feedback
3. Once approved, a maintainer will merge your PR

---

## Style Guide

### Code Style

- We use **Ruff** for linting and formatting
- Line length: 88 characters
- Imports are sorted automatically (isort rules via Ruff)

### Type Hints

All code should be fully typed:

```python
# Good
def check_swappiness(threshold: int = 0) -> CheckResult:
    ...

# Avoid
def check_swappiness(threshold=0):
    ...
```

### Docstrings

Use Google-style docstrings:

```python
def audit_kernel(verbose: bool = False) -> AuditResult:
    """Audit kernel configuration for latency issues.

    Args:
        verbose: If True, include detailed diagnostic info.

    Returns:
        AuditResult containing pass/fail status and details.

    Raises:
        PermissionError: If unable to read /proc/sys files.
    """
```

---

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/latency_audit

# Run specific test file
pytest tests/test_kernel.py

# Run tests matching a pattern
pytest -k "test_swappiness"
```

### Writing Tests

- Place tests in `tests/` directory
- Name test files `test_*.py`
- Name test functions `test_*`
- Use `pytest` fixtures for common setup

```python
# tests/test_kernel.py
import pytest
from latency_audit.checks.kernel import check_swappiness


def test_swappiness_pass():
    """Test that swappiness=0 passes the check."""
    result = check_swappiness(current_value=0, threshold=0)
    assert result.passed is True


def test_swappiness_fail():
    """Test that swappiness>0 fails the check."""
    result = check_swappiness(current_value=60, threshold=0)
    assert result.passed is False
```

---

## Questions?

Feel free to open an issue for:

- Bug reports
- Feature requests
- Questions about the codebase

Thank you for contributing! 🚀
