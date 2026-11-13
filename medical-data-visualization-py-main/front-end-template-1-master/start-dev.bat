@echo off
chcp 65001 >nul
title Frontend Dev Server - Port 8080
echo ============================================================
echo   医疗疾病数据分析大屏可视化系统 - 前端开发服务器
echo ============================================================
echo.
echo  [1/2] 设置 NODE_OPTIONS=--openssl-legacy-provider
echo        (webpack 4 在 Node 17+ 上需要此开关，否则报 ERR_OSSL_EVP_UNSUPPORTED)
echo  [2/2] 启动 vue-cli-service serve ...
echo.
echo  首次编译需要 1-2 分钟，请耐心等待，不要关闭窗口。
echo  启动成功后访问: http://localhost:8080
echo ============================================================
echo.

set NODE_OPTIONS=--openssl-legacy-provider

cd /d "%~dp0"
call npm run serve

echo.
echo ============================================================
echo  前端服务已退出。如果上方有报错，请检查 node_modules 是否完整
echo  （重新安装依赖：npm install）
echo ============================================================
pause
