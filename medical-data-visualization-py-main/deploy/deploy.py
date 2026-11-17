#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""阶段四 · 项目部署与测试（Linux 沙箱 / 单命令自动化版）。

设计目标：**平台执行一条命令即可完成部署 + 测试**，非交互、可重复执行、退出码可判读。

    bash run.sh                      # 等价于 deploy.py all
    python3 deploy/deploy.py all     # 自检 -> 依赖(缺则装) -> 构建前端 -> 启动 -> 测试 -> 报告

子命令：
    check    仅做环境自检（Python / 依赖 / .env / MySQL / 端口 / dist）
    install  补齐 Python 依赖（跳过 mysqlclient，torch 自动走 CPU 源）
    build    构建前端 dist（Node>=17 自动加 --openssl-legacy-provider）
    start    后台启动后端(5000)+前端(8080)，--with-chat 追加 AI 服务(5001)
    serve    前台常驻运行（平台要求命令不退出时用）
    stop     停止本项目服务（pid -> ss/lsof/fuser 兜底）
    status   查看端口、dist、报告状态
    test     冒烟测试并生成《阶段四-测试报告.md》
    all      check -> install -> build -> start -> test（默认）
    pack     打包发布物 zip

退出码：0 成功 / 1 自检失败 / 2 依赖安装失败 / 3 前端构建失败 / 4 服务启动失败 / 5 测试失败

机器判读：结尾固定输出一行
    RESULT {"status": "PASS", "exit": 0, "report": "...", "url": "...", ...}
