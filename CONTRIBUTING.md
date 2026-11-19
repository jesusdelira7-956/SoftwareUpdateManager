# Contributing to Software Update Manager

Thank you for your interest in improving **Software Update Manager & Intrusion Shield**! We welcome community contributions, bug reports, and enhancements from developers of all skill levels.

---

## Core Project Tenets

Before contributing, please keep our core architectural rules in mind:

1. **Zero External Runtime Dependencies:**  
   The application core must run on clean Windows 10 & 11 installations using **100% Python Standard Library** and native Windows APIs (Registry, Win32, Netstat, Tasklist). Do not introduce third-party `pip` dependencies to the core application runtime.
2. **User Privacy & Transparency:**  
   There is zero telemetry, tracking, or background data collection. All network checks (such as optional cloud reputation or GitHub API releases) must be strictly user-facing, transparent, and non-blocking.
3. **Safety & Zero-Trust Execution:**  
   Because this tool requests Administrator elevation for package installations, all code handling external paths, process spawning, and firewall rules must adhere to strict defensive programming and input sanitization (`sanitize_untrusted_text`).

---

## How Can I Contribute?

### Reporting Bugs
- Search existing [Issues](https://github.com/jesusdelira7-956/SoftwareUpdateManager/issues) to see if the issue has already been reported.
- If not, open a new issue using our **Bug Report Template**.
- Include your Windows version/build, Python version, winget version, and steps to reproduce.

### Suggesting Enhancements
- Open an issue using the **Feature Request Template**.
- Explain the real-world problem you are trying to solve and how the suggested enhancement benefits users.

---

## Local Development Workflow

### 1. Clone & Set Up
```bash
git clone https://github.com/jesusdelira7-956/SoftwareUpdateManager.git
cd SoftwareUpdateManager
```

### 2. Run Directly from Source
```bash
python update_manager.py
```
*(Optionally pass `--no-admin` to test standard user UI handling without UAC elevation).*

### 3. Verify Code Quality & Schemas
Before opening a pull request, run the following verification checks:

```bash
# 1. Validate the PUP Blocklist schema and rules
python scripts/validate_blocklist.py

# 2. Syntax-check all Python modules
python -m py_compile update_manager.py security_auditor.py network_auditor.py

# 3. Test standalone compilation (optional but recommended)
python build_exe.py
```

---

## Pull Request Guidelines

1. Create a descriptive feature branch from `main`:
   ```bash
   git checkout -b feat/your-feature-name
   ```
2. Keep commits atomic, well-described, and formatted according to Conventional Commits (e.g., `feat:`, `fix:`, `docs:`, `ci:`).
3. Ensure automated CI checks (e.g., `validate_blocklist.py`) pass.
4. Submit your pull request to `main` with a summary of changes and testing steps completed.
