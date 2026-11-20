# Security Policy

The **Software Update Manager & Intrusion Shield** project treats software security, package authenticity, and system integrity as top priorities. Because this utility runs with Administrator privileges to manage system-wide updates, we enforce strict defensive design patterns across the entire codebase.

---

## Supported Versions

We provide active security maintenance and updates for the following releases:

| Version | Supported | Security Maintenance Status |
| :--- | :--- | :--- |
| **v2.5.x** | :white_check_mark: Yes | Current release (Active development & immediate security patches) |
| **v2.4.x** | :white_check_mark: Yes | Critical security fixes only |
| **< v2.4** | :x: No | Deprecated. Please update to the latest version immediately. |

---

## Reporting a Vulnerability

If you discover a security vulnerability or security bug, please report it responsibly:

> [!IMPORTANT]
> **Do NOT disclose vulnerabilities publicly in open GitHub issues, public pull requests, or forum discussions.**

### How to Report:
1. Use [GitHub Private Vulnerability Reporting](https://github.com/jesusdelira7-956/SoftwareUpdateManager/security/advisories/new) if available.
2. Alternatively, reach out directly to the maintainers through project administrative contacts.

### What to Include in Your Report:
- A clear description of the vulnerability and its potential impact.
- Step-by-step reproduction instructions or a minimal proof-of-concept.
- Affected Windows builds, environments, or specific software configurations.

### Response & Remediation SLA:
- **Initial Acknowledgment:** Within 48 hours.
- **Triage & Status Update:** Within 5 business days.
- **Fix & Coordinated Disclosure:** We will work with you to develop and verify a patch before publishing a security advisory and release notes.

---

## Core Security Invariants

Our codebase enforces the following defensive guarantees:
1. **Zero-Dependency Boundary:** Standard library only; no supply-chain risks from unvetted third-party packages.
2. **Authenticode Verification:** Evaluates digital signatures before updating executables.
3. **PUP/Adware Containment:** Blocks suspicious paths and known PUP identifiers via `pup_blocklist.json`.
4. **Network Boundary Isolation:** Audits listening TCP ports and offers 1-click native Defender Firewall hardening for local dev/AI endpoints.
5. **Input Sanitization:** Strips command separators and prompt injection tokens from untrusted package metadata.
6. **4-Tier AI Agent Permission Gatekeeper:** External AI assistants access diagnostic tools strictly through zero-port stdio JSON-RPC. Mutating operations (Level 2/3) enforce mandatory interactive confirmation modals, session timeouts, and automatic Windows System Restore Points.