"""

import argparse
import datetime
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FRONTEND = os.path.join(ROOT, "front-end-template-1-master")
DIST = os.path.join(FRONTEND, "dist")
DOCS = os.path.join(ROOT, "docs")

# 允许通过环境变量重定向（沙箱里项目目录只读时用）
LOG_DIR = os.environ.get("DEPLOY_LOG_DIR") or os.path.join(HERE, "logs")
RUN_DIR = os.environ.get("DEPLOY_RUN_DIR") or os.path.join(HERE, ".run")

IS_WIN = os.name == "nt"
VENV_PY = (os.path.join(ROOT, "venv", "Scripts", "python.exe") if IS_WIN
           else os.path.join(ROOT, "venv", "bin", "python"))
PY = VENV_PY if os.path.isfile(VENV_PY) else sys.executable

BACKEND_PORT = int(os.environ.get("BACKEND_PORT", "5000"))
FRONTEND_PORT = int(os.environ.get("FRONTEND_PORT", "8080"))
CHAT_PORT = int(os.environ.get("CHAT_PORT", "5001"))
SERVICES = {"backend": BACKEND_PORT, "frontend": FRONTEND_PORT, "chat": CHAT_PORT}

# 启动后端时依次导入的模块（缺任意一个都会导致 app.py 起不来）
REQUIRED_MODULES = [
    "flask", "flask_cors", "pandas", "numpy", "pymysql", "dotenv",
    "matplotlib", "docx", "reportlab", "openai", "torch", "transformers", "sklearn",
]

SUMMARY = {
    "status": "FAIL",
    "exit": 1,
    "startedAt": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "finishedAt": "",
    "mode": "",
    "url": "",
    "api": "",
    "dist": False,
    "deps": [],
    "report": "",
    "test": {},
    "stages": [],
    "notes": [],
}


# --------------------------------------------------------------------------
# 输出
# --------------------------------------------------------------------------
def say(msg=""):
    print(msg, flush=True)


def stage(name, status, detail=""):
    SUMMARY["stages"].append({"name": name, "status": status, "detail": detail,
                              "at": datetime.datetime.now().strftime("%H:%M:%S")})
    mark = {"OK": "[OK]  ", "FAIL": "[FAIL]", "SKIP": "[SKIP]", "WARN": "[WARN]"}.get(status, "[....]")
    say("%s %s%s" % (mark, name, (" —— " + detail) if detail else ""))


def title(msg):
    say()
    say("=" * 70)
    say(msg)
    say("=" * 70)


def ensure_dirs():
    """创建日志/pid 目录；项目目录不可写时退回临时目录（沙箱只读场景）。"""
    global LOG_DIR, RUN_DIR
    for attr in ("LOG_DIR", "RUN_DIR"):
        path = globals()[attr]
        try:
            os.makedirs(path, exist_ok=True)
            probe = os.path.join(path, ".w")
            with open(probe, "w") as fh:
                fh.write("ok")
            os.remove(probe)
        except Exception:
            fallback = os.path.join(tempfile.gettempdir(), "medicine-deploy",
                                    os.path.basename(path) or "run")
            os.makedirs(fallback, exist_ok=True)
            globals()[attr] = fallback
            say("[WARN] %s 不可写，改用 %s" % (path, fallback))


def finish(status, code):
    SUMMARY["status"] = status
    SUMMARY["exit"] = code
    SUMMARY["finishedAt"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        with open(os.path.join(LOG_DIR, "deploy-summary.json"), "w", encoding="utf-8") as fh:
            json.dump(SUMMARY, fh, ensure_ascii=False, indent=2)
    except Exception:
        pass
    say()
    say("-" * 70)
    for item in SUMMARY["stages"]:
        say("  %-6s %-20s %s" % (item["status"], item["name"], item["detail"]))
    say("-" * 70)
    payload = {k: SUMMARY[k] for k in ("status", "exit", "url", "api", "report", "test", "notes")}
    say("RESULT " + json.dumps(payload, ensure_ascii=False))
    return code


# --------------------------------------------------------------------------
# 基础工具
# --------------------------------------------------------------------------
def port_open(port, host="127.0.0.1", timeout=0.6):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        return sock.connect_ex((host, port)) == 0
    finally:
        sock.close()


def wait_port(port, timeout):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if port_open(port):
            return True
        time.sleep(1)
    return False


def lan_ip():
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        ip = sock.getsockname()[0]
        sock.close()
        return ip
    except Exception:
        return "127.0.0.1"


def run(cmd, cwd=None, env=None, timeout=None, stream=False, echo=True):
    if echo:
        say("  $ %s" % (cmd if isinstance(cmd, str) else " ".join(cmd)))
    try:
        proc = subprocess.run(
            cmd, cwd=cwd or ROOT, env=env, shell=isinstance(cmd, str),
            stdout=None if stream else subprocess.PIPE,
            stderr=subprocess.STDOUT if stream else subprocess.PIPE,
            timeout=timeout, text=True, encoding="utf-8", errors="replace",
        )
        return proc.returncode, "" if stream else ((proc.stdout or "") + (proc.stderr or ""))
    except FileNotFoundError as exc:
        return 127, str(exc)
    except subprocess.TimeoutExpired:
        return 124, "命令超时（%ss）" % timeout


def read_env(path=None):
    path = path or os.path.join(ROOT, ".env")
    cfg = {}
    if not os.path.isfile(path):
        return cfg
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            cfg[key.strip()] = value.strip().strip('"').strip("'")
    return cfg


def write_env_file(cfg):
    path = os.path.join(ROOT, ".env")
    lines = ["# 由 deploy.py 自动生成于 %s" % datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
    for key in ("DEEPSEEK_API_KEY", "FLASK_SECRET_KEY", "DB_HOST", "DB_PORT",
                "DB_USER", "DB_PASSWORD", "DB_NAME", "DB_CHARSET"):
        lines.append("%s=%s" % (key, cfg.get(key, "")))
    try:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
        return path
    except Exception as exc:
        say("  [WARN] 无法写入 .env（%s），仅使用环境变量" % exc)
        return None


# --------------------------------------------------------------------------
# 依赖
# --------------------------------------------------------------------------
def check_modules():
    code = ("import importlib.util\n"
            "mods=%r\n"
            "print(','.join([m for m in mods if importlib.util.find_spec(m) is None]))\n"
            % REQUIRED_MODULES)
    rc, out = run([PY, "-c", code], timeout=60, echo=False)
    if rc != 0:
        return list(REQUIRED_MODULES)
    return [m for m in out.strip().split(",") if m]


def filtered_requirements():
    """部署用依赖清单：剔除 Linux 沙箱里没必要 / 容易编译失败的包。"""
    src = os.path.join(ROOT, "requirements.txt")
    drop = {"mysqlclient", "selenium", "webdriver-manager", "pyopenssl",
            "urllib3-secure-extra", "virtualenvwrapper-win", "pycparser"}
    lines = []
    if os.path.isfile(src):
        with open(src, "r", encoding="utf-8", errors="replace") as fh:
            for raw in fh:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                name = line.split("=")[0].split(">")[0].split("<")[0].split("[")[0].strip().lower()
                if name in drop:
                    continue
                lines.append(line)
    if not lines:
        lines = ["Flask", "Flask-Cors", "pandas", "numpy<2", "PyMySQL", "python-dotenv",
                 "matplotlib", "python-docx", "reportlab", "openai", "torch",
                 "transformers", "scikit-learn", "flask-socketio", "requests", "openpyxl"]
    path = os.path.join(tempfile.gettempdir(), "medicine-requirements.txt")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    return path, len(lines)


def pip_install(args, timeout=2400):
    mirrors = ["https://pypi.tuna.tsinghua.edu.cn/simple", "https://mirrors.aliyun.com/pypi/simple/"]
    for mirror in mirrors + [None]:
        cmd = [PY, "-m", "pip", "install", "--disable-pip-version-check"] + args
        if mirror:
            cmd += ["-i", mirror, "--trusted-host", mirror.split("/")[2]]
        rc, _ = run(cmd, timeout=timeout, stream=True)
        if rc == 0:
            return True
        say("  [WARN] pip 源 %s 失败（退出码 %s），换下一个" % (mirror or "默认 PyPI", rc))
    return False


def ensure_deps(skip=False):
    missing = check_modules()
    SUMMARY["deps"] = missing
    if not missing:
        stage("Python 依赖", "OK", "全部已安装")
        return True
    if skip:
        stage("Python 依赖", "WARN", "缺少 %d 个（--skip-install 未安装）：%s"
              % (len(missing), ", ".join(missing)))
        return True

    stage("Python 依赖", "OK", "缺 %d 个，开始安装：%s" % (len(missing), ", ".join(missing)))
    req, count = filtered_requirements()
    say("  使用过滤后的依赖清单（%d 项，已剔除 mysqlclient 等）" % count)
    ok = pip_install(["-r", req])
    if not ok:
        say("  [WARN] 整表安装失败，改为只装核心运行依赖")
        ok = pip_install(["flask", "flask-cors", "pandas", "numpy<2", "PyMySQL",
                          "python-dotenv", "matplotlib", "python-docx", "reportlab",
                          "openai", "flask-socketio", "requests", "openpyxl", "scikit-learn"])

    missing = check_modules()
    if "torch" in missing or "transformers" in missing:
        say("  尝试从 PyTorch CPU 源安装（体积更小、无需 CUDA）……")
        rc, _ = run([PY, "-m", "pip", "install", "torch", "--index-url",
                     "https://download.pytorch.org/whl/cpu"], timeout=3600, stream=True)
        if rc == 0:
            pip_install(["transformers"], timeout=1800)
        missing = check_modules()

    SUMMARY["deps"] = missing
    if missing:
        stage("Python 依赖", "FAIL", "仍缺少：%s" % ", ".join(missing))
        return False
    stage("Python 依赖", "OK", "安装完成")
    return True


# --------------------------------------------------------------------------
# .env 与数据库
# --------------------------------------------------------------------------
def probe_mysql(cfg):
    code = (
        "import pymysql\n"
        "try:\n"
        "    c=pymysql.connect(host=%r,port=%d,user=%r,password=%r,database=%r,"
        "charset='utf8mb4',connect_timeout=8)\n"
        "    cur=c.cursor();cur.execute('SELECT COUNT(*) FROM cases');n=cur.fetchone()[0];c.close()\n"
        "    print('OK',n)\n"
        "except Exception as e:\n"
        "    print('ERR',type(e).__name__,str(e)[:200])\n"
    ) % (cfg["DB_HOST"], int(cfg["DB_PORT"]), cfg["DB_USER"], cfg["DB_PASSWORD"], cfg["DB_NAME"])
    rc, out = run([PY, "-c", code], timeout=60, echo=False)
    if rc != 0:
        return False, out.strip()[:300]
    out = out.strip()
    if out.startswith("OK"):
        return True, out.split(" ", 1)[1] if " " in out else ""
    return False, (out[4:].strip()[:300] if out.startswith("ERR") else out)


def ensure_env():
    """确保 .env 可用且数据库能连上；必要时自动生成 .env 并回写可用凭据。"""
    dotenv_path = os.path.join(ROOT, ".env")
    cfg = read_env(dotenv_path)

    base = {
        "DEEPSEEK_API_KEY": cfg.get("DEEPSEEK_API_KEY", os.environ.get("DEEPSEEK_API_KEY", "")),
        "FLASK_SECRET_KEY": cfg.get("FLASK_SECRET_KEY",
                                    os.environ.get("FLASK_SECRET_KEY", "medicine-deploy")),
        "DB_HOST": os.environ.get("DB_HOST") or cfg.get("DB_HOST", "127.0.0.1"),
        "DB_PORT": os.environ.get("DB_PORT") or cfg.get("DB_PORT", "3306"),
        "DB_USER": os.environ.get("DB_USER") or cfg.get("DB_USER", "root"),
        "DB_NAME": os.environ.get("DB_NAME") or cfg.get("DB_NAME", "medicalinfo"),
        "DB_CHARSET": "utf8mb4",
    }

    candidates = []
    for pw in (os.environ.get("DB_PASSWORD"), cfg.get("DB_PASSWORD"), "", "root", "123456"):
        if pw is not None and pw not in candidates:
            candidates.append(pw)

    last_error = ""
    for pw in candidates:
        ok, info = probe_mysql(dict(base, DB_PASSWORD=pw))
        if ok:
            base["DB_PASSWORD"] = pw
            if not os.path.isfile(dotenv_path) or cfg.get("DB_PASSWORD") != pw:
                write_env_file(base)
                stage(".env 配置", "OK", "已自动生成 / 回写 .env")
            else:
                stage(".env 配置", "OK", "已存在且连接成功")
            stage("数据库连接", "OK", "cases 表 %s 条记录" % info)
            SUMMARY["notes"].append("数据库可用：cases=%s" % info)
            return True
        last_error = info

    stage("数据库连接", "FAIL", last_error or "无法连接 MySQL")
    say("       检查：MySQL 是否启动、medicalinfo 是否已导入、"
        "以及 .env 的 DB_HOST/DB_USER/DB_PASSWORD（或同名环境变量）")
    return False


# --------------------------------------------------------------------------
# 前端构建
# --------------------------------------------------------------------------
def node_major():
    rc, out = run(["node", "-v"], timeout=30, echo=False)
    if rc != 0:
        return None
    try:
        return int(out.strip().lstrip("v").split(".")[0])
    except Exception:
        return None


def ensure_frontend(skip=False):
    index = os.path.join(DIST, "index.html")
    if os.path.isfile(index):
        stage("前端构建", "OK" if not skip else "SKIP",
              "dist 已存在，直接复用（要重建用 --rebuild）")
        SUMMARY["dist"] = True
        return True

    if not os.path.isdir(FRONTEND):
        stage("前端构建", "FAIL", "缺少前端目录 %s" % FRONTEND)
        return False
    if not shutil.which("npm"):
        stage("前端构建", "FAIL", "未找到 npm（需要 Node.js 16/18 LTS）")
        return False

    env = dict(os.environ)
    nmaj = node_major() or 0
    if nmaj >= 17:
        env["NODE_OPTIONS"] = "--openssl-legacy-provider --max-old-space-size=4096"

    if not os.path.isdir(os.path.join(FRONTEND, "node_modules")):
        stage("前端依赖", "OK", "npm install 中……")
        rc, _ = run("npm install --registry=https://registry.npmmirror.com --no-audit --no-fund",
                    cwd=FRONTEND, env=env, timeout=2400, stream=True)
        if rc != 0:
            stage("前端依赖", "FAIL", "npm install 失败（退出码 %d）" % rc)
            return False
        stage("前端依赖", "OK", "安装完成")

    say("  构建中（npm run build，约 1~3 分钟）……")
    rc, _ = run("npm run build", cwd=FRONTEND, env=env, timeout=2400, stream=True)
    if rc != 0 or not os.path.isfile(index):
        stage("前端构建", "FAIL", "npm run build 失败（退出码 %d）" % rc)
        return False

    files = sum(len(f) for _, _, f in os.walk(DIST))
    stage("前端构建", "OK", "%d 个文件" % files)
    SUMMARY["dist"] = True
    return True


# --------------------------------------------------------------------------
# 服务管理
# --------------------------------------------------------------------------
def pid_file(name):
    return os.path.join(RUN_DIR, "%s.pid" % name)


def spawn(name, cmd):
    log_path = os.path.join(LOG_DIR, "%s.log" % name)
    log_file = open(log_path, "a", encoding="utf-8", errors="replace")
    log_file.write("\n===== %s 启动 %s =====\n"
                   % (name, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    log_file.flush()
    kwargs = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if IS_WIN else {"start_new_session": True}
    proc = subprocess.Popen(cmd, cwd=ROOT, stdout=log_file, stderr=subprocess.STDOUT,
                            stdin=subprocess.DEVNULL, env=dict(os.environ), **kwargs)
    with open(pid_file(name), "w", encoding="utf-8") as fh:
        fh.write(str(proc.pid))
    say("  启动 %s（pid=%d），日志 %s" % (name, proc.pid, log_path))
    return proc


def kill_tree(pid):
    if IS_WIN:
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(os.getpgid(pid), sig)
            time.sleep(0.4)
        except Exception:
            try:
                os.kill(pid, sig)
                time.sleep(0.2)
            except Exception:
                break


def pids_on_port(port):
    """不依赖 lsof：Windows 用 netstat，Linux 用 ss -> lsof -> fuser 依次尝试。"""
    if IS_WIN:
        rc, out = run(["netstat", "-ano"], timeout=20, echo=False)
        pids = set()
        for line in out.splitlines():
            parts = line.split()
            if len(parts) >= 5 and parts[1].endswith(":%d" % port) and parts[3] == "LISTENING":
                if parts[4].isdigit():
                    pids.add(int(parts[4]))
        return pids

    cmds = [
        "ss -ltnp 2>/dev/null | awk '$4 ~ /:%d$/ {print $6}' | grep -o 'pid=[0-9]*' | cut -d= -f2" % port,
        "lsof -ti tcp:%d 2>/dev/null" % port,
        "fuser -n tcp %d 2>/dev/null" % port,
    ]
    for cmd in cmds:
        rc, out = run(["bash", "-c", cmd], timeout=20, echo=False)
        pids = {p for p in out.replace(",", " ").split() if p.isdigit()}
        if pids:
            return {int(p) for p in pids}
    return set()


def stop_all(quiet=False):
    stopped = []
    for name in ("chat", "frontend", "backend"):
        path = pid_file(name)
        if os.path.isfile(path):
            try:
                pid = int(open(path).read().strip())
            except Exception:
                pid = None
            if pid:
                kill_tree(pid)
                stopped.append("%s(%d)" % (name, pid))
            try:
                os.remove(path)
            except Exception:
                pass
    time.sleep(1)
    for name, port in SERVICES.items():
        if port_open(port):
            for pid in pids_on_port(port):
                kill_tree(pid)
                stopped.append("%s(port:%d)" % (name, port))
    time.sleep(0.5)
    remaining = [(name, port) for name, port in SERVICES.items() if port_open(port)]
    if stopped and not quiet:
        say("  已尝试停止：%s" % ", ".join(stopped))
    if remaining and not quiet:
        say("  [WARN] 端口仍被占用：%s（可能属于其他程序，或当前权限不足）"
            % ", ".join("%s:%d" % (n, p) for n, p in remaining))
    return stopped, remaining


def backend_cmd():
    rc, _ = run([PY, "-c", "import waitress"], timeout=30, echo=False)
    if rc == 0:
        say("  后端服务器：waitress（多线程，生产模式）")
        code = ("from waitress import serve; from app import app; "
                "serve(app, host='0.0.0.0', port=%d, threads=8, channel_timeout=300)"
                % BACKEND_PORT)
        return [PY, "-c", code]
    say("  后端服务器：flask 内置（需要生产级可 pip install waitress）")
    return [PY, "-m", "flask", "--app", "app", "run",
            "--host", "0.0.0.0", "--port", str(BACKEND_PORT)]


def start_services(with_chat=False):
    if not os.path.isfile(os.path.join(DIST, "index.html")):
        stage("服务启动", "FAIL", "前端 dist 不存在，请先构建")
        return False

    stop_all(quiet=True)
    started = [
        ("backend", spawn("backend", backend_cmd()), 420, "后端 API"),
        ("frontend", spawn("frontend", [
            PY, os.path.join(HERE, "serve_dist.py"),
            "--port", str(FRONTEND_PORT), "--api", "http://127.0.0.1:%d" % BACKEND_PORT,
        ]), 60, "前端静态服务"),
    ]
    if with_chat:
        started.append(("chat", spawn("chat", [PY, os.path.join(ROOT, "websocket_chat.py")]),
                        180, "AI 助手"))

    ok = True
    for name, proc, timeout, label in started:
        port = SERVICES[name]
        say("  等待 %s（端口 %d，最长 %ds）……" % (label, port, timeout))
        if wait_port(port, timeout):
            stage(label, "OK", "端口 %d 已监听" % port)
        else:
            ok = False
            proc.poll()
            detail = ("进程已退出（%s）" % proc.returncode) if proc.returncode is not None else "端口未监听"
            stage(label, "FAIL", "%s，日志 %s" % (detail, os.path.join(LOG_DIR, "%s.log" % name)))
            tail_log(name)

    ip = lan_ip()
    SUMMARY["url"] = "http://%s:%d/" % (ip, FRONTEND_PORT)
    SUMMARY["api"] = "http://%s:%d/" % (ip, BACKEND_PORT)
    say()
    say("  前端访问：%s" % SUMMARY["url"])
    say("  后端 API：%s" % SUMMARY["api"])
    return ok


def tail_log(name, lines=25):
    path = os.path.join(LOG_DIR, "%s.log" % name)
    if not os.path.isfile(path):
        return
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            content = fh.readlines()[-lines:]
        say("  --- %s.log 末尾 ---" % name)
        for line in content:
            say("  | " + line.rstrip())
        say("  --------------------")
    except Exception:
        pass


# --------------------------------------------------------------------------
# 测试
# --------------------------------------------------------------------------
def run_smoke():
    json_out = os.path.join(DOCS, "阶段四-测试结果.json")
    cmd = [PY, os.path.join(HERE, "smoke_test.py"),
           "--api", "http://127.0.0.1:%d" % BACKEND_PORT,
           "--web", "http://127.0.0.1:%d" % FRONTEND_PORT,
           "--json-out", json_out]
    rc = subprocess.call(cmd, cwd=ROOT)
    SUMMARY["report"] = os.path.join(DOCS, "阶段四-测试报告.md")
    if os.path.isfile(json_out):
        try:
            with open(json_out, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            SUMMARY["test"] = {k: data.get(k) for k in ("total", "passed", "failed", "skipped", "rate")}
        except Exception:
            pass
    if rc == 0:
        stage("冒烟测试", "OK", "通过 %s 条，跳过 %s 条"
              % (SUMMARY["test"].get("passed"), SUMMARY["test"].get("skipped")))
        return True
    stage("冒烟测试", "FAIL", "失败 %s 条，详见报告" % SUMMARY["test"].get("failed"))
    return False


# --------------------------------------------------------------------------
# 动作
# --------------------------------------------------------------------------
def cmd_check():
    title("环境自检")
    ok = True
    say("  Python：%s（%s）" % (sys.version.split()[0], PY))
    missing = check_modules()
    SUMMARY["deps"] = missing
    say("  [%s] 依赖：%s" % ("OK" if not missing else "WARN",
                            "齐全" if not missing else "缺少 " + ", ".join(missing)))
    nmaj = node_major()
    say("  [%s] Node：%s" % ("OK" if nmaj else "WARN",
                            ("v%d" % nmaj) if nmaj else "未安装（前端无法构建）"))
    has_dist = os.path.isfile(os.path.join(DIST, "index.html"))
    say("  [%s] dist/index.html：%s" % ("OK" if has_dist else "WARN",
                                       "已构建" if has_dist else "未构建"))

    if not ensure_env():
        ok = False
    for name, port in SERVICES.items():
        busy = port_open(port)
        say("  [%s] %s 端口 %d：%s" % ("WARN" if busy else "OK", name, port,
                                      "占用（all 会先清理）" if busy else "空闲"))
    stage("环境自检", "OK" if ok else "FAIL")
    return 0 if ok else 1


def cmd_install():
    title("安装 Python 依赖")
    return 0 if ensure_deps(skip=False) else 2


def cmd_build():
    title("构建前端")
    return 0 if ensure_frontend(skip=False) else 3


def cmd_start(with_chat=False, serve_forever=False):
    title("启动服务")
    if not start_services(with_chat=with_chat):
        return 4
    if serve_forever:
        say("  前台常驻模式，按 Ctrl+C 退出")
        try:
            while True:
                time.sleep(2)
                if not port_open(BACKEND_PORT) or not port_open(FRONTEND_PORT):
                    stage("服务存活", "FAIL", "服务已退出")
                    return 4
        except KeyboardInterrupt:
            stop_all()
            return 0
    return 0


def cmd_stop():
    title("停止服务")
    stopped, remaining = stop_all()
    if remaining:
        stage("停止服务", "FAIL", "仍有端口未释放：%s。可手动结束："
              "`kill -9 $(ss -ltnp | awk '$4 ~ /:5000$/ {print $6}' | grep -o 'pid=[0-9]*' | cut -d= -f2)`"
              % ", ".join("%s:%d" % (n, p) for n, p in remaining))
        return 1
    stage("停止服务", "OK", "已停止" if stopped else "本来就没有运行中的服务")
    return 0


def cmd_status():
    title("服务状态")
    ip = lan_ip()
    for name, port in SERVICES.items():
        alive = port_open(port)
        say("  [%s] %-9s 端口 %d  %s" % ("UP  " if alive else "DOWN", name, port,
                                        ("http://%s:%d/" % (ip, port)) if alive else ""))
    say("  dist：%s" % ("已构建" if os.path.isfile(os.path.join(DIST, "index.html")) else "未构建"))
    report = os.path.join(DOCS, "阶段四-测试报告.md")
    say("  测试报告：%s" % (report if os.path.isfile(report) else "尚未生成"))
    return 0


def cmd_test():
    title("冒烟测试")
    return 0 if run_smoke() else 5


def cmd_all(skip_install=False, skip_build=False, with_chat=False):
    title("阶段四：自检 -> 依赖 -> 构建 -> 启动 -> 测试")
    SUMMARY["mode"] = "all"

    if not ensure_env():
        stage("自检", "FAIL", "数据库不可用")
        return finish("FAIL", 1)
    if not ensure_deps(skip=skip_install):
        return finish("FAIL", 2)
    if not ensure_frontend(skip=skip_build):
        return finish("FAIL", 3)
    if not start_services(with_chat=with_chat):
        return finish("FAIL", 4)
    if not run_smoke():
        return finish("FAIL", 5)
    return finish("PASS", 0)


def cmd_pack(with_weights=False):
    title("打包发布物")
    out_dir = os.path.join(ROOT, "release")
    os.makedirs(out_dir, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M")
    name = "medicine-release-%s" % stamp
    stage_dir = os.path.join(out_dir, name)
    if os.path.isdir(stage_dir):
        shutil.rmtree(stage_dir)
    os.makedirs(stage_dir)

    patterns = ["__pycache__", "*.pyc", ".pytest_cache", ".DS_Store", ".run", "logs", "release"]
    if not with_weights:
        patterns += ["*.pth", "pytorch_model.bin"]
        say("  默认排除模型权重（需要时加 --with-weights）")
    skip = shutil.ignore_patterns(*patterns)

    def copy(rel):
        src = os.path.join(ROOT, rel)
        dst = os.path.join(stage_dir, rel)
        if not os.path.exists(src):
            return
        if os.path.isdir(src):
            shutil.copytree(src, dst, ignore=skip)
        else:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)

    for rel in ("app.py", "websocket_chat.py", "requirements.txt", ".env.example",
                "README.md", "medicalinfo.sql", "run.sh", "download_weights.py",
                "start-all.bat", "start-backend.bat", "start-websocket.bat",
                "docs", "utils", "spiders", "machine", "deploy"):
        copy(rel)
    # 前端：dist 开箱即用；源码与配置用于队友本地 npm install / 二次开发
    for rel in ("dist", "src", "public", "package.json", "package-lock.json",
                "vue.config.js", "babel.config.js", ".browserslistrc", "start-dev.bat"):
        copy("front-end-template-1-master/" + rel)

    archive = shutil.make_archive(os.path.join(out_dir, name), "zip",
                                  root_dir=out_dir, base_dir=name)
    shutil.rmtree(stage_dir, ignore_errors=True)
    stage("打包", "OK", "%s（%.1f MB）" % (archive, os.path.getsize(archive) / 1024 / 1024))
    return finish("PASS", 0)


def main():
    parser = argparse.ArgumentParser(description="阶段四 部署与测试（Linux 单命令版）")
    parser.add_argument("action", nargs="?", default="all",
                        choices=["check", "install", "build", "start", "serve", "stop",
                                 "status", "test", "all", "pack"])
    parser.add_argument("--skip-install", action="store_true", help="跳过依赖安装（环境已预装时）")
    parser.add_argument("--skip-build", action="store_true", help="跳过前端构建（dist 已存在时）")
    parser.add_argument("--rebuild", action="store_true", help="强制重新构建前端")
    parser.add_argument("--with-chat", action="store_true", help="同时启动 AI 助手服务(5001)")
    parser.add_argument("--with-weights", action="store_true", help="pack 时包含模型权重")
    args = parser.parse_args()

    ensure_dirs()
    if args.rebuild and os.path.isdir(DIST):
        shutil.rmtree(DIST, ignore_errors=True)

    try:
        if args.action == "check":
            return cmd_check()
        if args.action == "install":
            return cmd_install()
        if args.action == "build":
            return cmd_build()
        if args.action == "start":
            return cmd_start(with_chat=args.with_chat)
        if args.action == "serve":
            return cmd_start(with_chat=args.with_chat, serve_forever=True)
        if args.action == "stop":
            return cmd_stop()
        if args.action == "status":
            return cmd_status()
        if args.action == "test":
            return cmd_test()
        if args.action == "pack":
            return cmd_pack(with_weights=args.with_weights)
        return cmd_all(skip_install=args.skip_install, skip_build=args.skip_build,
                       with_chat=args.with_chat)
    except KeyboardInterrupt:
        say("\n中断，清理服务……")
        stop_all()
        return finish("FAIL", 130)


if __name__ == "__main__":
    sys.exit(main())
