@echo off
title Install Software Update Manager Shortcut
cd /d "%~dp0"

echo ========================================================
echo   Installing Software Update Manager Desktop Shortcut
echo ========================================================

:: Locate Python on any user's PC
where python >nul 2>&1
if %errorlevel% equ 0 (
    python setup_shortcut.py
    goto :done
)

where py >nul 2>&1
if %errorlevel% equ 0 (
    py setup_shortcut.py
    goto :done
)

for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python*") do (
    if exist "%%D\python.exe" (
        "%%D\python.exe" setup_shortcut.py
        goto :done
    )
)

echo [NOTICE] Python 3 was not detected on PATH.
echo Launching automated environment installer (install.ps1)...
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" -Local
if %errorlevel% equ 0 goto :done

echo [ERROR] Python 3 installation could not be completed automatically.
echo Please install Python 3.9+ from https://www.python.org/downloads/
pause
exit /b 1

:done
echo.
echo [DONE] You can now launch "Software Update Manager" directly from your Desktop!
timeout /t 4
