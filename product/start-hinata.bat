@echo off
rem HINATA one-click launcher (Windows)
rem 1. Backend exe (engine + model bundled)  2. Desktop shell overlay

setlocal
cd /d "%~dp0"

set BACKEND_EXE=%~dp0hinata-backend.exe
set SHELL_DIR=%~dp0desktop-shell

rem ---- Locate backend -------------------------------------------------------
if not exist "%BACKEND_EXE%" (
    if exist "%~dp0..\dist\hinata-backend.exe" set BACKEND_EXE=%~dp0..\dist\hinata-backend.exe
)

echo [HINATA] Starting backend: %BACKEND_EXE%
start "" /b "%BACKEND_EXE%"

rem ---- Wait for health (up to 150s: cold GPU model load) --------------------
set /a tries=0
:wait
set /a tries+=1
if %tries% gtr 50 goto :shell
curl -s -m 3 http://127.0.0.1:8080/api/health >nul 2>&1
if %errorlevel%==0 goto :shell
timeout /t 3 /nobreak >nul
goto :wait

:shell
echo [HINATA] Backend online. Launching desktop shell...
if exist "%SHELL_DIR%\node_modules" (
    cd /d "%SHELL_DIR%" && start "" cmd /c "npm start"
) else (
    echo [HINATA] Desktop shell not installed - open the browser UI instead:
    start http://127.0.0.1:8080
)
echo [HINATA] Ready. Alt+Shift+H toggles her overlay.
goto :eof
