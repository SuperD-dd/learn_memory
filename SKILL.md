---
name: project-vault
description: >-
  个人项目收藏知识库。当用户想保存/收藏一个浏览或学习过的项目（GitHub 仓库、工具、框架等），
  或想回顾/检索「我看过哪些项目」「有没有做 X 的项目」「按语言/分类找项目」时使用。
  与用户一起学习完一个项目后，负责把它存成结构化 Markdown 笔记并更新多维索引。
  触发词示例：保存这个项目、收藏这个 repo、记一下这个库、我之前看过哪些项目、
  找一下我收藏的 Rust 项目、有没有做 agent 的项目。
---

# project-vault — 项目收藏知识库技能

帮用户把浏览/学习过的项目沉淀成可检索的知识库。数据是本仓库 `projects/` 下的 Markdown 文件
（每个项目一个 `.md`，frontmatter 存元数据），`index/` 是脚本自动生成的多维目录页。

本技能仓库本身就是一个 git 仓库，克隆到任意机器的 `~/.claude/skills/project-vault/` 即可复用，
笔记数据随仓库一起同步。**所有脚本仅依赖 Python 标准库。**

---

## 何时触发

- 用户说「保存/收藏这个项目」，或你们刚一起分析/学习完一个项目 → 执行**保存工作流**
- 用户问「我看过哪些项目 / 找某类项目 / 按语言或分类浏览」 → 执行**检索工作流**

---

## 保存工作流（学习完一个项目后执行）

> 目标：把项目存成 `projects/<slug>.md`，更新索引，并同步到远端。

1. **先拉取最新**（多机防冲突）：
   ```
   python scripts/sync.py pull
   ```
2. **确定 slug**：用 `owner-repo` 的 kebab-case 形式（如 `langchain-ai-langchain`），
   或项目短名（如 `langchain`）。文件名即 `projects/<slug>.md`。
3. **复制模板**：以 `projects/_TEMPLATE.md` 为蓝本创建 `projects/<slug>.md`。
4. **填写内容**（中英混合：正文中文，技术术语/标签用英文）：
   - frontmatter：`name / url / language / category / tags / stars? / status / rating / date`
     - `language`：主要语言，英文单值（Python / Rust / TypeScript / Go / C++ / C# …）
     - `category`：从下方**受控词表**取一个；都不合适才用 `Other` 并考虑提议扩充词表
     - `tags`：英文小写自由标签，可多个，如 `[agent, RAG, orchestration]`
     - `date`：今天日期（YYYY-MM-DD）
     - `rating`：你和用户对其价值的主观评分 1-5
   - 正文：一句话简介（`>` 引用，会被索引抓取）/ 核心功能·亮点 / 技术栈 / 适用场景 /
     关键启发·可借鉴点 / 相关项目（用 `[[slug]]` 互链已有项目）
5. **重建索引**：
   ```
   python scripts/build_index.py
   ```
6. **同步到远端**：
   ```
   python scripts/sync.py push
   ```
7. **向用户报告**：存到了哪个文件、归入哪个语言/分类/标签、索引与远端是否已更新。

> 第 1 步和第 6 步在 `local` 后端下是「重建索引 / 无远端」的安全空操作，单机也能照常跑全流程。

---

## 检索工作流（回顾已收藏项目）

- 想总览：读 `index/INDEX.md`（按日期）。
- 按语言找：读 `index/by-language.md`。按功能找：`index/by-category.md`。按标签：`index/by-tag.md`。
- 若索引可能过期，先 `python scripts/build_index.py` 重建再读。
- 找具体项目：直接读 `projects/<slug>.md`。也可用 `grep` 在 `projects/` 里按关键词搜正文/标签。

---

## 功能分类受控词表（category）

保持分类稳定、可比较。初始词表（可按需扩充，扩充时同步更新本表）：

```
LLM-Framework, AI-Agent, Web-Framework, Frontend-UI, CLI-Tool, DevOps,
Database, Data-Pipeline, ML-Model, Infra, Security, Mobile, GameDev,
Learning-Resource, Other
```

---

## 配置与同步后端

`vault.config.json`（每台机器各一份，已被 git 忽略）的 `backend` 决定同步方式：

- `local`：纯本地，`pull/push` 仅重建索引、不联网。**默认，单机即用。**
- `git`：多机共享。各机 clone 同一远程库，`pull` = `git pull --rebase` + 重建索引，
  `push` = 提交并 `git push`。需先 `git remote add origin <url>`。
- `http`：云端备份/中转。对接 `server/vault_server.py`，`push/pull` 走 HTTP 上传/下载。
  需在 `http.endpoint` 填云主机地址、`http.token` 填令牌（详见 `server/README.md`）。

没有 `vault.config.json` 时自动回退 `local`。配置模板见 `vault.config.example.json`。

---

## 批量导入：学习周刊归档

`scripts/import_eryajf.py` 把 eryajf 学习周刊(wiki.eryajf.net)推荐的项目批量导入为**轻量归档笔记**：frontmatter 带 `via: eryajf-weekly` + `status: archived`，语言/分类用关键词推断，正文为周刊原描述 + 来源期号。它**保护手动精选笔记**（同名或同 URL 的非 archived 笔记不覆盖）。先 `--dry-run` 看量级再正式跑；正式跑只重建索引，**不自动 push**。

`build_index.py` 据 `via/status` 派生「来源」维度：**精选**(手动) vs **归档**(批量)，`vault.html` 顶栏可按来源筛选，并生成 `index/by-source.md`。日常「一起学一个 → 中等笔记」的项目即「精选」，无需特殊处理。

## 设计约定（勿违背）

- **文件是唯一真相源**；`index/` 与 `vault.config.json` 是派生/本机数据，**已 git 忽略**，不要提交。
- 分类信息只放在每个文件的 frontmatter，不靠文件夹层级——一个项目可同时属于多语言/分类/标签维度。
- 新增/修改后务必跑 `build_index.py`，让索引与数据一致。
