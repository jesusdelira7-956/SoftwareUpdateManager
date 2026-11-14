# 🛡️ Windows Software Update Manager & System Auditor (v2.0)

A portable, zero-dependency Python desktop application for **Windows 10 & Windows 11** that works automatically on **any user account and any computer**.

It performs a **two-stage startup scan** (Hardware Specifications &rarr; Deep Software Inventory), lists all available software updates via Windows Package Manager (`winget`), pushes updates **sequentially one-by-one**, and verifies each installation upon completion.

---

## ✨ Key Features

- **⚡ Automatic Administrator Elevation at Startup**:
  Requests UAC Administrator privileges on launch so system-wide installers (such as Visual C++ Redistributables, .NET Runtimes, VLC, 7-Zip, and Drivers) install smoothly without interrupting you with repeated permission prompts.
- **💻 Stage 1 — Universal Computer Spec & Health Scanner**:
  Dynamically detects the host PC's **Hostname, Manufacturer/Model, CPU, GPU (with VRAM), RAM (Total/Usable/Load %), Storage Drives (Used/Free GB), and Windows Build** using fast native Win32 & Registry APIs. Automatically updates the UI header badge and generates tailored hardware health recommendations.
- **🔍 Stage 2 — Deep Software Inventory & Update Scan**:
  Audits all installed applications across 64-bit, 32-bit, and User Registry hives, queries `winget` for available version upgrades, and checks Windows Update for pending OS patches.
- **🚀 Sequential One-by-One Update Pipeline + Verification**:
  Pushes updates strictly one at a time to prevent MSI installer lock collisions. After each installer exits, the engine verifies the installed version and marks each package as `✓ Verified`, `⚠ Reboot Needed`, or `✗ Failed`.
- **🔔 Separate Windows OS Update Reminder**:
  Detects pending Windows Security & Cumulative updates (e.g., `KB` patches and Defender definitions), reminds you that OS updates are installed separately to protect System Restore points, and provides a 1-click **"Open Windows Update"** button.
- **📑 Multi-Tab User-Friendly Interface**:
  1. **🚀 Software Updater**: KPI summary cards, real-time search filter, Select All / Highlighted updates, Silent Mode (`--silent`) toggle, Stop Batch button, and collapsible Live Console Log.
  2. **💻 Computer Specs & Installed Apps**: Full hardware breakdown, smart diagnostics, searchable installed software catalog, and **1-Click Export Audit Report (`.txt`)**.
  3. **❓ Help & User Guide**: Built-in documentation explaining every feature and status badge.

---

## 🚀 Quick Start (For Any User / Any Windows PC)

### Prerequisites
- **Operating System**: Windows 10 (1809+) or Windows 11 (includes `winget` / App Installer by default).
- **Python**: Python 3.9 or newer ([Download Python](https://www.python.org/downloads/) — uses only standard library `tkinter`, `ctypes`, `winreg`).

### Installation & Usage
1. **Clone or Download** this repository to any folder on your computer:
   ```bash
   git clone https://github.com/jesusdelira7-956/SoftwareUpdateManager.git
   cd SoftwareUpdateManager
   ```
2. **Create Desktop Shortcut (One Click)**:
   Double-click **`Install_Desktop_Shortcut.bat`** (or run `python setup_shortcut.py`).
   - This automatically finds Python on your computer, ensures `app_icon.ico` is present, and places the **"Software Update Manager"** shortcut on your Desktop.
3. **Launch the App**:
   - Double-click **"Software Update Manager"** on your Desktop, **OR**
   - Double-click **`Run_Update_Manager.bat`**, **OR**
   - Run via terminal:
     ```bash
     python update_manager.py
     ```

---

## 📂 Repository Structure

```text
SoftwareUpdateManager/
├── update_manager.py            # Main GUI application (v2.0 Universal Edition)
├── setup_shortcut.py            # Dynamic Desktop shortcut & icon generator for any PC
├── Install_Desktop_Shortcut.bat # One-click Desktop shortcut installer
├── Run_Update_Manager.bat       # Portable one-click launcher
├── app_icon.ico                 # Multi-resolution Windows application icon
├── requirements.txt             # Zero external dependencies (Python standard library)
├── LICENSE                      # MIT License
└── README.md                    # Documentation
```

---

## 🛠️ Command-Line Options

| Flag | Description |
| :--- | :--- |
| *(default)* | Automatically requests Administrator UAC elevation at startup and begins the 2-stage scan. |
| `--no-admin` | Runs in Standard User mode without requesting UAC elevation on startup. |

---

## 📜 License

Released under the [MIT License](LICENSE). Free to use, modify, and share across personal and enterprise computers.
