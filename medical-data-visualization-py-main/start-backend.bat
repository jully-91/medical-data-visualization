@echo off
chcp 65001 >nul
title Flask Backend - Port 5000
cd /d "%~dp0"

echo ============================================================
echo   Flask Backend  (REST API / Data / Reports)
echo   URL: http://localhost:5000
echo ============================================================
echo.
echo   First start: load 390 MB model + build 344 case vectors,
echo   about 1-2 minutes. Please wait for the log output.
echo.

if not exist ".\venv\Scripts\python.exe" (
    echo [ERROR] venv not found: .\venv\Scripts\python.exe
    echo         See docs\ for setup instructions.
    echo.
    pause
    exit /b 1
)

if not exist ".\.env" (
    echo [WARN] .env not found. Database connection will fail.
    echo        Copy .env.example to .env and set DB_PASSWORD.
    echo.
    pause
)

".\venv\Scripts\python.exe" app.py

echo.
echo ============================================================
echo   Flask backend stopped. Check the log above for errors.
echo ============================================================
pause
