@echo off
cd /d "%~dp0"
python -m prototype.app --egg-port COM5 --servo-port COM7 --connect
if errorlevel 1 pause
