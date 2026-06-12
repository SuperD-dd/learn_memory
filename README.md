# project-vault — 个人项目收藏知识库

把你浏览/学习过的项目（GitHub 仓库、工具、框架）沉淀成结构化、可多维检索的 Markdown 知识库。
和 Claude 一起学习完一个项目后，由 Claude 负责把它存好、归类、更新索引并同步。

这是一个**正式的 Claude Code Skill**：仓库本身就是 skill 目录，放在
`~/.claude/skills/project-vault/`，Claude 会在你说「保存这个项目 / 找我收藏的某类项目」时自动激活。

## 目录结构

```
project-vault/
├── SKILL.md                  # 技能说明 + 保存/检索工作流（Claude 读这个）
├── projects/                 # 真相源：每个项目一个 .md
│   └── _TEMPLATE.md          # 笔记模板
├── index/                    # 自动生成的目录页（git 忽略，本地重建）
├── scripts/
│   ├── build_index.py        # 生成多维索引（仅标准库）
│   └── sync.py               # 同步：local / git / http
├── vault.config.json         # 本机配置（git 忽略，从 example 复制）
├── vault.config.example.json
└── .gitignore
```

数据按 **frontmatter 元数据**（语言/分类/标签）组织，而非文件夹层级，因此一个项目可同时
出现在「Python」「LLM-Framework」「agent」等多个索引视图里。`index/` 是派生产物，不入库。

## 快速开始（单机）

```bash
# 1. 复制配置（默认 local 后端，单机即用）
cp vault.config.example.json vault.config.json   # 然后把 machine_id 改成本机名

# 2. 生成索引
python scripts/build_index.py

# 3. 浏览
#   index/vault.html      ★ 网页浏览器：搜索 + 语言/分类/标签筛选 + 点开看完整笔记（双击打开即可）
#   index/INDEX.md        全部（按日期）
#   index/by-language.md  按语言
#   index/by-category.md  按功能分类
#   index/by-tag.md       按标签
```

保存新项目：直接对 Claude 说「保存这个项目 <url>」，它会按 `SKILL.md` 的工作流建笔记、归类、
重建索引并同步。

## 多机共享（git 后端）

1. 在本机仓库执行 `git init`（首次）并提交。
2. 建一个**私有**远程库（GitHub 私有仓库 / 自建 Gitea），
   `git remote add origin <url>` 后 `git push -u origin main`。
3. 把 `vault.config.json` 的 `backend` 改成 `"git"`。
4. **新机器部署**：
   ```bash
   git clone <url> ~/.claude/skills/project-vault
   cd ~/.claude/skills/project-vault
   cp vault.config.example.json vault.config.json   # backend 设为 git，改 machine_id
   python scripts/build_index.py
   ```
   即同时获得技能与全部历史笔记。之后各机靠 `sync.py pull/push` 保持一致。

> 迁移 = 换机器只需 `git clone` 这一个仓库；不存在数据格式转换。

## 上云（http 后端，Phase 3）✅ 已就绪

云端服务 `server/vault_server.py`（仅标准库）+ `sync.py` 的 `http` 适配器已完成并通过自测。
定位是「额外的云端备份/中转」，文件仍是真相源；与 `git` 后端可并存。

1. 在云主机（装好 Python 3 即可，无需 pip）启动服务并设令牌——详见 `server/README.md`。
2. 在本机 `vault.config.json` 把 `backend` 改成 `"http"`，
   `http.endpoint` 填 `http://你的云主机IP:8000`、`http.token` 填与服务端一致的令牌。
3. `python scripts/sync.py push`（本地→云端）/ `pull`（云端→本地）。

> `endpoint` 还是 `http://<cloud-ip>:8000` 占位时，`sync.py` 会直接提示你去填，不会瞎连。
> 自测：`python server/_roundtrip_test.py`。

## 依赖

- Python 3（仅标准库，无需 pip 安装）
- git（仅 `git` 后端需要）
