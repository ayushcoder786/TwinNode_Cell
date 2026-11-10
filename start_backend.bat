@echo off
setlocal
title TwinNode Backend Server (FastAPI + WebSockets)

echo =====================================================================
echo  TWINNODE CELL - Starting Backend Server
echo =====================================================================
echo.

cd /d "%~dp0"
if exist "%~dp0backend\venv\Scripts\python.exe" (
    "%~dp0backend\venv\Scripts\python.exe" -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
) else (
    echo [ERROR] Virtual environment not found. Please run setup.bat first.
    pause
)
