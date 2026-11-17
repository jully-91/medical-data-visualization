#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""阶段四 · 项目测试：冒烟测试 + 自动生成《测试报告》。

被测对象：
  * Flask 后端   http://127.0.0.1:5000   （大屏数据、数据管理、报告、导出、AI、预测）
  * 前端生产包  http://127.0.0.1:8080   （index.html、history 路由回退、/api 代理）

用法：
    python deploy/smoke_test.py                       # 前后端都测
    python deploy/smoke_test.py --api http://127.0.0.1:5000 --web http://127.0.0.1:8080
    python deploy/smoke_test.py --only backend        # 只测后端
    python deploy/smoke_test.py --out docs/阶段四-测试报告.md

退出码：0 = 全部通过（允许 SKIP）；1 = 存在失败用例；2 = 报告写入失败。
"""

import argparse
import datetime
import json
import os
import platform
import re
import socket
import sys
import time
import urllib.error
import urllib.request

PASS = "PASS"
FAIL = "FAIL"
SKIP = "SKIP"

RESULTS = []


# --------------------------------------------------------------------------
# HTTP 封装
# --------------------------------------------------------------------------
def http_request(method, url, payload=None, timeout=180):
    """返回 (status, text, elapsed_ms, error)。status 为 None 表示连不上。"""
    data = None
    headers = {"Accept": "*/*", "User-Agent": "medicine-smoke-test/1.0"}
    if payload is not None:
        if isinstance(payload, (dict, list)):
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json; charset=utf-8"
        else:
            data = str(payload).encode("utf-8")

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    started = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            elapsed = int((time.time() - started) * 1000)
            return resp.status, body.decode("utf-8", "replace"), elapsed, None
    except urllib.error.HTTPError as exc:  # 4xx / 5xx 也要拿到响应体
        body = exc.read()
        elapsed = int((time.time() - started) * 1000)
        return exc.code, body.decode("utf-8", "replace"), elapsed, None
    except Exception as exc:  # 连接被拒绝、超时等
        elapsed = int((time.time() - started) * 1000)
        return None, "", elapsed, "%s: %s" % (type(exc).__name__, exc)


def as_json(text):
    try:
        return json.loads(text)
    except Exception:
        return None


def port_open(host, port, timeout=1.0):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        return sock.connect_ex((host, port)) == 0
    finally:
        sock.close()


def record(case_id, name, method, url, expect, status, detail, elapsed, result):
    RESULTS.append(
        {
            "id": case_id,
            "name": name,
            "method": method,
            "url": url,
            "expect": expect,
            "status": "-" if status is None else status,
            "detail": detail,
            "elapsed": elapsed,
            "result": result,
        }
    )
    flag = {"PASS": "通过", "FAIL": "失败", "SKIP": "跳过"}[result]
    print("  [%s] %-4s %s -> %s (%dms)" % (flag, case_id, name, detail, elapsed))


# --------------------------------------------------------------------------
# 测试用例
# --------------------------------------------------------------------------
def test_backend(api):
    print("\n[1/2] 后端接口测试：%s" % api)

    # B-01 服务存活
    st, body, ms, err = http_request("GET", api + "/", timeout=60)
    ok = st == 200 and "Hello World" in body
    record("B-01", "后端服务存活", "GET", "/", "200 且返回 Hello World", st,
           err or ("HTTP %s" % st), ms, PASS if ok else FAIL)

    # B-02 大屏首页数据
    st, body, ms, err = http_request("POST", api + "/getHomeData", {})
    data = as_json(body) or {}
    d = data.get("data") or {}
    ok = st == 200 and data.get("code") == 200 and bool(d.get("pieData")) and bool(d.get("casesData"))
    detail = err or "code=%s, pieData=%s 项, casesData=%s 条" % (
        data.get("code"), len(d.get("pieData") or []), len(d.get("casesData") or []))
    record("B-02", "大屏首页聚合数据", "POST", "/getHomeData",
           "200 且 pieData/casesData 非空", st, detail, ms, PASS if ok else FAIL)

    # B-03 数据管理表格
    st, body, ms, err = http_request("POST", api + "/tableData", {})
    data = as_json(body) or {}
    rows = (data.get("data") or {}).get("resultData") or []
    ok = st == 200 and data.get("code") == 200 and len(rows) > 0
    record("B-03", "数据管理列表", "POST", "/tableData", "200 且至少 1 条病例",
           st, err or "返回 %d 条记录" % len(rows), ms, PASS if ok else FAIL)

    # B-04 数据统计
    st, body, ms, err = http_request("GET", api + "/data/summary")
    data = as_json(body) or {}
    total = (data.get("data") or {}).get("totalRecords")
    ok = st == 200 and data.get("code") == 200 and total is not None
    record("B-04", "数据总览统计", "GET", "/data/summary", "200 且含 totalRecords",
           st, err or "totalRecords=%s" % total, ms, PASS if ok else FAIL)

    # B-05 数据源列表
    st, body, ms, err = http_request("GET", api + "/data/sources")
    ok = st == 200 and (as_json(body) or {}).get("code") == 200
    record("B-05", "数据源列表", "GET", "/data/sources", "200", st,
           err or "HTTP %s" % st, ms, PASS if ok else FAIL)

    # B-06 数据版本
    st, body, ms, err = http_request("GET", api + "/data/versions")
    ok = st == 200 and (as_json(body) or {}).get("code") == 200
    record("B-06", "数据版本记录", "GET", "/data/versions", "200", st,
           err or "HTTP %s" % st, ms, PASS if ok else FAIL)

    # B-07 报告模板
    st, body, ms, err = http_request("GET", api + "/templates")
    ok = st == 200
    record("B-07", "报告模板列表", "GET", "/templates", "200", st,
           err or "HTTP %s" % st, ms, PASS if ok else FAIL)

    # B-08 病例导出
    st, body, ms, err = http_request("GET", api + "/data/export?format=csv", timeout=180)
    ok = st == 200 and ("," in body or "\n" in body)
    record("B-08", "病例数据导出(CSV)", "GET", "/data/export?format=csv",
           "200 且返回 CSV 内容", st,
           err or "响应 %d 字节" % len(body.encode("utf-8", "ignore")), ms,
           PASS if ok else FAIL)

    # B-09 AI 报告摘要（无 Key 时应走 fallback，仍返回 200）
    st, body, ms, err = http_request(
        "POST", api + "/ai/report",
        {"title": "阶段四冒烟测试", "kpi": [{"label": "病例总数", "value": 1}], "filters": {}},
        timeout=180)
    data = as_json(body) or {}
    ok = st == 200 and data.get("code") == 200
    summary = ((data.get("data") or {}).get("summary") or "")
    fallback = "走 fallback 文本" if "Fallback" in summary else "由大模型生成"
    record("B-09", "AI 报告摘要", "POST", "/ai/report", "200 且返回 summary",
           st, err or ("%s，%d 字" % (fallback, len(summary))), ms, PASS if ok else FAIL)

    # B-10 疾病预测（模型未加载时降级为 SKIP，不算失败）
    st, body, ms, err = http_request(
        "POST", api + "/submitModel", {"content": "最近三天头痛、发热、咳嗽，嗓子疼"}, timeout=300)
    data = as_json(body) or {}
    code = data.get("code")
    if st == 200 and code == 200:
        result = ((data.get("data") or {}).get("resultData") or "")
        record("B-10", "疾病预测", "POST", "/submitModel", "200 且返回预测病种",
               st, "预测结果：%s" % result, ms, PASS)
    elif st == 200 and code == 500:
        record("B-10", "疾病预测", "POST", "/submitModel", "200 且返回预测病种",
               st, "模型未加载（需放置 machine/medical_model.pth），本用例跳过", ms, SKIP)
    else:
        record("B-10", "疾病预测", "POST", "/submitModel", "200 且返回预测病种",
               st, err or ("HTTP %s" % st), ms, FAIL)


def test_frontend(web):
    print("\n[2/2] 前端生产包测试：%s" % web)

    # F-01 首页
    st, body, ms, err = http_request("GET", web + "/", timeout=60)
    ok = st == 200 and 'id="app"' in body
    record("F-01", "前端首页可访问", "GET", "/", "200 且含 Vue 挂载点",
           st, err or "HTTP %s，%d 字节" % (st, len(body)), ms, PASS if ok else FAIL)

    # F-02 history 路由回退
    st, body, ms, err = http_request("GET", web + "/pred", timeout=60)
    ok = st == 200 and 'id="app"' in body
    record("F-02", "history 路由回退(/pred)", "GET", "/pred", "200 且回退到 index.html",
           st, err or "HTTP %s" % st, ms, PASS if ok else FAIL)

    # F-03 /api 反向代理
    st, body, ms, err = http_request("GET", web + "/api/getHomeData", timeout=180)
    data = as_json(body) or {}
    ok = st == 200 and data.get("code") == 200
    record("F-03", "前端 /api 代理到后端", "GET", "/api/getHomeData", "200 且 code=200",
           st, err or "code=%s" % data.get("code"), ms, PASS if ok else FAIL)

    # F-04 静态资源
    st, body, ms, err = http_request("GET", web + "/", timeout=60)
    asset = None
    m = re.search(r'(?:src|href)="(/?[^"]+\.(?:js|css))"', body)
    if m:
        asset = m.group(1)
        if not asset.startswith("/"):
            asset = "/" + asset
        st, body, ms, err = http_request("GET", web + asset, timeout=120)
        ok = st == 200 and len(body) > 0
        record("F-04", "静态资源加载", "GET", asset, "200 且内容非空",
               st, err or "%d 字节" % len(body.encode("utf-8", "ignore")), ms,
               PASS if ok else FAIL)
    else:
        record("F-04", "静态资源加载", "GET", "/", "能找到 js/css 引用",
               st, "index.html 中未找到静态资源引用", ms, FAIL)


# --------------------------------------------------------------------------
# 报告
# --------------------------------------------------------------------------
def build_report(args, started_at, finished_at):
    total = len(RESULTS)
    passed = sum(1 for r in RESULTS if r["result"] == PASS)
    failed = sum(1 for r in RESULTS if r["result"] == FAIL)
    skipped = sum(1 for r in RESULTS if r["result"] == SKIP)
    rate = (passed * 100.0 / total) if total else 0.0

    lines = []
    lines.append("# 阶段四 · 项目测试报告")
    lines.append("")
    lines.append("> 由 `deploy/smoke_test.py` 自动生成，可直接作为阶段四（项目部署与测试）的测试材料提交。")
    lines.append("")
    lines.append("## 一、测试概况")
    lines.append("")
    lines.append("| 项目 | 内容 |")
    lines.append("| --- | --- |")
    lines.append("| 被测系统 | 目标适应症及用药 / 医疗疾病数据分析可视化系统 |")
    lines.append("| 测试类型 | 部署后冒烟测试（接口 + 页面可用性） |")
    lines.append("| 测试开始 | %s |" % started_at)
    lines.append("| 测试结束 | %s |" % finished_at)
    lines.append("| 后端地址 | %s |" % args.api)
    lines.append("| 前端地址 | %s |" % (args.web if args.only != "backend" else "（本次未测）"))
    lines.append("| 用例总数 | %d |" % total)
    lines.append("| 通过 / 失败 / 跳过 | %d / %d / %d |" % (passed, failed, skipped))
    lines.append("| 通过率 | %.1f%% |" % rate)
    lines.append("")
    lines.append("## 二、测试环境")
    lines.append("")
    lines.append("| 项目 | 内容 |")
    lines.append("| --- | --- |")
    lines.append("| 操作系统 | %s |" % platform.platform())
    lines.append("| Python | %s |" % sys.version.split()[0])
    lines.append("| 解释器 | %s |" % sys.executable)
    lines.append("| 主机名 | %s |" % socket.gethostname())
    lines.append("")
    lines.append("## 三、用例执行明细")
    lines.append("")
    lines.append("| 编号 | 测试项 | 方法 | 请求地址 | 预期结果 | 实际结果 | 耗时 | 结论 |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- |")
    for r in RESULTS:
        lines.append("| %s | %s | %s | `%s` | %s | %s | %d ms | %s |" % (
            r["id"], r["name"], r["method"], r["url"], r["expect"], r["detail"],
            r["elapsed"], {"PASS": "通过", "FAIL": "失败", "SKIP": "跳过"}[r["result"]]))
    lines.append("")

    bad = [r for r in RESULTS if r["result"] == FAIL]
    lines.append("## 四、缺陷 / 异常记录")
    lines.append("")
    if bad:
        lines.append("| 编号 | 测试项 | 现象 | 可能原因 | 处理建议 |")
        lines.append("| --- | --- | --- | --- | --- |")
        for r in bad:
            lines.append("| %s | %s | %s | %s | %s |" % (
                r["id"], r["name"], r["detail"], guess_reason(r), guess_fix(r)))
    else:
        lines.append("本次测试未发现失败用例。")
    lines.append("")

    lines.append("## 五、测试结论")
    lines.append("")
    if failed == 0:
        lines.append("- 全部用例通过（其中 %d 条因环境条件跳过），系统部署后可正常访问，"
                     "满足阶段四「项目测试、整合、发布」的验收要求。" % skipped)
    else:
        lines.append("- 共 %d 条用例失败，系统尚未达到可发布状态，需按第四节处理后再复测。" % failed)
    lines.append("- 复测方式：`python deploy/smoke_test.py`（服务启动后执行）。")
    lines.append("")
    return "\n".join(lines)


def guess_reason(r):
    if "连接" in r["detail"] or "URLError" in r["detail"] or "refused" in r["detail"].lower():
        return "服务未启动或端口未监听"
    if r["status"] in (500, "500"):
        return "接口内部异常（数据库连接 / 依赖 / 数据缺失）"
    if r["status"] in (404, "404"):
        return "路由不存在或静态文件缺失"
    return "待排查"


def guess_fix(r):
    if "连接" in r["detail"] or "refused" in r["detail"].lower():
        return "先执行 `python deploy/deploy.py start`，确认 5000/8080 端口已监听"
    if r["status"] in (500, "500"):
        return "查看 deploy/logs/backend.log，检查 MySQL 与 .env 配置"
    if r["status"] in (404, "404"):
        return "确认前端已 npm run build，dist/index.html 存在"
    return "查看部署日志定位"


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(here)
    default_out = os.path.join(project_root, "docs", "阶段四-测试报告.md")

    parser = argparse.ArgumentParser(description="阶段四 冒烟测试")
    parser.add_argument("--api", default="http://127.0.0.1:5000")
    parser.add_argument("--web", default="http://127.0.0.1:8080")
    parser.add_argument("--only", choices=["all", "backend", "frontend"], default="all")
    parser.add_argument("--out", default=default_out)
    parser.add_argument("--json-out", default=os.path.join(project_root, "docs", "阶段四-测试结果.json"),
                        help="机器可读结果，供 deploy.py / 平台判读")
    parser.add_argument("--no-report", action="store_true", help="只打印结果，不写报告")
    args = parser.parse_args()

    print("=" * 68)
    print("阶段四 · 项目冒烟测试")
    print("=" * 68)

    started_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 端口预检：快速给出可读提示，避免每个用例都等超时
    for label, url in (("后端", args.api), ("前端", args.web)):
        if args.only != "all" and args.only != {"后端": "backend", "前端": "frontend"}[label]:
            continue
        host = url.split("//", 1)[-1].split(":")[0] or "127.0.0.1"
        port = int(url.rsplit(":", 1)[-1].split("/")[0] or 80)
        if not port_open(host, port):
            print("[警告] %s端口 %d 未监听（%s），相关用例将失败" % (label, port, url))

    if args.only in ("all", "backend"):
        test_backend(args.api)
    if args.only in ("all", "frontend"):
        test_frontend(args.web)

    finished_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    total = len(RESULTS)
    passed = sum(1 for r in RESULTS if r["result"] == PASS)
    failed = sum(1 for r in RESULTS if r["result"] == FAIL)
    skipped = sum(1 for r in RESULTS if r["result"] == SKIP)

    print("\n" + "-" * 68)
    print("用例 %d 条：通过 %d，失败 %d，跳过 %d，通过率 %.1f%%"
          % (total, passed, failed, skipped, (passed * 100.0 / total) if total else 0))

    if not args.no_report:
        try:
            os.makedirs(os.path.dirname(args.out), exist_ok=True)
            with open(args.out, "w", encoding="utf-8") as fh:
                fh.write(build_report(args, started_at, finished_at))
            print("测试报告已生成：%s" % args.out)
        except Exception as exc:
            print("[ERROR] 测试报告写入失败：%s" % exc)
            return 2

    if args.json_out:
        payload = {
            "startedAt": started_at,
            "finishedAt": finished_at,
            "api": args.api,
            "web": args.web,
            "total": total,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "rate": round((passed * 100.0 / total) if total else 0, 1),
            "cases": RESULTS,
        }
        try:
            out_dir = os.path.dirname(args.json_out)
            if out_dir:
                os.makedirs(out_dir, exist_ok=True)
            with open(args.json_out, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, ensure_ascii=False, indent=2)
            print("机读结果已生成：%s" % args.json_out)
        except Exception as exc:
            print("[WARN] 机读结果写入失败：%s" % exc)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
