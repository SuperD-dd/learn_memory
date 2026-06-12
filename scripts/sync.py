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
import urllib.error
import urllib.request

# Windows 默认控制台编码可能是 GBK，重设为 UTF-8 避免中文乱码 / UnicodeEncodeError
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# 允许用环境变量覆盖配置路径（便于测试/多 vault），默认仓库根的 vault.config.json
CONFIG_PATH = os.environ.get("VAULT_CONFIG", os.path.join(REPO_ROOT, "vault.config.json"))
PROJECTS_DIR = os.path.join(REPO_ROOT, "projects")
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


def git_identity_ok():
    for key in ("user.name", "user.email"):
        val = subprocess.run(["git", "config", key], cwd=REPO_ROOT,
                             capture_output=True, text=True).stdout.strip()
        if not val:
            return False
    return True


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
    elif not git_identity_ok():
        print("[sync] 本机未配置 git 身份，无法提交。请先运行一次：\n"
              '        git config --global user.name "你的名字"\n'
              '        git config --global user.email "你的邮箱"\n'
              "      （改动已暂存，配置后重跑 sync.py push 即可提交）", file=sys.stderr)
        return
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


# ---------- http（云端备份/中转，对接 server/vault_server.py） ----------
def _http_endpoint(cfg):
    h = cfg.get("http", {})
    endpoint = (h.get("endpoint") or "").rstrip("/")
    if not endpoint or "<" in endpoint:
        raise SystemExit(
            "[sync] http 后端未配置好：请在 vault.config.json 的 http.endpoint "
            "填入你的云主机地址，如 http://1.2.3.4:8000")
    return endpoint, h.get("token") or ""


def _http_request(method, url, token, data=None, ctype="text/markdown; charset=utf-8"):
    req = urllib.request.Request(url, data=data, method=method)
    if token:
        req.add_header("X-Vault-Token", token)
    if data is not None:
        req.add_header("Content-Type", ctype)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except urllib.error.URLError as e:
        raise SystemExit(f"[sync] 无法连接云端 {url}：{e.reason}")


def http_push(cfg):
    endpoint, token = _http_endpoint(cfg)
    files = sorted(f for f in os.listdir(PROJECTS_DIR) if f.endswith(".md"))
    ok = 0
    for fname in files:
        slug = fname[:-3]
        data = open(os.path.join(PROJECTS_DIR, fname), "rb").read()
        status, body = _http_request("PUT", f"{endpoint}/projects/{slug}", token, data=data)
        if status == 200:
            ok += 1
        else:
            print(f"[sync] 上传 {slug} 失败：HTTP {status} {body[:120]!r}", file=sys.stderr)
    print(f"[sync] 已上传 {ok}/{len(files)} 个项目到 {endpoint}")


def http_pull(cfg):
    endpoint, token = _http_endpoint(cfg)
    status, body = _http_request("GET", f"{endpoint}/projects", token)
    if status != 200:
        raise SystemExit(f"[sync] 拉取列表失败：HTTP {status} {body[:120]!r}")
    slugs = [p["slug"] for p in json.loads(body).get("projects", [])]
    os.makedirs(PROJECTS_DIR, exist_ok=True)
    got = 0
    for slug in slugs:
        st, content = _http_request("GET", f"{endpoint}/projects/{slug}", token)
        if st == 200:
            with open(os.path.join(PROJECTS_DIR, slug + ".md"), "wb") as f:
                f.write(content)
            got += 1
        else:
            print(f"[sync] 下载 {slug} 失败：HTTP {st}", file=sys.stderr)
    print(f"[sync] 已从 {endpoint} 拉取 {got}/{len(slugs)} 个项目")
    rebuild_index()


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
