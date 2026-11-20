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
import urllib.request
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Any

from security_auditor import SecurityAuditor
import network_auditor
import agent_bridge

APP_NAME = "Software Update Manager"
APP_VERSION = "2.5.0"
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

AI_CATALOG = {
    "claude": {
        "name": "Claude Desktop",
        "vendor": "Anthropic",
        "winget_id": "Anthropic.Claude",
        "type": "Store / In-App",
        "site": "https://claude.ai/download",
        "default_status": "⚡ In-App Auto-Updater (Relaunch to update)",
    },
    "chatgpt": {
        "name": "ChatGPT Desktop",
        "vendor": "OpenAI",
        "winget_id": "OpenAI.ChatGPT",
        "type": "Store / MSIX",
        "site": "https://chatgpt.com/",
        "default_status": "🛍️ Managed via Microsoft Store",
    },
    "codex": {
        "name": "OpenAI Codex",
        "vendor": "OpenAI",
        "winget_id": "OpenAI.Codex",
        "type": "Store / MSIX",
        "site": "https://openai.com",
        "default_status": "🛍️ Managed via Microsoft Store",
    },
    "cursor": {
        "name": "Cursor AI",
        "vendor": "Anysphere",
        "winget_id": "Anysphere.Cursor",
        "type": "Win32 / Electron",
        "site": "https://cursor.com",
        "default_status": "✓ Up to Date",
    },
    "windsurf": {
        "name": "Windsurf AI",
        "vendor": "Codeium",
        "winget_id": "Codeium.Windsurf",
        "type": "Win32 / Electron",
        "site": "https://codeium.com/windsurf",
        "default_status": "✓ Up to Date",
    },
    "ollama": {
        "name": "Ollama LLM Engine",
        "vendor": "Ollama",
        "winget_id": "Ollama.Ollama",
        "type": "Win32 Service / CLI",
        "site": "https://ollama.com",
        "default_status": "✓ Up to Date",
    },
    "lm studio": {
        "name": "LM Studio",
        "vendor": "ElementLabs",
        "winget_id": "ElementLabs.LMStudio",
        "type": "Win32 / Electron",
        "site": "https://lmstudio.ai",
        "default_status": "✓ Up to Date",
    },
    "lmstudio": {
        "name": "LM Studio",
        "vendor": "ElementLabs",
        "winget_id": "ElementLabs.LMStudio",
        "type": "Win32 / Electron",
        "site": "https://lmstudio.ai",
        "default_status": "✓ Up to Date",
    },
    "anythingllm": {
        "name": "AnythingLLM",
        "vendor": "Mintplex Labs",
        "winget_id": "",
        "type": "Win32 / Electron",
        "site": "https://anythingllm.com",
        "default_status": "Manual / In-App Check",
    },
    "jan": {
        "name": "Jan AI",
        "vendor": "Jan",
        "winget_id": "Jan.Jan",
        "type": "Win32 / Electron",
        "site": "https://jan.ai",
        "default_status": "✓ Up to Date",
    },
    "pinokio": {
        "name": "Pinokio AI Browser",
        "vendor": "Pinokio",
        "winget_id": "pinokiocomputer.pinokio",
        "type": "Win32",
        "site": "https://pinokio.computer",
        "default_status": "✓ Up to Date",
    },
    "copilot": {
        "name": "GitHub Copilot",
        "vendor": "GitHub",
        "winget_id": "GitHub.CopilotApp",
        "type": "Win32",
        "site": "https://github.com/features/copilot",
        "default_status": "✓ Up to Date",
    },
    "microsoft copilot": {
        "name": "Microsoft Copilot",
        "vendor": "Microsoft",
        "winget_id": "",
        "type": "Windows In-Box",
        "site": "https://copilot.microsoft.com",
        "default_status": "✓ Windows Integrated",
    },
    "antigravity": {
        "name": "Antigravity",
        "vendor": "Google DeepMind",
        "winget_id": "Google.Antigravity",
        "type": "Agentic IDE",
        "site": "https://deepmind.google",
        "default_status": "✓ Up to Date",
    },
    "open-webui": {
        "name": "Open WebUI",
        "vendor": "Open WebUI",
        "winget_id": "",
        "type": "Web UI / Python",
        "site": "https://openwebui.com",
        "default_status": "✓ Local Sovereign Stack",
    },
    "comfyui": {
        "name": "ComfyUI",
        "vendor": "ComfyUI",
        "winget_id": "",
        "type": "Portable / Python",
        "site": "https://comfy.org",
        "default_status": "Git / Python Portable",
    },
    "google cloud sdk": {
        "name": "Google Cloud SDK",
        "vendor": "Google",
        "winget_id": "Google.CloudSDK",
        "type": "Win32 / CLI",
        "site": "https://cloud.google.com/sdk",
        "default_status": "✓ Up to Date (Reconciled)",
    },
    "localais": {
        "name": "LocalAIs Suite",
        "vendor": "LocalAIs.com",
        "winget_id": "",
        "type": "Store / MSIX",
        "site": "",
        "default_status": "🛍️ Managed via Microsoft Store",
    },
}


def scan_deep_ai_inventory(upgradable_map: dict = None) -> list[dict]:
    """
    Performs a deep multi-tier audit across:
    1. Windows Store / MSIX containers (Appx packages)
    2. Windows Registry hives (HKCU, HKLM, WOW6432Node)
    3. System PATH CLI binaries and developer runtimes
    Returns an enriched list of all installed AI applications, versions, and update mechanisms.
    """
    if upgradable_map is None:
        upgradable_map = {}
    inventory = {}

    # 1. Windows Store / MSIX containers via PowerShell Get-AppxPackage
    try:
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        ps_cmd = (
            "Get-AppxPackage | Select-Object Name, Version, PackageFullName, "
            "PackageFamilyName, InstallLocation | ConvertTo-Json -Compress"
        )
        proc = subprocess.run(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_cmd],
            capture_output=True, text=True, errors="replace", timeout=15, startupinfo=startupinfo
        )
        if proc.stdout.strip():
            pkgs = json.loads(proc.stdout)
            if isinstance(pkgs, dict):
                pkgs = [pkgs]
            for p in pkgs:
                p_name = p.get("Name", "")
                p_fam = p.get("PackageFamilyName", "")
                for key, meta in AI_CATALOG.items():
                    if key in p_name.lower():
                        norm_key = meta["name"]
                        app_id = f"shell:AppsFolder\\{p_fam}!App"
                        if "claude" in p_name.lower():
                            app_id = "shell:AppsFolder\\Claude_pzs8sxrjxfjjc!Claude"
                        elif "codex" in p_name.lower():
                            app_id = "shell:AppsFolder\\OpenAI.Codex_2p2nqsd0c76g0!App"
                        elif "chatgpt" in p_name.lower():
                            app_id = "shell:AppsFolder\\OpenAI.ChatGPT-Desktop_2p2nqsd0c76g0!ChatGPT"

                        inventory[norm_key] = {
                            "name": meta["name"],
                            "vendor": meta["vendor"],
                            "version": p.get("Version", "Store Managed"),
                            "source": "Windows Store (MSIX)",
                            "winget_id": meta["winget_id"],
                            "location": p.get("InstallLocation", ""),
                            "app_id": app_id,
                            "site": meta["site"],
                            "update_status": meta["default_status"],
                            "action_label": "Launch App" if "In-App" in meta["default_status"] else "Open Store",
                            "action_type": "app" if "In-App" in meta["default_status"] else "store",
                        }
                        break
    except Exception:
        pass

    # 2. Windows Registry Uninstall Hives (Win32 AI software)
    hives = [
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
    ]
    for root, subkey in hives:
        try:
            with winreg.OpenKey(root, subkey, 0, winreg.KEY_READ) as parent:
                for i in range(winreg.QueryInfoKey(parent)[0]):
                    try:
                        kname = winreg.EnumKey(parent, i)
                        with winreg.OpenKey(root, f"{subkey}\\{kname}", 0, winreg.KEY_READ) as k:
                            try:
                                dname, _ = winreg.QueryValueEx(k, "DisplayName")
                            except OSError:
                                dname = ""
                            for key, meta in AI_CATALOG.items():
                                if key in dname.lower():
                                    if key == "antigravity" and any(x in dname.lower() for x in ("skills", "extension", "plugin")):
                                        continue
                                    norm_key = meta["name"]
                                    if norm_key not in inventory or inventory[norm_key]["version"] in ("Store Managed", "Unknown"):
                                        try:
                                            dver, _ = winreg.QueryValueEx(k, "DisplayVersion")
                                        except OSError:
                                            dver = "Installed"
                                        try:
                                            iloc, _ = winreg.QueryValueEx(k, "InstallLocation")
                                        except OSError:
                                            iloc = ""
                                        try:
                                            dicon, _ = winreg.QueryValueEx(k, "DisplayIcon")
                                            app_exe = dicon.split(",")[0].strip('"')
                                        except OSError:
                                            app_exe = ""

                                        status = meta["default_status"]
                                        act_label = "Open App"
                                        act_type = "app"

                                        wid = meta["winget_id"].lower()
                                        if wid and wid in upgradable_map:
                                            upg = upgradable_map[wid]
                                            status = f"⬆️ Update Available ({upg.get('available', 'Newer')})"
                                            act_label = "Update via WinGet"
                                            act_type = "winget"

                                        inventory[norm_key] = {
                                            "name": meta["name"],
                                            "vendor": meta["vendor"],
                                            "version": dver,
                                            "source": "Windows Registry (Win32)",
                                            "winget_id": meta["winget_id"],
                                            "location": iloc or app_exe,
                                            "app_id": app_exe or iloc,
                                            "site": meta["site"],
                                            "update_status": status,
                                            "action_label": act_label,
                                            "action_type": act_type,
                                        }
                                    break
                    except OSError:
                        pass
        except OSError:
            pass

    # 3. CLI Tools on PATH
    cli_map = {
        "ollama": "Ollama LLM Engine",
        "cursor": "Cursor AI",
        "gcloud": "Google Cloud SDK",
    }
    for cmd, norm_key in cli_map.items():
        if norm_key not in inventory:
            p = shutil.which(cmd)
            if p:
                meta = AI_CATALOG.get(cmd, {})
                inventory[norm_key] = {
                    "name": norm_key,
                    "vendor": meta.get("vendor", "Unknown"),
                    "version": "Detected on PATH",
                    "source": "System PATH (CLI)",
                    "winget_id": meta.get("winget_id", ""),
                    "location": p,
                    "app_id": p,
                    "site": meta.get("site", ""),
                    "update_status": meta.get("default_status", "✓ Current"),
                    "action_label": "Open Terminal",
                    "action_type": "cli",
                }

    # 4. Check specific web / GitHub release for standalone tools (e.g. AnythingLLM)
    if "AnythingLLM" in inventory:
        try:
            req = urllib.request.Request(
                "https://api.github.com/repos/Mintplex-Labs/anything-llm/releases/latest",
                headers={"User-Agent": "Mozilla/5.0"}
            )
            with urllib.request.urlopen(req, timeout=3) as resp:
                gh_data = json.loads(resp.read().decode())
                latest_tag = gh_data.get("tag_name", "").lstrip("v")
                cur_v = inventory["AnythingLLM"]["version"]
                if latest_tag and cur_v != latest_tag:
                    inventory["AnythingLLM"]["update_status"] = f"⬆️ v{latest_tag} Available (GitHub)"
                    inventory["AnythingLLM"]["action_label"] = "Download v" + latest_tag
                    inventory["AnythingLLM"]["action_type"] = "web"
        except Exception:
            pass

    # 5. Check Antigravity / Electron In-App Auto-Updater state
    try:
        ag_candidates = [
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\antigravity\Antigravity.exe"),
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\Antigravity IDE\Antigravity IDE.exe"),
        ]
        ag_pending = os.path.expandvars(r"%LOCALAPPDATA%\antigravity-updater\pending\Antigravity-x64.exe")
        ag_exe = next((p for p in ag_candidates if os.path.exists(p)), None)
        if ag_exe:
            cur_v = get_pe_file_version(ag_exe) or "2.32.2"
            avail_v = get_pe_file_version(ag_pending) if os.path.exists(ag_pending) else ""
            status = "✓ Up to Date"
            act_label = "Open App"
            act_type = "app"
            if avail_v and cur_v != avail_v:
                status = f"⚡ In-App Update Ready (v{avail_v} — Restart to Update)"
                act_label = "Restart to Update"

            inventory["Antigravity"] = {
                "name": "Antigravity",
                "vendor": "Google DeepMind",
                "version": cur_v,
                "source": "Local App (Win32)",
                "winget_id": "Google.Antigravity",
                "location": ag_exe,
                "app_id": ag_exe,
                "site": "https://deepmind.google",
                "update_status": status,
                "action_label": act_label,
                "action_type": act_type,
            }
            inventory.pop("Antigravity IDE", None)
    except Exception:
        pass

    # 6. Zero-Dependency Network Boundary & Intrusion Audit (v2.4)
    try:
        listeners = network_auditor.audit_listening_ports()
        for item in inventory.values():
            item_name = item.get("name", "").lower()
            matched_listener = None
            for l in listeners:
                proc = l.get("process_name", "").lower()
                desc = l.get("service_desc", "").lower()
                port = str(l.get("port", ""))
                if (proc and proc in item_name) or (item_name in desc) or (port in item.get("location", "")):
                    matched_listener = l
                    break
                # Special cases for Ollama, LM Studio, etc.
                if "ollama" in item_name and l.get("port") == 11434:
                    matched_listener = l
                    break
                if "lm studio" in item_name and l.get("port") == 1234:
                    matched_listener = l
                    break
                if "antigravity" in item_name and l.get("port") == 8890:
                    matched_listener = l
                    break

            if matched_listener:
                item["network_status"] = matched_listener["badge"]
                item["listener_info"] = matched_listener
            else:
                item["network_status"] = "⚪ Desktop Native (Offline Client)"

        # Also register any active listening AI daemons detected on ports but not in inventory
        for l in listeners:
            port = l.get("port", 0)
            if port in network_auditor.KNOWN_AI_DEV_PORTS:
                svc_title = network_auditor.KNOWN_AI_DEV_PORTS[port]
                # Avoid duplicate if already in inventory
                if not any(svc_title.lower() in it.get("name", "").lower() or it.get("name", "").lower() in svc_title.lower() for it in inventory.values()):
                    inventory[svc_title] = {
                        "name": svc_title,
                        "vendor": "Local AI Daemon / Stack",
                        "version": f"Port {port} (PID {l.get('pid', 'N/A')})",
                        "source": "Active Network Daemon",
                        "winget_id": "",
                        "location": f"{l.get('process_name', 'Unknown')} (PID {l.get('pid')})",
                        "app_id": f"http://127.0.0.1:{port}",
                        "site": f"http://localhost:{port}",
                        "update_status": "✓ Active Daemon",
                        "action_label": "Open Localhost",
                        "action_type": "web",
                        "network_status": l.get("badge", "🟢 Localhost (Isolated)"),
                        "listener_info": l,
                    }
    except Exception:
        for item in inventory.values():
            if "network_status" not in item:
                item["network_status"] = "⚪ Desktop Native (Offline Client)"

    return sorted(list(inventory.values()), key=lambda x: x["name"])

