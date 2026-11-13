@echo off
chcp 65001 >nul
title Frontend Dev Server - Port 8080
echo ============================================================
echo   Medical Data Visualization - Frontend Dev Server
echo ============================================================
echo.
echo  [1/2] Set NODE_OPTIONS=--openssl-legacy-provider
 echo        (required by webpack 4 on Node 17+)
echo  [2/2] Start vue-cli-service serve ...
echo.
echo  First compile takes 1-2 minutes. Do not close the window.
echo  When ready, open: http://localhost:8080
echo ============================================================
echo.

set NODE_OPTIONS=--openssl-legacy-provider

cd /d "%~dp0"
call npm run serve

echo.
echo ============================================================
echo   Frontend dev server stopped. If there are errors above,
echo   check that node_modules is complete (run: npm install).
echo ============================================================
pause
