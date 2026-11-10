@echo off
setlocal
title TwinNode Cell Master Launcher

echo =====================================================================
echo  TWINNODE CELL - DISTRIBUTED SENSING AND ACTUATION SUPERVISOR
echo  Starting Complete System: Backend & Frontend Dashboard
echo =====================================================================
echo.

:: Start Backend Server
echo [1/2] Launching FastAPI Backend on http://localhost:8000...
start "TwinNode Backend Service" cmd /k "%~dp0start_backend.bat"

:: Wait for backend to bind port
timeout /t 3 /nobreak >nul

:: Start Frontend Vite Server
echo [2/2] Launching React Vite Dashboard on http://localhost:5173...
start "TwinNode Frontend UI" cmd /k "%~dp0start_frontend.bat"

echo.
echo =====================================================================
echo  TwinNode Cell System is running!
echo  Dashboard UI: http://localhost:5173
echo  REST API Docs: http://localhost:8000/docs
echo =====================================================================
