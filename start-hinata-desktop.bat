@echo off
REM HINATA one-click launcher — FastAPI backend + Electron desktop overlay
REM Requires: Ollama running with hinata-omni model

echo [HINATA] Starting FastAPI backend (brain + memory + KG + React UI)...
REM Keep the model resident in VRAM so she never cold-starts
start "HINATA Backend" cmd /c "set OLLAMA_KEEP_ALIVE=-1 && cd /d %~dp0 && python -m uvicorn backend.main:app --port 8080"

echo [HINATA] Waiting for backend to come up...
timeout /t 5 /nobreak >nul

echo [HINATA] Launching desktop overlay...
cd /d %~dp0desktop-shell
if not exist node_modules (
  echo [HINATA] First run — installing Electron...
  call npm install
)
call npm start
