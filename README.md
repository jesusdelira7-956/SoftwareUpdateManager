# 🛡️ Windows Software Update Manager & System Auditor (v2.1)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.9+](https://img.shields.io/badge/Python-3.9%2B-brightgreen.svg)](https://www.python.org/downloads/)
[![Platform: Windows 10/11](https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-0078D6.svg)](https://microsoft.com)
[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-Donate-yellow.svg?logo=buy-me-a-coffee)](https://buymeacoffee.com/JesseInTheLab)

A portable, high-performance desktop application for **Windows 10 & Windows 11** that audits hardware specifications, performs deep software inventory, updates software **sequentially one-by-one**, tracks AI/Dev suites, orchestrates browser updates, and cryptographically verifies each installation.

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
> **Make sure to copy the entire command** including `irm` at the beginning and `| iex` at the end! Pasty only the web URL will cause PowerShell to show a `CommandNotFoundException`.

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

- **⚡ Automatic Administrator Elevation at Startup**:
  Requests UAC Administrator privileges on launch so system-wide installers (Visual C++ Runtimes, .NET, VLC, 7-Zip, Drivers) install smoothly without interrupting you with repeated permission prompts.
- **💻 Stage 1 — Universal Computer Spec & Health Scanner**:
  Dynamically detects the host PC's **Hostname, Manufacturer/Model, CPU, GPU (with VRAM), RAM (Total/Usable/Load %), Storage Drives (Used/Free GB), and Windows Build** using fast native Win32 & Registry APIs.
- **🔍 Stage 2 — Deep Software Inventory & Update Scan**:
  Audits all installed applications across 64-bit, 32-bit, and User Registry hives, queries `winget` for available version upgrades, and checks Windows Update for pending OS patches.
- **↕ Interactive Draggable Live Console Resizer**:
  Easily click and drag the splitter bar up or down to expand or shrink the live log drawer, or double-click to instantly toggle between compact and expanded views.
- **🤖 Dedicated AI Assistants & Developer Suite Tracking**:
  First-class inspection and 1-click **"🤖 AI & Dev Tools"** selection for:
  - **IDEs & AI Editors**: Visual Studio Code, Cursor AI, Android Studio, Antigravity IDE
  - **AI Assistants**: GitHub Copilot, ChatGPT Desktop, Claude Desktop, OpenAI Codex
  - **Local LLM Inference Engines**: Ollama, LM Studio, Pinokio AI
  - **Dev Infrastructure**: Docker Desktop, GitHub Desktop, Git SCM, Node.js, Python runtimes
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
├── update_manager.py            # Main application & GUI (v2.1 Master Edition)
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
