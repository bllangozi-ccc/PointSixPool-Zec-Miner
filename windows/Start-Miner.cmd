@echo off
setlocal
cd /d "%~dp0"
python -c "import sys;sys.exit(0 if sys.version_info.major == 3 else 1)" >nul 2>&1
if not errorlevel 1 goto use_python
py -3 -c "import sys;sys.exit(0 if sys.version_info.major == 3 else 1)" >nul 2>&1
if not errorlevel 1 goto use_py
echo Python 3 was not found. Install it from https://www.python.org/downloads/windows/
echo Then close this window and double-click this launcher again.
pause
exit /b 1
:use_python
python -B point6miner_ui.py
set "miner_exit=%errorlevel%"
goto finished
:use_py
py -3 -B point6miner_ui.py
set "miner_exit=%errorlevel%"
:finished
if not "%miner_exit%"=="0" pause
exit /b %miner_exit%
