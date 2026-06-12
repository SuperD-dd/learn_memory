---
name: Impeccable
url: https://github.com/pbakaus/impeccable
language: JavaScript
category: AI-Agent
tags: [claude-code, agent-skill, frontend, ui-design, design-system, cli, linter]
stars: 37.8k
status: learned
rating: 5
date: 2026-06-13
---

# Impeccable

> 「让你的 AI harness 更懂设计的设计语言」：给 AI 编码 agent 的前端设计指导系统，含命令、可确定性运行的规则检测和浏览器实时迭代。

## 核心功能 / 亮点
- **23 个设计命令**：`/impeccable audit`、`polish`、`critique`、`animate` 等，覆盖 shape→build→polish→ship 全流程
- **41 条确定性反模式规则**：是真正的规则检测器，**无需 LLM / API key 也能跑**（纯静态扫描）
- **一次性初始化**：生成 `PRODUCT.md` 和 `DESIGN.md` 沉淀产品/设计语言
- **浏览器实时迭代**：live iteration 模式边改边看
- **独立 CLI**：可扫描目录 / HTML 文件 / URL；`npx impeccable skills install` 安装

## 技术栈
- JavaScript 为主（含 CSS/Astro/HTML/TS/Svelte）；Apache 2.0
- 由 Paul Bakaus 开发，**脱胎于 Anthropic 的 frontend-design skill**
- 支持 11+ agent：**Claude Code**、Cursor、OpenCode、Gemini CLI、GitHub Copilot 等

## 适用场景
- AI 辅助前端开发中做设计质量把关（ship 前体检）
- 把通用 SaaS 模板改造成有品牌感的界面
- 想要「可复现、不靠模型也能查」的设计 lint

## 关键启发 / 可借鉴点
- **与 [[taste-skill]] 是同一赛道的强竞品**，但定位有别：
  - taste-skill 偏「生成更有品味的 UI（可调审美旋钮）」
  - Impeccable 偏「**确定性规则检测 + 命令化流程**」，41 条规则不依赖 LLM 是最大差异点 → 可复现、可进 CI
- 「把设计规范沉淀成 `PRODUCT.md` / `DESIGN.md`」的做法，和我们 project-vault 用 frontmatter+文件沉淀知识同源——**用文件固化标准**是好范式
- 若做机器人 Web 控制台：taste-skill 负责出彩、Impeccable 负责守底线（lint），二者可互补

## 相关项目
- [[taste-skill]]
- [[anthropic-frontend-design-skill]]