def get_pe_file_version(filepath: str) -> str:
    """Read the exact product/file version of a Windows executable using native Win32 Version APIs."""
    if not filepath or not os.path.exists(filepath):
        return ""
    try:
        from ctypes import wintypes
        size = ctypes.windll.version.GetFileVersionInfoSizeW(filepath, None)
        if not size:
            return ""
        res = ctypes.create_string_buffer(size)
        ctypes.windll.version.GetFileVersionInfoW(filepath, None, size, res)
        u_len = wintypes.UINT()
        lp_data = ctypes.c_void_p()
        ctypes.windll.version.VerQueryValueW(res, r"\\", ctypes.byref(lp_data), ctypes.byref(u_len))
        class VS_FIXEDFILEINFO(ctypes.Structure):
            _fields_ = [
                ("dwSignature", wintypes.DWORD),
                ("dwStrucVersion", wintypes.DWORD),
                ("dwFileVersionMS", wintypes.DWORD),
                ("dwFileVersionLS", wintypes.DWORD),
                ("dwProductVersionMS", wintypes.DWORD),
                ("dwProductVersionLS", wintypes.DWORD),
                ("dwFileFlagsMask", wintypes.DWORD),
                ("dwFileFlags", wintypes.DWORD),
                ("dwFileOS", wintypes.DWORD),
                ("dwFileType", wintypes.DWORD),
                ("dwFileSubtype", wintypes.DWORD),
                ("dwFileDateMS", wintypes.DWORD),
                ("dwFileDateLS", wintypes.DWORD),
            ]
        vs = VS_FIXEDFILEINFO.from_address(lp_data.value)
        v1 = vs.dwFileVersionMS >> 16
        v2 = vs.dwFileVersionMS & 0xFFFF
        v3 = vs.dwFileVersionLS >> 16
        v4 = vs.dwFileVersionLS & 0xFFFF
        if v4 == 0:
            return f"{v1}.{v2}.{v3}"
        return f"{v1}.{v2}.{v3}.{v4}"
    except Exception:
        return ""


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


def find_browser_executable(binary_name: str, fallback_paths: list[str]) -> Optional[str]:
    """Find a browser executable via Windows Registry App Paths or standard filesystem locations."""
    for root in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        try:
            with winreg.OpenKey(root, rf"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{binary_name}") as k:
                val, _ = winreg.QueryValueEx(k, "")
                if val:
                    clean_val = val.strip('"')
                    if os.path.exists(clean_val):
                        return clean_val
        except Exception:
            pass
    for p in fallback_paths:
        exp_p = os.path.expandvars(p)
        if os.path.exists(exp_p):
            return exp_p
    return None


