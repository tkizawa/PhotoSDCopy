@echo off
cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
    echo Creating virtual environment...
    python -m venv venv
    echo Installing dependencies...
    "venv\Scripts\python.exe" -m pip install --upgrade pip
    "venv\Scripts\python.exe" -m pip install -r requirements.txt
)

echo Starting PhotoSDCopy...
start "" "venv\Scripts\pythonw.exe" PhotoSDCopy.py
