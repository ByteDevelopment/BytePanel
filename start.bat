@echo off
setlocal
cd /d "%~dp0"

title BytePanel

if not exist "venv\Scripts\activate.bat" (
    echo  [ERROR] Virtual environment not found.
    echo          Run install.bat first.
    pause
    exit /b 1
)

call venv\Scripts\activate.bat
python run.py
pause
