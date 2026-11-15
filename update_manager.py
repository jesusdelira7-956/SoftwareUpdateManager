"""
Universal Windows Software Update Manager & System Auditor (v2.0)
=================================================================
A portable, zero-dependency Python desktop application for Windows 10 & 11.
Works across any user account and any computer configuration.

Workflow:
1. Requests Administrator elevation at launch so package installers run smoothly without UAC interruptions.
2. Stage 1 Scan: Dynamically detects the host computer's hardware & OS specifications (CPU, GPU, RAM, Disks, OS Build).
3. Stage 2 Scan: Performs a deep scan of all installed software and queries Winget + Windows Update for available upgrades.
4. Sequential Push & Verification: Installs updates one-by-one and verifies each package post-install.
5. Includes a dedicated System Specs & Inventory tab and a comprehensive Help & User Guide tab.
"""

import os
import re
import sys
import json
import time
import queue
import string
import shutil
import ctypes
import winreg
import platform
import threading
import subprocess
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
from datetime import datetime
from pathlib import Path

APP_NAME = "Software Update Manager"
APP_VERSION = "2.1.0"
APP_DIR = Path(__file__).parent.resolve()
LOG_FILE = APP_DIR / "update_history.log"
DONATION_URL = "https://buymeacoffee.com/JesseInTheLab"


def get_asset_file(filename: str) -> Path:
    """Resolve asset paths both in PyInstaller bundled environments and source directories."""
    if hasattr(sys, "_MEIPASS"):
        p_bundle = Path(sys._MEIPASS) / "assets" / filename
        if p_bundle.exists():
            return p_bundle
        p_bundle_root = Path(sys._MEIPASS) / filename
        if p_bundle_root.exists():
            return p_bundle_root
    p_local = APP_DIR / "assets" / filename
    if p_local.exists():
        return p_local
    return APP_DIR / filename


ICON_FILE = get_asset_file("app_icon.ico")
LOGO_FILE = get_asset_file("circle_logo.png")
LOGO_LARGE_FILE = get_asset_file("circle_logo_large.png")
HEADER_BG_FILE = get_asset_file("header_banner.png")
WINDOW_BG_FILE = get_asset_file("window_bg.png")

# AI Assistants, Developer Environments & Local Inference Suite tracking
AI_DEV_PACKAGES = {
    "Microsoft.VisualStudioCode": "Visual Studio Code",
    "Anysphere.Cursor": "Cursor AI",
    "Google.AndroidStudio": "Android Studio",
    "Google.Antigravity": "Antigravity IDE",
    "GitHub.CopilotApp": "GitHub Copilot",
    "OpenAI.ChatGPT": "ChatGPT Desktop",
    "OpenAI.Codex": "OpenAI Codex",
    "Anthropic.Claude": "Claude Desktop",
    "Ollama.Ollama": "Ollama LLM Engine",
    "ElementLabs.LMStudio": "LM Studio",
    "pinokiocomputer.pinokio": "Pinokio AI Browser",
    "Docker.DockerDesktop": "Docker Desktop",
    "GitHub.GitHubDesktop": "GitHub Desktop",
    "Git.Git": "Git SCM",
    "Python.Python.3.12": "Python 3.12",
    "Python.Python.3.11": "Python 3.11",
    "Nodejs.Nodejs": "Node.js",
}

# Known winget (APPINSTALLER_CLI_ERROR_*) HRESULTs & Windows installer exit codes
EXIT_CODE_MAP = {
    0: ("✓ Verified", "Installed successfully"),
    3010: ("⚠ Reboot Needed", "Restart required to complete"),
    1641: ("⚠ Reboot Needed", "Restart initiated by installer"),
    1602: ("✗ Cancelled", "Installation cancelled by user"),
    1618: ("✗ Busy", "Another installer is already running"),
    0x8A150006: ("✗ Failed", "Installer error (manual install required)"),
    0x8A150008: ("✗ Network Err", "Download failed"),
    0x8A150011: ("✗ Hash Err", "Installer hash mismatch"),
    0x8A150014: ("✗ Not Found", "Package not found in source"),
    0x8A15002B: ("✓ Up to Date", "Already at the latest version"),
    0x8A150101: ("✗ App In-Use", "Application is open. Close and retry."),
    0x8A150102: ("✗ Busy", "Another installer in progress"),
    0x8A150103: ("✗ File In-Use", "Files locked by running program"),
    0x8A150105: ("✗ Disk Full", "Insufficient disk space"),
    0x8A150107: ("✗ Offline", "No internet connection"),
    0x8A150109: ("⚠ Reboot Needed", "Restart required to finish"),
    0x8A15010A: ("⚠ Reboot Needed", "Restart required before install"),
    0x8A15010B: ("⚠ Reboot Needed", "Installer requested restart"),
    0x8A15010C: ("✗ Cancelled", "Installation cancelled"),
    0x8A15010D: ("✓ Up to Date", "Already up to date"),
}


def decode_winget_exit_code(code: int) -> tuple[str, str]:
    """Decode signed or unsigned winget exit code into a human-readable badge & detail."""
    u_code = code & 0xFFFFFFFF
    if code in EXIT_CODE_MAP:
        return EXIT_CODE_MAP[code]
    if u_code in EXIT_CODE_MAP:
        return EXIT_CODE_MAP[u_code]
    return (f"✗ Code {code}", f"Process exited with code {code}")


def trigger_browser_background_updates() -> list[str]:
    """Trigger native background updater services for Chrome, Edge, Brave, and Firefox."""
    triggered = []
    browser_paths = [
        ("Google Chrome", [
            r"C:\Program Files\Google\Update\GoogleUpdate.exe",
            r"C:\Program Files (x86)\Google\Update\GoogleUpdate.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Update\GoogleUpdate.exe"),
        ], ["/c"]),
        ("Microsoft Edge", [
            r"C:\Program Files (x86)\Microsoft\EdgeUpdate\MicrosoftEdgeUpdate.exe",
            r"C:\Program Files\Microsoft\EdgeUpdate\MicrosoftEdgeUpdate.exe",
        ], ["/c"]),
        ("Brave Browser", [
            r"C:\Program Files\BraveSoftware\Update\BraveUpdate.exe",
            r"C:\Program Files (x86)\BraveSoftware\Update\BraveUpdate.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\BraveSoftware\Update\BraveUpdate.exe"),
        ], ["/c"]),
        ("Mozilla Firefox", [
            r"C:\Program Files\Mozilla Firefox\firefox.exe",
            r"C:\Program Files (x86)\Mozilla Firefox\firefox.exe",
        ], ["-os-recheck"]),
    ]
    for b_name, exes, args in browser_paths:
        for exe in exes:
            if os.path.exists(exe):
                try:
                    subprocess.Popen([exe] + args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    triggered.append(b_name)
                    break
                except Exception:
                    pass
    return triggered


def create_windows_restore_point(description: str = "Before Software Update") -> tuple[bool, str]:
    """Create a Windows System Restore Point using PowerShell Checkpoint-Computer."""
    clean_desc = description.replace("'", "").replace('"', "")
    ps_cmd = (
        f"$ErrorActionPreference = 'Stop'; "
        f"Checkpoint-Computer -Description '{clean_desc}' -RestorePointType 'APPLICATION_INSTALL'"
    )
    try:
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        res = subprocess.run(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_cmd],
            capture_output=True, text=True, errors="replace", timeout=120, startupinfo=startupinfo
        )
        out = (res.stdout + " " + res.stderr).strip()
        if res.returncode == 0:
            return True, "System Restore Point created successfully."
        if "1440" in out or "already exists" in out.lower():
            return True, "Recent restore point already exists (created within the last 24 hours)."
        if "disabled" in out.lower() or "not enabled" in out.lower() or "0x80042306" in out:
            return False, "System Protection is currently disabled on drive C: in Windows Settings."
        return False, out[:150] if out else f"Code {res.returncode}"
    except subprocess.TimeoutExpired:
        return False, "Restore point creation timed out."
    except Exception as e:
        return False, str(e)


# =====================================================================
# ADMINISTRATOR PRIVILEGE & STARTUP HELPERS
# =====================================================================
def is_User_Admin() -> bool:
    """Return True if the current process has Administrator privileges."""
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def relaunch_as_admin():
    """Relaunch the current Python script with UAC Administrator elevation."""
    try:
        script_path = os.path.abspath(sys.argv[0])
        extra_args = [f'"{a}"' for a in sys.argv[1:] if a != "--elevated"]
        params = f'"{script_path}" --elevated ' + " ".join(extra_args)

        # Prefer pythonw.exe so no console window stays open behind the GUI
        exe = sys.executable
        pythonw = Path(exe).with_name("pythonw.exe")
        if pythonw.exists():
            exe = str(pythonw)

        ret = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", exe, params.strip(), str(APP_DIR), 1
        )
        if int(ret) > 32:
            sys.exit(0)
    except Exception:
        pass


