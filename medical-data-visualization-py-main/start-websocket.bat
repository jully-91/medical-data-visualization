@echo off
chcp 65001 >nul
title SocketIO AI Assistant - Port 5001
cd /d "%~dp0"

echo ============================================================
echo   WebSocket / AI 医疗助手服务
echo   访问地址: http://localhost:5001  (namespace: /ws/chat)
echo ============================================================
echo.
echo  说明: 需要在 .env 中配置真实的 DEEPSEEK_API_KEY，
echo        且修改 Key 后必须重启本服务才会生效。
echo.

if not exist ".\venv\Scripts\python.exe" (
    echo [错误] 未找到虚拟环境: .\venv\Scripts\python.exe
    echo        请先按 docs\运行手册.md 第 2 章创建虚拟环境并安装依赖。
    echo.
    pause
    exit /b 1
)

".\venv\Scripts\python.exe" websocket_chat.py

echo.
echo ============================================================
echo   WebSocket 服务已退出
echo ============================================================
pause
