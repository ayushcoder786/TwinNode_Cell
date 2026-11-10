@echo off
setlocal
title TwinNode Simulation Mode

echo =====================================================================
echo  TWINNODE CELL - Starting Simulation Mode (Zero Hardware Required)
echo =====================================================================
echo.

start "TwinNode Backend [Simulation]" cmd /k "%~dp0start_backend.bat"
timeout /t 2 /nobreak >nul
start "TwinNode Frontend [Dashboard]" cmd /k "%~dp0start_frontend.bat"

echo.
echo Both Simulation Backend and Frontend Dashboard have been launched.
echo Open your browser at: http://localhost:5173
echo.
