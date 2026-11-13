@echo off
chcp 65001 >nul
title 医疗数据可视化系统 - 一键启动
cd /d "%~dp0"

echo ============================================================
echo   医疗疾病数据分析大屏可视化系统 - 一键启动
echo ============================================================
echo.
echo   即将打开 3 个窗口：
echo     1) Flask 主服务        http://localhost:5000
echo     2) SocketIO AI 助手    http://localhost:5001
echo     3) Vue 前端            http://localhost:8080
echo.
echo   后端首次启动需 1~2 分钟加载模型，之后访问 http://localhost:8080
echo.

if not exist ".\venv\Scripts\python.exe" (
    echo [错误] 未找到虚拟环境: .\venv\Scripts\python.exe
    echo        请先按 docs\运行手册.md 第 2 章创建虚拟环境并安装依赖。
    echo.
    pause
    exit /b 1
)

if not exist ".\machine\medical_model.pth" (
    echo [提示] 未找到模型权重，先执行下载脚本...
    echo.
    ".\venv\Scripts\python.exe" download_weights.py
    echo.
)

echo 正在启动 3 个服务窗口...
start "Flask-5000" "%~dp0start-backend.bat"
start "SocketIO-5001" "%~dp0start-websocket.bat"
start "Vue-8080" "%~dp0front-end-template-1-master\start-dev.bat"

echo.
echo ============================================================
echo   3 个窗口已启动
echo   - 后端日志窗口标题: Flask-5000 / SocketIO-5001
echo   - 前端首次编译约 1~2 分钟，完成后访问 http://localhost:8080
echo ============================================================
timeout /t 8 >nul
exit /b 0
