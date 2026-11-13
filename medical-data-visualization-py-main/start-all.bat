@echo off
chcp 65001 >nul
title Medical Data Visualization - Start All
cd /d "%~dp0"

echo ============================================================
echo   Medical Data Visualization - Start All
echo ============================================================
echo.
echo   Opening 3 windows:
echo     1) Flask backend       http://localhost:5000
echo     2) SocketIO AI         http://localhost:5001
echo     3) Vue frontend        http://localhost:8080
echo.
echo   Backend needs 1-2 minutes on first start. Then open
 echo   http://localhost:8080 in your browser.
echo.

if not exist ".\venv\Scripts\python.exe" (
    echo [ERROR] venv not found: .\venv\Scripts\python.exe
    echo         See docs\ for setup instructions.
    echo.
    pause
    exit /b 1
)

if not exist ".\machine\medical_model.pth" (
    echo [INFO] Model weights not found. Running download script...
    echo.
    ".\venv\Scripts\python.exe" download_weights.py
    echo.
)

echo Starting 3 service windows...
start "Flask-5000" "%~dp0start-backend.bat"
start "SocketIO-5001" "%~dp0start-websocket.bat"
start "Vue-8080" "%~dp0front-end-template-1-master\start-dev.bat"

echo.
echo ============================================================
echo   3 windows started
echo   - Backend log windows: Flask-5000 / SocketIO-5001
echo   - Frontend: wait 1-2 min, then open http://localhost:8080
echo ============================================================
timeout /t 8 >nul
exit /b 0
