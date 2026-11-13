@echo off
chcp 65001 >nul
title SocketIO AI Assistant - Port 5001
cd /d "%~dp0"

echo ============================================================
echo   WebSocket / AI Medical Assistant
echo   URL: http://localhost:5001   (namespace: /ws/chat)
echo ============================================================
echo.
echo   Requires a real DEEPSEEK_API_KEY in .env.
echo   Restart this service after changing the key.
echo.

if not exist ".\venv\Scripts\python.exe" (
    echo [ERROR] venv not found: .\venv\Scripts\python.exe
    echo         See docs\ for setup instructions.
    echo.
    pause
    exit /b 1
)

".\venv\Scripts\python.exe" websocket_chat.py

echo.
echo ============================================================
echo   WebSocket service stopped.
echo ============================================================
pause
