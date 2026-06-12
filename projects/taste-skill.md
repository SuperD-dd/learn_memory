---
name: taste-skill
url: https://github.com/Leonxlnx/taste-skill
language: Shell
category: AI-Agent
tags: [claude-code, agent-skill, frontend, ui-design, vercel, prompt-engineering]
stars: 42.2k
status: learned
rating: 5
date: 2026-06-13
---

# taste-skill

> 「给 AI agent 用的反垃圾(Anti-Slop)前端框架」：一套可移植的 agent 技能，让 AI 生成的界面在布局、排版、动效、留白上更有品味。

## 核心功能 / 亮点
- **可调设计旋钮**：`VARIANCE`（多样性）、`MOTION_INTENSITY`（动效强度）、`VISUAL_DENSITY`（视觉密度）等参数控制风格
- **多风格变体**：default v2 / v1 legacy / GPT 优化版 / minimalist / brutalist / soft 等
- **图像生成技能**：先生成 web/mobile/品牌套件设计参考图，再 image-to-code 落地
- **框架无关**：输出可用于 React / Vue / Svelte
- **两类流程**：greenfield 新建 + redesign（对现有项目做设计审计改造）
- **一键安装**：`npx skills add ...` CLI 分发

## 技术栈
- 以 Shell + 技能描述（prompt/markdown）为主；属于 Vercel 的 agent-skills 框架生态
- 支持的 agent：**Claude Code**、Cursor、Codex；图像侧接 ChatGPT Images。MIT 协议

## 适用场景
- 让编码 agent 产出的前端更精致，摆脱「千篇一律的 AI 味」
- 给现有项目做 UI 升级/重设计
- 图像优先工作流：先出设计参考再实现

## 关键启发 / 可借鉴点
- **与我们自建的 project-vault skill 同属「Claude Code Skill」玩法**：是研究「如何组织/分发 agent 技能」的极佳范本（`npx skills add` 的安装分发方式值得借鉴）
- 「把审美做成可调参数（旋钮）」的思路：把模糊的「好看」拆成 VARIANCE/MOTION/DENSITY 等可控维度，是提示工程的好范式
- 42.2k stars 说明「提升 AI 输出质感」是真痛点——若以后做机器人配套的 Web 控制台/仪表盘，可直接用它提质

## 相关项目
- [[vercel-agent-skills]]
