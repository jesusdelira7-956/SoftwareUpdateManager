@echo off
cd /d "%~dp0"

:: Locate pythonw.exe or python.exe dynamically on any computer
where pythonw >nul 2>&1
if %errorlevel% equ 0 (
    start "" pythonw "update_manager.py"
    exit /b 0
)

where python >nul 2>&1
if %errorlevel% equ 0 (
    start "" python "update_manager.py"
    exit /b 0
)

where pyw >nul 2>&1
if %errorlevel% equ 0 (
    start "" pyw "update_manager.py"
    exit /b 0
)

for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python*") do (
    if exist "%%D\pythonw.exe" (
        start "" "%%D\pythonw.exe" "update_manager.py"
        exit /b 0
    )
)

echo [ERROR] Python 3 was not found on this computer.
echo Please install Python 3.9+ from https://www.python.org/downloads/
pause
exit /b 1
