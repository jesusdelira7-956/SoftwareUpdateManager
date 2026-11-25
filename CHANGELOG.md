# 📜 Changelog — Windows Software Update Manager & Intrusion Shield

All notable changes to **Software Update Manager** are documented in this file.
This project adheres strictly to a **Zero-Dependency Architecture** (100% Python Standard Library, 0 third-party runtime `pip` packages).

---

## [v2.6.0] — 2026-11-24

### 🐛 Fixed & Enhanced
- **🔍 Winget Update Scanner & Registry Matching (`update_manager.py`)**:
  - Fixed critical Pass 1/Pass 2 indentation bug inside `check_winget_upgrades()` where updates that matched the Windows Registry were silently skipped instead of evaluated and appended.
  - Added prefix matching for version-suffixed DisplayNames (e.g., `AnythingLLM 1.12.0` ↔ `AnythingLLM`), `--include-pinned` hold detection (`📌 Pinned (Hold)` protected from `Push All`), and Windows Update COM `[Driver]` update discovery.
- **🤖 Deep AI & Dev Suite Auditor Expansion (`update_manager.py`)**:
  - Added `Docker Desktop`, `Bionic AI`, `Visual Studio Code`, `GitHub Desktop`, `Git SCM`, `FFmpeg`, `RipGrep MSVC`, and `Node.js` with word-boundary matching to eliminate substring collisions.
  - Corrected `Claude Desktop` MSIX/Store status (`🛍️ Up to Date (Store / MSIX)`) so it no longer hardcodes `Relaunch to update`.
- **⚡ Silent Update Engine & Standalone GitHub Releases (`update_manager.py`)**:
  - Enabled `Silent Install Mode (--silent --disable-interactivity)` by default with automatic interactive fallback on exit code `0x8A150013` and safe `python.exe` `CLOUDSDK_PYTHON` resolution under `pythonw.exe`.
  - Added standalone GitHub release tracking (`_query_anythingllm_github_update`), SHA-256 download logging, and silent NSIS `/S` installer execution for `AnythingLLM`.
  - Added an inline unverified package opt-in checkbox inside `RestorePointConfirmDialog` before running sequential batches.
