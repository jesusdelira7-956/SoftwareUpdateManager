# ==============================================================================
# Software Update Manager & System Auditor — Universal Remote & Local Installer
# One-Liner Web Install:
#   irm https://raw.githubusercontent.com/jesusdelira7-956/SoftwareUpdateManager/main/install.ps1 | iex
#
# Support the project: https://buymeacoffee.com/JesseInTheLab
# ==============================================================================

param(
    [string]$InstallDir = "$env:USERPROFILE\SoftwareUpdateManager",
    [switch]$NoLaunch,
    [switch]$Local
)

$ErrorActionPreference = 'Stop'

function Write-BrandHeader {
    Write-Host ""
    Write-Host " ==================================================================== " -ForegroundColor Cyan
    Write-Host "   🛡️  Software Update Manager & System Auditor (v2.1)             " -ForegroundColor White
    Write-Host "   ⚡ Universal Windows 10 & 11 Fast Installer                      " -ForegroundColor Gray
    Write-Host "   ☕ Support: https://buymeacoffee.com/JesseInTheLab             " -ForegroundColor Yellow
    Write-Host " ==================================================================== " -ForegroundColor Cyan
    Write-Host ""
}

function Write-Step([string]$msg) {
    Write-Host " [*] $msg" -ForegroundColor Cyan
}

function Write-Success([string]$msg) {
    Write-Host " [✓] $msg" -ForegroundColor Green
}

function Write-Warn([string]$msg) {
    Write-Host " [!] $msg" -ForegroundColor Yellow
}

function Refresh-EnvPath {
    $machinePath = [Environment]::GetEnvironmentVariable("Path", [EnvironmentVariableTarget]::Machine)
    $userPath    = [Environment]::GetEnvironmentVariable("Path", [EnvironmentVariableTarget]::User)
    $env:Path    = "$machinePath;$userPath"
}

Write-BrandHeader

# ------------------------------------------------------------------------------
# 1. Check OS Architecture & Version
# ------------------------------------------------------------------------------
$os = [Environment]::OSVersion.Version
if ($os.Major -lt 10) {
    Write-Error "Software Update Manager requires Windows 10 (Build 17763+) or Windows 11."
    exit 1
}

# ------------------------------------------------------------------------------
# 2. Check for Windows Package Manager (winget)
# ------------------------------------------------------------------------------
Write-Step "Checking Windows Package Manager (winget)..."
$hasWinget = Get-Command "winget" -ErrorAction SilentlyContinue
if (-not $hasWinget) {
    Write-Warn "winget was not found on PATH. Attempting to locate App Installer package..."
    $appInstallerPath = Get-ChildItem -Path "$env:LOCALAPPDATA\Microsoft\WindowsApps\winget.exe" -ErrorAction SilentlyContinue
    if ($appInstallerPath) {
        $env:Path = "$env:LOCALAPPDATA\Microsoft\WindowsApps;$env:Path"
        Write-Success "Located winget in WindowsApps."
    } else {
        Write-Warn "winget is not yet installed. Please ensure the Windows App Installer is updated from the Microsoft Store."
    }
} else {
    Write-Success "Windows Package Manager (winget) is ready."
}

# ------------------------------------------------------------------------------
# 3. Detect or Auto-Install Python 3
# ------------------------------------------------------------------------------
Write-Step "Checking Python 3 environment..."
$pyExe = Get-Command "python" -ErrorAction SilentlyContinue
$pyVersionOk = $false

if ($pyExe) {
    try {
        $verOut = & python -c "import sys; print(sys.version_info[0], sys.version_info[1])" 2>$null
        $parts = $verOut.Split()
        if ([int]$parts[0] -ge 3 -and [int]$parts[1] -ge 9) {
            $pyVersionOk = $true
            Write-Success "Python $($parts[0]).$($parts[1]) detected ($($pyExe.Source))."
        }
    } catch {}
}

if (-not $pyVersionOk) {
    Write-Warn "Python 3.9+ was not found on this computer. Installing Python 3.12 automatically via winget..."
    try {
        winget install --id Python.Python.3.12 -e --silent --accept-package-agreements --accept-source-agreements
        Refresh-EnvPath
        $pyExe = Get-Command "python" -ErrorAction SilentlyContinue
        if ($pyExe) {
            Write-Success "Python 3.12 successfully installed!"
        } else {
            Write-Warn "Python installed. A terminal restart might be required for PATH updates."
        }
    } catch {
        Write-Warn "Automatic Python installation via winget failed. Please install Python from https://www.python.org/downloads/."
    }
}

# ------------------------------------------------------------------------------
# 4. Stage Repository Files
# ------------------------------------------------------------------------------
$RepoUrl = "https://github.com/jesusdelira7-956/SoftwareUpdateManager.git"
$ZipUrl  = "https://github.com/jesusdelira7-956/SoftwareUpdateManager/archive/refs/heads/main.zip"

