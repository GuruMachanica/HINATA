@echo off
REM HINATA one-click launcher — FastAPI backend + Electron desktop overlay
REM Requires: Ollama running with hinata-brain model

echo [HINATA] Starting FastAPI backend (brain + memory + KG + React UI)...
start "HINATA Backend" cmd /c "cd /d %~dp0 && python -m uvicorn backend.main:app --port 8080"

echo [HINATA] Waiting for backend to come up...
timeout /t 5 /nobreak >nul

echo [HINATA] Launching desktop overlay...
cd /d %~dp0desktop-shell
if not exist node_modules (
  echo [HINATA] First run — installing Electron...
  call npm install
)
call npm start
