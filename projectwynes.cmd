@echo off
rem Project Wynes local launcher (Method 2 — GitHub ZIP).
rem Resolves everything relative to its own directory; no absolute paths.
setlocal

set "ROOT=%~dp0"

if exist "%ROOT%dist\projectwynes.exe" (
    start "" "%ROOT%dist\projectwynes.exe"
    exit /b 0
)

if exist "%ROOT%.venv\Scripts\pythonw.exe" (
    start "" "%ROOT%.venv\Scripts\pythonw.exe" "%ROOT%run.py"
    exit /b 0
)

echo Project Wynes is not set up yet.
echo Run the setup once:
echo     powershell -ExecutionPolicy Bypass -File setup.ps1
exit /b 1
