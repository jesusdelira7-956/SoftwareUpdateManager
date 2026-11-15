"""
Universal Standalone Executable Compiler for Software Update Manager
===================================================================
Compiles update_manager.py into a single, self-contained SoftwareUpdateManager.exe
using PyInstaller. The resulting binary requires ZERO Python installation on target PCs.
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

APP_DIR = Path(__file__).parent.resolve()
SCRIPT_PATH = APP_DIR / "update_manager.py"
ICON_PATH = APP_DIR / "app_icon.ico"
DIST_DIR = APP_DIR / "dist"
BUILD_DIR = APP_DIR / "build"
EXE_NAME = "SoftwareUpdateManager"


def find_pyinstaller():
    """Find a Python environment with PyInstaller installed."""
    # 1. Try current python
    try:
        res = subprocess.run([sys.executable, "-m", "PyInstaller", "--version"], capture_output=True, text=True)
        if res.returncode == 0:
            return [sys.executable, "-m", "PyInstaller"]
    except Exception:
        pass

    # 2. Try py launcher targets (3.11, 3.10)
    for ver in ["-3.11", "-3.10"]:
        try:
            res = subprocess.run(["py", ver, "-m", "PyInstaller", "--version"], capture_output=True, text=True)
            if res.returncode == 0:
                return ["py", ver, "-m", "PyInstaller"]
        except Exception:
            pass

    return None


def build():
    print("=" * 68)
    print("  🔨 Building Standalone SoftwareUpdateManager.exe (Zero-Prerequisites)")
    print("=" * 68)

    pyinstaller_cmd = find_pyinstaller()
    if not pyinstaller_cmd:
        print("[!] PyInstaller was not found. Attempting to install...")
        try:
            subprocess.run(["py", "-3.10", "-m", "pip", "install", "pyinstaller"], check=True)
            pyinstaller_cmd = ["py", "-3.10", "-m", "PyInstaller"]
        except Exception:
            try:
                subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
                pyinstaller_cmd = [sys.executable, "-m", "PyInstaller"]
            except Exception as e:
                print(f"[ERROR] Could not install PyInstaller automatically: {e}")
                return False

    print(f"[*] Using compiler: {' '.join(pyinstaller_cmd)}")

    cmd = pyinstaller_cmd + [
        "--noconfirm",
        "--clean",
        "--onefile",
        "--windowed",
        f"--name={EXE_NAME}",
        f"--icon={str(ICON_PATH)}",
        "--uac-admin",
        f"--add-data={str(ICON_PATH)};.",
        f"--distpath={str(DIST_DIR)}",
        f"--workpath={str(BUILD_DIR)}",
        f"--specpath={str(APP_DIR)}",
        str(SCRIPT_PATH),
    ]

    print("[*] Running compilation pipeline...")
    res = subprocess.run(cmd)

    if res.returncode == 0:
        exe_path = DIST_DIR / f"{EXE_NAME}.exe"
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            print("\n" + "=" * 68)
            print(f"  [✓] BUILD SUCCESSFUL!")
            print(f"  Binary : {exe_path}")
            print(f"  Size   : {size_mb:.1f} MB")
            print(f"  Usage  : Distribute this single .exe to any Windows 10/11 PC.")
            print(f"           NO Python, Git, or PowerShell commands required!")
            print("=" * 68 + "\n")

            # Clean up intermediate build folders to keep repo clean
            spec_file = APP_DIR / f"{EXE_NAME}.spec"
            if spec_file.exists():
                try:
                    spec_file.unlink()
                except Exception:
                    pass
            if BUILD_DIR.exists():
                try:
                    shutil.rmtree(BUILD_DIR)
                except Exception:
                    pass

            return True

    print("\n[!] Compilation failed with return code:", res.returncode)
    return False


if __name__ == "__main__":
    success = build()
    sys.exit(0 if success else 1)
