@echo off
title BlogDraft Studio
cd /d "%~dp0"

set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY (where python >nul 2>nul && set "PY=python")
if not defined PY (
  echo.
  echo  Python is not installed.
  echo  1. Download it from https://www.python.org/downloads/
  echo  2. During install, tick "Add python.exe to PATH".
  echo  3. Then double-click this file again.
  echo.
  start https://www.python.org/downloads/
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo First start: setting things up, please wait a minute...
  %PY% -m venv .venv || (echo Could not create the environment. & pause & exit /b 1)
  ".venv\Scripts\python.exe" -m pip install -q --upgrade pip
  ".venv\Scripts\python.exe" -m pip install -q -r requirements.txt || (echo Could not install requirements. Check your internet. & pause & exit /b 1)
)

rem Stop an older copy of the app that may still be running in the background
set "APPDIR=%~dp0"
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='pythonw.exe' OR Name='python.exe'\" | Where-Object { $_.CommandLine -and $_.CommandLine.Contains($env:APPDIR) -and $_.CommandLine.Contains('server.py') } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }" >nul 2>nul

echo Opening BlogDraft Studio in your browser...
start "" "%~dp0.venv\Scripts\pythonw.exe" "%~dp0server.py"
timeout /t 2 >nul
exit /b 0
