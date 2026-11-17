@echo off
chcp 65001 >nul
title Stage4 - Deploy & Test
cd /d "%~dp0.."

set "PY=venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"

echo ============================================================
echo   Stage 4 : check - build - start - smoke test
echo   Output  : docs\阶段四-测试报告.md
echo ============================================================
echo.

"%PY%" deploy\deploy.py all %*
set "RC=%ERRORLEVEL%"

echo.
echo Exit code: %RC%
echo.
pause
exit /b %RC%
