# project-vault 云端服务（Phase 3）

`vault_server.py` 是一个**仅用 Python 标准库**的小服务，部署到你的云主机后，
客户端 `sync.py` 的 `http` 后端就能把项目笔记上传/拉取做云端备份。
**文件仍是真相源**：服务端把每个项目按 slug 落盘成 `<VAULT_DIR>/projects/<slug>.md`。

> 多机日常同步推荐用 `git` 后端（Phase 2）；`http` 后端定位是「额外的云端备份/中转」。
> 两者可并存：本机既 `git push` 又能定期 `http` 备份。

## 在云主机上启动

云主机只需装好 **Python 3**（无需 pip / 任何依赖）：

```bash
# 1. 拿到服务脚本（任选其一）
#    a) 直接 scp server/vault_server.py 上传，或
#    b) 在云主机 git clone 本仓库
# 2. 设定令牌与数据目录后启动
export VAULT_TOKEN="换成一串足够长的随机字符串"
export VAULT_DIR="/opt/project-vault-data"     # 笔记会存到这里的 projects/ 下
export VAULT_PORT=8000
python3 vault_server.py
# 看到：[vault_server] 监听 http://0.0.0.0:8000 ... 已启用令牌鉴权
```

后台常驻可用 systemd（示例 `/etc/systemd/system/project-vault.service`）：

```ini
[Unit]
Description=project-vault server
After=network.target

[Service]
Environment=VAULT_TOKEN=换成随机串
Environment=VAULT_DIR=/opt/project-vault-data
Environment=VAULT_PORT=8000
ExecStart=/usr/bin/python3 /opt/project-vault/server/vault_server.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now project-vault
```

记得放行安全组/防火墙的 `VAULT_PORT`。

## 客户端配置（IP 接口，后续你自己填）

在每台机器的 `vault.config.json` 里：

```json
{
  "backend": "http",
  "machine_id": "desktop-home",
  "http": {
    "endpoint": "http://你的云主机IP:8000",
    "token": "和服务端 VAULT_TOKEN 相同的串"
  }
}
```

然后：
```bash
python scripts/sync.py push    # 本地 projects/*.md -> 云端
python scripts/sync.py pull    # 云端 -> 本地，并重建索引
```

`endpoint` 仍是 `http://<cloud-ip>:8000` 占位时，`sync.py` 会直接报错提示你去填，不会瞎连。

## 接口一览

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/health` | 健康检查（无需令牌） |
| GET | `/projects` | 列出 `[{slug, sha256, bytes}]` |
| GET | `/projects/<slug>` | 取某项目 markdown 原文 |
| PUT/POST | `/projects/<slug>` | 上传/覆盖（请求体=markdown） |

鉴权：设置 `VAULT_TOKEN` 后，除 `/health` 外都需带请求头
`X-Vault-Token: <token>`（或 `Authorization: Bearer <token>`）。

## 安全建议

- **务必设 `VAULT_TOKEN`**，且走 HTTPS：生产建议在前面挂 nginx/caddy 做 TLS，
  或仅通过 SSH 隧道访问（`ssh -L 8000:localhost:8000 user@cloud`，endpoint 用 `http://localhost:8000`）。
- 令牌只存在各机 `vault.config.json`（已 git 忽略），不会进仓库。

## 自测

```bash
python server/_roundtrip_test.py   # 线程内起服务，跑 push/pull/鉴权 全链路
```