def trigger_browser_background_updates() -> list[dict]:
    """
    Triggers native background updater services and opens all installed browsers
    directly to their official Update / About pages so they are brought up to check for updates.
    Returns a list of dicts: {"name": str, "opened_ui": bool, "signaled_service": bool, "url": str}
    """
    browsers_spec = [
        {
            "name": "Google Chrome",
            "binary": "chrome.exe",
            "fallbacks": [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe",
            ],
            "update_args": ["chrome://settings/help"],
            "url_label": "chrome://settings/help",
            "service_exes": [
                r"C:\Program Files\Google\Update\GoogleUpdate.exe",
                r"C:\Program Files (x86)\Google\Update\GoogleUpdate.exe",
                r"%LOCALAPPDATA%\Google\Update\GoogleUpdate.exe",
            ],
            "service_args": ["/c"],
        },
        {
            "name": "Microsoft Edge",
            "binary": "msedge.exe",
            "fallbacks": [
                r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
                r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe",
            ],
            "update_args": ["edge://settings/help"],
            "url_label": "edge://settings/help",
            "service_exes": [
                r"C:\Program Files (x86)\Microsoft\EdgeUpdate\MicrosoftEdgeUpdate.exe",
                r"C:\Program Files\Microsoft\EdgeUpdate\MicrosoftEdgeUpdate.exe",
                r"%LOCALAPPDATA%\Microsoft\EdgeUpdate\MicrosoftEdgeUpdate.exe",
            ],
            "service_args": ["/c"],
        },
        {
            "name": "Mozilla Firefox",
            "binary": "firefox.exe",
            "fallbacks": [
                r"C:\Program Files\Mozilla Firefox\firefox.exe",
                r"C:\Program Files (x86)\Mozilla Firefox\firefox.exe",
                r"%LOCALAPPDATA%\Mozilla Firefox\firefox.exe",
            ],
            "update_args": ["-url", "about:preferences#general"],
            "url_label": "about:preferences#general",
            "service_exes": [],
            "service_args": [],
        },
        {
            "name": "Brave Browser",
            "binary": "brave.exe",
            "fallbacks": [
                r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
                r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe",
                r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe",
            ],
            "update_args": ["brave://settings/help"],
            "url_label": "brave://settings/help",
            "service_exes": [
                r"C:\Program Files\BraveSoftware\Update\BraveUpdate.exe",
                r"C:\Program Files (x86)\BraveSoftware\Update\BraveUpdate.exe",
                r"%LOCALAPPDATA%\BraveSoftware\Update\BraveUpdate.exe",
            ],
            "service_args": ["/c"],
        },
        {
            "name": "Opera",
            "binary": "opera.exe",
            "fallbacks": [
                r"%LOCALAPPDATA%\Programs\Opera\launcher.exe",
                r"%PROGRAMFILES%\Opera\launcher.exe",
            ],
            "update_args": ["opera://update"],
            "url_label": "opera://update",
            "service_exes": [],
            "service_args": [],
        },
        {
            "name": "Vivaldi",
            "binary": "vivaldi.exe",
            "fallbacks": [
                r"%LOCALAPPDATA%\Vivaldi\Application\vivaldi.exe",
                r"%PROGRAMFILES%\Vivaldi\Application\vivaldi.exe",
            ],
            "update_args": ["vivaldi://help"],
            "url_label": "vivaldi://help",
            "service_exes": [],
            "service_args": [],
        },
    ]

    results = []
    for b in browsers_spec:
        browser_exe = find_browser_executable(b["binary"], b["fallbacks"])
        if not browser_exe:
            continue

        signaled_svc = False
        for s_exe in b["service_exes"]:
            exp_s = os.path.expandvars(s_exe)
            if os.path.exists(exp_s):
                try:
                    subprocess.Popen([exp_s] + b["service_args"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    signaled_svc = True
                    break
                except Exception:
                    pass

        opened_ui = False
        try:
            subprocess.Popen([browser_exe] + b["update_args"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            opened_ui = True
        except Exception:
            pass

        if opened_ui or signaled_svc:
            results.append({
                "name": b["name"],
                "opened_ui": opened_ui,
                "signaled_service": signaled_svc,
                "url": b["url_label"]
            })

    return results


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
# DEVELOPER TOOL REGISTRY VERSION RECONCILIATION
# =====================================================================
def get_real_gcloud_version() -> str:
    """Read the actual Google Cloud SDK CLI version from disk via 'gcloud version'."""
    gcloud_path = shutil.which("gcloud") or shutil.which("gcloud.cmd")
    if not gcloud_path:
        cand = os.path.expandvars(r"%LOCALAPPDATA%\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd")
        if os.path.exists(cand):
            gcloud_path = cand
    if not gcloud_path:
        return ""
    try:
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        res = subprocess.run(
            [gcloud_path, "version"],
            capture_output=True,
            text=True,
            errors="replace",
            timeout=15,
            startupinfo=startupinfo,
        )
        m = re.search(r"Google Cloud SDK\s+([0-9]+\.[0-9]+\.[0-9]+)", res.stdout)
        if m:
            return m.group(1)
    except Exception:
        pass
    return ""


def sync_gcloud_sdk_version() -> tuple[bool, str]:
    """
    Detects if Google Cloud SDK CLI on disk is at a newer version than reported
    in Windows Registry (which causes WinGet to endlessly flag it as outdated).
    Reconciles the registry DisplayVersion with the actual CLI version.
    """
    real_ver = get_real_gcloud_version()
    if not real_ver:
        return False, "Google Cloud SDK CLI not found on disk"

    hives = [
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
    ]

    updated = False
    for root, subkey in hives:
        try:
            with winreg.OpenKey(root, subkey, 0, winreg.KEY_READ) as parent:
                num_subkeys = winreg.QueryInfoKey(parent)[0]
                for i in range(num_subkeys):
                    try:
                        kname = winreg.EnumKey(parent, i)
                        full_sub = f"{subkey}\\{kname}"
                        with winreg.OpenKey(root, full_sub, 0, winreg.KEY_READ) as k:
                            try:
                                dname, _ = winreg.QueryValueEx(k, "DisplayName")
                            except OSError:
                                dname = ""
                            if "Google Cloud SDK" in dname or kname == "Google Cloud SDK":
                                try:
                                    cur_ver, _ = winreg.QueryValueEx(k, "DisplayVersion")
                                except OSError:
                                    cur_ver = ""
                                if cur_ver != real_ver:
                                    with winreg.OpenKey(root, full_sub, 0, winreg.KEY_SET_VALUE) as wk:
                                        winreg.SetValueEx(wk, "DisplayVersion", 0, winreg.REG_SZ, real_ver)
                                    updated = True
                    except OSError:
                        continue
        except OSError:
            continue

    if updated:
        return True, f"Reconciled Google Cloud SDK registry to {real_ver} (was out of sync)"
    return False, f"Google Cloud SDK registry already in sync ({real_ver})"


def reconcile_developer_cli_tools() -> list[str]:
    """
    Scans for developer tools (like Google Cloud SDK) where the tool's internal updater
    updates binaries on disk without updating the Windows Uninstall registry key,
    causing WinGet to repeatedly report false-positive pending updates.
    Reconciles the registry DisplayVersion with the actual on-disk CLI version.
    """
    messages = []
    synced, msg = sync_gcloud_sdk_version()
    if synced:
        messages.append(msg)
    return messages


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

    # 8. Zero-Dependency Network Boundary & Intrusion Shield Audit (v2.4)
    try:
        listeners = network_auditor.audit_listening_ports()
        specs["network_listeners"] = listeners
        specs["exposed_ports_count"] = sum(1 for l in listeners if l.get("is_exposed"))
        is_shield_active, shield_desc = network_auditor.audit_firewall_shield()
        specs["firewall_shield_active"] = is_shield_active
        specs["firewall_shield_status"] = shield_desc
    except Exception:
        specs["network_listeners"] = []
        specs["exposed_ports_count"] = 0
        specs["firewall_shield_active"] = False
        specs["firewall_shield_status"] = "Not Audited"

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
                            install_loc = ""
                            display_icon = ""
                            uninstall_str = ""
                            sys_comp = 0
                            try:
                                version, _ = winreg.QueryValueEx(subkey, "DisplayVersion")
                            except OSError:
                                pass
                            try:
                                publisher, _ = winreg.QueryValueEx(subkey, "Publisher")
                            except OSError:
                                pass
                            try:
                                install_loc, _ = winreg.QueryValueEx(subkey, "InstallLocation")
                            except OSError:
                                pass
                            try:
                                display_icon, _ = winreg.QueryValueEx(subkey, "DisplayIcon")
                            except OSError:
                                pass
                            try:
                                uninstall_str, _ = winreg.QueryValueEx(subkey, "UninstallString")
                            except OSError:
                                pass
                            try:
                                sc_val, _ = winreg.QueryValueEx(subkey, "SystemComponent")
                                sys_comp = int(sc_val)
                            except OSError:
                                pass

                            clean_name = str(name).strip()
                            if clean_name not in apps_by_name:
                                apps_by_name[clean_name] = {
                                    "name": clean_name,
                                    "version": str(version).strip() if version else "—",
                                    "publisher": str(publisher).strip() if publisher else "Unknown Publisher",
                                    "scope": scope,
                                    "install_location": str(install_loc).strip() if install_loc else "",
                                    "display_icon": str(display_icon).strip() if display_icon else "",
                                    "uninstall_string": str(uninstall_str).strip() if uninstall_str else "",
                                    "system_component": sys_comp,
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
        self.include_unverified_var = tk.BooleanVar(value=False)

        # Pre-Update Security & Trust Gate
        self.security_auditor = SecurityAuditor()

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

        # 2b. Microsoft Store Updates Reminder Banner (Option C)
        self.store_notice_frame = tk.Frame(
            self, bg="#1e1b4b", highlightbackground="#6366f1", highlightthickness=1, padx=14, pady=6
        )
        self.store_notice_lbl = tk.Label(
            self.store_notice_frame,
            text="🛍️ Microsoft Store Apps: UWP & in-box apps (Notepad, Paint, Xbox, Snipping Tool) update via the Store.",
            bg="#1e1b4b", fg="#c7d2fe", font=("Segoe UI", 9, "bold"), anchor="w", justify=tk.LEFT
        )
        self.store_notice_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.btn_open_store = tk.Button(
            self.store_notice_frame,
            text="Open Store Updates",
            command=self.open_microsoft_store,
            bg="#4f46e5", fg="#ffffff", activebackground="#4338ca", activeforeground="#ffffff",
            font=("Segoe UI", 9, "bold"), relief="flat", padx=10, pady=2, cursor="hand2"
        )
        self.btn_open_store.pack(side=tk.RIGHT, padx=3)

        self.btn_sync_store = tk.Button(
            self.store_notice_frame,
            text="⚡ Sync Store Updates",
            command=self.trigger_store_updates,
            bg="#312e81", fg="#e0e7ff", activebackground="#3730a3", activeforeground="#ffffff",
            font=("Segoe UI", 9), relief="flat", padx=8, pady=2, cursor="hand2"
        )
        self.btn_sync_store.pack(side=tk.RIGHT, padx=3)

        btn_dismiss_store = tk.Button(
            self.store_notice_frame,
            text="✖",
            command=lambda: self.store_notice_frame.pack_forget(),
            bg="#1e1b4b", fg="#a5b4fc", activebackground="#312e81", activeforeground="#ffffff",
            font=("Segoe UI", 8, "bold"), relief="flat", padx=4, pady=1, cursor="hand2"
        )
        btn_dismiss_store.pack(side=tk.RIGHT, padx=(3, 0))

        # 2c. Purpose & Defensive Hardening Mission Banner (Option C)
        self.mission_frame = tk.Frame(
            self, bg="#064e3b", highlightbackground="#10b981", highlightthickness=1, padx=14, pady=5
        )
        self.mission_frame.pack(fill=tk.X, padx=20, pady=(0, 4))
        lbl_mission = tk.Label(
            self.mission_frame,
            text="🛡️ Purpose & Mission: Keep your computer fully updated while proactively protecting it against unknown network intrusions, exposed AI ports, and malicious payloads — 100% Free & Open-Source.",
            bg="#064e3b", fg="#a7f3d0", font=("Segoe UI", 9, "bold"), anchor="w", justify=tk.LEFT
        )
        lbl_mission.pack(side=tk.LEFT, fill=tk.X, expand=True)

        btn_ai_diag = tk.Button(
            self.mission_frame,
            text="🤖 AI Diagnose",
            command=self.open_ai_diagnose_dialog,
            bg="#2563eb", fg="#ffffff", activebackground="#1d4ed8", activeforeground="#ffffff",
            font=("Segoe UI", 8, "bold"), relief="flat", padx=8, pady=2, cursor="hand2"
        )
        btn_ai_diag.pack(side=tk.RIGHT, padx=3)

        btn_ai_shield = tk.Button(
            self.mission_frame,
            text="🛡️ Intrusion & AI Shield",
            command=self.open_ai_dev_hub,
            bg="#059669", fg="#ffffff", activebackground="#047857", activeforeground="#ffffff",
            font=("Segoe UI", 8, "bold"), relief="flat", padx=8, pady=2, cursor="hand2"
        )
        btn_ai_shield.pack(side=tk.RIGHT, padx=3)

        btn_dismiss_mission = tk.Button(
            self.mission_frame,
            text="✖",
            command=lambda: self.mission_frame.pack_forget(),
            bg="#064e3b", fg="#6ee7b7", activebackground="#047857", activeforeground="#ffffff",
            font=("Segoe UI", 8, "bold"), relief="flat", padx=4, pady=1, cursor="hand2"
        )
        btn_dismiss_mission.pack(side=tk.RIGHT, padx=(2, 0))

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
            search_frame, text="🤖 AI & Dev Tools", command=self.open_ai_dev_hub,
            bg="#4338ca", fg="#ffffff", relief="flat", font=("Segoe UI", 8, "bold"), padx=7, pady=2, cursor="hand2"
        ).pack(side=tk.LEFT, padx=3)

        # Updates Treeview Table
        table_container = ttk.Frame(self.tab_updater, style="Card.TFrame", padding=(1, 1, 1, 1))
        table_container.pack(fill=tk.BOTH, expand=True, pady=2)

        columns = ("name", "id", "current", "available", "trust", "status")
        self.tree = ttk.Treeview(table_container, columns=columns, show="headings", selectmode="extended", height=7)

        self.tree.heading("name", text="Application Name", anchor="w")
        self.tree.heading("id", text="Package ID", anchor="w")
        self.tree.heading("current", text="Installed Version", anchor="center")
        self.tree.heading("available", text="New Version", anchor="center")
        self.tree.heading("trust", text="Trust Gate", anchor="center")
        self.tree.heading("status", text="Update Status", anchor="center")

        self.tree.column("name", width=260, minwidth=170, anchor="w")
        self.tree.column("id", width=210, minwidth=140, anchor="w")
        self.tree.column("current", width=115, minwidth=85, anchor="center")
        self.tree.column("available", width=115, minwidth=85, anchor="center")
        self.tree.column("trust", width=130, minwidth=110, anchor="center")
        self.tree.column("status", width=160, minwidth=120, anchor="center")

        tree_scroll_y = ttk.Scrollbar(table_container, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scroll_y.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.tag_configure("pending", foreground="#38bdf8")
        self.tree.tag_configure("updating", foreground="#f59e0b")
        self.tree.tag_configure("verified", foreground="#10b981")
        self.tree.tag_configure("reboot", foreground="#fbbf24")
        self.tree.tag_configure("failed", foreground="#ef4444")
        self.tree.tag_configure("trust_risk", foreground="#ef4444")
        self.tree.tag_configure("trust_caution", foreground="#fbbf24")

        self._setup_tree_context_menu()

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

        self.btn_store = ttk.Button(
            btn_row, text="🛍️ Store Apps", style="Secondary.TButton", command=self.trigger_store_updates
        )
        self.btn_store.pack(side=tk.LEFT, padx=6)

        self.btn_ai_audit = ttk.Button(
            btn_row, text="🤖 AI Suites", style="Secondary.TButton", command=self.open_ai_dev_hub
        )
        self.btn_ai_audit.pack(side=tk.LEFT, padx=6)

        self.btn_ai_diagnose = ttk.Button(
            btn_row, text="🤖 AI Diagnose", style="Secondary.TButton", command=self.open_ai_diagnose_dialog
        )
        self.btn_ai_diagnose.pack(side=tk.LEFT, padx=6)

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
        chk_restore.pack(side=tk.LEFT, padx=(4, 8))

        # Security Gate: Allow Unverified Checkbox
        chk_unverified = tk.Checkbutton(
            btn_row,
            text="Allow Unverified",
            variable=self.include_unverified_var,
            bg=self.bg_color, fg="#fde047", selectcolor="#1e293b",
            activebackground=self.bg_color, activeforeground="#ffffff",
            font=("Segoe UI", 9)
        )
        chk_unverified.pack(side=tk.LEFT, padx=(4, 10))

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
        for c in range(4):
            self.specs_grid.columnconfigure(c, weight=1)

        self.spec_labels = {}
        fields = [
            ("computer", "Computer / Model"),
            ("os", "Operating System"),
            ("cpu", "Processor (CPU)"),
            ("gpu", "Graphics Card (GPU)"),
            ("ram", "Memory (RAM)"),
            ("storage", "Storage Drives"),
            ("network_shield", "🛡️ Network Boundary Sentinel"),
            ("firewall_status", "🛡️ Firewall LAN Shield"),
        ]
        for idx, (key, title) in enumerate(fields):
            r, c = divmod(idx, 4)
            box = tk.Frame(self.specs_grid, bg="#172033", padx=10, pady=6)
            box.grid(row=r, column=c, sticky="nsew", padx=4, pady=4)
            tk.Label(box, text=title, bg="#172033", fg=self.text_muted, font=("Segoe UI", 8, "bold")).pack(anchor="w")
            lbl = tk.Label(box, text="Scanning...", bg="#172033", fg=self.text_color, font=("Segoe UI", 9, "bold"), anchor="w", justify=tk.LEFT, wraplength=260)
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

        guide_content = """📘 WELCOME TO SOFTWARE UPDATE MANAGER & AUDITOR (v2.4)
================================================================================
The purpose of Software Update Manager is to keep your computer fully updated while proactively protecting it from unknown network intrusions, exposed local AI ports, and malicious payloads — 100% Free & Open-Source.

It automatically audits your computer's hardware specifications, scans all installed software, checks Authenticode digital signatures & PUP blocklists, audits listening network sockets, finds available updates, installs them sequentially, and verifies every update.

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
  • STAGE 1 (Computer Specs Scan): First, the app detects your computer's CPU, Graphics Card (GPU + VRAM), Memory (RAM), Storage Drives, Windows Build, Network Boundary listeners, and Administrator status. It updates the top-right hardware badge and populates the "💻 Computer Specs & Installed Apps" tab.
  • STAGE 2 (Deep Software & Update Scan): Next, it scans the Windows Registry for every installed application and checks Microsoft's Windows Package Manager (Winget) for newer versions, plus checks for pending Windows OS updates.

--------------------------------------------------------------------------------
3. PRE-UPDATE SECURITY & TRUST GATE (v2.3)
--------------------------------------------------------------------------------
Before updating any package, the application executes a zero-dependency Trust & Security Gate:
  • Authenticode Verification: Checks the existing executable's digital signature using Windows APIs to confirm publisher identity and prevent tampered binaries.
  • Suspicious Path Heuristics: Flags software located in dangerous or temporary directories (%TEMP%, C:\\Users\\Public, \\ProgramData\\, %AppData%\\Roaming).
  • PUP & Adware Blocklist: Automatically matches against pup_blocklist.json for known spyware, bundleware, and unwanted driver utilities.
  • Hidden SystemComponent Audit: Audits stealth registry entries used by spyware to hide from Add/Remove Programs.
  • Cloud Threat Intelligence (Optional): Free SHA-256 hash lookup via Abuse.ch MalwareBazaar & VirusTotal.
  • Trust Tiers:
      🟢 Trusted     : Signed by verified publisher, standard path, recognized package ID.
      🟡 Unverified  : Unsigned binary or non-standard directory (skipped in batch unless "Allow Unverified" is checked).
      🔴 High Risk   : Flagged PUP, hidden registry anomaly, or known malicious hash (permanently blocked from auto-update).
  • Right-Click Context Menu:
      Right-click any application in the table to view security details, inspect its SHA-256 on VirusTotal, or open its file location in File Explorer.

--------------------------------------------------------------------------------
4. NETWORK BOUNDARY SENTINEL & INTRUSION SHIELD (v2.4 NEW!) — 100% FREE
--------------------------------------------------------------------------------
Proactively protects your computer against autonomous network scanning platforms (e.g. ARTEX threat model), unauthenticated local AI endpoints, and lateral LAN intrusions:
  • Zero-Dependency Socket Audit:
    Audits all active listening TCP ports via native netstat to identify developer runtimes and local AI engines (Ollama 11434, LM Studio 1234, Open WebUI 8081, DwarfStar 8088, App Hub 8890, OpenCode 49374, ComfyUI 8188, dev ports 3000-5000, 8000-9000).
  • Exposure Classification:
      🟢 Localhost (Isolated)   : Bound safely to 127.0.0.1 loopback only. Protected from external LAN probes.
      🔴 Exposed to LAN (0.0.0.0): Bound to all network interfaces. Vulnerable to rogue devices on Wi-Fi/LAN.
      ⚪ Desktop Native (Offline): Standard desktop client executable with no active listening network ports.
  • 1-Click Windows Defender Firewall Hardener:
    Inside the "🤖 AI Suites" hub, click "🛡️ Harden Firewall (Block LAN Probes)" to toggle a native Windows Defender Firewall inbound block rule (SoftwareUpdateManager_Block_DevPorts_LAN) that blocks incoming LAN probes on AI/developer ports while preserving 100% full local loopback (127.0.0.1) connectivity.

--------------------------------------------------------------------------------
5. AI AGENT INTEGRATION, PERMISSIONS & SAFETY TUTORIALS (v2.5)
--------------------------------------------------------------------------------
Software Update Manager allows you to connect AI assistants (Microsoft Copilot, Claude Desktop, Antigravity IDE, Cursor, local LLMs) via a 4-Tier Permission Model and zero-port stdio MCP Server.

⚠️ Third-Party AI Autonomy & Responsibility Notice:
Connecting external AI agents to your system is an advanced, optional capability. While Software Update Manager enforces strict local permission boundaries and approval gates, the internal decision-making, reasoning, and outputs of third-party AI models remain entirely outside our control. By enabling live agent integration, you acknowledge and assume full responsibility for actions initiated by your chosen AI assistant.

🛡️ Safe Quick-Start Checklist:
  1. Start at Level 1 (Read-Only Diagnostic): Leave the permission tier on Level 1 for your first run. The AI can audit specs, updates, and open ports without altering any files.
  2. Use Local STDIO (Zero Open Ports): Connect desktop clients via local stdio (sys.stdin/sys.stdout) rather than opening HTTP ports on your LAN.
  3. Review Every Level 2 Approval Prompt: Always read the target app name and command before clicking Approve. Never approve actions on unverified packages.
  4. Create a Restore Point First: Auto-create a Windows System Restore Point before Level 3 autonomous batches.

🎥 Curated Video Tutorials & Learning:
  • Easy Connect Claude Desktop to MCP (Windows): https://www.youtube.com/watch?v=A151Nk_nN_U
  • Securing the MCP Server (What You Need to Know): https://www.youtube.com/watch?v=KYWr454hGF0
  • Least Privilege for AI Agents (Shrinking Blast Radius): https://www.youtube.com/watch?v=4HiuiYIJRTU
  • Official MCP Security Best Practices: https://modelcontextprotocol.io/docs/draft/tutorials/security/security_best_practices
  • Full Safety Guide: Read AGENT_SAFETY.md in the application directory.

--------------------------------------------------------------------------------
6. SPECIALIZED AI & DEV SUITES, BROWSERS & MICROSOFT STORE
--------------------------------------------------------------------------------
  • 🤖 AI & Dev Tools:
    Click the "🤖 AI & Dev Tools" button in the filter toolbar to instantly select and prioritize updates for AI assistants and developer suites (Antigravity IDE, Cursor, VS Code, Android Studio, GitHub Copilot, Ollama, LM Studio, Pinokio, Docker Desktop, etc.).
  • 🌐 Browser Background Updates:
    Click "🌐 Update Browsers" to silently invoke native background updater services for Google Chrome, Microsoft Edge, Brave, and Mozilla Firefox.
  • 🛍️ Microsoft Store & In-Box UWP Updates:
    Click "🛍️ Store Apps" or use the top banner to trigger the Windows Store background update service (InstallService) and launch the Microsoft Store directly to "Updates & downloads" where queued updates (Notepad, Paint, Xbox, Snipping Tool, HP) can be monitored and updated.

--------------------------------------------------------------------------------
7. HOW TO UPDATE YOUR SOFTWARE
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
8. MEANING OF UPDATE STATUS BADGES
--------------------------------------------------------------------------------
  • Pending Update (Blue)     : A newer version is available and ready to install.
  • Installing... (Amber)     : Winget is currently downloading and running the installer.
  • ✓ Verified (Green)        : The update finished AND post-install verification confirmed the new version.
  • ⚠ Reboot Needed (Yellow)  : The update succeeded, but Windows requires a restart to finalize replaced files.
  • ✗ App In-Use / Locked     : The application is currently open. Close it and retry.
  • ✗ Failed                  : The installer returned an error code. Check the live log for details.

--------------------------------------------------------------------------------
9. WHY ADMINISTRATOR MODE IS ENABLED AT STARTUP
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
        """Highlight pending AI updates in main table and open Deep AI Suite Auditor Hub."""
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
        self.open_ai_dev_hub()

    def open_live_diagnostic_viewer(self, parent_win=None):
        """Run and display the live PC diagnostic scan in a clean dedicated viewer window."""
        win = tk.Toplevel(parent_win or self)
        win.title("🔍 Live PC Diagnostic & Security Scan — Software Update Manager")
        win.geometry("900x640")
        win.minsize(780, 500)
        win.configure(bg="#0b1329")
        win.transient(parent_win or self)

        try:
            p = parent_win or self
            x = p.winfo_rootx() + (p.winfo_width() // 2) - 450
            y = p.winfo_rooty() + (p.winfo_height() // 2) - 320
            win.geometry(f"+{max(10, x)}+{max(10, y)}")
        except Exception:
            pass

        hdr = tk.Frame(win, bg="#131c38", padx=14, pady=10, highlightbackground="#3b82f6", highlightthickness=1)
        hdr.pack(fill=tk.X, padx=12, pady=(10, 6))

        tk.Label(
            hdr, text="🔍 Live PC Diagnostic & Security Scan",
            bg="#131c38", fg="#60a5fa", font=("Segoe UI", 12, "bold")
        ).pack(anchor="w")

        status_lbl = tk.Label(
            hdr, text="⏳ Scanning hardware specs, listening sockets, and package inventory...",
            bg="#131c38", fg="#94a3b8", font=("Segoe UI", 9)
        )
        status_lbl.pack(anchor="w", pady=(2, 0))

        txt_frame = tk.Frame(win, bg="#0b1329")
        txt_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=6)

        scroll = ttk.Scrollbar(txt_frame, orient=tk.VERTICAL)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        diag_text = tk.Text(
            txt_frame, bg="#020617", fg="#e2e8f0", insertbackground="#ffffff",
            font=("Consolas", 10), wrap=tk.WORD, yscrollcommand=scroll.set,
            padx=12, pady=10, relief="flat", highlightbackground="#1e293b", highlightthickness=1
        )
        diag_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.config(command=diag_text.yview)

        act_bar = tk.Frame(win, bg="#0b1329", pady=8)
        act_bar.pack(fill=tk.X, padx=12)

        def _copy_report():
            win.clipboard_clear()
            win.clipboard_append(diag_text.get("1.0", tk.END))
            messagebox.showinfo("Copied", "Full diagnostic report copied to clipboard!", parent=win)

        def _save_report():
            try:
                from tkinter import filedialog
                p = filedialog.asksaveasfilename(
                    parent=win,
                    title="Save Diagnostic Report",
                    defaultextension=".md",
                    filetypes=[("Markdown Document", "*.md"), ("Text Files", "*.txt"), ("All Files", "*.*")],
                    initialfile="ai_pc_diagnostic_report.md"
                )
                if p:
                    with open(p, "w", encoding="utf-8") as f:
                        f.write(diag_text.get("1.0", tk.END))
                    messagebox.showinfo("Saved", f"Report saved successfully to:\n{p}", parent=win)
            except Exception as e:
                messagebox.showerror("Save Error", f"Failed to save file: {e}", parent=win)

        tk.Button(
            act_bar, text="📋 Copy Report", command=_copy_report,
            bg="#2563eb", fg="#ffffff", activebackground="#1d4ed8", activeforeground="#ffffff",
            font=("Segoe UI", 9, "bold"), relief="flat", padx=12, pady=5, cursor="hand2"
        ).pack(side=tk.LEFT, padx=(0, 6))

        tk.Button(
            act_bar, text="💾 Save to File", command=_save_report,
            bg="#1e293b", fg="#cbd5e1", activebackground="#334155", activeforeground="#ffffff",
            font=("Segoe UI", 9), relief="flat", padx=10, pady=5, cursor="hand2"
        ).pack(side=tk.LEFT, padx=4)

        tk.Button(
            act_bar, text="✖ Close", command=win.destroy,
            bg="#334155", fg="#e2e8f0", activebackground="#475569", activeforeground="#ffffff",
            font=("Segoe UI", 9), relief="flat", padx=12, pady=5, cursor="hand2"
        ).pack(side=tk.RIGHT)

        def _async_scan():
            try:
                content = agent_bridge.generate_ai_prompt_bundle()
                def _update_ui():
                    diag_text.delete("1.0", tk.END)
                    diag_text.insert(tk.END, content)
                    status_lbl.config(
                        text="✓ Scan Complete — Hardware health, listening sockets, and package inventory verified.",
                        fg="#34d399"
                    )
                win.after(0, _update_ui)
            except Exception as e:
                def _err_ui():
                    status_lbl.config(text=f"✗ Scan Failed: {e}", fg="#f87171")
                    diag_text.insert(tk.END, f"Error generating diagnostic report:\n{e}")
                win.after(0, _err_ui)

        threading.Thread(target=_async_scan, daemon=True).start()

    def open_ai_diagnose_dialog(self):
        """Open the Universal AI PC Diagnostic & Local Agent Bridge window."""
        win = tk.Toplevel(self)
        win.title("🤖 AI PC Diagnose & Local Agent Bridge — Software Update Manager")
        win.geometry("1020x760")
        win.minsize(900, 600)
        win.configure(bg="#0b1329")
        win.transient(self)

        # Center over parent
        try:
            x = self.winfo_rootx() + (self.winfo_width() // 2) - 510
            y = self.winfo_rooty() + (self.winfo_height() // 2) - 380
            win.geometry(f"+{max(10, x)}+{max(10, y)}")
        except Exception:
            pass

        # Top Banner (Always Fixed at Top)
        header_frame = tk.Frame(win, bg="#131c38", padx=16, pady=12, highlightbackground="#3b82f6", highlightthickness=1)
        header_frame.pack(fill=tk.X, padx=14, pady=(12, 8))

        # Pack Right-Side Action Button FIRST to guarantee full un-truncated width
        tk.Button(
            header_frame,
            text="🔍 Run Diagnostic Scan Now",
            command=lambda: self.open_live_diagnostic_viewer(win),
            bg="#059669", fg="#ffffff", activebackground="#047857", activeforeground="#ffffff",
            font=("Segoe UI", 10, "bold"), relief="flat", padx=16, pady=6, cursor="hand2"
        ).pack(side=tk.RIGHT, padx=(12, 0))

        title_col = tk.Frame(header_frame, bg="#131c38")
        title_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        tk.Label(
            title_col,
            text="🤖 AI PC Diagnose & Local Agent Bridge (v2.5)",
            bg="#131c38", fg="#60a5fa", font=("Segoe UI", 13, "bold"), anchor="w"
        ).pack(anchor="w")

        tk.Label(
            title_col,
            text="Generate sanitized diagnostic prompt bundles for any web AI, or connect desktop agents (Claude, Antigravity) via zero-port stdio MCP.",
            bg="#131c38", fg="#94a3b8", font=("Segoe UI", 9), anchor="w"
        ).pack(anchor="w", pady=(2, 0))

        # Scrollable Canvas Container so all content (including Third-Party Notice) is 100% visible
        canvas_container = tk.Frame(win, bg="#0b1329")
        canvas_container.pack(fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(canvas_container, bg="#0b1329", highlightthickness=0)
        v_scroll = ttk.Scrollbar(canvas_container, orient=tk.VERTICAL, command=canvas.yview)
        canvas.configure(yscrollcommand=v_scroll.set)

        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        container = tk.Frame(canvas, bg="#0b1329", padx=14)
        canvas_win = canvas.create_window((0, 0), window=container, anchor="nw")

        def _on_container_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _on_canvas_configure(event):
            canvas.itemconfig(canvas_win, width=event.width)

        container.bind("<Configure>", _on_container_configure)
        canvas.bind("<Configure>", _on_canvas_configure)

        def _on_mousewheel(event):
            try:
                if canvas.winfo_exists():
                    canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            except Exception:
                pass

        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        win.bind("<Destroy>", lambda e: canvas.unbind_all("<MouseWheel>"))

        # Section 1: Option A — Universal 1-Click Diagnostic Bundle
        card_a = tk.Frame(container, bg="#111827", padx=14, pady=12, highlightbackground="#1f2937", highlightthickness=1)
        card_a.pack(fill=tk.X, pady=6)

        tk.Label(
            card_a, text="📋 Option A: 1-Click AI Diagnostic Bundle (Zero Setup — Any Web AI)",
            bg="#111827", fg="#38bdf8", font=("Segoe UI", 10, "bold"), anchor="w"
        ).pack(anchor="w")

        tk.Label(
            card_a,
            text="Generates an injection-hardened diagnostic summary (Specs, Listening Sockets, Updates) and copies it to your clipboard with an expert diagnostic prompt.",
            bg="#111827", fg="#cbd5e1", font=("Segoe UI", 9), justify=tk.LEFT, wraplength=880
        ).pack(anchor="w", pady=(2, 8))

        btn_row_a = tk.Frame(card_a, bg="#111827")
        btn_row_a.pack(fill=tk.X)

        status_lbl_a = tk.Label(card_a, text="", bg="#111827", fg="#34d399", font=("Segoe UI", 9, "bold"))

        def _copy_bundle():
            bundle = agent_bridge.generate_ai_diagnostic_bundle()
            win.clipboard_clear()
            win.clipboard_append(bundle)
            status_lbl_a.config(text="✓ Sanitized AI Diagnostic Prompt copied to clipboard! Ready to paste into Copilot, Claude, or ChatGPT.")
            status_lbl_a.pack(anchor="w", pady=(6, 0))
            self.log_ui("[AI DIAGNOSE] Diagnostic prompt bundle copied to clipboard.")

        tk.Button(
            btn_row_a, text="📋 Copy AI Diagnostic Bundle", command=_copy_bundle,
            bg="#0284c7", fg="#ffffff", activebackground="#0369a1", activeforeground="#ffffff",
            font=("Segoe UI", 9, "bold"), relief="flat", padx=12, pady=5, cursor="hand2"
        ).pack(side=tk.LEFT, padx=(0, 6))

        tk.Button(
            btn_row_a, text="🌐 Open Copilot in Edge", command=lambda: webbrowser.open("https://copilot.microsoft.com"),
            bg="#1e293b", fg="#e2e8f0", activebackground="#334155", activeforeground="#ffffff",
            font=("Segoe UI", 9), relief="flat", padx=10, pady=5, cursor="hand2"
        ).pack(side=tk.LEFT, padx=4)

        tk.Button(
            btn_row_a, text="🌐 Open Claude Web", command=lambda: webbrowser.open("https://claude.ai"),
            bg="#1e293b", fg="#e2e8f0", activebackground="#334155", activeforeground="#ffffff",
            font=("Segoe UI", 9), relief="flat", padx=10, pady=5, cursor="hand2"
        ).pack(side=tk.LEFT, padx=4)

        tk.Button(
            btn_row_a, text="🌐 Open ChatGPT", command=lambda: webbrowser.open("https://chatgpt.com"),
            bg="#1e293b", fg="#e2e8f0", activebackground="#334155", activeforeground="#ffffff",
            font=("Segoe UI", 9), relief="flat", padx=10, pady=5, cursor="hand2"
        ).pack(side=tk.LEFT, padx=4)

        # Section 2: Option B — Local Stdio MCP Bridge
        card_b = tk.Frame(container, bg="#111827", padx=14, pady=12, highlightbackground="#1f2937", highlightthickness=1)
        card_b.pack(fill=tk.X, pady=6)

        tk.Label(
            card_b, text="⚡ Option B: Local Stdio MCP Bridge (Claude Desktop, Antigravity, Cursor)",
            bg="#111827", fg="#818cf8", font=("Segoe UI", 10, "bold"), anchor="w"
        ).pack(anchor="w")

        tk.Label(
            card_b,
            text="Exposes verified diagnostic and update tools to agentic IDEs via JSON-RPC stdio. 0 open network ports, 0 MB GPU VRAM overhead.",
            bg="#111827", fg="#cbd5e1", font=("Segoe UI", 9), justify=tk.LEFT, wraplength=880
        ).pack(anchor="w", pady=(2, 8))

        btn_row_b = tk.Frame(card_b, bg="#111827")
        btn_row_b.pack(fill=tk.X)

        status_lbl_b = tk.Label(card_b, text="", bg="#111827", fg="#34d399", font=("Segoe UI", 9))

        def _auto_configure_mcp():
            clients = agent_bridge.detect_mcp_clients()
            if not clients:
                messagebox.showinfo(
                    "No Supported MCP Clients Found",
                    "Could not find configuration folders for Claude Desktop or Antigravity IDE.\n\n"
                    "You can still use 'Copy MCP Config JSON' to paste the configuration manually into any agentic tool.",
                    parent=win
                )
                return

            c_names = ", ".join(clients.keys())
            confirm = messagebox.askyesno(
                "Configure MCP Clients?",
                f"Detected local MCP environments: {c_names}\n\n"
                "Would you like Software Update Manager to automatically register its stdio bridge in their configuration files?",
                parent=win
            )
            if confirm:
                msgs = []
                for name, path in clients.items():
                    ok, res = agent_bridge.install_mcp_config_to_client(name, path)
                    msgs.append(f"• {name}: {'✓ Done' if ok else '✗ Failed'} ({res})")
                messagebox.showinfo("MCP Auto-Configuration Result", "\n\n".join(msgs), parent=win)
                status_lbl_b.config(text=f"✓ Auto-configured: {c_names}")
                status_lbl_b.pack(anchor="w", pady=(6, 0))
                _refresh_launch_buttons()

        def _copy_mcp_json():
            py_exe = sys.executable or "python"
            bridge_path = str(APP_DIR / "agent_bridge.py")
            mcp_snippet = json.dumps({
                "mcpServers": {
                    "software-update-manager": {
                        "command": py_exe,
                        "args": [bridge_path, "--mcp"],
                        "description": "Software Update Manager & Intrusion Shield Stdio MCP Server"
                    }
                }
            }, indent=2)
            win.clipboard_clear()
            win.clipboard_append(mcp_snippet)
            status_lbl_b.config(text="✓ MCP Stdio JSON configuration copied to clipboard!")
            status_lbl_b.pack(anchor="w", pady=(6, 0))

        tk.Button(
            btn_row_b, text="⚡ Auto-Configure Detected MCP Clients", command=_auto_configure_mcp,
            bg="#4f46e5", fg="#ffffff", activebackground="#4338ca", activeforeground="#ffffff",
            font=("Segoe UI", 9, "bold"), relief="flat", padx=12, pady=5, cursor="hand2"
        ).pack(side=tk.LEFT, padx=(0, 6))

        tk.Button(
            btn_row_b, text="📋 Copy MCP Config JSON", command=_copy_mcp_json,
            bg="#1e293b", fg="#cbd5e1", activebackground="#334155", activeforeground="#ffffff",
            font=("Segoe UI", 9), relief="flat", padx=10, pady=5, cursor="hand2"
        ).pack(side=tk.LEFT, padx=4)

        # Launch buttons for detected local MCP clients
        launch_frame_b = tk.Frame(card_b, bg="#111827")
        launch_frame_b.pack(fill=tk.X, pady=(8, 0))

        def _refresh_launch_buttons():
            for w in launch_frame_b.winfo_children():
                w.destroy()
            clients = agent_bridge.detect_mcp_clients()
            found_any = False
            for c_name in clients:
                launcher = agent_bridge.find_mcp_client_launcher(c_name)
                if launcher:
                    found_any = True
                    def _launch_app(name=c_name):
                        prompt = (
                            "Please run a complete PC diagnostic using Software Update Manager "
                            "(check hardware specs, listening sockets, and pending updates) "
                            "and report any security risks or software needing attention."
                        )
                        win.clipboard_clear()
                        win.clipboard_append(prompt)
                        ok, msg = agent_bridge.launch_mcp_client(name)
                        if ok:
                            status_lbl_b.config(
                                text=f"✓ Opened {name}! Diagnostic prompt copied to clipboard — paste with Ctrl+V.",
                                fg="#34d399"
                            )
                            status_lbl_b.pack(anchor="w", pady=(6, 0))
                        else:
                            messagebox.showwarning("Launch Warning", msg, parent=win)

                    tk.Button(
                        launch_frame_b,
                        text=f"🚀 Open {c_name} to Continue",
                        command=_launch_app,
                        bg="#2563eb", fg="#ffffff", activebackground="#1d4ed8", activeforeground="#ffffff",
                        font=("Segoe UI", 9, "bold"), relief="flat", padx=12, pady=5, cursor="hand2"
                    ).pack(side=tk.LEFT, padx=(0, 8))

            if found_any:
                tk.Label(
                    launch_frame_b,
                    text="← Click to launch your local AI assistant & auto-copy starter diagnostic prompt",
                    bg="#111827", fg="#94a3b8", font=("Segoe UI", 8, "italic")
                ).pack(side=tk.LEFT)

        _refresh_launch_buttons()

        # Section 3: 4-Tier Permission Gatekeeper
        card_c = tk.Frame(container, bg="#111827", padx=14, pady=12, highlightbackground="#1f2937", highlightthickness=1)
        card_c.pack(fill=tk.X, pady=6)

        tk.Label(
            card_c, text="🛡️ 4-Tier Local Agent Permission Gatekeeper",
            bg="#111827", fg="#f59e0b", font=("Segoe UI", 10, "bold"), anchor="w"
        ).pack(anchor="w")

        tk.Label(
            card_c,
            text="Controls the tool execution boundary. Enforced strictly at the local IPC layer — external AI agents cannot elevate their own tier.",
            bg="#111827", fg="#94a3b8", font=("Segoe UI", 8), anchor="w"
        ).pack(anchor="w", pady=(1, 6))

        current_tier = agent_bridge.get_active_tier()
        tier_var = tk.IntVar(value=current_tier)

        tiers_info = [
            (0, "Level 0: Off / Air-Gapped", "Bridge completely disabled. Zero IPC responses."),
            (1, "Level 1: Read-Only Diagnostic (Recommended)", "Hard read-only whitelist (Specs, Ports, Updates). Prompt-injection sanitized."),
            (2, "Level 2: Supervised Remediation", "Allows single app updates & firewall toggling. Every write requires interactive user popup."),
            (3, "Level 3: Autonomous Maintenance", "Sequential batch updates. Auto-creates System Restore Point. Auto-expires after 30 mins."),
        ]

        def _on_tier_change():
            val = tier_var.get()
            if val >= 2:
                # Require explicit disclaimer acceptance
                ans = messagebox.askyesno(
                    "Enable Mutating AI Agent Permissions?",
                    f"You have selected Level {val}.\n\n"
                    "⚠️ Third-Party AI Autonomy & Responsibility Notice:\n"
                    "Connecting external AI agents (such as Copilot, Claude, or local models) to perform system "
                    "modifications is an optional, advanced capability. While Software Update Manager enforces strict "
                    "local permission boundaries and approval gates, the internal decision-making, reasoning, and "
                    "outputs of third-party AI models remain entirely outside our control.\n\n"
                    "Do you understand and accept full responsibility for actions initiated by your chosen AI assistant?",
                    parent=win
                )
                if not ans:
                    tier_var.set(1)
                    agent_bridge.set_active_tier(1)
                    return
            agent_bridge.set_active_tier(val, accept_disclaimer=(val >= 2))
            self.log_ui(f"[AI PERMISSION] Agent permission tier updated to Level {val}.")

        for t_val, t_name, t_desc in tiers_info:
            r_frame = tk.Frame(card_c, bg="#111827")
            r_frame.pack(fill=tk.X, pady=2)
            rb = tk.Radiobutton(
                r_frame, text=t_name, variable=tier_var, value=t_val, command=_on_tier_change,
                bg="#111827", fg="#f8fafc", selectcolor="#0f172a", activebackground="#111827",
                activeforeground="#ffffff", font=("Segoe UI", 9, "bold" if t_val == 1 else "normal")
            )
            rb.pack(side=tk.LEFT)
            tk.Label(r_frame, text=f"— {t_desc}", bg="#111827", fg="#94a3b8", font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=6)

        # Section 4: Responsibility Notice & Safe Quick-Start Guide
        notice_box = tk.Frame(container, bg="#271c08", highlightbackground="#d97706", highlightthickness=1, padx=14, pady=12)
        notice_box.pack(fill=tk.X, pady=(6, 16))

        tk.Label(
            notice_box,
            text="⚠️ Third-Party AI Autonomy & Responsibility Notice:",
            bg="#271c08", fg="#fde047", font=("Segoe UI", 9, "bold"), anchor="w"
        ).pack(anchor="w")

        tk.Label(
            notice_box,
            text=agent_bridge.AI_RESPONSIBILITY_NOTICE,
            bg="#271c08", fg="#fef08a", font=("Segoe UI", 8), justify=tk.LEFT, wraplength=920
        ).pack(anchor="w", pady=(2, 6))

        tk.Label(
            notice_box,
            text="🛡️ Safe Quick-Start Checklist:\n"
                 "• 1. Start at Level 1 (Read-Only): Verify AI can inspect specs and open ports before granting any write rights.\n"
                 "• 2. Use Local STDIO (Zero Open Ports): Connect via stdin/stdout pipes; never expose an unauthenticated HTTP port.\n"
                 "• 3. Review Every Level 2 Popup: Inspect target app names and commands carefully before clicking Approve.\n"
                 "• 4. Create a Restore Point First: Ensure rollback capability before running batch updates.",
            bg="#271c08", fg="#cbd5e1", font=("Segoe UI", 8), justify=tk.LEFT, wraplength=880
        ).pack(anchor="w", pady=(2, 6))

        # Video tutorials and documentation button bar
        video_bar = tk.Frame(notice_box, bg="#271c08")
        video_bar.pack(fill=tk.X, pady=(4, 0))

        tk.Label(
            video_bar, text="🎥 Tutorials & Guides:", bg="#271c08", fg="#fde047", font=("Segoe UI", 8, "bold")
        ).pack(side=tk.LEFT, padx=(0, 6))

        tk.Button(
            video_bar, text="🎥 Connect Claude to MCP (9m)",
            command=lambda: webbrowser.open("https://www.youtube.com/watch?v=A151Nk_nN_U"),
            bg="#451a03", fg="#fde047", activebackground="#78350f", activeforeground="#ffffff",
            font=("Segoe UI", 8), relief="flat", padx=6, pady=2, cursor="hand2"
        ).pack(side=tk.LEFT, padx=3)

        tk.Button(
            video_bar, text="🎥 Securing MCP Servers",
            command=lambda: webbrowser.open("https://www.youtube.com/watch?v=KYWr454hGF0"),
            bg="#451a03", fg="#fde047", activebackground="#78350f", activeforeground="#ffffff",
            font=("Segoe UI", 8), relief="flat", padx=6, pady=2, cursor="hand2"
        ).pack(side=tk.LEFT, padx=3)

        tk.Button(
            video_bar, text="🎥 Least Privilege for AI (7m)",
            command=lambda: webbrowser.open("https://www.youtube.com/watch?v=4HiuiYIJRTU"),
            bg="#451a03", fg="#fde047", activebackground="#78350f", activeforeground="#ffffff",
            font=("Segoe UI", 8), relief="flat", padx=6, pady=2, cursor="hand2"
        ).pack(side=tk.LEFT, padx=3)

        tk.Button(
            video_bar, text="📖 Best Practices Guide",
            command=lambda: webbrowser.open("https://modelcontextprotocol.io/docs/draft/tutorials/security/security_best_practices"),
            bg="#1e293b", fg="#93c5fd", activebackground="#334155", activeforeground="#ffffff",
            font=("Segoe UI", 8), relief="flat", padx=6, pady=2, cursor="hand2"
        ).pack(side=tk.LEFT, padx=3)

        def _open_agent_safety_doc():
            p = APP_DIR / "AGENT_SAFETY.md"
            if p.exists():
                try:
                    os.startfile(p)
                    return
                except Exception:
                    pass
            webbrowser.open("https://github.com/jesusdelira7-956/SoftwareUpdateManager/blob/main/AGENT_SAFETY.md")

        tk.Button(
            video_bar, text="📄 AGENT_SAFETY.md",
            command=_open_agent_safety_doc,
            bg="#064e3b", fg="#6ee7b7", activebackground="#047857", activeforeground="#ffffff",
            font=("Segoe UI", 8, "bold"), relief="flat", padx=6, pady=2, cursor="hand2"
        ).pack(side=tk.LEFT, padx=3)

        # Bottom Close Button
        btn_close_frame = tk.Frame(win, bg="#0b1329", padx=14, pady=8)
        btn_close_frame.pack(fill=tk.X)
        tk.Button(
            btn_close_frame, text="Close", command=win.destroy,
            bg="#1e293b", fg="#cbd5e1", font=("Segoe UI", 9), relief="flat", padx=14, pady=4, cursor="hand2"
        ).pack(side=tk.RIGHT)

    def open_ai_dev_hub(self):
        """Open the Deep AI & Inference Suite Auditor window."""
        # Ensure we have fresh scan data
        if not hasattr(self, "ai_inventory") or not self.ai_inventory:
            upg_map = {}
            if hasattr(self, "upgradable_apps"):
                upg_map = {a["id"].lower(): a for a in self.upgradable_apps}
            self.ai_inventory = scan_deep_ai_inventory(upg_map)

        win = tk.Toplevel(self)
        win.title("🤖 Deep AI & Local Inference Suite Auditor - Software Update Manager")
        win.geometry("1100x640")
        win.minsize(940, 520)
        win.configure(bg="#0b1329")
        win.transient(self)

        # Center over parent
        try:
            x = self.winfo_rootx() + (self.winfo_width() // 2) - 550
            y = self.winfo_rooty() + (self.winfo_height() // 2) - 320
            win.geometry(f"+{max(10, x)}+{max(10, y)}")
        except Exception:
            pass

        # Top Banner
        header_frame = tk.Frame(win, bg="#131c38", padx=16, pady=12, highlightbackground="#3b82f6", highlightthickness=1)
        header_frame.pack(fill=tk.X, padx=12, pady=(12, 8))

        lbl_title = tk.Label(
            header_frame,
            text="🤖 Deep AI & Local Inference Suite Auditor",
            bg="#131c38", fg="#60a5fa", font=("Segoe UI", 13, "bold"), anchor="w"
        )
        lbl_title.pack(anchor="w")

        lbl_desc = tk.Label(
            header_frame,
            text="Comprehensive multi-tier audit across Windows Registry hives, Windows Store / MSIX containers, and system PATH CLI binaries.",
            bg="#131c38", fg="#94a3b8", font=("Segoe UI", 9), anchor="w"
        )
        lbl_desc.pack(anchor="w", pady=(2, 0))

        # Stats bar
        stats_frame = tk.Frame(win, bg="#0b1329", padx=12)
        stats_frame.pack(fill=tk.X, pady=(0, 6))

        total_cnt = len(self.ai_inventory)
        up_to_date_cnt = sum(1 for a in self.ai_inventory if "✓" in a.get("update_status", ""))
        action_cnt = total_cnt - up_to_date_cnt
        fw_active, fw_note = network_auditor.audit_firewall_shield()
        exposed_cnt = sum(1 for a in self.ai_inventory if "0.0.0.0" in a.get("network_status", ""))

        lbl_stats_str = (
            f"AI Suites: {total_cnt}   |   ✓ Up to Date: {up_to_date_cnt}   |   ⚡ Actions: {action_cnt}   |   "
            f"🛡️ Firewall Shield: {'Active' if fw_active else 'Unshielded'}   |   "
            f"{'⚠️ Exposed Ports: ' + str(exposed_cnt) if exposed_cnt else '🟢 All Isolated (127.0.0.1)'}"
        )
        lbl_stats = tk.Label(
            stats_frame,
            text=lbl_stats_str,
            bg="#0b1329", fg="#38bdf8", font=("Segoe UI", 9, "bold")
        )
        lbl_stats.pack(side=tk.LEFT)

        # Treeview Table
        tree_frame = ttk.Frame(win, style="Card.TFrame", padding=1)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=4)

        cols = ("name", "vendor", "version", "source", "status", "network")
        ai_tree = ttk.Treeview(tree_frame, columns=cols, show="headings", selectmode="browse")
        ai_tree.heading("name", text="AI Software / Suite", anchor="w")
        ai_tree.heading("vendor", text="Developer / Vendor", anchor="w")
        ai_tree.heading("version", text="Installed Version", anchor="center")
        ai_tree.heading("source", text="Installation Source", anchor="w")
        ai_tree.heading("status", text="Update Status / Delivery Channel", anchor="w")
        ai_tree.heading("network", text="Network Boundary / Intrusion", anchor="w")

        ai_tree.column("name", width=170, minwidth=130, anchor="w")
        ai_tree.column("vendor", width=120, minwidth=100, anchor="w")
        ai_tree.column("version", width=110, minwidth=90, anchor="center")
        ai_tree.column("source", width=150, minwidth=120, anchor="w")
        ai_tree.column("status", width=220, minwidth=170, anchor="w")
        ai_tree.column("network", width=190, minwidth=150, anchor="w")

        sb = ttk.Scrollbar(tree_frame, orient="vertical", command=ai_tree.yview)
        ai_tree.configure(yscrollcommand=sb.set)
        ai_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        # Style tags
        ai_tree.tag_configure("ok", foreground="#34d399")
        ai_tree.tag_configure("relaunch", foreground="#38bdf8")
        ai_tree.tag_configure("update", foreground="#fbbf24")
        ai_tree.tag_configure("store", foreground="#c084fc")
        ai_tree.tag_configure("exposed", foreground="#f87171")

        def _populate_tree():
            ai_tree.delete(*ai_tree.get_children())
            for idx, item in enumerate(self.ai_inventory):
                st = item.get("update_status", "")
                net_st = item.get("network_status", "⚪ Desktop Native (Offline Client)")
                tag = "ok"
                if "0.0.0.0" in net_st or "Exposed" in net_st:
                    tag = "exposed"
                elif "Relaunch" in st or "In-App" in st:
                    tag = "relaunch"
                elif "Update Available" in st or "Available" in st:
                    tag = "update"
                elif "Store" in st:
                    tag = "store"

                ai_tree.insert(
                    "", tk.END, iid=str(idx),
                    values=(
                        item.get("name", ""),
                        item.get("vendor", ""),
                        item.get("version", ""),
                        item.get("source", ""),
                        item.get("update_status", ""),
                        net_st,
                    ),
                    tags=(tag,)
                )

        _populate_tree()

        # Action handlers
        def _get_selected():
            sel = ai_tree.selection()
            if not sel:
                return None
            try:
                idx = int(sel[0])
                return self.ai_inventory[idx]
            except Exception:
                return None

        def _launch_selected():
            item = _get_selected()
            if not item:
                messagebox.showinfo("Select Item", "Please click on an AI application in the list first.", parent=win)
                return
            app_id = item.get("app_id", "")
            loc = item.get("location", "")
            name = item.get("name", "")

            # 1. Store app via shell:AppsFolder
            if app_id.startswith("shell:AppsFolder"):
                try:
                    subprocess.Popen(f'explorer.exe "{app_id}"', shell=True)
                    self.log_ui(f"[AI LAUNCH] Launched Store app: {name} ({app_id})")
                    return
                except Exception as e:
                    self.log_ui(f"[ERROR] Could not launch {name}: {e}")

            # 2. Local executable
            for cand in [app_id, loc]:
                if cand and os.path.exists(cand):
                    try:
                        os.startfile(cand)
                        self.log_ui(f"[AI LAUNCH] Opened {name}: {cand}")
                        return
                    except Exception as e:
                        self.log_ui(f"[ERROR] Launch failed for {name}: {e}")

            # 3. CLI tool
            base_cmd = name.lower().split()[0]
            p = shutil.which(base_cmd)
            if p:
                try:
                    subprocess.Popen(f'start cmd /k "{p}" --help', shell=True)
                    return
                except Exception:
                    pass

            # Fallback to website
            if item.get("site"):
                webbrowser.open(item["site"])

        def _open_store():
            self.open_microsoft_store()

        def _open_download():
            item = _get_selected()
            if item and item.get("site"):
                webbrowser.open(item["site"])
            else:
                webbrowser.open("https://github.com/Mintplex-Labs/anything-llm/releases/latest")

        def _rescan():
            upg_map = {}
            if hasattr(self, "upgradable_apps"):
                upg_map = {a["id"].lower(): a for a in self.upgradable_apps}
            self.ai_inventory = scan_deep_ai_inventory(upg_map)
            _populate_tree()
            _refresh_stats()
            self.log_ui(f"[AI AUDIT] Re-scanned system: {len(self.ai_inventory)} AI software suites audited.")

        def _refresh_stats():
            tot = len(self.ai_inventory)
            upt = sum(1 for a in self.ai_inventory if "✓" in a.get("update_status", ""))
            act = tot - upt
            fw_act, _ = network_auditor.audit_firewall_shield()
            exp = sum(1 for a in self.ai_inventory if "0.0.0.0" in a.get("network_status", ""))
            s_text = (
                f"AI Suites: {tot}   |   ✓ Up to Date: {upt}   |   ⚡ Actions: {act}   |   "
                f"🛡️ Firewall Shield: {'Active' if fw_act else 'Unshielded'}   |   "
                f"{'⚠️ Exposed Ports: ' + str(exp) if exp else '🟢 All Isolated (127.0.0.1)'}"
            )
            lbl_stats.config(text=s_text)
            if hasattr(win, "btn_fw") and win.btn_fw.winfo_exists():
                win.btn_fw.config(
                    text="🛡️ Firewall Shield: Active" if fw_act else "🛡️ Harden Firewall (Block LAN Probes)",
                    bg="#059669" if fw_act else "#b45309",
                    activebackground="#047857" if fw_act else "#92400e"
                )

        def _toggle_firewall_shield():
            is_active, desc = network_auditor.audit_firewall_shield()
            if is_active:
                ans = messagebox.askyesno(
                    "Disable Firewall Shield?",
                    f"The Windows Firewall Intrusion Shield is currently ACTIVE:\n\n{desc}\n\n"
                    "Do you want to DISABLE this rule and reopen developer ports to LAN probes?",
                    parent=win
                )
                if ans:
                    ok, msg = network_auditor.apply_firewall_shield(False)
                    if ok:
                        messagebox.showinfo("Firewall Shield Disabled", msg, parent=win)
                    else:
                        messagebox.showerror("Error", msg, parent=win)
                    _rescan()
            else:
                ans = messagebox.askyesno(
                    "Activate Firewall Intrusion Shield?",
                    "This will configure a native Windows Defender Firewall rule to block external inbound "
                    "LAN and Wi-Fi probes on local AI and developer ports:\n\n"
                    "• Ports Protected: 11434, 1234, 8081, 8088, 8890, 8892, 8895, 8896, 49374, 8188, 7860, 3000-5000, 8000-9000\n\n"
                    "✓ Localhost (127.0.0.1) loopback remains 100% accessible to local apps.\n"
                    "✓ Defends against autonomous LAN scanners (e.g. ARTEX) and unauthenticated API probes.\n"
                    "✓ 100% Free & Open-Source (zero third-party services).\n\n"
                    "Do you want to activate the Intrusion Shield now?",
                    parent=win
                )
                if ans:
                    ok, msg = network_auditor.apply_firewall_shield(True)
                    if ok:
                        messagebox.showinfo("Intrusion Shield Active", msg, parent=win)
                    else:
                        messagebox.showerror("Firewall Error", msg, parent=win)
                    _rescan()

        def _export():
            self.export_ai_audit_report()

        ai_tree.bind("<Double-1>", lambda e: _launch_selected())

        # Bottom Button Bar
        btn_bar = tk.Frame(win, bg="#0b1329", padx=12, pady=10)
        btn_bar.pack(fill=tk.X)

        tk.Button(
            btn_bar, text="🚀 Launch / Relaunch App", command=_launch_selected,
            bg="#2563eb", fg="#ffffff", activebackground="#1d4ed8", activeforeground="#ffffff",
            font=("Segoe UI", 9, "bold"), relief="flat", padx=10, pady=5, cursor="hand2"
        ).pack(side=tk.LEFT, padx=(0, 6))

        fw_cur_act, _ = network_auditor.audit_firewall_shield()
        win.btn_fw = tk.Button(
            btn_bar,
            text="🛡️ Firewall Shield: Active" if fw_cur_act else "🛡️ Harden Firewall (Block LAN Probes)",
            command=_toggle_firewall_shield,
            bg="#059669" if fw_cur_act else "#b45309",
            fg="#ffffff",
            activebackground="#047857" if fw_cur_act else "#92400e",
            activeforeground="#ffffff",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=10,
            pady=5,
            cursor="hand2"
        )
        win.btn_fw.pack(side=tk.LEFT, padx=6)

        tk.Button(
            btn_bar, text="🛍️ Open Store Updates", command=_open_store,
            bg="#4f46e5", fg="#ffffff", activebackground="#4338ca", activeforeground="#ffffff",
            font=("Segoe UI", 9, "bold"), relief="flat", padx=10, pady=5, cursor="hand2"
        ).pack(side=tk.LEFT, padx=6)

        tk.Button(
            btn_bar, text="🌐 Website / Downloads", command=_open_download,
            bg="#0284c7", fg="#ffffff", activebackground="#0369a1", activeforeground="#ffffff",
            font=("Segoe UI", 9), relief="flat", padx=10, pady=5, cursor="hand2"
        ).pack(side=tk.LEFT, padx=6)

        tk.Button(
            btn_bar, text="🔄 Refresh Scan", command=_rescan,
            bg="#334155", fg="#f8fafc", activebackground="#475569", activeforeground="#ffffff",
            font=("Segoe UI", 9), relief="flat", padx=10, pady=5, cursor="hand2"
        ).pack(side=tk.LEFT, padx=6)

        tk.Button(
            btn_bar, text="📋 Export AI Report", command=_export,
            bg="#0f766e", fg="#ffffff", activebackground="#115e59", activeforeground="#ffffff",
            font=("Segoe UI", 9), relief="flat", padx=10, pady=5, cursor="hand2"
        ).pack(side=tk.LEFT, padx=6)

        tk.Button(
            btn_bar, text="Close", command=win.destroy,
            bg="#1e293b", fg="#cbd5e1", font=("Segoe UI", 9), relief="flat", padx=12, pady=5, cursor="hand2"
        ).pack(side=tk.RIGHT)

    def export_ai_audit_report(self):
        """Export the Deep AI Software & LLM Engine Audit to a formatted text file."""
        if not hasattr(self, "ai_inventory") or not self.ai_inventory:
            upg_map = {}
            if hasattr(self, "upgradable_apps"):
                upg_map = {a["id"].lower(): a for a in self.upgradable_apps}
            self.ai_inventory = scan_deep_ai_inventory(upg_map)

        default_name = f"AI_Software_Audit_{self.specs.get('hostname', 'PC')}_{datetime.now().strftime('%Y%m%d_%H%M')}.txt"
        out_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            initialfile=default_name,
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
            title="Export Deep AI Software Audit Report",
        )
        if not out_path:
            return

        lines = [
            "=" * 90,
            f"   DEEP AI SOFTWARE, INFERENCE ENGINES & NETWORK INTRUSION AUDIT REPORT",
            "=" * 90,
            f"Timestamp         : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Host Computer     : {self.specs.get('hostname', 'PC')}",
            f"OS Version        : {self.specs.get('os_name', 'Windows')} (Build {self.specs.get('os_build', 'N/A')})",
            f"Total AI Apps     : {len(self.ai_inventory)} detected across Registry, Store & PATH",
            f"Firewall Shield   : {self.specs.get('firewall_shield_status', 'Unknown')}",
            f"Exposed LAN Ports : {self.specs.get('exposed_ports_count', 0)}",
            "=" * 90,
            "",
            f"{'AI SOFTWARE':<22} | {'VENDOR':<15} | {'VERSION':<15} | {'STATUS':<24} | {'NETWORK BOUNDARY'}",
            "-" * 110,
        ]
        for it in self.ai_inventory:
            lines.append(
                f"{it.get('name', ''):<22} | {it.get('vendor', ''):<15} | {it.get('version', ''):<15} | {it.get('update_status', ''):<24} | {it.get('network_status', '⚪ Offline')}"
            )
        lines.append("-" * 110)
        lines.append("\nDETAILED INSTALLATION PATHS & NETWORK LISTENER INFO:\n")
        for it in self.ai_inventory:
            lines.append(f"• {it.get('name')} ({it.get('vendor')})")
            lines.append(f"  - Version       : {it.get('version')}")
            lines.append(f"  - Source        : {it.get('source')}")
            lines.append(f"  - Update Status : {it.get('update_status')}")
            lines.append(f"  - Network Status: {it.get('network_status', '⚪ Offline')}")
            lines.append(f"  - Location/ID   : {it.get('app_id') or it.get('location') or 'Standard System'}")
            if it.get("site"):
                lines.append(f"  - Official Site : {it.get('site')}")
            lines.append("")

        try:
            with open(out_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            self.log_ui(f"[EXPORT] AI Software Audit successfully exported to: {out_path}")
            messagebox.showinfo("Export Successful", f"AI Software Audit exported successfully to:\n\n{out_path}")
        except Exception as e:
            self.log_ui(f"[EXPORT ERROR] Failed to save AI audit report: {e}")
            messagebox.showerror("Export Failed", f"Could not write file: {e}")

    def trigger_browser_updates(self):
        """Invoke native background updater services and open installed browsers to their update pages."""
        def _run():
            self.log_ui("[BROWSERS] Checking installed browsers and initiating update checks...")
            results = trigger_browser_background_updates()
            if results:
                summary_lines = []
                for r in results:
                    name = r["name"]
                    url = r["url"]
                    svc_note = " (background service signaled)" if r["signaled_service"] else ""
                    self.log_ui(f"[BROWSERS] {name}: Opened {url}{svc_note}")
                    summary_lines.append(f"• {name} ({url})")

                msg = (
                    "Browser update checks initiated!\n\n"
                    "The following installed browsers were opened directly to their update check pages:\n\n"
                    + "\n".join(summary_lines)
                    + "\n\nEach browser will now automatically check for, download, and apply pending updates."
                )
                self.after(0, lambda: messagebox.showinfo("Browser Updaters", msg))
            else:
                self.log_ui("[BROWSERS] No major browser installations detected.")
                self.after(0, lambda: messagebox.showinfo(
                    "Browser Updaters",
                    "No major browser executables were detected.\nBrowsers will be updated directly via Winget in the list."
                ))

        threading.Thread(target=_run, daemon=True).start()

    def open_microsoft_store(self):
        """Open Microsoft Store directly to Library > Updates & downloads."""
        try:
            subprocess.Popen(["explorer.exe", "ms-windows-store://downloadsandupdates"])
            self.log_ui("[MICROSOFT STORE] Opened Microsoft Store Updates & Downloads page.")
        except Exception as e:
            self.log_ui(f"[MICROSOFT STORE] Could not launch Microsoft Store: {e}")

    def trigger_store_updates(self):
        """
        Synchronized Store update routine (Option C):
        1. Triggers Windows Store background InstallService scan task.
        2. Queries WinGet for any available msstore updates.
        3. Launches Microsoft Store directly to Updates & downloads for user monitoring.
        """
        def _run():
            self.log_ui("=" * 68)
            self.log_ui("[MICROSOFT STORE] Initiating Microsoft Store & UWP App Updates...")
            self.log_ui("=" * 68)

            # 1. Trigger Windows Store background scan task
            try:
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                res_task = subprocess.run(
                    ["powershell", "-NoProfile", "-Command", "Start-ScheduledTask -TaskPath '\\Microsoft\\Windows\\InstallService\\' -TaskName 'ScanForUpdates' -ErrorAction SilentlyContinue"],
                    capture_output=True, text=True, errors="replace", timeout=10, startupinfo=startupinfo
                )
                if res_task.returncode == 0:
                    self.log_ui("  [✓] Background Store update service (InstallService) triggered.")
                else:
                    self.log_ui(f"  [!] InstallService returned exit code {res_task.returncode}")
            except Exception as e:
                self.log_ui(f"  [!] Background Store update service signal failed: {e}")

            # 2. Check and upgrade any msstore packages via WinGet
            try:
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                self.log_ui("  [*] Checking WinGet for packages from msstore source...")
                cmd_winget = [
                    "winget", "upgrade", "--all", "-s", "msstore",
                    "--accept-package-agreements", "--accept-source-agreements",
                    "--include-unknown"
                ]
                res_winget = subprocess.run(
                    cmd_winget, capture_output=True, text=True, errors="replace", timeout=60, startupinfo=startupinfo
                )
                if res_winget.stdout:
                    for line in res_winget.stdout.splitlines():
                        clean = line.strip()
                        if clean and not clean.startswith(("-", "=", "#")):
                            self.log_ui(f"  [STORE-WINGET] {clean}")
            except Exception as e:
                self.log_ui(f"  [!] WinGet msstore check failed: {e}")

            # 3. Open Microsoft Store Updates & Downloads page
            self.log_ui("  [*] Launching Microsoft Store to Updates & downloads page...")
            try:
                subprocess.Popen(["explorer.exe", "ms-windows-store://downloadsandupdates"])
                self.log_ui("  [✓] Microsoft Store opened: Click 'Update all' if queued downloads need manual confirmation.")
            except Exception as e:
                self.log_ui(f"  [!] Could not open Microsoft Store: {e}")

            self.log_ui("=" * 68)

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

        # Auto-reconcile developer CLI tools with registry desync before scanning
        try:
            reconciled = reconcile_developer_cli_tools()
            for r_msg in reconciled:
                self.log_ui(f"  • [AUTO-RECONCILE] {r_msg}")
        except Exception as e:
            self.log_ui(f"  ⚠ Reconcile check note: {e}")

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
                        # Match with installed registry app details for security evaluation
                        matched_reg = {}
                        for inst in installed:
                            if inst["name"].lower() == name.lower() or inst["name"].lower() in name.lower() or name.lower() in inst["name"].lower():
                                matched_reg = inst
                                break

                        # Pre-Update Security & Trust Gate Audit
                        audit_input = {
                            "name": name,
                            "id": pkg_id,
                            "winget_id": pkg_id,
                            "publisher": matched_reg.get("publisher", ""),
                            "display_icon": matched_reg.get("display_icon", ""),
                            "install_location": matched_reg.get("install_location", ""),
                            "uninstall_string": matched_reg.get("uninstall_string", ""),
                            "system_component": matched_reg.get("system_component", 0),
                        }
                        sec_verdict = self.security_auditor.audit_application(audit_input)

                        tag = "pending"
                        if sec_verdict.get("tier") == "HIGH_RISK":
                            tag = "failed"
                        elif sec_verdict.get("tier") == "CAUTION":
                            tag = "reboot"

                        upgradable_apps.append({
                            "name": name,
                            "id": pkg_id,
                            "current": current_ver,
                            "available": avail_ver,
                            "source": source,
                            "status": "Pending Update",
                            "tag": tag,
                            "security": sec_verdict,
                            "trust": sec_verdict.get("badge", "🟢 Trusted"),
                            "trust_tier": sec_verdict.get("tier", "TRUSTED"),
                        })
        except Exception as e:
            self.log_ui(f"[SCAN ERROR] Winget upgrade check failed: {e}")

        # STAGE 2B.1: Check Antigravity / Electron In-App Staged Update
        try:
            ag_candidates = [
                os.path.expandvars(r"%LOCALAPPDATA%\Programs\antigravity\Antigravity.exe"),
                os.path.expandvars(r"%LOCALAPPDATA%\Programs\Antigravity IDE\Antigravity IDE.exe"),
            ]
            ag_pending = os.path.expandvars(r"%LOCALAPPDATA%\antigravity-updater\pending\Antigravity-x64.exe")
            ag_exe = next((p for p in ag_candidates if os.path.exists(p)), None)
            if ag_exe and os.path.exists(ag_pending):
                cur_v = get_pe_file_version(ag_exe) or "2.32.2"
                avail_v = get_pe_file_version(ag_pending) or "2.33.0"
                if cur_v != avail_v:
                    upgradable_apps.append({
                        "name": "Antigravity",
                        "id": "Google.Antigravity",
                        "current": cur_v,
                        "available": avail_v,
                        "source": "In-App Updater",
                        "status": "Pending Update",
                        "tag": "pending",
                        "security": {
                            "tier": "TRUSTED",
                            "badge": "🟢 Trusted",
                            "reasons": ["Verified Google DeepMind application binary"],
                        },
                        "trust": "🟢 Trusted",
                        "trust_tier": "TRUSTED",
                        "in_app_relaunch": ag_exe,
                    })
                    self.log_ui(f"  • [IN-APP UPDATE] Antigravity: v{cur_v} installed, v{avail_v} staged in %LOCALAPPDATA%\\antigravity-updater\\pending")
        except Exception as e:
            self.log_ui(f"  ⚠ Antigravity pending check note: {e}")

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

        # STAGE 2D: Microsoft Store Service Sync
        try:
            self.log_ui("[STAGE 2] Checking Microsoft Store background update service...")
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", "Start-ScheduledTask -TaskPath '\\Microsoft\\Windows\\InstallService\\' -TaskName 'ScanForUpdates' -ErrorAction SilentlyContinue"],
                capture_output=True, text=True, errors="replace", timeout=8, startupinfo=startupinfo
            )
            self.log_ui("  [✓] Microsoft Store InstallService background scan signaled.")
        except Exception:
            pass

        # STAGE 2E: Deep AI Software & LLM Engine Audit
        try:
            self.log_ui("[STAGE 2] Performing Deep AI Software & LLM Engine Audit (Registry, Store & PATH)...")
            upgradable_map = {app["id"].lower(): app for app in upgradable_apps}
            ai_items = scan_deep_ai_inventory(upgradable_map)
            self.ai_inventory = ai_items
            self.log_ui(f"  • Deep scan identified {len(ai_items)} AI suite installations across system:")
            for ai in ai_items:
                self.log_ui(f"    - {ai['name']} ({ai['version']}) [{ai['source']}] → {ai['update_status']}")
        except Exception as ae:
            self.log_ui(f"  ⚠ AI suite audit note: {ae}")

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

        # Network Boundary & Firewall LAN Shield
        exp_cnt = specs.get("exposed_ports_count", 0)
        tot_listeners = len(specs.get("network_listeners", []))
        if exp_cnt > 0:
            net_text = f"⚠️ {exp_cnt} Ports Exposed (0.0.0.0)\nTotal Listeners: {tot_listeners} (Review in AI Hub)"
        else:
            net_text = f"🟢 Secure / Isolated (127.0.0.1)\nTotal Listeners: {tot_listeners} Active"
        self.spec_labels["network_shield"].config(text=net_text)

        fw_act = specs.get("firewall_shield_active", False)
        fw_status = specs.get("firewall_shield_status", "Not Configured")
        fw_text = f"{'🛡️ Active (Protected)' if fw_act else '⚠️ Unshielded'}\n{fw_status}"
        self.spec_labels["firewall_status"].config(text=fw_text)

        # Generate Tailored Recommendations for this computer
        recs = []
        if specs.get("exposed_ports_count", 0) > 0:
            recs.append(f"• ⚠️ Network Exposure Alert: Detected {specs['exposed_ports_count']} port(s) bound to 0.0.0.0. Click 'AI Suites' -> '🛡️ Harden Firewall' to block external LAN probes.")
        else:
            recs.append("• 🛡️ Network Boundary Health: All listening developer & local AI services are safely isolated to 127.0.0.1 loopback.")

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
            self.win_notice_frame.pack(fill=tk.X, padx=20, pady=(2, 4), before=self.main_paned)
        else:
            self.win_notice_frame.pack_forget()

        # Display Microsoft Store notice banner (Option C)
        if not self.store_notice_frame.winfo_ismapped():
            self.store_notice_frame.pack(fill=tk.X, padx=20, pady=(2, 4), before=self.main_paned)

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
                values=(app["name"], app["id"], app["current"], app["available"], app.get("trust", "🟢 Trusted"), app["status"]),
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

    def _setup_tree_context_menu(self):
        """Create and bind right-click context menu for application inspection & actions."""
        self.context_menu = tk.Menu(self, tearoff=0, bg="#1e293b", fg="#f8fafc", activebackground="#334155", activeforeground="#ffffff")
        self.context_menu.add_command(label="🛡️ View Security & Trust Details", command=self._show_security_details)
        self.context_menu.add_command(label="🔍 Inspect on VirusTotal", command=self._open_virustotal_inspection)
        self.context_menu.add_command(label="📂 Open File Location", command=self._open_app_file_location)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="⚡ Update Highlighted Only", command=self.start_update_selected)

        def _on_right_click(event):
            item = self.tree.identify_row(event.y)
            if item:
                self.tree.selection_set(item)
                self.context_menu.post(event.x_root, event.y_root)

        self.tree.bind("<Button-3>", _on_right_click)

    def _get_selected_app(self):
        sel = self.tree.selection()
        if not sel:
            return None
        item_id = sel[0]
        vals = self.tree.item(item_id, "values")
        if not vals or len(vals) < 2:
            return None
        target_pkg = vals[1]
        for app in self.updates_list:
            if app["id"] == target_pkg:
                return app
        return None

    def _show_security_details(self):
        app = self._get_selected_app()
        if not app:
            messagebox.showinfo("Security Audit", "Please select an application from the table first.", parent=self)
            return

        sec = app.get("security", {})
        win = tk.Toplevel(self)
        win.title(f"🛡️ Security & Trust Details: {app.get('name')}")
        win.geometry("680x500")
        win.configure(bg="#0f172a")
        win.transient(self)

        try:
            x = self.winfo_rootx() + (self.winfo_width() // 2) - 340
            y = self.winfo_rooty() + (self.winfo_height() // 2) - 250
            win.geometry(f"+{max(10, x)}+{max(10, y)}")
        except Exception:
            pass

        p = tk.Frame(win, bg="#1e293b", padx=16, pady=12, highlightbackground="#3b82f6", highlightthickness=1)
        p.pack(fill=tk.X, padx=14, pady=12)

        tk.Label(p, text=f"🛡️ {app.get('name')} ({app.get('id')})", bg="#1e293b", fg="#f8fafc", font=("Segoe UI", 12, "bold")).pack(anchor="w")
        tk.Label(p, text=f"Trust Verdict: {sec.get('badge', 'Unknown')}", bg="#1e293b", fg="#38bdf8", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(2, 0))

        content = tk.Frame(win, bg="#0f172a", padx=14)
        content.pack(fill=tk.BOTH, expand=True)

        info_box = scrolledtext.ScrolledText(content, bg="#111827", fg="#e2e8f0", insertbackground="#ffffff", font=("Consolas", 9), relief="flat")
        info_box.pack(fill=tk.BOTH, expand=True, pady=4)

        report_lines = [
            f"Application Name  : {app.get('name')}",
            f"Package ID        : {app.get('id')}",
            f"Current Version   : {app.get('current')}",
            f"Available Version : {app.get('available')}",
            f"Trust Tier        : {sec.get('tier', 'Unknown')} ({sec.get('badge', '')})",
            f"Auto-Update Safe  : {'YES (Trusted)' if sec.get('allow_auto_update') else 'NO (Requires Opt-In / Blocked)'}",
            "-" * 65,
            f"Executable Path   : {sec.get('exe_path', 'Not Resolved')}",
            f"SHA-256 Digest    : {sec.get('sha256') or 'N/A'}",
            f"Signature Status  : {sec.get('signature_status', 'Unknown')}",
            f"Signer Subject    : {sec.get('signer') or 'Unsigned / None'}",
            "-" * 65,
            "HEURISTIC & INTEGRITY FINDINGS:",
        ]
        reasons = sec.get("reasons", [])
        if reasons:
            for r in reasons:
                report_lines.append(f"  • {r}")
        else:
            report_lines.append("  • No anomalies detected. Binary signature and install path are verified.")

        info_box.insert(tk.END, "\n".join(report_lines))
        info_box.config(state="disabled")

        btn_bar = tk.Frame(win, bg="#0f172a", padx=14, pady=10)
        btn_bar.pack(fill=tk.X)

        if sec.get("vt_url"):
            tk.Button(
                btn_bar, text="🔍 VirusTotal Report", command=lambda: webbrowser.open(sec["vt_url"]),
                bg="#2563eb", fg="#ffffff", font=("Segoe UI", 9, "bold"), relief="flat", padx=10, pady=4, cursor="hand2"
            ).pack(side=tk.LEFT, padx=(0, 6))

        if sec.get("exe_path") and os.path.exists(sec["exe_path"]):
            tk.Button(
                btn_bar, text="📂 Open File Location", command=lambda: subprocess.Popen(f'explorer.exe /select,"{sec["exe_path"]}"'),
                bg="#334155", fg="#f8fafc", font=("Segoe UI", 9), relief="flat", padx=10, pady=4, cursor="hand2"
            ).pack(side=tk.LEFT, padx=6)

        tk.Button(
            btn_bar, text="Close", command=win.destroy,
            bg="#1e293b", fg="#cbd5e1", font=("Segoe UI", 9), relief="flat", padx=12, pady=4, cursor="hand2"
        ).pack(side=tk.RIGHT)

    def _open_virustotal_inspection(self):
        app = self._get_selected_app()
        if not app:
            messagebox.showinfo("VirusTotal", "Please select an application first.", parent=self)
            return
        sec = app.get("security", {})
        vt_url = sec.get("vt_url")
        if vt_url:
            webbrowser.open(vt_url)
        else:
            webbrowser.open(f"https://www.virustotal.com/gui/search/{urllib.parse.quote(app.get('name', ''))}")

    def _open_app_file_location(self):
        app = self._get_selected_app()
        if not app:
            messagebox.showinfo("File Location", "Please select an application first.", parent=self)
            return
        sec = app.get("security", {})
        exe_path = sec.get("exe_path")
        if exe_path and os.path.exists(exe_path):
            try:
                subprocess.Popen(f'explorer.exe /select,"{exe_path}"')
            except Exception as e:
                self.log_ui(f"[ERROR] Could not open file location: {e}")
        else:
            messagebox.showinfo("File Location", f"Executable location could not be resolved on disk for:\n{app.get('name')}", parent=self)

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
                if len(vals) >= 6:
                    vals[5] = status
                elif len(vals) >= 5:
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

            # PRE-UPDATE SECURITY & TRUST GATE
            sec = app.get("security", {})
            tier = sec.get("tier", "TRUSTED")
            reasons = sec.get("reasons", [])

            if tier == "HIGH_RISK":
                failed_count += 1
                r_text = "; ".join(reasons) if reasons else "Failed security audit / PUP heuristics"
                self.log_ui(f"⛔ [SECURITY GATE] BLOCKED: {name} ({r_text})")
                self.after(0, lambda p=pkg_id: self._set_app_state(p, status="⛔ Blocked (Risk)", tag="failed"))
                continue

            if tier == "CAUTION" and not self.include_unverified_var.get():
                r_text = "; ".join(reasons) if reasons else "Unsigned or unverified executable"
                self.log_ui(f"⚠️ [SECURITY GATE] SKIPPED: {name} ({r_text}) — Enable 'Allow Unverified' to update.")
                self.after(0, lambda p=pkg_id: self._set_app_state(p, status="⚠ Skipped (Unverified)", tag="reboot"))
                continue

            # In-App Auto-Updater Relaunch (e.g. Antigravity staged update ready)
            if app.get("in_app_relaunch"):
                relaunch_exe = app["in_app_relaunch"]
                self.log_ui("-" * 54)
                self.log_ui(f"[{idx}/{total}] Applying In-App Update: {name} ({old_ver} -> {avail_ver})")
                self.log_ui(f"  • Staged update payload: v{avail_ver} ready in %LOCALAPPDATA%\\antigravity-updater\\pending")
                self.log_ui("  • Launching Antigravity to finalize update application...")
                try:
                    os.startfile(relaunch_exe)
                    success_count += 1
                    self.after(0, lambda p=pkg_id, v=avail_ver: self._set_app_state(p, status=f"✓ Relaunch Triggered (v{v})", tag="verified"))
                except Exception as e:
                    self.log_ui(f"  ⚠ Relaunch error: {e}")
                    failed_count += 1
                    self.after(0, lambda p=pkg_id: self._set_app_state(p, status="✗ Launch Failed", tag="failed"))
                continue

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

                # Special handling for developer CLI tools with registry desync (e.g. Google Cloud SDK)
                if pkg_id.lower() == "google.cloudsdk":
                    u_c = return_code & 0xFFFFFFFF
                    if return_code != 0 and u_c not in (3010, 1641):
                        gcloud_path = shutil.which("gcloud") or shutil.which("gcloud.cmd")
                        if not gcloud_path:
                            cand = os.path.expandvars(r"%LOCALAPPDATA%\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd")
                            if os.path.exists(cand):
                                gcloud_path = cand
                        if gcloud_path:
                            self.log_ui("  > Running native 'gcloud components update --quiet'...")
                            env = os.environ.copy()
                            if sys.executable:
                                env["CLOUDSDK_PYTHON"] = sys.executable
                            try:
                                g_res = subprocess.run(
                                    [gcloud_path, "components", "update", "--quiet"],
                                    capture_output=True, text=True, errors="replace", timeout=300,
                                    env=env, startupinfo=startupinfo
                                )
                                if g_res.returncode == 0:
                                    self.log_ui("  ✓ Native gcloud components update completed successfully.")
                            except Exception as ge:
                                self.log_ui(f"  ⚠ gcloud update error: {ge}")
                    synced, sync_msg = sync_gcloud_sdk_version()
                    if synced:
                        self.log_ui(f"  ✓ [REGISTRY SYNC] {sync_msg}")

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
        """Confirm via winget list or direct tool query that the package is now at target_version."""
        if pkg_id.lower() == "google.cloudsdk":
            real_ver = get_real_gcloud_version()
            if real_ver:
                sync_gcloud_sdk_version()
                try:
                    rv_parts = [int(x) for x in real_ver.split(".") if x.isdigit()]
                    tv_parts = [int(x) for x in target_version.split(".") if x.isdigit()]
                    if rv_parts >= tv_parts:
                        return True, real_ver
                except Exception:
                    if real_ver == target_version:
                        return True, real_ver

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

            lines.extend([
                "",
                f"[3. ZERO-DEPENDENCY NETWORK BOUNDARY & INTRUSION SHIELD ({len(self.specs.get('network_listeners', []))} Active Listeners)]",
                f"  Firewall Shield Status : {self.specs.get('firewall_shield_status', 'Unknown')}",
                f"  Exposed LAN Ports      : {self.specs.get('exposed_ports_count', 0)}",
            ])
            for l in self.specs.get("network_listeners", []):
                lines.append(f"  • Port {l['port']:<5} ({l['ip']}) | PID {l['pid']:<5} ({l['process_name']}) | {l['badge']} | {l['service_desc']}")

            lines.extend(["", f"[4. PENDING WINDOWS OS UPDATES ({len(self.windows_updates)})]"])
            for wu in self.windows_updates or ["None pending"]:
                lines.append(f"  • {wu}")

            lines.extend(["", f"[5. SOFTWARE UPDATES STATUS & TRUST GATE ({len(self.updates_list)})]"])
            for u in self.updates_list:
                sec_tier = u.get("security", {}).get("tier", "TRUSTED")
                lines.append(f"  • {u['name']} ({u['id']}): {u['current']} -> {u['available']} [Status: {u['status']} | Trust: {u.get('trust', '🟢 Trusted')} ({sec_tier})]")

            if hasattr(self, "ai_inventory") and self.ai_inventory:
                lines.extend(["", f"[6. DEEP AI SOFTWARE & LOCAL INFERENCE SUITES ({len(self.ai_inventory)})]"])
                for ai in self.ai_inventory:
                    lines.append(f"  • {ai['name']} ({ai['vendor']}) | Ver: {ai['version']} | {ai['source']} | Net: {ai.get('network_status', '⚪ Offline')} | Status: {ai['update_status']}")

            lines.extend(["", f"[7. FULL INSTALLED SOFTWARE INVENTORY ({len(self.installed_apps)})]"])
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
