@echo off
chcp 65001 >nul
title Flask Backend - Port 5000
cd /d "%~dp0"

echo ============================================================
echo   Flask 主服务  (REST API / 数据管理 / 报告生成)
echo   访问地址: http://localhost:5000
echo ============================================================
echo.
echo  注意: 首次启动需加载 390 MB 模型并为 344 条病例计算特征向量，
echo        大约需要 1~2 分钟，请耐心等待日志输出。
echo.

if not exist ".\venv\Scripts\python.exe" (
    echo [错误] 未找到虚拟环境: .\venv\Scripts\python.exe
    echo        请先按 docs\运行手册.md 第 2 章创建虚拟环境并安装依赖。
    echo.
    pause
    exit /b 1
)

if not exist ".\.env" (
    echo [警告] 未找到 .env 配置文件，数据库连接会失败。
    echo        请复制 .env.example 为 .env 并填写 DB_PASSWORD。
    echo.
    pause
)

".\venv\Scripts\python.exe" app.py

echo.
echo ============================================================
echo   Flask 服务已退出（若上方有报错，请根据提示排查）
echo ============================================================
pause
