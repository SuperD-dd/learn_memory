#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
端到端自测：在线程里启动 vault_server，用真实的 sync.py http 适配器做一次
push（本地 projects/ -> 云端）+ pull（云端 -> 临时目录），校验内容一致。
仅标准库，运行：python server/_roundtrip_test.py
"""
import hashlib
import os
import sys
import tempfile
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import vault_server
import sync

HOST, PORT = "127.0.0.1", 8731
TOKEN = "test-token-123"


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def main():
    server_vault = tempfile.mkdtemp(prefix="vault_server_")
    pull_dir = tempfile.mkdtemp(prefix="vault_pull_")

    srv = vault_server.make_server(server_vault, TOKEN, HOST, PORT)
    threading.Thread(target=srv.serve_forever, daemon=True).start()

    cfg = {"backend": "http", "machine_id": "selftest",
           "http": {"endpoint": f"http://{HOST}:{PORT}", "token": TOKEN}}

    local_files = sorted(f for f in os.listdir(sync.PROJECTS_DIR) if f.endswith(".md"))

    # 1) push 本地 -> 云端
    sync.http_push(cfg)
    server_proj = os.path.join(server_vault, "projects")
    pushed = sorted(f for f in os.listdir(server_proj) if f.endswith(".md"))
    assert pushed == local_files, f"push 文件集不一致: {pushed} != {local_files}"
    for f in local_files:
        assert sha(os.path.join(server_proj, f)) == sha(os.path.join(sync.PROJECTS_DIR, f)), \
            f"push 内容不一致: {f}"
    print(f"[selftest] PUSH OK  ({len(pushed)} 个文件，内容哈希一致)")

    # 2) pull 云端 -> 临时目录（验证另一台机器能拿到全部）
    orig_pdir, orig_rebuild = sync.PROJECTS_DIR, sync.rebuild_index
    sync.PROJECTS_DIR = pull_dir
    sync.rebuild_index = lambda: None
    try:
        sync.http_pull(cfg)
    finally:
        sync.PROJECTS_DIR, sync.rebuild_index = orig_pdir, orig_rebuild

    pulled = sorted(f for f in os.listdir(pull_dir) if f.endswith(".md"))
    assert pulled == local_files, f"pull 文件集不一致: {pulled} != {local_files}"
    for f in local_files:
        assert sha(os.path.join(pull_dir, f)) == sha(os.path.join(orig_pdir, f)), \
            f"pull 内容不一致: {f}"
    print(f"[selftest] PULL OK  ({len(pulled)} 个文件，内容哈希一致)")

    # 3) 鉴权校验：错误 token 应被拒
    bad = {"http": {"endpoint": f"http://{HOST}:{PORT}", "token": "wrong"}}
    st, _ = sync._http_request("GET", f"http://{HOST}:{PORT}/projects", "wrong")
    assert st == 401, f"错误 token 应返回 401，实际 {st}"
    print("[selftest] AUTH OK  (错误 token 被拒 401)")

    srv.shutdown()
    print("[selftest] ✅ ALL PASS")


if __name__ == "__main__":
    main()
