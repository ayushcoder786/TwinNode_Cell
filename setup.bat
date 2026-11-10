@echo off
setlocal enabledelayedexpansion

echo =====================================================================
echo  TWINNODE CELL - DISTRIBUTED SENSING AND ACTUATION SUPERVISOR
echo  Automated Environment Setup Script
echo =====================================================================
echo.

:: Detect Python
set "PYTHON_EXE="
if exist "%~dp0backend\venv\Scripts\python.exe" (
    set "PYTHON_EXE=%~dp0backend\venv\Scripts\python.exe"
    goto :PYTHON_FOUND
)
where python >nul 2>&1
if %errorlevel% equ 0 (
    set "PYTHON_EXE=python"
    goto :PYTHON_FOUND
)
if exist "%LOCALAPPDATA%\Python\bin\python.exe" (
    set "PYTHON_EXE=%LOCALAPPDATA%\Python\bin\python.exe"
    goto :PYTHON_FOUND
)
where py >nul 2>&1
if %errorlevel% equ 0 (
    set "PYTHON_EXE=py -3"
    goto :PYTHON_FOUND
)

echo [ERROR] Python was not found in PATH or standard user directories.
echo Please ensure Python 3.10+ is installed.
pause
exit /b 1

:PYTHON_FOUND
echo [INFO] Using Python: %PYTHON_EXE%

:: 1. Create Python Virtual Environment if not exists
if not exist "%~dp0backend\venv\Scripts\python.exe" (
    echo [INFO] Creating Python virtual environment in backend\venv...
    %PYTHON_EXE% -m venv "%~dp0backend\venv"
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
)

:: 2. Install Python Dependencies
echo [INFO] Installing Python backend requirements...
"%~dp0backend\venv\Scripts\python.exe" -m pip install --upgrade pip
"%~dp0backend\venv\Scripts\python.exe" -m pip install -r "%~dp0backend\requirements.txt"
if %errorlevel% neq 0 (
    echo [ERROR] Python requirements installation failed.
    pause
    exit /b 1
)

:: 3. Install Node.js Frontend Dependencies
echo [INFO] Installing Node.js frontend dependencies via npm.cmd...
cd /d "%~dp0frontend"
call npm.cmd install
if %errorlevel% neq 0 (
    echo [ERROR] npm install failed.
    cd /d "%~dp0"
    pause
    exit /b 1
)
cd /d "%~dp0"

echo.
echo =====================================================================
echo [SUCCESS] TwinNode Cell setup complete!
echo You can now run "start_all.bat" to start both backend and frontend.
echo =====================================================================
pause
