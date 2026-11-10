@echo off
setlocal

echo =====================================================================
echo  TWINNODE CELL - MACHINE LEARNING PIPELINE TRAINING BENCHMARK
echo  Generates Multi-Session Sensor Telemetry and Trains All ML Models
echo =====================================================================
echo.

cd /d "%~dp0"
set PYTHONPATH=%~dp0

if not exist "%~dp0backend\venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found. Please run setup.bat first.
    pause
    exit /b 1
)

echo [1/2] Generating Labelled Multi-Session Simulation Dataset...
"%~dp0backend\venv\Scripts\python.exe" -m backend.app.data.generate_simulation_dataset
if %errorlevel% neq 0 (
    echo [ERROR] Dataset generation failed.
    pause
    exit /b 1
)

echo.
echo [2/2] Training & Benchmarking Supervised and Unsupervised Models...
"%~dp0backend\venv\Scripts\python.exe" -m backend.app.ml.train
if %errorlevel% neq 0 (
    echo [ERROR] Model training failed.
    pause
    exit /b 1
)

echo.
echo =====================================================================
echo [SUCCESS] All ML models trained and saved to backend\models\saved\
echo Model checkpoints and metadata logged to SQLite registry.
echo =====================================================================
pause
