@echo off
setlocal
cd /d "%~dp0"

echo ==============================================================================
echo   OvaLens Hatchery Platform -- Dual Dev Server Launcher
echo ==============================================================================
echo.

set "PY_EXE="

if exist "%LOCALAPPDATA%\Python\bin\python.exe" set "PY_EXE=%LOCALAPPDATA%\Python\bin\python.exe"

if not defined PY_EXE (
    for /f "delims=" %%i in ('where python 2^>nul') do (
        if not defined PY_EXE set "PY_EXE=%%i"
    )
)

if not defined PY_EXE (
    for /f "delims=" %%i in ('where py 2^>nul') do (
        if not defined PY_EXE set "PY_EXE=%%i"
    )
)

if not defined PY_EXE (
    echo [ERROR] Python was not found on your system.
    echo Please ensure Python 3.10+ is installed and on your PATH.
    pause
    exit /b 1
)

echo [OK] Using Python: %PY_EXE%
echo.

"%PY_EXE%" run_dev.py %*
if %ERRORLEVEL% neq 0 (
    echo.
    echo [INFO] Dev servers stopped.
    pause
)

