# 🛡️ Windows Software Update Manager & System Auditor (v2.3)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.9+](https://img.shields.io/badge/Python-3.9%2B-brightgreen.svg)](https://www.python.org/downloads/)
[![Platform: Windows 10/11](https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-0078D6.svg)](https://microsoft.com)
[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-Donate-yellow.svg?logo=buy-me-a-coffee)](https://buymeacoffee.com/JesseInTheLab)

A portable, high-performance desktop application for **Windows 10 & Windows 11** that audits hardware specifications, performs deep software inventory, updates software **sequentially one-by-one**, provides an offline/cloud **Pre-Update Security & Trust Gate** against PUPs/adware, audits all AI suites across Registry/Store/PATH, reconciles developer CLI versions, orchestrates browser updates, and cryptographically verifies each installation.

---

## ☕ Support the Project

If this tool saves you time maintaining your Windows PCs, consider supporting future development:

[![Buy Me A Coffee](https://img.buymeacoffee.com/button-api/?text=Buy%20me%20a%20coffee&emoji=☕&slug=JesseInTheLab&button_colour=FFDD00&font_colour=000000&font_family=Inter&outline_colour=000000&coffee_colour=ffffff)](https://buymeacoffee.com/JesseInTheLab)

👉 **[buymeacoffee.com/JesseInTheLab](https://buymeacoffee.com/JesseInTheLab)**

---

## 🚀 Easy Installation Options (Choose What Works Best For You)

### 🥇 Option 1: Standalone Single Executable (`.exe`) — Zero Prerequisites!
> **Best for casual users or running from a USB drive. Requires NO Python, NO Git, and NO Terminal!**

1. Download **`SoftwareUpdateManager.exe`** from [Releases](https://github.com/jesusdelira7-956/SoftwareUpdateManager/releases) (or compile your own with `build_exe.bat`).
2. Double-click **`SoftwareUpdateManager.exe`**.
3. Accept the UAC prompt once, and the app launches immediately!

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
Run directly with Python (uses 100% standard library, zero pip packages):
```bash
python update_manager.py
```
Or double-click **`Run_Update_Manager.bat`**.

---

## ✨ Key Features

- **🛡️ Pre-Update Security & Trust Gate (v2.3 New!)**:
  To protect against inadvertent installation or legitimization of spyware, adware, Potentially Unwanted Programs (PUPs), or hijacked binaries:
  - **Offline Authenticode Signature Verification**: Evaluates executables via PowerShell `Get-AuthenticodeSignature` to confirm valid vendor code signatures and publisher identity.
  - **Suspicious Install Path Heuristics**: Detects executables residing in anomalous or high-risk folders (`%TEMP%`, `C:\Users\Public`, `\ProgramData\`, `%AppData%\Roaming`).
  - **Built-in PUP & Adware Blocklist**: Evaluates against `pup_blocklist.json` covering notorious bundleware, hijackers, and driver boosters.
  - **Hidden SystemComponent Audit**: Detects stealth registry entries (`SystemComponent = 1` or missing `UninstallString`) commonly used by spyware to hide from the Control Panel.
  - **Optional Cloud Reputation (ThreatFox / MalwareBazaar / VirusTotal)**: Computes SHA-256 binary hashes and cross-references active malware databases without external dependencies.
  - **Tri-Tier Trust Badges & Safe Defaults**: Displays `🟢 Trusted`, `🟡 Unverified / Caution`, and `🔴 High Risk / Blocked`. High-risk items are permanently locked out of auto-batch updates, and unverified items require explicit user opt-in ("Allow Unverified" checkbox).
  - **Right-Click Security Context Menu**: Right-click any package to inspect file location, view Authenticode details, or look up its SHA-256 hash on VirusTotal.
- **⚡ Automatic Administrator Elevation at Startup**:
  Requests UAC Administrator privileges on launch so system-wide installers (Visual C++ Runtimes, .NET, VLC, 7-Zip, Drivers) install smoothly without interrupting you with repeated permission prompts.
- **🛡️ Windows System Restore Point Safety Net**:
  Before pushing batch updates, prompts you to create a Windows System Restore Point ("Before Software Update") with a single click, providing an instant safety net.
- **💻 Stage 1 — Universal Computer Spec & Health Scanner**:
  Dynamically detects the host PC's **Hostname, Manufacturer/Model, CPU, GPU (with VRAM), RAM (Total/Usable/Load %), Storage Drives (Used/Free GB), and Windows Build** using fast native Win32 & Registry APIs.
- **🔍 Stage 2 — Deep Software Inventory & Update Scan**:
  Audits all installed applications across 64-bit, 32-bit, and User Registry hives, queries `winget` for available version upgrades, and checks Windows Update for pending OS patches.
- **🤖 Deep AI Software & Local Inference Suite Auditor (v2.2 New!)**:
  Performs a deep multi-tier audit across **Windows Store / MSIX containers**, **Windows Registry (Win32)**, and **System PATH CLI runtimes** for:
  - **Claude Desktop** (Anthropic): Detects MSIX store packaging and embedded Electron delta-updater state; provides 1-click relaunch to apply pending in-app updates.
  - **ChatGPT Desktop & OpenAI Codex**: Tracks Microsoft Store app versions.
  - **Cursor AI & Windsurf**: Tracks AI IDE versions.
  - **Ollama Engine & LM Studio**: Tracks local LLM inference engines and models.
  - **AnythingLLM**: Checks real-time GitHub releases when packages are unindexed in WinGet.
  - **GitHub Copilot & Microsoft Copilot**: Tracks assistant runtimes.
  - **Dedicated "🤖 AI Suites" Hub**: View full AI inventory, color-coded update badges, 1-click launchers, store updater shortcuts, and export dedicated AI audit reports.
- **🔄 Developer CLI Auto-Reconciliation (Google Cloud SDK Bug Fix)**:
  Automatically reconciles version desync where developer tools (like `gcloud`) self-update on disk but fail to update the Windows Registry uninstaller string, permanently preventing false-positive phantom update loops.
- **🛍️ Hybrid Microsoft Store Integration**:
  Silently signals the Windows `InstallService` background update task, provides a non-intrusive status notification banner, and includes a 1-click launcher to open the Microsoft Store Library page.
- **↕ Interactive Draggable Live Console Resizer**:
  Easily click and drag the splitter bar up or down to expand or shrink the live log drawer, or double-click to instantly toggle between compact and expanded views.
- **🌐 1-Click Native Browser Update Service Trigger**:
  Click **"🌐 Update Browsers"** to silently invoke background update services for Google Chrome (`GoogleUpdate.exe`), Microsoft Edge (`MicrosoftEdgeUpdate.exe`), Brave Browser, and Mozilla Firefox.
- **🎯 Precise HRESULT Exit Code Decoding**:
  Maps raw Windows installer & Winget exit codes to human-readable statuses (e.g., `App In-Use / Locked`, `Reboot Required`, `Download Failed`, `Another Installer Active`).
- **🚀 Sequential One-by-One Pipeline + Post-Install Verification**:
  Pushes updates strictly one at a time to eliminate MSI mutex collisions, and queries the system registry post-install to verify version changes (`✓ Verified`, `⚠ Reboot Needed`, or `✗ Failed`).
- **📑 Multi-Tab Interface**:
  1. **🚀 Software Updater**: KPI summary cards, real-time search filter, AI/Dev filter, silent mode toggle, stop batch button, and collapsible live console log.
  2. **💻 Computer Specs & Installed Apps**: Full hardware breakdown, smart diagnostics, searchable installed software catalog, and **1-Click Export Audit Report (`.txt`)**.
  3. **❓ Help & User Guide**: Built-in documentation, status badge explanations, and Buy Me a Coffee support card.

---

## 📂 Repository Structure

```text
SoftwareUpdateManager/
├── update_manager.py            # Main application & GUI (v2.3 Master Edition)
├── security_auditor.py          # Pre-Update Security & Trust Gate (100% Python stdlib)
├── pup_blocklist.json           # Known PUP, adware, and high-risk path definitions
├── Install.cmd                  # 1-click double-clickable installer (Option 2)
├── install.ps1                  # Universal remote & local one-liner installer (Option 3)
├── build_exe.py                 # Standalone single-file compiler (PyInstaller)
├── build_exe.bat                # 1-click binary compiler for releases (Option 1)
├── setup_shortcut.py            # Dynamic Desktop shortcut & icon generator
├── Install_Desktop_Shortcut.bat # Desktop shortcut installer
├── Run_Update_Manager.bat       # Portable one-click launcher
├── app_icon.ico                 # Multi-resolution Windows application icon
├── requirements.txt             # Zero external dependencies (Python standard library)
├── LICENSE                      # MIT License
└── README.md                    # Documentation & Support Links
```

---

## 📜 License

Released under the [MIT License](LICENSE). Free to use, modify, and share across personal and enterprise computers.
