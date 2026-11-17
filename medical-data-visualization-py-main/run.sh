#!/usr/bin/env bash
# =============================================================================
# 阶段四 · 项目部署与测试 —— 单命令入口
#
#   bash run.sh                # 自检 -> 依赖 -> 构建前端 -> 启动 -> 冒烟测试 -> 报告
#   bash run.sh serve          # 同上但前台常驻（平台要求命令不退出时用）
#   bash run.sh test           # 只跑测试（服务已在运行）
#   bash run.sh stop           # 停止服务
#   bash run.sh --skip-install # 环境已预装依赖，跳过 pip
#   bash run.sh --skip-build   # dist 已存在，跳过 npm build
#
# 退出码：0 成功 / 1 自检 / 2 依赖 / 3 构建 / 4 启动 / 5 测试失败
# 结果行：结尾固定打印 RESULT {...} 一行 JSON，便于平台判读
# =============================================================================
set -uo pipefail

cd "$(dirname "$0")" || exit 1

ACTION="${1:-all}"
case "$ACTION" in
  check|install|build|start|serve|stop|status|test|all|pack)
    shift || true
    ;;
  *)
    ACTION="all"
    ;;
esac

# 优先用项目自带 venv，其次是 python3 / python
PY=""
if [ -x "venv/bin/python" ]; then
  PY="venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PY="python3"
elif command -v python >/dev/null 2>&1; then
  PY="python"
else
  echo "[FAIL] 未找到 Python 解释器（需要 Python 3.8+）"
  echo 'RESULT {"status": "FAIL", "exit": 1, "notes": ["python not found"]}'
  exit 1
fi

echo "=============================================================="
echo " 阶段四 · 部署与测试"
echo " 解释器 : $PY ($($PY -V 2>&1))"
echo " 动作   : $ACTION"
echo " 工作目录: $(pwd)"
echo "=============================================================="

"$PY" deploy/deploy.py "$ACTION" "$@"
CODE=$?
exit $CODE