- **🛡️ Security & Trust Gate Hardening (`security_auditor.py`) & MCP Bridge (`agent_bridge.py`)**:
  - Added `%ProgramFiles%` MSI binary probing (resolving `ArtCraft.EffectCraft` and `Microsoft Power BI Desktop`), WiX Burn `\Package Cache\` directory exemptions, quote-stripped `DisplayIcon` parsing, CLI aliases (`rg.exe`), verified CLI/SDK trust, publisher aliases (`Learning Machines`, `Docker`, `Mintplex Labs`), and `audit_all_installed_software()`.
  - Resolved cross-module calls in `agent_bridge.py` (`generate_ai_prompt_bundle` alias, pending updates in diagnostic bundle, `create_windows_restore_point`).

---

## [v2.5.0] — 2026-11-20

### ✨ Added
- **🤖 4-Tier AI Agent Permission Model & Universal PC Diagnostic Bridge (`agent_bridge.py`)**:
  - **Option A (Universal 1-Click AI Diagnostic Bundle)**: Generates an Indirect Prompt Injection (IPI)-hardened system diagnostic summary (Hardware Specs, Listening TCP Sockets, Upgradable Packages) with 1-click launchers for Microsoft Copilot, Claude Web, and ChatGPT.
  - **Option B (Zero-Port Local Stdio MCP Server)**: Connects desktop AI agents (Claude Desktop, Antigravity IDE, Cursor) via standard `stdin`/`stdout` JSON-RPC with **0 open network ports** and **0 MB GPU VRAM overhead**.
  - **4-Tier Local Agent Permission Gatekeeper**:
    - `Level 0 (Off / Air-Gapped)`: Bridge disabled.
    - `Level 1 (Read-Only Diagnostic — Default)`: Hard read-only whitelist for specs, sockets, and pending updates.
    - `Level 2 (Supervised Remediation)`: Interactive GUI confirmation popup required for every single package update or firewall toggle.
    - `Level 3 (Autonomous Maintenance)`: Sequential batch updates for trusted packages with automatic Windows System Restore Point creation and 30-minute session auto-expiry.
- **🎨 Consolidated Modern 4-Tab UI & Collapsible Accordions**:
  - Dedicated **`🤖 AI Diagnose & Agent Bridge`** main tab featuring a split-pane `ttk.PanedWindow` layout (Collapsible Accordion controls on the left, live embedded diagnostic console on the right).
  - Consolidated bottom toolbar into 4 primary action buttons alongside **`🛠 Quick Tools ▾`** and **`⚙ Update Settings ▾`** dropdown menus.
- **🛡️ Safe AI Onboarding & Video Guides (`AGENT_SAFETY.md`)**:
  - Added Third-Party AI Autonomy & Responsibility Notice, 4-step Safe Quick-Start Checklist, and curated YouTube tutorial links on MCP setup and least-privilege AI security.
- **⚙️ Automated Windows Release Pipeline (`.github/workflows/release-build.yml`)**:
  - Compiles standalone `SoftwareUpdateManager.exe` on `windows-latest`, generates `SHA256SUMS.txt`, and publishes release assets automatically.

### 🐛 Fixed
- **Exact-First Multi-Pass Registry Matcher (`update_manager.py`)**: Fixed substring collisions where short app names (e.g., `"Git"`) matched longer names (`"GitHub Desktop"`), preventing false publisher mismatch verdicts.
- **Trusted Publisher ↔ Certificate Signer Aliases (`security_auditor.py`)**: Added canonical vendor/maintainer alias mappings (`The Git Development Community` ↔ `Johannes Schindelin`, `LM Studio` ↔ `Element Labs Inc.`, `GitHub, Inc.` ↔ `GitHub`, `Google` ↔ `Google LLC`) so officially signed binaries evaluate to `🟢 Trusted`.
- **Winget Pin Footer Filter (`update_manager.py`)**: Filtered out informational Winget status lines (`1 package(s) have pins that prevent upgrade...`) and whitespace-containing IDs from the updates table.
- **CLI & Portable Executable Resolution (`security_auditor.py`)**: Extended `resolve_executable_path()` to inspect `%LOCALAPPDATA%\Microsoft\WinGet\Links` and system `PATH` via `shutil.which()`.

---

## [v2.4.0] — 2026-11-18

### ✨ Added
- **🛡️ Zero-Dependency Network Boundary Sentinel & Intrusion Shield (`network_auditor.py`)**:
  - Native Windows `netstat -ano` and `tasklist` socket auditor detecting active listening ports across local AI & developer servers (Ollama `11434`, LM Studio `1234`, Open WebUI `8081`, DwarfStar `8088`, App Hub `8890`, ComfyUI `8188`).
  - Automatic exposure classification: `🟢 Localhost (127.0.0.1)` vs. `🔴 Exposed to LAN (0.0.0.0)`.
  - **1-Click Native Windows Firewall Hardener**: Configures `SoftwareUpdateManager_Block_DevPorts_LAN` inbound block rule for exposed developer ports while keeping localhost loopback open.
  - **Indirect Prompt Injection (IPI) Metadata Sanitizer**: Strips control characters, shell metacharacters, and prompt override patterns from untrusted package fields.

---

## [v2.3.0] — 2026-11-16

### ✨ Added
- **🛡️ Pre-Update Security & Trust Gate (`security_auditor.py` & `pup_blocklist.json`)**:
  - Native Windows Authenticode digital signature verification via PowerShell `Get-AuthenticodeSignature`.
  - Suspicious install directory heuristics (`%TEMP%`, `C:\Users\Public`, `\ProgramData\`, `%AppData%\Roaming`).
  - Offline PUP/Adware blocklist (`pup_blocklist.json`) with CI schema validator (`scripts/validate_blocklist.py`).
  - Stealth registry flag detection (`SystemComponent=1` and missing `UninstallString`).
  - Optional SHA-256 cloud hash lookup against Abuse.ch MalwareBazaar and VirusTotal API v3.

---

## [v2.2.0] — 2026-11-15

### ✨ Added
- **🤖 Deep AI Software & Local Inference Suite Auditor**:
  - Multi-tier discovery across Windows Store (MSIX), Win32 Registry, and System PATH for Claude Desktop, ChatGPT Desktop, Cursor, Windsurf, Ollama, LM Studio, AnythingLLM, and GitHub Copilot.
  - Automatic Developer CLI version reconciliation (resolving Google Cloud SDK phantom update loops).

---

## [v2.0.0] — 2026-11-14

### ✨ Added
- Initial public release featuring Stage 1 Hardware Spec Scanner, Stage 2 Multi-Hive Registry & Winget Updater, Sequential One-by-One Update Pipeline with Post-Install Verification, 1-Click Windows System Restore Point Safety Net, and Standalone PyInstaller `.exe` compiler.
