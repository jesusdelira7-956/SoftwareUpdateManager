<div align="center">

<img src="assets/circle_logo_large.png" alt="Software Update Manager — Jesse In The Lab" width="140" />

# 🛡️ Windows Software Update Manager & Intrusion Shield (v2.6.0)

**Sequential Verified Software Updates • Authenticode & PUP Trust Gate • `0.0.0.0` LAN Intrusion Shield • Zero-Port 4-Tier AI MCP Bridge**

[![Download Standalone EXE](https://img.shields.io/badge/⬇_Download_.EXE-SoftwareUpdateManager_v2.6.0-0078D6?style=for-the-badge&logo=windows&logoColor=white)](https://github.com/jesusdelira7-956/SoftwareUpdateManager/releases/latest)
[![Buy Me A Coffee](https://img.shields.io/badge/☕_Buy_Me_A_Coffee-Support_Development-FFDD00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black)](https://buymeacoffee.com/JesseInTheLab)
[![Universal Linux Edition](https://img.shields.io/badge/🐧_Universal_Linux_Edition-Also_Available-E95420?style=for-the-badge&logo=linux&logoColor=white)](https://github.com/jesusdelira7-956/SoftwareUpdateManager-Linux)

[![GitHub Release](https://img.shields.io/github/v/release/jesusdelira7-956/SoftwareUpdateManager?style=flat-square&label=Latest%20Release&color=brightgreen)](https://github.com/jesusdelira7-956/SoftwareUpdateManager/releases/latest)
[![Zero Dependencies](https://img.shields.io/badge/Dependencies-0%20(100%25%20Python%20Stdlib)-success?style=flat-square)](requirements.txt)
[![CI Schema Check](https://img.shields.io/github/actions/workflow/status/jesusdelira7-956/SoftwareUpdateManager/validate-blocklist.yml?style=flat-square&label=PUP%20Blocklist%20CI)](https://github.com/jesusdelira7-956/SoftwareUpdateManager/actions)
[![Platform: Windows 10/11](https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-0078D6?style=flat-square&logo=windows)](https://microsoft.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue?style=flat-square)](LICENSE)

</div>

---

A portable, high-performance desktop application for **Windows 10 & Windows 11** built with **100% Python Standard Library (zero third-party `pip` dependencies)**. It audits hardware specifications, scans installed software across all Registry hives, updates packages **sequentially one-by-one**, enforces an offline/cloud **Pre-Update Security & Trust Gate** against PUPs/adware, defends against LAN network probes with the **Network Boundary Sentinel & Intrusion Shield**, and connects safely to AI assistants via a **4-Tier Local Agent Permission Model & Zero-Port Stdio MCP Server**.

> [!NOTE]
> **Our Mission:** Keep your Windows PC fully updated while proactively protecting it from unknown network intrusions, exposed local AI ports (`0.0.0.0`), and untrusted binaries — **100% Free, Transparent, & Open-Source.**

---

## ⚡ Why Software Update Manager Instead of Raw `winget upgrade --all`?

| Capability | Raw `winget upgrade --all` | 🛡️ Software Update Manager (v2.6.0) |
| :--- | :---: | :---: |
| **Installer Execution** | Uncontrolled batch (risks MSI mutex collisions) | **Sequential One-by-One Pipeline** with post-install Registry verification |
| **Digital Signature & PUP Check** | ❌ None | **Pre-Update Trust Gate** (Authenticode verify, publisher-signer alias check, `pup_blocklist.json`, SHA-256 hash lookup) |
| **System Rollback Safety** | ❌ Manual | **1-Click Automatic Windows System Restore Point** before batch updates |
| **Local AI & Dev Port Security** | ❌ None | **Network Boundary Sentinel** (Flags `0.0.0.0` LAN exposure on Ollama/LM Studio/WebUI + 1-Click Firewall Hardener) |
| **AI Assistant Integration** | ❌ None | **4-Tier Permission Gatekeeper + Zero-Port Stdio MCP Server** (Claude Desktop, Antigravity, Cursor, Copilot) |
| **CLI Desync Loops (e.g. `gcloud`)** | ❌ Infinite phantom update loop | **Auto-Reconciles** on-disk CLI versions with Windows Registry uninstall keys |
| **Runtime Dependencies** | CLI only | **Zero `pip` packages** (100% Python Standard Library or 1-Click Portable `.exe`) |

---

## ☕ Support the Project

If this tool saves you time maintaining and securing your Windows PCs, consider supporting future development:

[![Buy Me A Coffee](https://img.buymeacoffee.com/button-api/?text=Buy%20me%20a%20coffee&emoji=☕&slug=JesseInTheLab&button_colour=FFDD00&font_colour=000000&font_family=Inter&outline_colour=000000&coffee_colour=ffffff)](https://buymeacoffee.com/JesseInTheLab)

👉 **[buymeacoffee.com/JesseInTheLab](https://buymeacoffee.com/JesseInTheLab)**

---

## 🚀 Easy Installation Options (Choose What Works Best For You)

### 🥇 Option 1: Standalone Single Executable (`.exe`) — Zero Prerequisites!
> **Best for instant use or running from a USB drive. Requires NO Python, NO Git, and NO Terminal!**

1. Download **`SoftwareUpdateManager.exe`** from **[GitHub Releases (v2.5.0)](https://github.com/jesusdelira7-956/SoftwareUpdateManager/releases/latest)** (or compile your own locally with `build_exe.bat`).
2. Double-click **`SoftwareUpdateManager.exe`**.
3. Accept the UAC Administrator prompt once, and the app launches immediately!

---

### 🥈 Option 2: 1-Click `Install.cmd` (Double-Click from Windows Explorer)
> **Best if you download the ZIP or clone the repository.**

1. Download or clone this repository.
2. Double-click **`Install.cmd`**.
   - Automatically detects if Python is missing and installs Python 3.12 via `winget`.
   - Generates the Desktop & Start Menu shortcuts with icons.
   - Launches the app. Zero typing required!

---

### 🥉 Option 3: PowerShell Fast Web One-Liner (Remote Install)
> **Best for IT admins or quickly provisioning a new Windows machine.**

Open **PowerShell** (Run as Administrator recommended) and paste the **entire line**:

```powershell
irm https://raw.githubusercontent.com/jesusdelira7-956/SoftwareUpdateManager/main/install.ps1 | iex
```

> [!IMPORTANT]
> **Make sure to copy the entire command** including `irm` at the beginning and `| iex` at the end! Pasting only the web URL will cause PowerShell to show a `CommandNotFoundException`.

#### What the one-liner does automatically:
- Checks Windows Package Manager (`winget`).
- If Python is missing, installs Python 3.12 automatically in the background.
- Stages the latest application files to `$env:USERPROFILE\SoftwareUpdateManager`.
- Places high-resolution **"Software Update Manager"** shortcuts on your **Desktop** and **Start Menu**.
- Launches the application.

---

### 🛠️ Option 4: Portable / Developer Run
Run directly with Python (uses 100% standard library, zero `pip` packages):
```bash
python update_manager.py
```
Or double-click **`Run_Update_Manager.bat`**.

---

## ✨ Key Features

- **🤖 4-Tier AI Agent Permission Model & Universal PC Diagnostic Bridge (v2.5.0)**:
  Exposes verified system diagnostics and update modules to any AI assistant (Microsoft Copilot, Claude Desktop, Antigravity IDE, Cursor, or local LLMs) without violating zero-dependency or intrusion-shield security:
  - **Universal 1-Click AI Diagnostic Bundle (Option A)**: Compiles an injection-hardened diagnostic summary (Specs, Listening Sockets, Updates) to the clipboard with an expert diagnostic prompt and 1-click launchers for Copilot, Claude Web, and ChatGPT.
  - **Zero-Dependency Stdio MCP Server (`agent_bridge.py` - Option B)**: Connects directly to Claude Desktop, Antigravity, or Cursor using standard `sys.stdin`/`sys.stdout` JSON-RPC with 1-click local client launchers. **Zero open TCP ports** (`0.0.0.0` or `127.0.0.1`) — completely immune to external network probes.
  - **4-Tier Permission Gatekeeper**:
    - **Level 0 (Off / Air-Gapped)**: Bridge completely inactive (Zero attack surface).
    - **Level 1 (Read-Only Diagnostic — Recommended Default)**: Hard read-only whitelist for specs, ports, and updates. Output sanitized against Indirect Prompt Injection (IPI).
    - **Level 2 (Supervised Remediation)**: Allows single-package upgrades and firewall toggling. Every write operation pauses and requires an interactive confirmation modal in the GUI.
    - **Level 3 (Autonomous Maintenance)**: Automated sequential batch updates for trusted packages with an automatic Windows System Restore Point and a 30-minute session auto-expiry.
  - **Third-Party AI Autonomy Notice & Safe Quick-Start Guide**: Built-in safety checklist and curated video tutorials (also documented in [`AGENT_SAFETY.md`](AGENT_SAFETY.md)).
- **🛡️ Zero-Dependency Network Boundary Sentinel & Intrusion Shield (v2.4)**:
  Proactively protects your PC from autonomous network exploitation frameworks, unauthenticated local AI endpoints, and lateral LAN snooping:
  - **Zero-Dependency Socket Auditor (`network_auditor.py`)**: Uses native Windows `netstat` and `tasklist` (100% Python standard library) to identify all active listening TCP ports across local AI and developer daemons (Ollama `11434`, LM Studio `1234`, Open WebUI `8081`, DwarfStar `8088`, Antigravity App Hub `8890`, OpenCode `49374`, ComfyUI `8188`, dev ports `3000-5000`, `8000-9000`).
  - **Exposure Classification**: Automatically tags every AI tool as `🟢 Localhost (Isolated)` (bound strictly to `127.0.0.1`), `🔴 Exposed to LAN (0.0.0.0)` (bound to all interfaces and reachable from Wi-Fi/LAN devices), or `⚪ Desktop Native (Offline Client)`.
  - **1-Click Native Firewall Hardener**: Toggle **"🛡️ Harden Firewall (Block LAN Probes)"** to configure a native Windows Defender Firewall rule (`SoftwareUpdateManager_Block_DevPorts_LAN`) blocking incoming LAN probes on developer/AI ports while keeping `127.0.0.1` localhost loopback 100% open.
  - **Package Metadata Sanitization**: Sanitizes untrusted package descriptions, display names, and arguments against Indirect Prompt Injection (IPI) and argument tampering.
- **🛡️ Pre-Update Security & Trust Gate (`security_auditor.py`)**:
  To protect against inadvertent installation of spyware, adware, Potentially Unwanted Programs (PUPs), or hijacked binaries:
  - **Offline Authenticode Signature Verification & Alias Resolution**: Evaluates executables via PowerShell `Get-AuthenticodeSignature` and cross-checks canonical publisher ↔ certificate signer aliases (e.g., *Git for Windows* / *Johannes Schindelin*, *LM Studio* / *Element Labs Inc.*, *GitHub*, *Google LLC*).
  - **Exact-First Multi-Pass Registry Matching**: Matches packages via exact name, exact Winget ID, and alphanumeric tokens before falling back to `%LOCALAPPDATA%\Microsoft\WinGet\Links` and system `PATH`.
  - **Suspicious Install Path Heuristics**: Detects executables residing in high-risk folders (`%TEMP%`, `C:\Users\Public`, `\ProgramData\`, `%AppData%\Roaming`).
  - **Built-in PUP & Adware Blocklist**: Evaluates against `pup_blocklist.json` covering notorious bundleware, hijackers, and driver boosters.
  - **Hidden SystemComponent Audit**: Detects stealth registry entries (`SystemComponent = 1` or missing Win32 `UninstallString`).
  - **Optional Cloud Reputation (MalwareBazaar / VirusTotal)**: Computes SHA-256 binary hashes and cross-references active malware databases without external dependencies.
  - **Tri-Tier Trust Badges & Safe Defaults**: Displays `🟢 Trusted`, `🟡 Unverified`, and `🔴 High Risk`. High-risk items are permanently locked out of auto-batch updates, and unverified items (such as unsigned open-source builds) can be opted in via `⚙ Update Settings ▾ -> Allow Unverified`.
- **💻 Stage 1 & Stage 2 Hardware + Software Inventory**:
  Dynamically detects **Hostname, Manufacturer/Model, CPU, GPU (with VRAM), RAM, Storage Drives, and Windows Build**, audits 64-bit/32-bit/User Registry hives, reconciles CLI versions (`gcloud`), triggers browser updaters (Chrome, Edge, Brave, Firefox), and checks Microsoft Store apps.
- **📑 Modernized 4-Tab Interface & Consolidated Dropdown Toolbars**:
  1. **🚀 Software Updater**: KPI summary cards, real-time search filter, AI/Dev filter, consolidated **`🛠 Quick Tools ▾`** and **`⚙ Update Settings ▾`** dropdown menus, and draggable live console log.
  2. **💻 Computer Specs & Installed Apps**: Full hardware breakdown, smart diagnostics, searchable installed software catalog, and **1-Click Export Audit Report (`.txt`)**.
  3. **🤖 AI Diagnose & Agent Bridge**: Split-pane workspace with collapsible accordion controls (`CollapsiblePane`) on the left and a live diagnostic & security scan output console on the right.
  4. **❓ Help & User Guide**: Built-in documentation, status badge explanations, safe AI onboarding checklist, and support links.

---

## 📂 Repository Structure

```text
SoftwareUpdateManager/
├── .github/
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug_report.md          # Structured bug reporting form
│   │   └── feature_request.md     # Architectural feature proposal form
│   ├── workflows/
│   │   ├── release-build.yml      # Automated Windows .exe compiler & GitHub Release publisher
│   │   └── validate-blocklist.yml # GitHub Actions CI schema validator
│   ├── FUNDING.yml                # Native GitHub "Sponsor" button config
│   └── pull_request_template.md   # PR quality & testing checklist
├── assets/                        # Application icons, emblems, and visual banners
├── scripts/
│   └── validate_blocklist.py      # Zero-dependency blocklist schema checker
├── update_manager.py              # Main application & GUI (v2.5.0 Master Edition)
├── agent_bridge.py                # Zero-dependency Stdio MCP Server & AI Bridge (v2.5.0)
├── network_auditor.py             # Network Boundary Sentinel & Intrusion Shield
├── security_auditor.py            # Pre-Update Security & Trust Gate (100% Python stdlib)
├── pup_blocklist.json             # Known PUP, adware, and high-risk path definitions
├── AGENT_SAFETY.md                # AI Agent integration, least privilege & video guides
├── CHANGELOG.md                   # Release history & version ledger
├── CODE_OF_CONDUCT.md             # Community standards & behavioral pledge
├── CONTRIBUTING.md                # Contributor guide & zero-pip architecture rules
├── SECURITY.md                    # Vulnerability reporting & supported versions policy
├── Install.cmd                    # 1-click double-clickable installer (Option 2)
├── install.ps1                    # Universal remote & local one-liner installer (Option 3)
├── build_exe.py                   # Standalone single-file compiler (PyInstaller)
├── build_exe.bat                  # 1-click binary compiler for releases (Option 1)
├── setup_shortcut.py              # Dynamic Desktop shortcut & icon generator
├── Install_Desktop_Shortcut.bat   # Desktop shortcut installer
├── Run_Update_Manager.bat         # Portable one-click launcher
├── app_icon.ico                   # Multi-resolution Windows application icon
├── requirements.txt               # Zero external dependencies (Python standard library)
├── LICENSE                        # MIT License
└── README.md                      # Documentation & 1-Click Download Links
```

---

## 📜 License & Privacy Notice

Released under the [MIT License](LICENSE). Free to use, modify, and share across personal and enterprise computers.

> **Privacy & Anti-Solicitation Notice:** Automated scraping of maintainer contact details, unsolicited third-party "trust index" or badge-farming outreach, and commercial email solicitations regarding this repository are unwelcome. All legitimate inquiries and bug reports belong exclusively in **GitHub Issues**. Please respect developer privacy.
