@echo off
cd /d "%~dp0"
if exist "venv\Scripts\pythonw.exe" (
    start "" "venv\Scripts\pythonw.exe" PhotoSDCopy.py
) else (
    echo Virtual environment pythonw.exe not found in venv\Scripts.
    echo Please ensure the venv directory exists and is set up.
    pause
)
