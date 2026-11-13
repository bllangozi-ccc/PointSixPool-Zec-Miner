@echo off
cd /d "%~dp0"
py -3 point6miner_ui.py
if errorlevel 1 pause
