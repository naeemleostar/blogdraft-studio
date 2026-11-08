@echo off
rem Builds "BlogDraft Studio.exe" (no Python needed by your viewers). Run this on a Windows PC that has Python.
title Build BlogDraft Studio.exe
cd /d "%~dp0"
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY (where python >nul 2>nul && set "PY=python")
if not defined PY (echo Install Python from https://www.python.org/downloads/ first. & pause & exit /b 1)

if not exist ".buildenv\Scripts\python.exe" %PY% -m venv .buildenv
".buildenv\Scripts\python.exe" -m pip install -q --upgrade pip
".buildenv\Scripts\python.exe" -m pip install -q -r requirements.txt pyinstaller || (echo Install failed. & pause & exit /b 1)

".buildenv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --onefile --windowed ^
  --name "BlogDraft Studio" --icon app.ico ^
  --add-data "web;web" ^
  server.py || (echo Build failed. & pause & exit /b 1)

rem Package: exe + WordPress plugin + readme
if exist release rmdir /s /q release
mkdir release\BlogDraft-Studio
copy "dist\BlogDraft Studio.exe" release\BlogDraft-Studio\ >nul
xcopy wp-plugin release\BlogDraft-Studio\wp-plugin\ /e /i /q >nul
copy README.md release\BlogDraft-Studio\ >nul
powershell -NoProfile -Command "Compress-Archive -Path 'release\BlogDraft-Studio\*' -DestinationPath 'release\BlogDraft-Studio-Windows.zip' -Force"
echo.
echo Done: release\BlogDraft-Studio-Windows.zip
pause
