@echo off
title Build Standalone SoftwareUpdateManager.exe
cd /d "%~dp0"

echo ========================================================
echo   Building Standalone Single-File Windows Executable
echo ========================================================
echo.

where py >nul 2>&1
if %errorlevel% equ 0 (
    py -3.10 build_exe.py
    if %errorlevel% equ 0 goto :done
    py -3.11 build_exe.py
    if %errorlevel% equ 0 goto :done
)

python build_exe.py

:done
pause
