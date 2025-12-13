# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability in `latency-audit`, please report it responsibly:

1. **Do NOT** open a public GitHub issue
2. Email: [contact@nikhilpadala.com](mailto:contact@nikhilpadala.com)
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

## Response Timeline

- **Acknowledgement**: Within 48 hours
- **Initial Assessment**: Within 7 days
- **Resolution**: Depends on severity, typically within 30 days

## Scope

This tool is **read-only by design** — it only reads from `/proc`, `/sys`, and system utilities. However, we take the following seriously:

- Command injection vulnerabilities
- Path traversal attacks
- Information disclosure beyond intended scope
- Dependency vulnerabilities

## Recognition

Security researchers who responsibly disclose vulnerabilities will be credited in the release notes (unless they prefer anonymity).
