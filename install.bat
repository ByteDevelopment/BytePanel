@echo off
setlocal
cd /d "%~dp0"

title BytePanel Installer

echo.
echo  ============================================
echo    BytePanel Installer
echo  ============================================
echo.

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo  [ERROR] Python was not found.
    echo          Install Python 3.9+ from https://www.python.org/downloads/
    echo          and make sure "Add python.exe to PATH" is checked.
    pause
    exit /b 1
)

for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set "PYVER=%%v"
echo  [1/4] Found Python %PYVER%

echo  [2/4] Creating virtual environment...
python -m venv venv
if %errorlevel% neq 0 (
    echo  [ERROR] Failed to create virtual environment.
    pause
    exit /b 1
)

echo  [3/4] Installing dependencies...
call venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo  [ERROR] Failed to activate virtual environment.
    pause
    exit /b 1
)

python -m pip install --upgrade pip --quiet
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo  [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)

echo  [4/4] Creating folders...
if not exist "instance" mkdir "instance"
if not exist "servers" mkdir "servers"

echo.
echo  ============================================
echo    Installation complete!
echo    Run start.bat to launch the panel.
echo    Open http://localhost:8080 in your browser.
echo  ============================================
echo.
pause
