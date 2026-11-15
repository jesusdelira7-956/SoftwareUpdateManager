@echo off
title Software Update Manager - Fast Installer
cd /d "%~dp0"

echo ====================================================================
echo   Software Update Manager ^& System Auditor - 1-Click Installer
echo ====================================================================
echo.

:: Check if local install.ps1 exists in current directory
if exist "%~dp0install.ps1" (
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" -Local
) else (
    echo Downloading and launching installer...
    powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; irm https://raw.githubusercontent.com/jesusdelira7-956/SoftwareUpdateManager/main/install.ps1 | iex"
)

if %errorlevel% neq 0 (
    echo.
    echo [!] Installation encountered an issue.
    pause
)
