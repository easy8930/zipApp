@echo off
cd /d "%~dp0"
py -3 app.py
if errorlevel 1 (
  echo Python 3 with Tcl/Tk is required. Install Python from python.org.
  pause
)
