#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""前端生产环境静态服务器（阶段四「项目发布」用）。

作用：
  1. 托管 `front-end-template-1-master/dist` 里的 Vue 打包产物；
  2. 支持 vue-router 的 history 模式：找不到的路径统一回退到 index.html，
     否则直接访问 http://ip:8080/pred 会 404；
  3. 把 /api/xxx 反向代理到 Flask 后端 http://127.0.0.1:5000/xxx，
     这样前端打包时不需要写死服务器 IP，换机器 / 换 IP 都不用重新 build。

只用 Python 标准库，不依赖 Flask / nginx。

用法：
    python deploy/serve_dist.py                    # 默认 8080 端口，代理到 127.0.0.1:5000
    python deploy/serve_dist.py --port 8080 --api http://127.0.0.1:5000
    python deploy/serve_dist.py --dist ../dist     # 指定打包产物目录
"""

import argparse
import http.client
import os
import posixpath
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlsplit

# 不要把这些请求头转发给后端（由 http.client 自己生成）
HOP_BY_HOP = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "host",
    "content-length",
}

API_BASE = "http://127.0.0.1:5000"
DIST_DIR = ""
API_PREFIX = "/api"


class Handler(SimpleHTTPRequestHandler):
    """静态文件 + SPA 回退 + /api 反向代理。"""

    server_version = "MedicineDist/1.0"

    # ---------- 日志 ----------
    def log_message(self, fmt, *args):
        sys.stdout.write(
            "%s - - [%s] %s\n"
            % (self.address_string(), self.log_date_time_string(), fmt % args)
        )
        sys.stdout.flush()

    # ---------- 路由 ----------
    def do_GET(self):
        if self.path.startswith(API_PREFIX + "/") or self.path == API_PREFIX:
            self._proxy()
        else:
            self._static()

    def do_POST(self):
        if self.path.startswith(API_PREFIX + "/") or self.path == API_PREFIX:
            self._proxy()
        else:
            self._static()

    def do_PUT(self):
        if self.path.startswith(API_PREFIX + "/"):
            self._proxy()
        else:
            self.send_error(405)

    def do_DELETE(self):
        if self.path.startswith(API_PREFIX + "/"):
            self._proxy()
        else:
            self.send_error(405)

    # ---------- 静态资源 ----------
    def _static(self):
        path = unquote(urlsplit(self.path).path)
        if path == "/":
            path = "/index.html"

        # 防止 ../ 穿越到 dist 目录之外
        safe = posixpath.normpath(path).lstrip("/")
        full = os.path.join(DIST_DIR, safe.replace("/", os.sep))

        if not os.path.isfile(full):
            # history 模式回退：没有扩展名的路径交给 index.html
            if "." not in os.path.basename(path):
                self.path = "/index.html"
            else:
                self.send_error(404, "Not Found: %s" % path)
                return

        super().do_GET()

    def end_headers(self):
        # 首页不缓存，方便答辩时改完代码直接刷新看到效果
        if self.path.endswith(("index.html", "/")):
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        super().end_headers()

    # ---------- 反向代理 ----------
    def _proxy(self):
        parts = urlsplit(API_BASE)
        target_path = self.path[len(API_PREFIX):] or "/"
        if not target_path.startswith("/"):
            target_path = "/" + target_path

        body = None
        length = self.headers.get("Content-Length")
        if length:
            body = self.rfile.read(int(length))

        headers = {}
        for key, value in self.headers.items():
            if key.lower() not in HOP_BY_HOP:
                headers[key] = value

        conn_cls = (
            http.client.HTTPSConnection if parts.scheme == "https" else http.client.HTTPConnection
        )
        conn = conn_cls(parts.hostname, parts.port or (443 if parts.scheme == "https" else 80), timeout=120)
        try:
            conn.request(self.command, target_path, body=body, headers=headers)
            upstream = conn.getresponse()
            payload = upstream.read()
        except Exception as exc:  # 后端没起来时给出看得懂的提示
            message = (
                "后端服务不可用：%s\n请先启动 Flask 后端（python app.py 或 deploy/deploy.py start）\n"
                % exc
            ).encode("utf-8")
            self.send_response(502)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(message)))
            self.end_headers()
            self.wfile.write(message)
            return
        finally:
            conn.close()

        self.send_response(upstream.status)
        for key, value in upstream.getheaders():
            if key.lower() not in HOP_BY_HOP:
                self.send_header(key, value)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def main():
    global API_BASE, DIST_DIR

    here = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(here)
    default_dist = os.path.join(project_root, "front-end-template-1-master", "dist")

    parser = argparse.ArgumentParser(description="药品/疾病分析系统前端生产服务")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--host", default="0.0.0.0", help="0.0.0.0 表示局域网其他机器也能访问")
    parser.add_argument("--dist", default=default_dist)
    parser.add_argument("--api", default="http://127.0.0.1:5000")
    args = parser.parse_args()

    DIST_DIR = os.path.abspath(args.dist)
    API_BASE = args.api.rstrip("/")

    if not os.path.isdir(DIST_DIR):
        print("[ERROR] 找不到前端打包产物：%s" % DIST_DIR)
        print("        请先在 front-end-template-1-master 目录执行：npm run build")
        return 2
    if not os.path.isfile(os.path.join(DIST_DIR, "index.html")):
        print("[ERROR] 打包产物里没有 index.html：%s" % DIST_DIR)
        return 2

    os.chdir(DIST_DIR)
    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    print("[前端] dist 目录 : %s" % DIST_DIR)
    print("[前端] 代理 /api  -> %s" % API_BASE)
    print("[前端] 监听地址  : http://%s:%d" % (args.host, args.port))
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[前端] 已停止")
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
