"""
Universal Desktop Shortcut & Icon Installer
===========================================
Automatically detects the current user's Python environment, current folder location,
and Desktop path on ANY Windows computer, ensures app_icon.ico exists, and creates
the 'Software Update Manager' shortcut on the user's Desktop.
"""

import os
import sys
import subprocess
from pathlib import Path

APP_DIR = Path(__file__).parent.resolve()
SCRIPT_PATH = APP_DIR / "update_manager.py"
ICON_PATH = APP_DIR / "app_icon.ico"


def ensure_icon_exists():
    """Generate app_icon.ico dynamically via System.Drawing if not already present."""
    if ICON_PATH.exists() and ICON_PATH.stat().st_size > 100:
        return True

    ps_icon_gen = f"""
Add-Type -AssemblyName System.Drawing
$icoPath = "{str(ICON_PATH)}"
$bmp = New-Object System.Drawing.Bitmap(256, 256, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
$g.Clear([System.Drawing.Color]::Transparent)
$rect = New-Object System.Drawing.Rectangle(12, 12, 232, 232)
$brush = New-Object System.Drawing.Drawing2D.LinearGradientBrush(
    $rect,
    [System.Drawing.Color]::FromArgb(255, 30, 41, 59),
    [System.Drawing.Color]::FromArgb(255, 15, 23, 42),
    45.0
)
$path = New-Object System.Drawing.Drawing2D.GraphicsPath
$d = 96
$path.AddArc($rect.X, $rect.Y, $d, $d, 180, 90)
$path.AddArc($rect.X + $rect.Width - $d, $rect.Y, $d, $d, 270, 90)
$path.AddArc($rect.X + $rect.Width - $d, $rect.Y + $rect.Height - $d, $d, $d, 0, 90)
$path.AddArc($rect.X, $rect.Y + $rect.Height - $d, $d, $d, 90, 90)
$path.CloseFigure()
$g.FillPath($brush, $path)
$penBorder = New-Object System.Drawing.Pen([System.Drawing.Color]::FromArgb(220, 56, 189, 248), 6)
$g.DrawPath($penBorder, $path)
$centerPen = New-Object System.Drawing.Pen([System.Drawing.Color]::FromArgb(255, 14, 165, 233), 16)
$centerPen.StartCap = [System.Drawing.Drawing2D.LineCap]::Round
$centerPen.EndCap = [System.Drawing.Drawing2D.LineCap]::Round
$arcRect = New-Object System.Drawing.Rectangle(56, 56, 144, 144)
$g.DrawArc($centerPen, $arcRect, 30, 120)
$g.DrawArc($centerPen, $arcRect, 210, 120)
$pulseBrush = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(255, 16, 185, 129))
$g.FillEllipse($pulseBrush, 116, 116, 24, 24)
$g.Flush()
$pngStream = New-Object System.IO.MemoryStream
$bmp.Save($pngStream, [System.Drawing.Imaging.ImageFormat]::Png)
$pngBytes = $pngStream.ToArray()
$icoStream = New-Object System.IO.FileStream($icoPath, [System.IO.FileMode]::Create)
$writer = New-Object System.IO.BinaryWriter($icoStream)
$writer.Write([UInt16]0); $writer.Write([UInt16]1); $writer.Write([UInt16]1)
$writer.Write([Byte]0); $writer.Write([Byte]0); $writer.Write([Byte]0); $writer.Write([Byte]0)
$writer.Write([UInt16]1); $writer.Write([UInt16]32)
$writer.Write([UInt32]$pngBytes.Length); $writer.Write([UInt32]22)
$writer.Write($pngBytes)
$writer.Close(); $icoStream.Close(); $pngStream.Close(); $bmp.Dispose(); $g.Dispose()
"""
    try:
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_icon_gen], check=True, capture_output=True)
        return ICON_PATH.exists()
    except Exception as e:
        print(f"[WARN] Could not generate icon: {e}")
        return False


def create_desktop_shortcut():
    """Create the Desktop shortcut dynamically for the active Windows user."""
    ensure_icon_exists()

    # Locate pythonw.exe next to current python executable
    py_exe = Path(sys.executable).resolve()
    pythonw_exe = py_exe.with_name("pythonw.exe")
    target_exe = str(pythonw_exe if pythonw_exe.exists() else py_exe)

    ps_shortcut = f"""
$DesktopPath = [Environment]::GetFolderPath('Desktop')
if (-not $DesktopPath -or -not (Test-Path $DesktopPath)) {{
    $DesktopPath = Join-Path $env:USERPROFILE "Desktop"
}}
$ShortcutPath = Join-Path $DesktopPath "Software Update Manager.lnk"
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = "{target_exe}"
$Shortcut.Arguments = '"{str(SCRIPT_PATH)}"'
$Shortcut.WorkingDirectory = "{str(APP_DIR)}"
$Shortcut.IconLocation = "{str(ICON_PATH)}, 0"
$Shortcut.Description = "Universal Windows Software Update Scanner, Auditor & Sequential Updater"
$Shortcut.Save()
Write-Output $ShortcutPath
"""
    res = subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps_shortcut],
        capture_output=True, text=True, errors="replace"
    )
    if res.returncode == 0:
        out_path = res.stdout.strip()
        print(f"[SUCCESS] Desktop shortcut created at: {out_path}")
        return True
    else:
        print(f"[ERROR] Failed creating shortcut: {res.stderr}")
        return False


if __name__ == "__main__":
    create_desktop_shortcut()