if ($Local -or (Test-Path "$PSScriptRoot\update_manager.py")) {
    $TargetDir = $PSScriptRoot
    Write-Success "Running from existing local workspace at: $TargetDir"
} else {
    $TargetDir = $InstallDir
    if (Test-Path "$TargetDir\.git") {
        Write-Step "Updating existing installation at $TargetDir..."
        try {
            git -C "$TargetDir" pull --ff-only
            Write-Success "Repository updated to latest version."
        } catch {
            Write-Warn "Could not pull updates via git. Using current files."
        }
    } elseif (Test-Path "$TargetDir\update_manager.py") {
        Write-Success "Software Update Manager is already installed at: $TargetDir"
    } else {
        Write-Step "Cloning repository to: $TargetDir..."
        New-Item -ItemType Directory -Force -Path $TargetDir | Out-Null
        $hasGit = Get-Command "git" -ErrorAction SilentlyContinue

        if ($hasGit) {
            git clone "$RepoUrl" "$TargetDir"
            Write-Success "Cloned via git."
        } else {
            Write-Step "Git not found; downloading zip archive from GitHub..."
            $tempZip = Join-Path $env:TEMP "SoftwareUpdateManager-main.zip"
            $tempExtract = Join-Path $env:TEMP "SoftwareUpdateManager-extract"
            
            [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
            Invoke-WebRequest -Uri $ZipUrl -OutFile $tempZip -UseBasicParsing
            Expand-Archive -Path $tempZip -DestinationPath $tempExtract -Force
            
            Copy-Item -Path "$tempExtract\SoftwareUpdateManager-main\*" -Destination $TargetDir -Recurse -Force
            Remove-Item -Path $tempZip, $tempExtract -Recurse -Force -ErrorAction SilentlyContinue
            Write-Success "Extracted archive successfully."
        }
    }
}

# ------------------------------------------------------------------------------
# 5. Create Desktop & Start Menu Shortcuts
# ------------------------------------------------------------------------------
Write-Step "Configuring Windows Desktop & Start Menu shortcuts..."
$IconPath = Join-Path $TargetDir "app_icon.ico"
$MainScript = Join-Path $TargetDir "update_manager.py"

# Locate pythonw.exe to prevent terminal window popup
$pythonwExe = $null
if ($pyExe) {
    $candidate = Join-Path (Split-Path $pyExe.Source) "pythonw.exe"
    if (Test-Path $candidate) { $pythonwExe = $candidate }
}
if (-not $pythonwExe) {
    $pyCmd = Get-Command "pythonw" -ErrorAction SilentlyContinue
    if ($pyCmd) { $pythonwExe = $pyCmd.Source }
}
if (-not $pythonwExe) {
    $pythonwExe = if ($pyExe) { $pyExe.Source } else { "python.exe" }
}

$WshShell = New-Object -ComObject WScript.Shell
$DesktopPath = [Environment]::GetFolderPath('Desktop')
if (-not $DesktopPath -or -not (Test-Path $DesktopPath)) {
    $DesktopPath = Join-Path $env:USERPROFILE "Desktop"
}

$LnkPath = Join-Path $DesktopPath "Software Update Manager.lnk"
$Shortcut = $WshShell.CreateShortcut($LnkPath)
$Shortcut.TargetPath = $pythonwExe
$Shortcut.Arguments = "`"$MainScript`""
$Shortcut.WorkingDirectory = $TargetDir
if (Test-Path $IconPath) {
    $Shortcut.IconLocation = "$IconPath, 0"
}
$Shortcut.Description = "Universal Windows Software Update Manager & System Auditor"
$Shortcut.Save()
Write-Success "Desktop shortcut created: $LnkPath"

# Also add to Start Menu Programs
try {
    $StartMenuPrograms = [Environment]::GetFolderPath('Programs')
    if ($StartMenuPrograms -and (Test-Path $StartMenuPrograms)) {
        $StartLnk = Join-Path $StartMenuPrograms "Software Update Manager.lnk"
        $ShortcutStart = $WshShell.CreateShortcut($StartLnk)
        $ShortcutStart.TargetPath = $pythonwExe
        $ShortcutStart.Arguments = "`"$MainScript`""
        $ShortcutStart.WorkingDirectory = $TargetDir
        if (Test-Path $IconPath) { $ShortcutStart.IconLocation = "$IconPath, 0" }
        $ShortcutStart.Description = "Universal Windows Software Update Manager & System Auditor"
        $ShortcutStart.Save()
        Write-Success "Start Menu shortcut created."
    }
} catch {}

# ------------------------------------------------------------------------------
# 6. Summary & Launch
# ------------------------------------------------------------------------------
Write-Host ""
Write-Host " ==================================================================== " -ForegroundColor Green
Write-Host "   ✓ INSTALLATION COMPLETE!                                          " -ForegroundColor Green
Write-Host "   Shortcut: Desktop -> 'Software Update Manager'                    " -ForegroundColor White
Write-Host "   Directory: $TargetDir                                             " -ForegroundColor Gray
Write-Host ""
Write-Host "   ☕ Love this tool? Support development at:                        " -ForegroundColor Yellow
Write-Host "      https://buymeacoffee.com/JesseInTheLab                         " -ForegroundColor Yellow
Write-Host " ==================================================================== " -ForegroundColor Green
Write-Host ""

if (-not $NoLaunch) {
    $runNow = Read-Host "Launch Software Update Manager now? (Y/n)"
    if ($runNow -eq '' -or $runNow -match '^[Yy]') {
        Write-Step "Starting Software Update Manager..."
        Start-Process $pythonwExe -ArgumentList "`"$MainScript`"" -WorkingDirectory $TargetDir
    }
}