def enable_high_dpi():
    """Enable crisp high-DPI scaling on modern Windows displays."""
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def log_message(msg: str):
    """Append a timestamped log line to update_history.log."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{timestamp}] {msg}\n"
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(entry)
    except Exception:
        pass


# =====================================================================
# UNIVERSAL HARDWARE & SYSTEM INVENTORY SCANNER
# =====================================================================
class MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [
        ("dwLength", ctypes.c_ulong),
        ("dwMemoryLoad", ctypes.c_ulong),
        ("ullTotalPhys", ctypes.c_ulonglong),
        ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong),
        ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong),
        ("ullAvailVirtual", ctypes.c_ulonglong),
        ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
    ]


def scan_computer_specs() -> dict:
    """
    Dynamically detect hardware and operating system specs on ANY Windows PC
    using fast native Windows Registry & Win32 API calls.
    """
    specs = {
        "hostname": platform.node() or os.environ.get("COMPUTERNAME", "Windows-PC"),
        "username": os.environ.get("USERNAME", "User"),
        "manufacturer": "Generic PC",
        "model": "Desktop / Laptop",
        "cpu_name": platform.processor() or "Unknown Processor",
        "cpu_threads": os.cpu_count() or 1,
        "ram_total_gb": 0,
        "ram_usable_gb": 0.0,
        "ram_avail_gb": 0.0,
        "ram_used_pct": 0,
        "gpus": [],
        "primary_gpu": "Integrated / Standard Graphics",
        "os_name": "Windows",
        "os_display_ver": "",
        "os_build": "",
        "drives": [],
        "is_admin": is_User_Admin(),
        "winget_version": "Not Found",
        "python_version": platform.python_version(),
    }

    # 1. CPU Name
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0") as k:
            cpu, _ = winreg.QueryValueEx(k, "ProcessorNameString")
            if cpu:
                specs["cpu_name"] = cpu.strip()
    except OSError:
        pass

    # 2. System Manufacturer & Model
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\BIOS") as k:
            mfg, _ = winreg.QueryValueEx(k, "SystemManufacturer")
            mdl, _ = winreg.QueryValueEx(k, "SystemProductName")
            if mfg:
                specs["manufacturer"] = mfg.strip()
            if mdl:
                specs["model"] = mdl.strip()
    except OSError:
        pass

    # 3. Physical RAM via Win32 GlobalMemoryStatusEx
    try:
        mem = MEMORYSTATUSEX()
        mem.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(mem))
        specs["ram_usable_gb"] = round(mem.ullTotalPhys / (1024 ** 3), 1)
        specs["ram_total_gb"] = int(round(mem.ullTotalPhys / (1024 ** 3)))
        # Snap common RAM sizes (e.g., 15.6 -> 16, 31.2 -> 32, 7.8 -> 8)
        for std in (4, 8, 12, 16, 24, 32, 48, 64, 96, 128, 256):
            if abs(specs["ram_usable_gb"] - std) <= 1.2:
                specs["ram_total_gb"] = std
                break
        specs["ram_avail_gb"] = round(mem.ullAvailPhys / (1024 ** 3), 1)
        specs["ram_used_pct"] = int(mem.dwMemoryLoad)
    except Exception:
        pass

    # 4. GPU Adapters from Display Class Registry
    gpus = []
    try:
        cls_path = r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, cls_path) as k:
            for i in range(16):
                sub = f"{i:04d}"
                try:
                    with winreg.OpenKey(k, sub) as sk:
                        desc, _ = winreg.QueryValueEx(sk, "DriverDesc")
                        if not desc:
                            continue
                        drv_ver = ""
                        vram_gb = 0
                        try:
                            drv_ver, _ = winreg.QueryValueEx(sk, "DriverVersion")
                        except OSError:
                            pass
                        try:
                            vram, _ = winreg.QueryValueEx(sk, "HardwareInformation.qwMemorySize")
                            if isinstance(vram, bytes):
                                vram = int.from_bytes(vram, "little")
                            vram_gb = round(vram / (1024 ** 3))
                        except OSError:
                            pass
                        gpu_entry = {
                            "name": desc.strip(),
                            "driver": drv_ver,
                            "vram_gb": vram_gb,
                        }
                        if not any(g["name"] == gpu_entry["name"] for g in gpus):
                            gpus.append(gpu_entry)
                except OSError:
                    continue
    except OSError:
        pass

    if gpus:
        # Prefer discrete GPU (NVIDIA / AMD Radeon / Intel Arc) as primary display badge
        gpus.sort(key=lambda g: (any(k in g["name"].upper() for k in ("NVIDIA", "RTX", "GTX", "RADEON", "ARC")), g["vram_gb"]), reverse=True)
        specs["gpus"] = gpus
        top_gpu = gpus[0]
        specs["primary_gpu"] = f"{top_gpu['name']} ({top_gpu['vram_gb']} GB)" if top_gpu["vram_gb"] > 0 else top_gpu["name"]

    # 5. Windows Edition & Build
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion") as k:
            prod, _ = winreg.QueryValueEx(k, "ProductName")
            build, _ = winreg.QueryValueEx(k, "CurrentBuild")
            disp = ""
            try:
                disp, _ = winreg.QueryValueEx(k, "DisplayVersion")
            except OSError:
                pass
            if build and int(build) >= 22000 and "Windows 10" in prod:
                prod = prod.replace("Windows 10", "Windows 11")
            specs["os_name"] = prod
            specs["os_display_ver"] = disp
            specs["os_build"] = str(build)
    except Exception:
        pass

    # 6. Storage Drives
    drives = []
    try:
        bitmask = ctypes.windll.kernel32.GetLogicalDrives()
        for i, letter in enumerate(string.ascii_uppercase):
            if bitmask & (1 << i):
                root = f"{letter}:\\"
                dtype = ctypes.windll.kernel32.GetDriveTypeW(root)
                if dtype in (2, 3):  # Removable or Fixed disk
                    try:
                        u = shutil.disk_usage(root)
                        if u.total > 0:
                            drives.append({
                                "drive": f"{letter}:",
                                "type": "Fixed SSD/HDD" if dtype == 3 else "Removable",
                                "total_gb": round(u.total / (1024 ** 3), 1),
                                "used_gb": round(u.used / (1024 ** 3), 1),
                                "free_gb": round(u.free / (1024 ** 3), 1),
                                "used_pct": round((u.used / u.total) * 100, 1),
                            })
                    except OSError:
                        pass
    except Exception:
        pass
    specs["drives"] = drives

    # 7. Winget Version Check
    try:
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        res = subprocess.run(
            ["winget", "--version"],
            capture_output=True, text=True, errors="replace", timeout=8, startupinfo=startupinfo
        )
        if res.returncode == 0 and res.stdout.strip():
            specs["winget_version"] = res.stdout.strip()
    except Exception:
        pass

    return specs


def scan_installed_registry_apps() -> list:
    """
    Fast pure-Python scan of all installed programs across 64-bit, 32-bit, and User Registry hives.
    Works on every Windows PC without spawning PowerShell.
    """
    apps_by_name = {}
    hives = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall", winreg.KEY_READ | winreg.KEY_WOW64_64KEY, "System (x64)"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall", winreg.KEY_READ | winreg.KEY_WOW64_32KEY, "System (x86)"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall", winreg.KEY_READ, "User"),
    ]

    for root_hive, subkey_path, access_mask, scope in hives:
        try:
            with winreg.OpenKey(root_hive, subkey_path, 0, access_mask) as key:
                num_subkeys, _, _ = winreg.QueryInfoKey(key)
                for idx in range(num_subkeys):
                    try:
                        sub_name = winreg.EnumKey(key, idx)
                        with winreg.OpenKey(key, sub_name, 0, access_mask) as subkey:
                            try:
                                name, _ = winreg.QueryValueEx(subkey, "DisplayName")
                            except OSError:
                                continue
                            if not name or not str(name).strip():
                                continue

                            # Skip hidden system components
                            try:
                                sys_comp, _ = winreg.QueryValueEx(subkey, "SystemComponent")
                                if sys_comp == 1:
                                    continue
                            except OSError:
                                pass

                            version = ""
                            publisher = ""
                            try:
                                version, _ = winreg.QueryValueEx(subkey, "DisplayVersion")
                            except OSError:
                                pass
                            try:
                                publisher, _ = winreg.QueryValueEx(subkey, "Publisher")
                            except OSError:
                                pass

                            clean_name = str(name).strip()
                            if clean_name not in apps_by_name:
                                apps_by_name[clean_name] = {
                                    "name": clean_name,
                                    "version": str(version).strip() if version else "—",
                                    "publisher": str(publisher).strip() if publisher else "Unknown Publisher",
                                    "scope": scope,
                                }
                    except OSError:
                        continue
        except OSError:
            continue

    return sorted(apps_by_name.values(), key=lambda x: x["name"].lower())


def format_short_cpu(cpu_name: str) -> str:
    """Create a concise CPU label for the header badge on any PC."""
    s = re.sub(r"\(R\)|\(TM\)|Processor|CPU|@.*|\d+-Core", "", cpu_name, flags=re.IGNORECASE)
    s = " ".join(s.split())
    return s[:28] if len(s) > 28 else (s or "CPU")


def format_short_gpu(gpu_name: str) -> str:
    """Create a concise GPU label for the header badge on any PC."""
    s = re.sub(r"NVIDIA GeForce |AMD Radeon |\(TM\)|\(R\)|Graphics", "", gpu_name, flags=re.IGNORECASE)
    s = " ".join(s.split())
    return s[:26] if len(s) > 26 else (s or "GPU")


# =====================================================================
# SYSTEM RESTORE POINT CONFIRMATION DIALOG
# =====================================================================
class RestorePointConfirmDialog(tk.Toplevel):
    def __init__(self, parent, target_count: int, silent_mode: bool):
        super().__init__(parent)
        self.result = None  # "yes", "no", or None
        self.title("🛡️ Windows System Protection & Update Confirmation")
        self.geometry("560x360")
        self.resizable(False, False)
        self.configure(bg="#0f172a")
        self.transient(parent)
        self.grab_set()

        # Center over parent window
        self.update_idletasks()
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        px = parent.winfo_rootx()
        py = parent.winfo_rooty()
        x = px + max(0, (pw - 560) // 2)
        y = py + max(0, (ph - 360) // 2)
        self.geometry(f"+{x}+{y}")

        frame = tk.Frame(self, bg="#0f172a", padx=24, pady=20)
        frame.pack(fill=tk.BOTH, expand=True)

        # Header Title
        tk.Label(
            frame, text="🛡️ Confirm Updates & System Protection",
            bg="#0f172a", fg="#f8fafc", font=("Segoe UI", 13, "bold"), anchor="w"
        ).pack(fill=tk.X, pady=(0, 6))

        mode_text = "Silent Background Mode" if silent_mode else "Interactive Mode"
        tk.Label(
            frame,
            text=f"Ready to install {target_count} package update(s) sequentially in {mode_text}.\nEach application will be automatically verified post-installation.",
            bg="#0f172a", fg="#94a3b8", font=("Segoe UI", 9), anchor="w", justify=tk.LEFT
        ).pack(fill=tk.X, pady=(0, 14))

        # Recommendation Card
        card = tk.Frame(
            frame, bg="#1e293b", highlightbackground="#059669", highlightthickness=1, padx=14, pady=12
        )
        card.pack(fill=tk.X, pady=(0, 16))

        tk.Label(
            card, text="🛡️ CREATE SYSTEM RESTORE POINT? (RECOMMENDED: YES)",
            bg="#1e293b", fg="#34d399", font=("Segoe UI", 10, "bold"), anchor="w"
        ).pack(fill=tk.X, pady=(0, 4))

        tk.Label(
            card,
            text="Creating a Windows Restore Point creates a safe recovery snapshot before modifying system files. If any driver, runtime, or third-party software update causes system instability, you can safely roll back your PC.",
            bg="#1e293b", fg="#cbd5e1", font=("Segoe UI", 9), anchor="w", justify=tk.LEFT, wraplength=480
        ).pack(fill=tk.X)

        # Action Buttons
        btn_frame = tk.Frame(frame, bg="#0f172a")
        btn_frame.pack(fill=tk.X, pady=(4, 0))

        # 1. Yes (Recommended)
        btn_yes = tk.Button(
            btn_frame,
            text="✔ Yes, Create Restore Point & Update (Recommended)",
            command=self._on_yes,
            bg="#059669", fg="#ffffff", activebackground="#047857", activeforeground="#ffffff",
            font=("Segoe UI", 9, "bold"), relief="flat", padx=12, pady=7, cursor="hand2"
        )
        btn_yes.pack(fill=tk.X, pady=(0, 8))

        # 2. No (Skip) & Cancel Row
        sub_row = tk.Frame(btn_frame, bg="#0f172a")
        sub_row.pack(fill=tk.X)

        btn_no = tk.Button(
            sub_row,
            text="⚡ No, Update Directly (Skip Restore Point)",
            command=self._on_no,
            bg="#334155", fg="#f1f5f9", activebackground="#475569", activeforeground="#ffffff",
            font=("Segoe UI", 9), relief="flat", padx=10, pady=5, cursor="hand2"
        )
        btn_no.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))

        btn_cancel = tk.Button(
            sub_row,
            text="Cancel",
            command=self._on_cancel,
            bg="#1e293b", fg="#94a3b8", activebackground="#334155", activeforeground="#ffffff",
            font=("Segoe UI", 9), relief="flat", padx=16, pady=5, cursor="hand2"
        )
        btn_cancel.pack(side=tk.RIGHT)

        self.protocol("WM_DELETE_WINDOW", self._on_cancel)
        self.bind("<Escape>", lambda e: self._on_cancel())
        btn_yes.focus_set()

    def _on_yes(self):
        self.result = "yes"
        self.destroy()

    def _on_no(self):
        self.result = "no"
        self.destroy()

    def _on_cancel(self):
        self.result = None
        self.destroy()


# =====================================================================
# MAIN TKINTER APPLICATION
# =====================================================================
class UpdateManagerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} v{APP_VERSION}")
        self.geometry("1100x770")
        self.minsize(940, 640)

        if ICON_FILE.exists():
            try:
                self.iconbitmap(str(ICON_FILE))
            except Exception:
                pass

        # Visual Assets (Background & Logos)
        self.bg_photo = None
        self.header_bg_photo = None
        self.logo_photo = None
        self.logo_large_photo = None

        if WINDOW_BG_FILE.exists():
            try:
                self.bg_photo = tk.PhotoImage(file=str(WINDOW_BG_FILE))
            except Exception:
                pass

        if HEADER_BG_FILE.exists():
            try:
                self.header_bg_photo = tk.PhotoImage(file=str(HEADER_BG_FILE))
            except Exception:
                pass

        if LOGO_FILE.exists():
            try:
                self.logo_photo = tk.PhotoImage(file=str(LOGO_FILE))
            except Exception:
                pass

        if LOGO_LARGE_FILE.exists():
            try:
                self.logo_large_photo = tk.PhotoImage(file=str(LOGO_LARGE_FILE))
            except Exception:
                pass

        # Runtime State
        self.is_scanning = False
        self.is_updating = False
        self.stop_requested = False
        self.specs = {}
        self.installed_apps = []
        self.updates_list = []
        self.windows_updates = []
        self.verified_session_count = 0
        self.log_queue = queue.Queue()

        # Filter & Options
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._refresh_updates_tree())
        self.inv_search_var = tk.StringVar()
        self.inv_search_var.trace_add("write", lambda *_: self._refresh_inventory_tree())
        self.silent_mode_var = tk.BooleanVar(value=False)

        self._configure_styles()
        self._build_ui()
        self._poll_log_queue()

        # Automatically start Stage 1 (Specs Scan) -> Stage 2 (Software Scan)
        self.after(350, self.start_full_scan)

    def _configure_styles(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        self.bg_color = "#0f172a"
        self.card_bg = "#1e293b"
        self.card_alt = "#172033"
        self.border_color = "#334155"
        self.text_color = "#f8fafc"
        self.text_muted = "#94a3b8"
        self.accent_color = "#0284c7"
        self.accent_hover = "#0369a1"
        self.green_accent = "#10b981"

        self.configure(bg=self.bg_color)

        style.configure("TFrame", background=self.bg_color)
        style.configure("Card.TFrame", background=self.card_bg, relief="flat")
        style.configure("Header.TLabel", background=self.bg_color, foreground=self.text_color, font=("Segoe UI", 16, "bold"))
        style.configure("SubHeader.TLabel", background=self.bg_color, foreground=self.text_muted, font=("Segoe UI", 9))
        style.configure("Status.TLabel", background=self.card_bg, foreground=self.text_color, font=("Segoe UI", 10))
        style.configure("Badge.TLabel", background="#1e293b", foreground="#38bdf8", font=("Segoe UI", 9, "bold"), padding=(8, 4))
        style.configure("AdminOk.TLabel", background="#064e3b", foreground="#34d399", font=("Segoe UI", 9, "bold"), padding=(8, 4))
        style.configure("AdminWarn.TLabel", background="#78350f", foreground="#fcd34d", font=("Segoe UI", 9, "bold"), padding=(8, 4))

        # Notebook Tabs
        style.configure("TNotebook", background=self.bg_color, borderwidth=0)
        style.configure("TNotebook.Tab", background="#1e293b", foreground="#94a3b8", font=("Segoe UI", 10, "bold"), padding=(16, 8), borderwidth=0)
        style.map("TNotebook.Tab", background=[("selected", "#0284c7"), ("active", "#334155")], foreground=[("selected", "#ffffff"), ("active", "#f8fafc")])

        # Buttons (High contrast even when disabled)
        style.configure("Primary.TButton", font=("Segoe UI", 10, "bold"), background=self.accent_color, foreground="#ffffff", padding=(12, 6))
        style.map("Primary.TButton", background=[("active", self.accent_hover), ("disabled", "#334155")], foreground=[("disabled", "#94a3b8")])

        style.configure("Success.TButton", font=("Segoe UI", 10, "bold"), background="#059669", foreground="#ffffff", padding=(12, 6))
        style.map("Success.TButton", background=[("active", "#047857"), ("disabled", "#334155")], foreground=[("disabled", "#94a3b8")])

        style.configure("Danger.TButton", font=("Segoe UI", 9, "bold"), background="#dc2626", foreground="#ffffff", padding=(10, 5))
        style.map("Danger.TButton", background=[("active", "#b91c1c"), ("disabled", "#334155")], foreground=[("disabled", "#64748b")])

        style.configure("Secondary.TButton", font=("Segoe UI", 9), background="#334155", foreground=self.text_color, padding=(10, 5))
        style.map("Secondary.TButton", background=[("active", "#475569"), ("disabled", "#1e293b")], foreground=[("disabled", "#64748b")])

        # Treeview
        style.configure("Treeview", background=self.card_bg, foreground=self.text_color, fieldbackground=self.card_bg, rowheight=29, font=("Segoe UI", 9), borderwidth=0)
        style.configure("Treeview.Heading", background="#0b1120", foreground="#cbd5e1", font=("Segoe UI", 9, "bold"), relief="flat", padding=5)
        style.map("Treeview", background=[("selected", "#0369a1")], foreground=[("selected", "#ffffff")])

        style.configure("Horizontal.TProgressbar", background="#0ea5e9", troughcolor="#1e293b", borderwidth=0)

        # PanedWindow & Sash Divider
        style.configure("TPanedwindow", background=self.bg_color)
        style.configure("Sash", sashthickness=6, gripcount=14, background="#334155")

    def _build_ui(self):
        # 0. Global Window Background Wallpaper
        if self.bg_photo:
            self.bg_label = tk.Label(self, image=self.bg_photo, bd=0)
            self.bg_label.place(x=0, y=0, relwidth=1, relheight=1)
            self.bg_label.lower()

        # 1. Top Header Banner Canvas (with high-tech background & Jesse In The Lab circle logo)
        self.top_canvas = tk.Canvas(self, height=84, bd=0, highlightthickness=0, bg="#0b1329")
        self.top_canvas.pack(fill=tk.X)

        if self.header_bg_photo:
            self.top_canvas.create_image(0, 0, image=self.header_bg_photo, anchor="nw")

        title_x = 24
        if self.logo_photo:
            self.top_canvas.create_image(20, 18, image=self.logo_photo, anchor="nw")
            title_x = 80

        self.top_canvas.create_text(
            title_x, 30, text=APP_NAME, fill="#ffffff", font=("Segoe UI", 16, "bold"), anchor="w"
        )
        self.top_canvas.create_text(
            title_x, 56,
            text="Stage 1: Hardware Spec Detection • Stage 2: Deep Software Audit • Sequential Verified Updates",
            fill="#93c5fd", font=("Segoe UI", 9), anchor="w"
        )

        # Dynamic Hardware + Admin Badges on the right
        badge_box = tk.Frame(self.top_canvas, bg="#0d1527", padx=4, pady=4, highlightthickness=1, highlightbackground="#1e3a5f")

        # Buy Me a Coffee Button (Amber / Warm Gold)
        self.btn_coffee = tk.Button(
            badge_box,
            text=" ☕ Buy Me a Coffee ",
            command=self.open_buy_me_coffee,
            bg="#f59e0b", fg="#000000", activebackground="#d97706", activeforeground="#ffffff",
            relief="flat", font=("Segoe UI", 9, "bold"), padx=8, pady=3, cursor="hand2"
        )
        self.btn_coffee.pack(side=tk.RIGHT, padx=(6, 0))

        if is_User_Admin():
            self.lbl_admin_badge = ttk.Label(badge_box, text=" 🛡️ Administrator ", style="AdminOk.TLabel")
            self.lbl_admin_badge.pack(side=tk.RIGHT, padx=(6, 0))
        else:
            self.lbl_admin_badge = tk.Button(
                badge_box,
                text=" ⚠️ Standard User (Click to Elevate) ",
                command=relaunch_as_admin,
                bg="#78350f", fg="#fde047", relief="flat", font=("Segoe UI", 9, "bold"), padx=8, pady=3, cursor="hand2"
            )
            self.lbl_admin_badge.pack(side=tk.RIGHT, padx=(6, 0))

        self.lbl_hw_badge = ttk.Label(badge_box, text=" 🔍 Detecting Computer Specs... ", style="Badge.TLabel")
        self.lbl_hw_badge.pack(side=tk.RIGHT)

        self.badge_window = self.top_canvas.create_window(1080, 42, window=badge_box, anchor="e")

        def _on_header_resize(e):
            try:
                self.top_canvas.coords(self.badge_window, e.width - 20, 42)
            except Exception:
                pass

        self.top_canvas.bind("<Configure>", _on_header_resize)

        # 2. Windows Updates Reminder Banner (Shown dynamically when pending OS updates exist)
        self.win_notice_frame = tk.Frame(
            self, bg="#451a03", highlightbackground="#d97706", highlightthickness=1, padx=14, pady=7
        )
        self.win_notice_lbl = tk.Label(
            self.win_notice_frame,
            text="🔔 Windows OS Updates Detected: Installed separately via Windows Update.",
            bg="#451a03", fg="#fef08a", font=("Segoe UI", 9, "bold"), anchor="w", justify=tk.LEFT
        )
        self.win_notice_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.btn_open_winupdate = tk.Button(
            self.win_notice_frame,
            text="Open Windows Update",
            command=self.open_windows_update,
            bg="#d97706", fg="#ffffff", activebackground="#b45309", activeforeground="#ffffff",
            font=("Segoe UI", 9, "bold"), relief="flat", padx=12, pady=3, cursor="hand2"
        )
        self.btn_open_winupdate.pack(side=tk.RIGHT, padx=4)

        # 3. Main Split-Pane Container (Native Draggable PanedWindow)
        self.main_paned = ttk.PanedWindow(self, orient=tk.VERTICAL)
        self.main_paned.pack(fill=tk.BOTH, expand=True, padx=20, pady=(6, 10))

        # Main Multi-Tab Notebook (Upper Pane)
        self.notebook = ttk.Notebook(self.main_paned)
        self.main_paned.add(self.notebook, weight=3)

        self.tab_updater = ttk.Frame(self.notebook)
        self.tab_specs = ttk.Frame(self.notebook)
        self.tab_help = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_updater, text="  🚀 Software Updater  ")
        self.notebook.add(self.tab_specs, text="  💻 Computer Specs & Installed Apps  ")
        self.notebook.add(self.tab_help, text="  ❓ Help & User Guide  ")

        self._build_updater_tab()
        self._build_specs_tab()
        self._build_help_tab()

        # 4. Collapsible & Vertically Resizable Live Console Log Drawer (Lower Pane)
        self.log_pane_height = 180
        self.log_visible = False
        self.log_container = tk.Frame(
            self.main_paned, bg="#020617", highlightbackground="#1e293b", highlightthickness=1
        )

        # Header / Resizer Splitter Bar (Sits at the top of the log container)
        self.log_header = tk.Frame(
            self.log_container, bg="#1e293b", height=28, cursor="size_ns"
        )
        self.log_header.pack(fill=tk.X, side=tk.TOP)
        self.log_header.pack_propagate(False)

        self.log_resizer_grip = tk.Label(
            self.log_header,
            text="━ ━ ━   📜 Live Console & Installation Log   (Drag Divider or Double-Click to Resize)   ━ ━ ━",
            fg="#94a3b8",
            bg="#1e293b",
            font=("Segoe UI", 8, "bold"),
            cursor="size_ns",
        )
        self.log_resizer_grip.pack(side=tk.LEFT, fill=tk.Y, padx=10)

        # Quick Control Buttons on the Right Side of the Header
        btn_hide = tk.Button(
            self.log_header, text="✖ Hide", command=self.toggle_log_pane,
            bg="#334155", fg="#cbd5e1", activebackground="#dc2626", activeforeground="#ffffff",
            relief="flat", font=("Segoe UI", 8), padx=6, pady=1, cursor="hand2"
        )
        btn_hide.pack(side=tk.RIGHT, padx=(2, 6), pady=2)

        btn_copy = tk.Button(
            self.log_header, text="📋 Copy", command=self.copy_log_to_clipboard,
            bg="#334155", fg="#cbd5e1", activebackground="#0284c7", activeforeground="#ffffff",
            relief="flat", font=("Segoe UI", 8), padx=6, pady=1, cursor="hand2"
        )
        btn_copy.pack(side=tk.RIGHT, padx=2, pady=2)

        btn_clear = tk.Button(
            self.log_header, text="🗑 Clear", command=self.clear_log,
            bg="#334155", fg="#cbd5e1", activebackground="#0284c7", activeforeground="#ffffff",
            relief="flat", font=("Segoe UI", 8), padx=6, pady=1, cursor="hand2"
        )
        btn_clear.pack(side=tk.RIGHT, padx=2, pady=2)

        btn_expanded = tk.Button(
            self.log_header, text="🔼 Expanded (360px)", command=lambda: self.set_log_height(360),
            bg="#334155", fg="#38bdf8", activebackground="#0369a1", activeforeground="#ffffff",
            relief="flat", font=("Segoe UI", 8, "bold"), padx=6, pady=1, cursor="hand2"
        )
        btn_expanded.pack(side=tk.RIGHT, padx=2, pady=2)

        btn_compact = tk.Button(
            self.log_header, text="🔽 Compact (160px)", command=lambda: self.set_log_height(160),
            bg="#334155", fg="#38bdf8", activebackground="#0369a1", activeforeground="#ffffff",
            relief="flat", font=("Segoe UI", 8, "bold"), padx=6, pady=1, cursor="hand2"
        )
        btn_compact.pack(side=tk.RIGHT, padx=2, pady=2)

        # Scrolled Text for Console Logs
        self.log_text = scrolledtext.ScrolledText(
            self.log_container,
            bg="#020617",
            fg="#38bdf8",
            insertbackground="#ffffff",
            font=("Consolas", 9),
            relief="flat",
            padx=10,
            pady=6,
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # Resizer Drag, Hover & Double-Click Bindings
        def _resizer_hover(e):
            self.log_header.configure(bg="#0369a1")
            self.log_resizer_grip.configure(bg="#0369a1", fg="#ffffff")

        def _resizer_leave(e):
            self.log_header.configure(bg="#1e293b")
            self.log_resizer_grip.configure(bg="#1e293b", fg="#94a3b8")

        self._drag_data = {}
        def _start_resize(e):
            self._drag_data["y"] = e.y_root
            try:
                self._drag_data["sash"] = self.main_paned.sashpos(0)
            except Exception:
                self._drag_data["sash"] = self.main_paned.winfo_height() - self.log_pane_height

        def _on_resize_drag(e):
            if "y" in self._drag_data and "sash" in self._drag_data:
                delta = e.y_root - self._drag_data["y"]
                total_h = self.main_paned.winfo_height()
                new_pos = max(180, min(total_h - 70, self._drag_data["sash"] + delta))
                try:
                    self.main_paned.sashpos(0, new_pos)
                    self.log_pane_height = max(70, total_h - new_pos)
                except Exception:
                    pass

        def _on_resizer_dblclick(e):
            curr_h = self.log_container.winfo_height()
            if curr_h > 240:
                self.set_log_height(160)
            else:
                self.set_log_height(360)

        for w in (self.log_header, self.log_resizer_grip):
            w.bind("<Enter>", _resizer_hover)
            w.bind("<Leave>", _resizer_leave)
            w.bind("<Button-1>", _start_resize)
            w.bind("<B1-Motion>", _on_resize_drag)
            w.bind("<Double-Button-1>", _on_resizer_dblclick)

    # -----------------------------------------------------------------
    # TAB 1: SOFTWARE UPDATER
    # -----------------------------------------------------------------
    def _build_updater_tab(self):
        # Summary KPI Cards Row
        cards_row = ttk.Frame(self.tab_updater, padding=(0, 8, 0, 8))
        cards_row.pack(fill=tk.X)
        for i in range(4):
            cards_row.columnconfigure(i, weight=1)

        self.card_pc_val, self.card_pc_sub = self._make_kpi_card(cards_row, 0, "HOST SYSTEM", "Scanning...", "Detecting OS & Hardware", "#38bdf8")
        self.card_inst_val, self.card_inst_sub = self._make_kpi_card(cards_row, 1, "INSTALLED SOFTWARE", "—", "Audited in Registry", "#a855f7")
        self.card_upd_val, self.card_upd_sub = self._make_kpi_card(cards_row, 2, "UPDATES AVAILABLE", "—", "Ready via Winget", "#f59e0b")
        self.card_ver_val, self.card_ver_sub = self._make_kpi_card(cards_row, 3, "VERIFIED UPDATED", "0", "Completed this session", "#10b981")

        # Status & Search Filter Bar
        filter_bar = ttk.Frame(self.tab_updater, style="Card.TFrame", padding=(12, 7, 12, 7))
        filter_bar.pack(fill=tk.X, pady=(0, 6))

        self.lbl_status = ttk.Label(filter_bar, text="Initializing scan...", style="Status.TLabel")
        self.lbl_status.pack(side=tk.LEFT)

        # Right side search & selection helpers
        search_frame = tk.Frame(filter_bar, bg=self.card_bg)
        search_frame.pack(side=tk.RIGHT)

        tk.Label(search_frame, text="🔍 Filter:", bg=self.card_bg, fg=self.text_muted, font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(0, 4))
        search_entry = tk.Entry(
            search_frame, textvariable=self.search_var, bg="#0f172a", fg="#f8fafc",
            insertbackground="#ffffff", relief="flat", font=("Segoe UI", 9), width=22
        )
        search_entry.pack(side=tk.LEFT, padx=(0, 8), ipady=3)

        tk.Button(
            search_frame, text="Select All", command=self.select_all_updates,
            bg="#334155", fg="#f8fafc", relief="flat", font=("Segoe UI", 8), padx=6, pady=2, cursor="hand2"
        ).pack(side=tk.LEFT, padx=2)

        tk.Button(
            search_frame, text="Clear", command=self.deselect_all_updates,
            bg="#334155", fg="#f8fafc", relief="flat", font=("Segoe UI", 8), padx=6, pady=2, cursor="hand2"
        ).pack(side=tk.LEFT, padx=2)

        tk.Button(
            search_frame, text="🤖 AI & Dev Tools", command=self.filter_ai_dev_tools,
            bg="#4338ca", fg="#ffffff", relief="flat", font=("Segoe UI", 8, "bold"), padx=7, pady=2, cursor="hand2"
        ).pack(side=tk.LEFT, padx=3)

        # Updates Treeview Table
        table_container = ttk.Frame(self.tab_updater, style="Card.TFrame", padding=(1, 1, 1, 1))
        table_container.pack(fill=tk.BOTH, expand=True, pady=2)

        columns = ("name", "id", "current", "available", "status")
        self.tree = ttk.Treeview(table_container, columns=columns, show="headings", selectmode="extended", height=7)

        self.tree.heading("name", text="Application Name", anchor="w")
        self.tree.heading("id", text="Package ID", anchor="w")
        self.tree.heading("current", text="Installed Version", anchor="center")
        self.tree.heading("available", text="New Version", anchor="center")
        self.tree.heading("status", text="Update Status", anchor="center")

        self.tree.column("name", width=300, minwidth=180, anchor="w")
        self.tree.column("id", width=240, minwidth=150, anchor="w")
        self.tree.column("current", width=130, minwidth=90, anchor="center")
        self.tree.column("available", width=130, minwidth=90, anchor="center")
        self.tree.column("status", width=170, minwidth=120, anchor="center")

        tree_scroll_y = ttk.Scrollbar(table_container, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scroll_y.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.tag_configure("pending", foreground="#38bdf8")
        self.tree.tag_configure("updating", foreground="#f59e0b")
        self.tree.tag_configure("verified", foreground="#10b981")
        self.tree.tag_configure("reboot", foreground="#fbbf24")
        self.tree.tag_configure("failed", foreground="#ef4444")

        # Bottom Controls & Progress Bar
        control_frame = ttk.Frame(self.tab_updater, padding=(0, 8, 0, 4))
        control_frame.pack(fill=tk.X)

        self.progress_var = tk.DoubleVar(value=0.0)
        self.progress_bar = ttk.Progressbar(
            control_frame, variable=self.progress_var, maximum=100.0, style="Horizontal.TProgressbar"
        )
        self.progress_bar.pack(fill=tk.X, pady=(0, 8))

        btn_row = ttk.Frame(control_frame)
        btn_row.pack(fill=tk.X)

        self.btn_scan = ttk.Button(btn_row, text="🔄 Full System & Update Scan", style="Primary.TButton", command=self.start_full_scan)
        self.btn_scan.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_update_all = ttk.Button(
            btn_row, text="⚡ Push All Updates (One-by-One)", style="Success.TButton", command=self.start_update_all
        )
        self.btn_update_all.pack(side=tk.LEFT, padx=6)

        self.btn_update_selected = ttk.Button(
            btn_row, text="✔ Update Highlighted Only", style="Secondary.TButton", command=self.start_update_selected
        )
        self.btn_update_selected.pack(side=tk.LEFT, padx=6)

        self.btn_stop = ttk.Button(
            btn_row, text="⏹ Stop Batch", style="Danger.TButton", command=self.request_stop_batch, state="disabled"
        )
        self.btn_stop.pack(side=tk.LEFT, padx=6)

        self.btn_browsers = ttk.Button(
            btn_row, text="🌐 Update Browsers", style="Secondary.TButton", command=self.trigger_browser_updates
        )
        self.btn_browsers.pack(side=tk.LEFT, padx=6)

        # Silent Mode Checkbox
        chk_silent = tk.Checkbutton(
            btn_row,
            text="Silent Install (--silent)",
            variable=self.silent_mode_var,
            bg=self.bg_color, fg="#cbd5e1", selectcolor="#1e293b",
            activebackground=self.bg_color, activeforeground="#ffffff",
            font=("Segoe UI", 9)
        )
        chk_silent.pack(side=tk.LEFT, padx=8)

        # System Restore Point Checkbox
        self.restore_point_var = tk.BooleanVar(value=True)
        chk_restore = tk.Checkbutton(
            btn_row,
            text="Restore Point (Recommended)",
            variable=self.restore_point_var,
            bg=self.bg_color, fg="#34d399", selectcolor="#1e293b",
            activebackground=self.bg_color, activeforeground="#ffffff",
            font=("Segoe UI", 9, "bold")
        )
        chk_restore.pack(side=tk.LEFT, padx=(4, 10))

        self.btn_toggle_log = ttk.Button(btn_row, text="📜 View Live Log", style="Secondary.TButton", command=self.toggle_log_pane)
        self.btn_toggle_log.pack(side=tk.RIGHT, padx=2)

    def _make_kpi_card(self, parent, col, title, initial_val, sub_text, color):
        card = tk.Frame(parent, bg=self.card_bg, highlightbackground=self.border_color, highlightthickness=1, padx=12, pady=8)
        card.grid(row=0, column=col, sticky="nsew", padx=(0 if col == 0 else 6, 0 if col == 3 else 6))
        tk.Label(card, text=title, bg=self.card_bg, fg=self.text_muted, font=("Segoe UI", 8, "bold")).pack(anchor="w")
        val_lbl = tk.Label(card, text=initial_val, bg=self.card_bg, fg=color, font=("Segoe UI", 14, "bold"))
        val_lbl.pack(anchor="w", pady=(2, 1))
        sub_lbl = tk.Label(card, text=sub_text, bg=self.card_bg, fg=self.text_muted, font=("Segoe UI", 8))
        sub_lbl.pack(anchor="w")
        return val_lbl, sub_lbl

    # -----------------------------------------------------------------
    # TAB 2: COMPUTER SPECS & INSTALLED APPS
    # -----------------------------------------------------------------
    def _build_specs_tab(self):
        # Top Hardware Specs Panel
        specs_card = tk.Frame(self.tab_specs, bg=self.card_bg, highlightbackground=self.border_color, highlightthickness=1, padx=16, pady=12)
        specs_card.pack(fill=tk.X, pady=(8, 8))

        header_row = tk.Frame(specs_card, bg=self.card_bg)
        header_row.pack(fill=tk.X, pady=(0, 8))

        tk.Label(
            header_row, text="💻 Detected Computer Specifications & Health Diagnostics",
            bg=self.card_bg, fg="#38bdf8", font=("Segoe UI", 11, "bold")
        ).pack(side=tk.LEFT)

        tk.Button(
            header_row, text="💾 Export Full Audit Report (.txt)", command=self.export_audit_report,
            bg="#0284c7", fg="#ffffff", relief="flat", font=("Segoe UI", 9, "bold"), padx=10, pady=3, cursor="hand2"
        ).pack(side=tk.RIGHT)

        self.specs_grid = tk.Frame(specs_card, bg=self.card_bg)
        self.specs_grid.pack(fill=tk.X)
        for c in range(3):
            self.specs_grid.columnconfigure(c, weight=1)

        self.spec_labels = {}
        fields = [
            ("computer", "Computer / Model"),
            ("os", "Operating System"),
            ("cpu", "Processor (CPU)"),
            ("gpu", "Graphics Card (GPU)"),
            ("ram", "Memory (RAM)"),
            ("storage", "Storage Drives"),
        ]
        for idx, (key, title) in enumerate(fields):
            r, c = divmod(idx, 3)
            box = tk.Frame(self.specs_grid, bg="#172033", padx=10, pady=6)
            box.grid(row=r, column=c, sticky="nsew", padx=4, pady=4)
            tk.Label(box, text=title, bg="#172033", fg=self.text_muted, font=("Segoe UI", 8, "bold")).pack(anchor="w")
            lbl = tk.Label(box, text="Scanning...", bg="#172033", fg=self.text_color, font=("Segoe UI", 9, "bold"), anchor="w", justify=tk.LEFT, wraplength=300)
            lbl.pack(anchor="w", pady=(2, 0))
            self.spec_labels[key] = lbl

        # Automatic Recommendations Box
        self.lbl_recommendations = tk.Label(
            specs_card,
            text="💡 Recommendations will appear here once the hardware scan completes.",
            bg="#0f172a", fg="#34d399", font=("Segoe UI", 9), anchor="w", justify=tk.LEFT, padx=10, pady=6
        )
        self.lbl_recommendations.pack(fill=tk.X, pady=(6, 0))

        # Bottom Installed Software Catalog
        inv_bar = tk.Frame(self.tab_specs, bg=self.card_bg, padx=12, pady=6)
        inv_bar.pack(fill=tk.X, pady=(0, 4))

        self.lbl_inv_count = tk.Label(
            inv_bar, text="📦 Installed Software Inventory (0 programs)",
            bg=self.card_bg, fg=self.text_color, font=("Segoe UI", 10, "bold")
        )
        self.lbl_inv_count.pack(side=tk.LEFT)

        inv_search_box = tk.Frame(inv_bar, bg=self.card_bg)
        inv_search_box.pack(side=tk.RIGHT)
        tk.Label(inv_search_box, text="🔍 Search Installed:", bg=self.card_bg, fg=self.text_muted, font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=4)
        tk.Entry(
            inv_search_box, textvariable=self.inv_search_var, bg="#0f172a", fg="#f8fafc",
            insertbackground="#ffffff", relief="flat", font=("Segoe UI", 9), width=26
        ).pack(side=tk.LEFT, ipady=3)

        inv_table_frame = ttk.Frame(self.tab_specs, style="Card.TFrame")
        inv_table_frame.pack(fill=tk.BOTH, expand=True)

        inv_cols = ("name", "version", "publisher", "scope")
        self.inv_tree = ttk.Treeview(inv_table_frame, columns=inv_cols, show="headings", height=7)
        self.inv_tree.heading("name", text="Installed Application Name", anchor="w")
        self.inv_tree.heading("version", text="Installed Version", anchor="center")
        self.inv_tree.heading("publisher", text="Publisher / Vendor", anchor="w")
        self.inv_tree.heading("scope", text="Install Scope", anchor="center")

        self.inv_tree.column("name", width=360, anchor="w")
        self.inv_tree.column("version", width=150, anchor="center")
        self.inv_tree.column("publisher", width=260, anchor="w")
        self.inv_tree.column("scope", width=120, anchor="center")

        inv_scroll = ttk.Scrollbar(inv_table_frame, orient=tk.VERTICAL, command=self.inv_tree.yview)
        self.inv_tree.configure(yscrollcommand=inv_scroll.set)
        self.inv_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        inv_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    # -----------------------------------------------------------------
    # TAB 3: HELP & USER GUIDE
    # -----------------------------------------------------------------
    def _build_help_tab(self):
        help_frame = tk.Frame(self.tab_help, bg=self.card_bg, padx=16, pady=14)
        help_frame.pack(fill=tk.BOTH, expand=True, pady=8)

        # Brand Hero Card (Jesse In The Lab Logo & Community)
        brand_card = tk.Frame(help_frame, bg="#131c2e", highlightbackground="#0284c7", highlightthickness=1, padx=14, pady=10)
        brand_card.pack(fill=tk.X, pady=(0, 10))

        if self.logo_large_photo:
            lbl_brand_logo = tk.Label(brand_card, image=self.logo_large_photo, bg="#131c2e")
            lbl_brand_logo.pack(side=tk.LEFT, padx=(4, 16))

        brand_info = tk.Frame(brand_card, bg="#131c2e")
        brand_info.pack(side=tk.LEFT, fill=tk.Y)

        tk.Label(
            brand_info, text="Jesse In The Lab • AI & System Engineering",
            bg="#131c2e", fg="#38bdf8", font=("Segoe UI", 12, "bold")
        ).pack(anchor="w")
        tk.Label(
            brand_info,
            text="Official Software Update Manager & System Auditor Suite • Designed for high reliability & zero dependencies.",
            bg="#131c2e", fg="#cbd5e1", font=("Segoe UI", 9)
        ).pack(anchor="w", pady=(2, 0))
        tk.Label(
            brand_info,
            text="Support the developer on Buy Me a Coffee: https://buymeacoffee.com/JesseInTheLab",
            bg="#131c2e", fg="#94a3b8", font=("Segoe UI", 9)
        ).pack(anchor="w", pady=(2, 0))

        tk.Button(
            brand_card,
            text="☕ Support Project",
            command=self.open_buy_me_coffee,
            bg="#f59e0b", fg="#000000", activebackground="#d97706", activeforeground="#ffffff",
            font=("Segoe UI", 9, "bold"), relief="flat", padx=12, pady=4, cursor="hand2"
        ).pack(side=tk.RIGHT, padx=6)

        help_text = scrolledtext.ScrolledText(
            help_frame, bg=self.card_bg, fg=self.text_color, font=("Segoe UI", 10),
            relief="flat", wrap=tk.WORD, padx=12, pady=8, height=10
        )
        help_text.pack(fill=tk.BOTH, expand=True)

        guide_content = """📘 WELCOME TO SOFTWARE UPDATE MANAGER & AUDITOR (v2.1)
