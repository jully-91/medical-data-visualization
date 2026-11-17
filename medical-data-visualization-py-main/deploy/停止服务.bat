@echo off
chcp 65001 >nul
title Stage4 - Stop Services
cd /d "%~dp0.."

set "PY=venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"

"%PY%" deploy\deploy.py stop
echo.
pause
