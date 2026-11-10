@echo off
setlocal
title TwinNode Frontend Server (Vite + React)

echo =====================================================================
echo  TWINNODE CELL - Starting Frontend Dashboard
echo =====================================================================
echo.

cd /d "%~dp0frontend"
call npm.cmd run dev
