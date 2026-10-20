@echo off
setlocal
cd /d "%~dp0"
set "PYTHONHOME="
set "PYTHONPATH="
if not exist "%~dp0.venv\Scripts\python.exe" (
    echo OvaLens needs its project Python environment.
    echo Run: python -m venv --system-site-packages .venv
    echo Then: .venv\Scripts\python.exe -m pip install -r edge\requirements.txt
    pause
    exit /b 1
)
"%~dp0.venv\Scripts\python.exe" "%~dp0edge\launcher.py"
if errorlevel 1 pause
