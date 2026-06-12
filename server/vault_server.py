#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
vault_server.py — project-vault 的云端备份/中转服务（仅 Python 标准库，无第三方依赖）。
在云主机上跑它，客户端 sync.py 的 http 后端就能把 projects/*.md 上传/拉取。
文件仍是真相源：服务端只是把每个项目笔记按 slug 落盘成文件。

环境变量：
    VAULT_PORT   监听端口，默认 8000
    VAULT_HOST   监听地址，默认 0.0.0.0（对外可访问）
    VAULT_DIR    数据目录，默认 ./vault_data（笔记存到 <VAULT_DIR>/projects/）
    VAULT_TOKEN  访问令牌；设置后所有请求需带 X-Vault-Token 或 Authorization: Bearer

HTTP 接口：
    GET  /health              健康检查
    GET  /projects            列出所有项目 [{slug, sha256, bytes}]
    GET  /projects/<slug>     取某项目的 markdown 原文
    PUT  /projects/<slug>     上传/覆盖某项目（请求体 = markdown 原文）
    POST /projects/<slug>     同 PUT

启动：
    python vault_server.py
"""
import hashlib
import json
import os
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

SLUG_RE = re.compile(r"^[A-Za-z0-9._-]+$")


def projects_dir(vault_dir):
    d = os.path.join(vault_dir, "projects")
    os.makedirs(d, exist_ok=True)
    return d


def make_handler(vault_dir, token):
    pdir = projects_dir(vault_dir)

    class Handler(BaseHTTPRequestHandler):
        server_version = "project-vault/1.0"

        # ---- helpers ----
        def _send(self, code, body, ctype="application/json; charset=utf-8"):
            if isinstance(body, (dict, list)):
                body = json.dumps(body, ensure_ascii=False).encode("utf-8")
            elif isinstance(body, str):
                body = body.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

        def _authed(self):
            if not token:
                return True
            got = self.headers.get("X-Vault-Token", "")
            if not got:
                auth = self.headers.get("Authorization", "")
                if auth.startswith("Bearer "):
                    got = auth[7:]
            return got == token

        def _slug_path(self, slug):
            if not SLUG_RE.match(slug):
                return None
            return os.path.join(pdir, slug + ".md")

        def log_message(self, fmt, *args):
            sys.stderr.write("[vault_server] %s - %s\n" % (self.address_string(), fmt % args))

        # ---- routing ----
        def do_GET(self):
            if self.path == "/health":
                slugs = [f[:-3] for f in os.listdir(pdir) if f.endswith(".md")]
                return self._send(200, {"status": "ok", "count": len(slugs)})
            if not self._authed():
                return self._send(401, {"error": "unauthorized"})
            if self.path == "/projects":
                items = []
                for f in sorted(os.listdir(pdir)):
                    if not f.endswith(".md"):
                        continue
                    raw = open(os.path.join(pdir, f), "rb").read()
                    items.append({"slug": f[:-3],
                                  "sha256": hashlib.sha256(raw).hexdigest(),
                                  "bytes": len(raw)})
                return self._send(200, {"projects": items})
            if self.path.startswith("/projects/"):
                slug = self.path[len("/projects/"):]
                path = self._slug_path(slug)
                if path is None:
                    return self._send(400, {"error": "bad slug"})
                if not os.path.exists(path):
                    return self._send(404, {"error": "not found"})
                return self._send(200, open(path, "rb").read(),
                                  ctype="text/markdown; charset=utf-8")
            return self._send(404, {"error": "no route"})

        def _do_write(self):
            if not self._authed():
                return self._send(401, {"error": "unauthorized"})
            if not self.path.startswith("/projects/"):
                return self._send(404, {"error": "no route"})
            slug = self.path[len("/projects/"):]
            path = self._slug_path(slug)
            if path is None:
                return self._send(400, {"error": "bad slug"})
            length = int(self.headers.get("Content-Length", 0))
            data = self.rfile.read(length) if length else b""
            with open(path, "wb") as f:
                f.write(data)
            return self._send(200, {"slug": slug, "bytes": len(data)})

        do_PUT = _do_write
        do_POST = _do_write

    return Handler


def make_server(vault_dir, token, host="0.0.0.0", port=8000):
    handler = make_handler(vault_dir, token)
    return ThreadingHTTPServer((host, port), handler)


def main():
    port = int(os.environ.get("VAULT_PORT", "8000"))
    host = os.environ.get("VAULT_HOST", "0.0.0.0")
    vault_dir = os.environ.get("VAULT_DIR", os.path.join(os.getcwd(), "vault_data"))
    token = os.environ.get("VAULT_TOKEN", "")
    srv = make_server(vault_dir, token, host, port)
    auth = "已启用令牌鉴权" if token else "⚠ 未设置 VAULT_TOKEN（无鉴权，仅建议内网/隧道使用）"
    print(f"[vault_server] 监听 http://{host}:{port}  数据目录={vault_dir}  {auth}")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n[vault_server] 已停止")


if __name__ == "__main__":
    main()
