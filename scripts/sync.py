#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sync.py — 同步适配器，把本地笔记与远端保持一致。
后端由 vault.config.json 的 "backend" 决定：local / git / http。
数据真相源永远是本地 projects/*.md 文件；index/ 是派生产物，pull 后本地重建。

用法:
    python sync.py pull     # 先拉取最新（多机防冲突），并重建索引
    python sync.py push     # 提交并推送本地改动到远端
"""
import json
import os
import subprocess
import sys

# Windows 默认控制台编码可能是 GBK，重设为 UTF-8 避免中文乱码 / UnicodeEncodeError
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(REPO_ROOT, "vault.config.json")
BUILD_INDEX = os.path.join(REPO_ROOT, "scripts", "build_index.py")


def load_config():
    if not os.path.exists(CONFIG_PATH):
        print("[sync] 未找到 vault.config.json，回退到 local 后端。"
              "（可复制 vault.config.example.json 并按需修改）", file=sys.stderr)
        return {"backend": "local", "machine_id": "unknown"}
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def run(cmd, check=True):
    print(f"[sync] $ {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=REPO_ROOT)
    if check and result.returncode != 0:
        raise SystemExit(f"[sync] 命令失败（退出码 {result.returncode}）: {' '.join(cmd)}")
    return result.returncode


def rebuild_index():
    run([sys.executable, BUILD_INDEX])


# ---------- local ----------
def local_pull(cfg):
    rebuild_index()


def local_push(cfg):
    print("[sync] local 后端：无远端可推送，仅本地保存。")


# ---------- git ----------
def git_pull(cfg):
    g = cfg.get("git", {})
    remote = g.get("remote", "origin")
    branch = g.get("branch", "main")
    # 没有配置远端时跳过拉取，只重建索引
    code = subprocess.run(["git", "remote"], cwd=REPO_ROOT,
                          capture_output=True, text=True).stdout
    if remote in code.split():
        run(["git", "pull", "--rebase", remote, branch], check=False)
    else:
        print(f"[sync] 未配置远端 '{remote}'，跳过拉取（仅本地 + 重建索引）。")
    rebuild_index()


def git_push(cfg):
    g = cfg.get("git", {})
    remote = g.get("remote", "origin")
    branch = g.get("branch", "main")
    machine = cfg.get("machine_id", "unknown")
    run(["git", "add", "-A"])  # .gitignore 会自动排除 index/ 和 vault.config.json
    # 没有改动则不提交
    code = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=REPO_ROOT).returncode
    if code == 0:
        print("[sync] 无待提交改动。")
    else:
        run(["git", "commit", "-m", f"vault: update from {machine}"])
    if g.get("auto_push", True):
        remotes = subprocess.run(["git", "remote"], cwd=REPO_ROOT,
                                 capture_output=True, text=True).stdout.split()
        if remote in remotes:
            run(["git", "push", remote, branch], check=False)
        else:
            print(f"[sync] 未配置远端 '{remote}'，跳过推送。"
                  f"（git remote add {remote} <url> 后即可推送）")


# ---------- http (Phase 3：待云主机就绪后补全) ----------
def http_pull(cfg):
    raise NotImplementedError(
        "http 后端尚未实现（Phase 3）。待你提供云主机 IP 后，"
        "在云端部署 HTTP 服务并在此实现 GET /projects 拉取。")


def http_push(cfg):
    # TODO(Phase 3): 读取 projects/*.md，POST 到 cfg['http']['endpoint'] /projects，
    # 带上 cfg['http']['token'] 鉴权。云端落盘存文件（文件仍是真相源）。
    raise NotImplementedError(
        "http 后端尚未实现（Phase 3）。待你提供云主机 IP 后，"
        "在此实现 POST {endpoint}/projects 上传。")


BACKENDS = {
    "local": (local_pull, local_push),
    "git": (git_pull, git_push),
    "http": (http_pull, http_push),
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ("pull", "push"):
        print(__doc__)
        raise SystemExit(1)
    action = sys.argv[1]
    cfg = load_config()
    backend = cfg.get("backend", "local")
    if backend not in BACKENDS:
        raise SystemExit(f"[sync] 未知后端 '{backend}'，可选：local / git / http")
    pull_fn, push_fn = BACKENDS[backend]
    (pull_fn if action == "pull" else push_fn)(cfg)
    print(f"[sync] {action} 完成（后端：{backend}）")


if __name__ == "__main__":
    main()