================================================================================
This utility is designed to work out-of-the-box on ANY Windows 10 or Windows 11 computer. It automatically audits your computer's hardware specifications, scans all installed software, finds available updates, installs them sequentially, and verifies every update.

--------------------------------------------------------------------------------
1. FAST ONE-LINER INSTALLATION (OPTION A)
--------------------------------------------------------------------------------
On any Windows 10 or 11 PC, you can install or update Software Update Manager with a single PowerShell line:
  irm https://raw.githubusercontent.com/jesusdelira7-956/SoftwareUpdateManager/main/install.ps1 | iex

This automatically ensures Python 3 and Winget are configured, creates the Desktop and Start Menu shortcuts with high-resolution icons, and readies the system.

--------------------------------------------------------------------------------
2. HOW THE TWO-STAGE AUTOMATIC SCAN WORKS
--------------------------------------------------------------------------------
When you launch the app (or click "🔄 Full System & Update Scan"):
  • STAGE 1 (Computer Specs Scan): First, the app detects your computer's CPU, Graphics Card (GPU + VRAM), Memory (RAM), Storage Drives, Windows Build, and Administrator status. It updates the top-right hardware badge and populates the "💻 Computer Specs & Installed Apps" tab.
  • STAGE 2 (Deep Software & Update Scan): Next, it scans the Windows Registry for every installed application and checks Microsoft's Windows Package Manager (Winget) for newer versions, plus checks for pending Windows OS updates.

--------------------------------------------------------------------------------
3. SPECIALIZED AI & DEV SUITES + BROWSER ORCHESTRATION
--------------------------------------------------------------------------------
  • 🤖 AI & Dev Tools:
    Click the "🤖 AI & Dev Tools" button in the filter toolbar to instantly select and prioritize updates for AI assistants and developer suites (Antigravity IDE, Cursor, VS Code, Android Studio, GitHub Copilot, Ollama, LM Studio, Pinokio, Docker Desktop, etc.).
  • 🌐 Browser Background Updates:
    Click "🌐 Update Browsers" to silently invoke native background updater services for Google Chrome, Microsoft Edge, Brave, and Mozilla Firefox.

--------------------------------------------------------------------------------
4. HOW TO UPDATE YOUR SOFTWARE
--------------------------------------------------------------------------------
  • Update Everything Sequentially:
    Click "⚡ Push All Updates (One-by-One)". The app downloads and installs updates strictly one at a time so installers never collide or lock the same system files.
  • Update Specific Apps Only:
    Click on one or more rows in the table (hold Ctrl or Shift to highlight multiple rows, or use the Search box), then click "✔ Update Highlighted Only".
  • Silent / Unattended Mode:
    Check "Silent Install (--silent)" at the bottom if you want installers to update silently in the background without showing setup wizard windows.
  • Stopping a Batch:
    Click "⏹ Stop Batch" at any time during updates; the app will safely finish the current installer and stop before starting the next one.

--------------------------------------------------------------------------------
5. MEANING OF UPDATE STATUS BADGES
--------------------------------------------------------------------------------
  • Pending Update (Blue)     : A newer version is available and ready to install.
  • Installing... (Amber)     : Winget is currently downloading and running the installer.
  • ✓ Verified (Green)        : The update finished AND post-install verification confirmed the new version.
  • ⚠ Reboot Needed (Yellow)  : The update succeeded, but Windows requires a restart to finalize replaced files.
  • ✗ App In-Use / Locked     : The application is currently open. Close it and retry.
  • ✗ Failed                  : The installer returned an error code. Check the live log for details.

--------------------------------------------------------------------------------
6. WHY ADMINISTRATOR MODE IS ENABLED AT STARTUP
--------------------------------------------------------------------------------
Many system applications (such as Visual C++ Redistributables, .NET Runtimes, VLC, 7-Zip, and Hardware Drivers) require Administrator rights to update files in "C:\\Program Files".
By requesting Administrator elevation once when the app starts (shown by the green "🛡️ Administrator" badge in the top-right), all updates run smoothly without interrupting you with repeated UAC prompts.
"""
        help_text.insert(tk.END, guide_content)
        help_text.configure(state="disabled")

        # Buy Me a Coffee Support Bar at the bottom of Help Tab
        coffee_bar = tk.Frame(help_frame, bg="#0f172a", highlightbackground="#d97706", highlightthickness=1, padx=14, pady=10)
        coffee_bar.pack(fill=tk.X, pady=(10, 0))

        tk.Label(
            coffee_bar,
            text="☕ Support the Independent Developer & Ongoing Updates",
            bg="#0f172a", fg="#fde047", font=("Segoe UI", 10, "bold")
        ).pack(side=tk.LEFT)

        tk.Button(
            coffee_bar,
            text="☕ Buy Me a Coffee (JesseInTheLab)",
            command=self.open_buy_me_coffee,
            bg="#f59e0b", fg="#000000", activebackground="#d97706", activeforeground="#ffffff",
            font=("Segoe UI", 9, "bold"), relief="flat", padx=14, pady=4, cursor="hand2"
        ).pack(side=tk.RIGHT)

    # -----------------------------------------------------------------
    # LOGGING & UI HELPERS
    # -----------------------------------------------------------------
    def set_log_height(self, target_h: int):
        self.log_pane_height = target_h
        if not self.log_visible:
            self.toggle_log_pane()
            return
        total_h = self.main_paned.winfo_height()
        if total_h <= 100:
            total_h = max(200, self.winfo_height() - 100)
        new_sash = max(180, min(total_h - 70, total_h - target_h))
        try:
            self.main_paned.sashpos(0, new_sash)
        except Exception:
            pass

    def toggle_log_pane(self):
        if self.log_visible:
            try:
                self.main_paned.forget(self.log_container)
            except Exception:
                pass
            self.btn_toggle_log.config(text="📜 View Live Log")
            self.log_visible = False
        else:
            try:
                self.main_paned.add(self.log_container, weight=1)
            except Exception:
                pass
            self.btn_toggle_log.config(text="✖ Hide Live Log")
            self.log_visible = True
            self.after(50, lambda: self.set_log_height(self.log_pane_height))

    def clear_log(self):
        self.log_text.delete("1.0", tk.END)

    def copy_log_to_clipboard(self):
        content = self.log_text.get("1.0", tk.END).strip()
        if content:
            self.clipboard_clear()
            self.clipboard_append(content)
            self.log_ui("[INFO] Log output copied to Windows clipboard.")

    def log_ui(self, msg: str, to_file=True):
        self.log_queue.put(msg)
        if to_file:
            log_message(msg)

    def _poll_log_queue(self):
        while not self.log_queue.empty():
            msg = self.log_queue.get_nowait()
            self.log_text.insert(tk.END, msg + "\n")
            self.log_text.see(tk.END)
        self.after(100, self._poll_log_queue)

    def open_windows_update(self):
        try:
            subprocess.Popen(["explorer.exe", "ms-settings:windowsupdate"])
            self.log_ui("[INFO] Opened Windows Update Settings.")
        except Exception as e:
            self.log_ui(f"[ERROR] Could not launch Windows Update: {e}")

    def select_all_updates(self):
        self.tree.selection_set(self.tree.get_children())

    def deselect_all_updates(self):
        self.tree.selection_remove(self.tree.get_children())

    def open_buy_me_coffee(self):
        """Open developer's Buy Me a Coffee page in the user's default browser."""
        try:
            webbrowser.open(DONATION_URL)
            self.log_ui(f"[DONATION] Opened Buy Me a Coffee: {DONATION_URL}")
        except Exception as e:
            self.log_ui(f"[ERROR] Could not open link: {e}")

    def filter_ai_dev_tools(self):
        """Highlight and select all pending updates for AI & Developer Environment packages."""
        matched = []
        for item in self.tree.get_children():
            vals = self.tree.item(item, "values")
            if len(vals) >= 2:
                name_str = vals[0].lower()
                pkg_id = vals[1].lower()
                if any(k.lower() in pkg_id or v.lower() in name_str for k, v in AI_DEV_PACKAGES.items()):
                    matched.append(item)
        if matched:
            self.tree.selection_set(matched)
            self.lbl_status.config(text=f"🤖 Selected {len(matched)} AI & Developer Suite update(s).")
            self.log_ui(f"[FILTER] Highlighted {len(matched)} AI / Developer tool(s) for update.")
        else:
            self.lbl_status.config(text="🤖 No pending updates for AI/Dev tools at this time.")
            messagebox.showinfo("AI & Dev Suites", "No pending updates found for AI assistants or Developer tools.\nAll monitored dev environments are current!")

    def trigger_browser_updates(self):
        """Invoke native background updater services for Chrome, Edge, Brave, and Firefox."""
        def _run():
            self.log_ui("[BROWSERS] Triggering native background update services...")
            triggered = trigger_browser_background_updates()
            if triggered:
                names = ", ".join(triggered)
                self.log_ui(f"[BROWSERS] Successfully signaled: {names}")
                self.after(0, lambda: messagebox.showinfo(
                    "Browser Updaters",
                    f"Background update service initiated for:\n\n• " + "\n• ".join(triggered) + "\n\nThese browsers will update silently in the background."
                ))
            else:
                self.log_ui("[BROWSERS] No standalone browser updater executables found.")
                self.after(0, lambda: messagebox.showinfo(
                    "Browser Updaters",
                    "No standalone background updater executables were found.\nBrowsers will be updated directly via Winget in the list."
                ))

        threading.Thread(target=_run, daemon=True).start()

    def request_stop_batch(self):
        if self.is_updating:
            self.stop_requested = True
            self.btn_stop.config(state="disabled")
            self.lbl_status.config(text="⏳ Stopping batch after current installer finishes...")
            self.log_ui("[USER ACTION] Stop requested. Will halt after current package completes.")

    # -----------------------------------------------------------------
    # STAGE 1 & STAGE 2 SCAN WORKFLOW
    # -----------------------------------------------------------------
    def start_full_scan(self):
        if self.is_scanning or self.is_updating:
            return
        self.is_scanning = True
        self.btn_scan.config(state="disabled")
        self.btn_update_all.config(state="disabled")
        self.btn_update_selected.config(state="disabled")
        self.lbl_status.config(text="🔍 Stage 1/2: Scanning computer hardware & OS specifications...")
        self.progress_var.set(10)

        threading.Thread(target=self._worker_full_scan, daemon=True).start()

    def _worker_full_scan(self):
        self.log_ui("=" * 68)
        self.log_ui(f"[STAGE 1] Scanning host computer hardware & operating system specs...")

        # STAGE 1: Computer Hardware Specs Scan
        specs = scan_computer_specs()
        self.specs = specs
        self.log_ui(f"  • Hostname / Model : {specs['hostname']} ({specs['manufacturer']} {specs['model']})")
        self.log_ui(f"  • Operating System : {specs['os_name']} {specs['os_display_ver']} (Build {specs['os_build']})")
        self.log_ui(f"  • Processor (CPU)  : {specs['cpu_name']} ({specs['cpu_threads']} threads)")
        self.log_ui(f"  • Graphics (GPU)   : {specs['primary_gpu']}")
        self.log_ui(f"  • Memory (RAM)     : {specs['ram_total_gb']} GB ({specs['ram_usable_gb']} GB usable, {specs['ram_used_pct']}% in use)")
        self.log_ui(f"  • Winget Engine    : {specs['winget_version']} | Admin Mode: {specs['is_admin']}")

        # Update UI with Stage 1 Hardware Results immediately before Stage 2 begins
        self.after(0, lambda: self._apply_specs_to_ui(specs))
        self.after(0, lambda: self.progress_var.set(35))
        self.after(0, lambda: self.lbl_status.config(text="🔍 Stage 2/2: Performing deep software inventory & checking for updates..."))

        # STAGE 2A: Installed Software Registry Scan
        self.log_ui("[STAGE 2] Auditing installed software across Windows Registry hives...")
        installed = scan_installed_registry_apps()
        self.installed_apps = installed
        self.log_ui(f"  • Found {len(installed)} installed software programs.")
        self.after(0, lambda: self.progress_var.set(55))

        # STAGE 2B: Winget Upgradable Packages Scan
        upgradable_apps = []
        try:
            self.log_ui("[STAGE 2] Querying Winget repository for available software updates...")
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            cmd = ["winget", "upgrade", "--include-unknown", "--accept-source-agreements"]
            proc = subprocess.run(
                cmd, capture_output=True, text=True, errors="replace", timeout=120, startupinfo=startupinfo
            )
            lines = proc.stdout.splitlines()

            header_idx = -1
            for i, line in enumerate(lines):
                if "Name" in line and "Id" in line and "Version" in line and "Available" in line:
                    header_idx = i
                    break

            if header_idx != -1 and header_idx < len(lines):
                header = lines[header_idx]
                idx_id = header.index("Id")
                idx_ver = header.index("Version")
                idx_avail = header.index("Available")
                idx_src = header.index("Source") if "Source" in header else len(header)

                for line in lines[header_idx + 2:]:
                    s = line.strip()
                    if not s or s.startswith("-") or "upgrade available" in s or "upgrades available" in s:
                        continue
                    if len(line) < idx_avail:
                        continue

                    name = line[:idx_id].strip()
                    pkg_id = line[idx_id:idx_ver].strip()
                    current_ver = line[idx_ver:idx_avail].strip()
                    avail_ver = line[idx_avail:idx_src].strip()
                    source = line[idx_src:].strip() if idx_src < len(line) else "winget"

                    if pkg_id and avail_ver and pkg_id != "Id":
                        upgradable_apps.append({
                            "name": name,
                            "id": pkg_id,
                            "current": current_ver,
                            "available": avail_ver,
                            "source": source,
                            "status": "Pending Update",
                            "tag": "pending",
                        })
        except Exception as e:
            self.log_ui(f"[SCAN ERROR] Winget upgrade check failed: {e}")

        self.after(0, lambda: self.progress_var.set(80))

        # STAGE 2C: Windows Update Check
        self.windows_updates.clear()
        try:
            self.log_ui("[STAGE 2] Checking Windows Update service for pending OS patches...")
            ps_script = (
                "$s = New-Object -ComObject Microsoft.Update.Session; "
                "$sr = $s.CreateUpdateSearcher().Search('IsInstalled=0 and Type=''Software'' and IsHidden=0'); "
                "foreach ($u in $sr.Updates) { Write-Output $u.Title }"
            )
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            ps_proc = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_script],
                capture_output=True, text=True, errors="replace", timeout=45, startupinfo=startupinfo
            )
            for title in ps_proc.stdout.splitlines():
                t = title.strip()
                if t:
                    self.windows_updates.append(t)
        except Exception as e:
            self.log_ui(f"[SCAN INFO] Windows Update check skipped/note: {e}")

        self.after(0, lambda: self.progress_var.set(100))
        self.after(80, lambda: self._on_scan_finished(upgradable_apps))

    def _apply_specs_to_ui(self, specs: dict):
        """Update badges, KPI cards, and the System Specs tab dynamically for this computer."""
        short_cpu = format_short_cpu(specs["cpu_name"])
        short_gpu = format_short_gpu(specs["primary_gpu"])
        badge_text = f" 💻 {short_cpu} | {short_gpu} | {specs['ram_total_gb']}GB RAM "
        self.lbl_hw_badge.config(text=badge_text)

        # KPI Card 1
        self.card_pc_val.config(text=specs["hostname"])
        self.card_pc_sub.config(text=f"{specs['os_name']} (Build {specs['os_build']})")

        # Populate Tab 2 Details
        self.spec_labels["computer"].config(text=f"{specs['hostname']}\n{specs['manufacturer']} — {specs['model']}")
        self.spec_labels["os"].config(
            text=f"{specs['os_name']} {specs['os_display_ver']} (Build {specs['os_build']})\nWinget: {specs['winget_version']} | Python {specs['python_version']}"
        )
        self.spec_labels["cpu"].config(text=f"{specs['cpu_name']}\n{specs['cpu_threads']} Logical Processors")

        gpu_lines = [f"{g['name']} ({g['vram_gb']} GB VRAM)" if g["vram_gb"] else g["name"] for g in specs["gpus"]] or [specs["primary_gpu"]]
        self.spec_labels["gpu"].config(text="\n".join(gpu_lines[:2]))

        self.spec_labels["ram"].config(
            text=f"{specs['ram_total_gb']} GB Installed ({specs['ram_usable_gb']} GB Usable)\nAvailable: {specs['ram_avail_gb']} GB ({specs['ram_used_pct']}% Load)"
        )

        drive_lines = [
            f"Drive {d['drive']} {d['used_gb']} GB / {d['total_gb']} GB used ({d['free_gb']} GB Free, {d['used_pct']}%)"
            for d in specs["drives"]
        ] or ["Standard Disk Storage"]
        self.spec_labels["storage"].config(text="\n".join(drive_lines[:3]))

        # Generate Tailored Recommendations for this computer
        recs = []
        if specs["ram_total_gb"] <= 8:
            recs.append("• Memory: 8 GB RAM or less detected. Closing heavy browser tabs before running large updates is recommended.")
        elif specs["ram_used_pct"] >= 85:
            recs.append(f"• High Memory Load ({specs['ram_used_pct']}%): Consider restarting or closing background apps for faster updates.")
        else:
            recs.append(f"• Memory Health: {specs['ram_total_gb']} GB RAM ({100 - specs['ram_used_pct']}% free) provides plenty of headroom for software updates.")

        for d in specs["drives"]:
            if d["free_gb"] < 20 or d["used_pct"] > 90:
                recs.append(f"• Low Disk Space on {d['drive']} ({d['free_gb']} GB free): Free up disk space before running large updates.")
            else:
                recs.append(f"• Storage Health ({d['drive']}): {d['free_gb']} GB free space available ({100 - d['used_pct']:.1f}% free) — optimal for SSD performance.")

        if not specs["is_admin"]:
            recs.append("• Privilege Notice: Running as Standard User. Click 'Elevate' in the top-right to prevent UAC popups during updates.")
        else:
            recs.append("• Privilege Status: Running with full Administrator privileges — updates will install smoothly.")

        self.lbl_recommendations.config(text="💡 Smart System Diagnostics:\n" + "\n".join(recs))

    def _on_scan_finished(self, upgradable_apps: list):
        self.is_scanning = False
        self.updates_list = upgradable_apps

        # Update KPI Cards
        self.card_inst_val.config(text=str(len(self.installed_apps)))
        self.card_upd_val.config(text=str(len(self.updates_list)))

        self._refresh_updates_tree()
        self._refresh_inventory_tree()

        self.btn_scan.config(state="normal")
        has_updates = len(self.updates_list) > 0
        self.btn_update_all.config(state="normal" if has_updates else "disabled")
        self.btn_update_selected.config(state="normal" if has_updates else "disabled")

        # Format Windows Updates Notice cleanly (extract KB numbers first)
        if self.windows_updates:
            kb_matches = []
            for title in self.windows_updates:
                found_kbs = re.findall(r"\bKB\d+\b", title, flags=re.IGNORECASE)
                if found_kbs:
                    kb_matches.extend(found_kbs)
                else:
                    kb_matches.append(title[:38] + ("..." if len(title) > 38 else ""))
            kb_summary = ", ".join(dict.fromkeys(kb_matches))
            self.win_notice_lbl.config(
                text=f"🔔 {len(self.windows_updates)} Windows OS Update(s) Available ({kb_summary}). Installed separately via Windows Update."
            )
            self.win_notice_frame.pack(fill=tk.X, padx=20, pady=(2, 4), before=self.notebook)
        else:
            self.win_notice_frame.pack_forget()

        self.lbl_status.config(
            text=f"✅ Scan complete on {self.specs.get('hostname', 'PC')}: {len(self.updates_list)} software updates available across {len(self.installed_apps)} installed apps."
        )
        self.log_ui(f"[SCAN COMPLETE] {len(self.updates_list)} software updates ready | {len(self.windows_updates)} Windows OS updates pending.")

    def _refresh_updates_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        query = self.search_var.get().strip().lower()
        for app in self.updates_list:
            if query and query not in app["name"].lower() and query not in app["id"].lower():
                continue
            self.tree.insert(
                "", tk.END,
                values=(app["name"], app["id"], app["current"], app["available"], app["status"]),
                tags=(app["tag"],)
            )

    def _refresh_inventory_tree(self):
        for item in self.inv_tree.get_children():
            self.inv_tree.delete(item)

        query = self.inv_search_var.get().strip().lower()
        shown = 0
        for app in self.installed_apps:
            if query and query not in app["name"].lower() and query not in app["publisher"].lower():
                continue
            self.inv_tree.insert("", tk.END, values=(app["name"], app["version"], app["publisher"], app["scope"]))
            shown += 1
        self.lbl_inv_count.config(text=f"📦 Installed Software Inventory ({shown} of {len(self.installed_apps)} programs shown)")

    # -----------------------------------------------------------------
    # SEQUENTIAL UPDATE & VERIFICATION WORKFLOW
    # -----------------------------------------------------------------
    def start_update_all(self):
        if not self.updates_list or self.is_updating:
            return
        pending = [a for a in self.updates_list if a["tag"] != "verified"]
        targets = pending if pending else self.updates_list
        self._start_sequential_updates(targets)

    def start_update_selected(self):
        if self.is_updating:
            return
        selected_ids = [self.tree.item(item)["values"][1] for item in self.tree.selection()]
        if not selected_ids:
            messagebox.showinfo("Select Applications", "Click one or more applications in the table to highlight them first.")
            return
        targets = [app for app in self.updates_list if app["id"] in selected_ids]
        self._start_sequential_updates(targets)

    def _start_sequential_updates(self, targets: list):
        if not targets:
            return

        # Show System Restore Confirmation Dialog (Yes/No with Recommendation to Yes)
        dialog = RestorePointConfirmDialog(self, len(targets), self.silent_mode_var.get())
        self.wait_window(dialog)

        if dialog.result is None:
            # User clicked Cancel or closed the dialog
            return

        create_restore = (dialog.result == "yes")
        self.restore_point_var.set(create_restore)

        self.is_updating = True
        self.stop_requested = False
        self.btn_scan.config(state="disabled")
        self.btn_update_all.config(state="disabled")
        self.btn_update_selected.config(state="disabled")
        self.btn_stop.config(state="normal")
        self.progress_var.set(0.0)

        if not self.log_visible:
            self.toggle_log_pane()

        threading.Thread(
            target=self._worker_sequential_updates,
            args=(targets, create_restore),
            daemon=True
        ).start()

    def _set_app_state(self, pkg_id: str, current_ver=None, status="Installing...", tag="updating"):
        for app in self.updates_list:
            if app["id"] == pkg_id:
                if current_ver:
                    app["current"] = current_ver
                app["status"] = status
                app["tag"] = tag
                break
        # Update matching row in tree if visible
        for item in self.tree.get_children():
            vals = list(self.tree.item(item)["values"])
            if len(vals) > 1 and vals[1] == pkg_id:
                if current_ver:
                    vals[2] = current_ver
                vals[4] = status
                self.tree.item(item, values=vals, tags=(tag,))
                self.tree.see(item)
                break

    def _worker_sequential_updates(self, targets: list, create_restore: bool = True):
        total = len(targets)
        self.log_ui("=" * 68)
        self.log_ui(f"[BATCH START] Updating {total} application(s) sequentially...")

        # 1. System Restore Point Protection (if requested)
        if create_restore:
            self.after(0, lambda: self.lbl_status.config(text="🛡️ Creating Windows System Restore Point... Please wait."))
            self.log_ui("[RESTORE POINT] Requesting Windows System Restore Point ('Before Software Update')...")
            ok, msg = create_windows_restore_point("Before Software Update")
            if ok:
                self.log_ui(f"[RESTORE POINT] ✓ {msg}")
            else:
                self.log_ui(f"[RESTORE POINT] ⚠ {msg}")
        else:
            self.log_ui("[RESTORE POINT] Skipped by user selection.")

        success_count = 0
        reboot_count = 0
        failed_count = 0

        for idx, app in enumerate(targets, 1):
            if self.stop_requested:
                self.log_ui("[BATCH STOPPED] Stopped by user before starting next package.")
                break

            pkg_id = app["id"]
            name = app["name"]
            old_ver = app["current"]
            avail_ver = app["available"]

            pct = ((idx - 1) / total) * 100
            self.after(0, lambda v=pct: self.progress_var.set(v))
            self.after(0, lambda n=name, i=idx, t=total: self.lbl_status.config(text=f"⚡ Updating [{i}/{t}]: {n} ({old_ver} → {avail_ver})..."))
            self.after(0, lambda p=pkg_id: self._set_app_state(p, status="Installing...", tag="updating"))

            self.log_ui("-" * 54)
            self.log_ui(f"[{idx}/{total}] Upgrading: {name} ({pkg_id}) | {old_ver} -> {avail_ver}")

            cmd = [
                "winget", "upgrade",
                "--id", pkg_id,
                "--exact",
                "--accept-source-agreements",
                "--accept-package-agreements",
            ]
            if self.silent_mode_var.get():
                cmd.append("--silent")

            try:
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                proc = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, errors="replace", bufsize=1, startupinfo=startupinfo
                )

                while True:
                    line = proc.stdout.readline()
                    if not line and proc.poll() is not None:
                        break
                    if line:
                        stripped = line.strip()
                        if stripped and len(stripped) > 2 and not all(c in "-\\|/" for c in stripped):
                            self.log_ui(f"  > {stripped}", to_file=False)

                return_code = proc.wait(timeout=600)
                decoded_badge, decoded_desc = decode_winget_exit_code(return_code)
                self.log_ui(f"[EXIT CODE] {name} finished with code {return_code} ({decoded_desc})")

                # Post-install verification
                self.after(0, lambda p=pkg_id: self._set_app_state(p, status="Verifying...", tag="updating"))
                verified, verified_ver = self._verify_installation(pkg_id, avail_ver)

                u_code = return_code & 0xFFFFFFFF
                # 0 = OK, -1978335189 (0x8A15002B) = No applicable upgrade found (already up to date)
                if return_code in (0, -1978335189, 0x8A15002B, 0x8A15010D) or u_code in (0x8A15002B, 0x8A15010D) or verified:
                    success_count += 1
                    self.verified_session_count += 1
                    final_ver = verified_ver or avail_ver
                    status_text = f"✓ Verified ({final_ver})"
                    self.after(0, lambda p=pkg_id, v=f"{old_ver} → {final_ver}", s=status_text: self._set_app_state(p, current_ver=v, status=s, tag="verified"))
                    self.after(0, lambda c=self.verified_session_count: self.card_ver_val.config(text=str(c)))
                    self.log_ui(f"[VERIFIED] {name} confirmed at version {final_ver}")
                elif return_code in (3010, 1641) or u_code in (0x8A150109, 0x8A15010A, 0x8A15010B):
                    reboot_count += 1
                    self.verified_session_count += 1
                    status_text = "⚠ Reboot Needed"
                    self.after(0, lambda p=pkg_id, v=f"{old_ver} → {avail_ver}", s=status_text: self._set_app_state(p, current_ver=v, status=s, tag="reboot"))
                    self.after(0, lambda c=self.verified_session_count: self.card_ver_val.config(text=str(c)))
                    self.log_ui(f"[REBOOT NEEDED] {name} installed; restart required ({decoded_desc}).")
                else:
                    failed_count += 1
                    status_text = decoded_badge
                    self.after(0, lambda p=pkg_id, s=status_text: self._set_app_state(p, status=s, tag="failed"))
                    self.log_ui(f"[STATUS] {name}: {decoded_badge} — {decoded_desc}")

            except Exception as e:
                failed_count += 1
                self.log_ui(f"[ERROR] Exception updating {name}: {e}")
                self.after(0, lambda p=pkg_id: self._set_app_state(p, status="✗ Error", tag="failed"))

            time.sleep(1.0)

        self.after(0, lambda: self.progress_var.set(100))
        self.after(100, lambda: self._on_batch_complete(total, success_count, reboot_count, failed_count))

    def _verify_installation(self, pkg_id: str, target_version: str):
        """Confirm via winget list that the package is now at target_version."""
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            res = subprocess.run(
                ["winget", "list", "--id", pkg_id, "--exact", "--accept-source-agreements"],
                capture_output=True, text=True, errors="replace", timeout=30, startupinfo=startupinfo
            )
            for line in res.stdout.splitlines():
                if pkg_id.lower() in line.lower():
                    if target_version in line:
                        return True, target_version
                    # Check if no Available version column remains (meaning up to date)
                    parts = line.split()
                    for p in parts:
                        if any(c.isdigit() for c in p) and "." in p and p.lower() != pkg_id.lower():
                            return False, p
            return False, target_version
        except Exception:
            return False, target_version

    def _on_batch_complete(self, total, success, reboot, failed):
        self.is_updating = False
        self.stop_requested = False
        self.btn_scan.config(state="normal")
        self.btn_update_all.config(state="normal")
        self.btn_update_selected.config(state="normal")
        self.btn_stop.config(state="disabled")

        summary_msg = f"Batch finished: {success} verified, {reboot} need reboot, {failed} failed."
        self.lbl_status.config(text=summary_msg)
        self.log_ui("=" * 68)
        self.log_ui(f"[BATCH SUMMARY] {summary_msg}")

        msg = (
            f"Update Batch Complete!\n\n"
            f"• Total Processed : {success + reboot + failed} of {total}\n"
            f"• ✓ Verified OK   : {success}\n"
            f"• ⚠ Needs Reboot  : {reboot}\n"
            f"• ✗ Failed        : {failed}\n"
        )
        if self.windows_updates:
            msg += f"\nReminder: {len(self.windows_updates)} Windows OS Update(s) are available in Windows Settings."
        messagebox.showinfo("Update Batch Summary", msg)

    # -----------------------------------------------------------------
    # EXPORT FULL AUDIT REPORT
    # -----------------------------------------------------------------
    def export_audit_report(self):
        default_name = f"System_Audit_{self.specs.get('hostname', 'PC')}_{datetime.now().strftime('%Y%m%d_%H%M')}.txt"
        out_path = filedialog.asksaveasfilename(
            title="Save System & Software Audit Report",
            defaultextension=".txt",
            initialfile=default_name,
            filetypes=[("Text Report", "*.txt"), ("All Files", "*.*")],
        )
        if not out_path:
            return

        try:
            lines = [
                "=" * 72,
                f"{APP_NAME} v{APP_VERSION} — SYSTEM & SOFTWARE AUDIT REPORT",
                f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                "=" * 72,
                "",
                "[1. COMPUTER HARDWARE & OS SPECIFICATIONS]",
                f"  Hostname         : {self.specs.get('hostname')}",
                f"  Manufacturer     : {self.specs.get('manufacturer')} ({self.specs.get('model')})",
                f"  Operating System : {self.specs.get('os_name')} {self.specs.get('os_display_ver')} (Build {self.specs.get('os_build')})",
                f"  Processor (CPU)  : {self.specs.get('cpu_name')} ({self.specs.get('cpu_threads')} threads)",
                f"  Graphics (GPU)   : {self.specs.get('primary_gpu')}",
                f"  Memory (RAM)     : {self.specs.get('ram_total_gb')} GB ({self.specs.get('ram_usable_gb')} GB usable)",
                f"  Winget Version   : {self.specs.get('winget_version')}",
                "",
                "[2. STORAGE DRIVES]",
            ]
            for d in self.specs.get("drives", []):
                lines.append(f"  Drive {d['drive']} ({d['type']}): {d['used_gb']} GB used / {d['total_gb']} GB total ({d['free_gb']} GB free)")

            lines.extend(["", f"[3. PENDING WINDOWS OS UPDATES ({len(self.windows_updates)})]"])
            for wu in self.windows_updates or ["None pending"]:
                lines.append(f"  • {wu}")

            lines.extend(["", f"[4. SOFTWARE UPDATES STATUS ({len(self.updates_list)})]"])
            for u in self.updates_list:
                lines.append(f"  • {u['name']} ({u['id']}): {u['current']} -> {u['available']} [{u['status']}]")

            lines.extend(["", f"[5. FULL INSTALLED SOFTWARE INVENTORY ({len(self.installed_apps)})]"])
            for app in self.installed_apps:
                lines.append(f"  • {app['name']} | Ver: {app['version']} | {app['publisher']} ({app['scope']})")

            with open(out_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))

            messagebox.showinfo("Report Saved", f"Audit report exported successfully to:\n{out_path}")
        except Exception as e:
            messagebox.showerror("Export Failed", f"Could not write report: {e}")


if __name__ == "__main__":
    enable_high_dpi()
    # Automatically request Administrator privileges on startup unless --no-admin is passed
    if "--no-admin" not in sys.argv and "--elevated" not in sys.argv and not is_User_Admin():
        relaunch_as_admin()

    app = UpdateManagerApp()
    app.mainloop()
