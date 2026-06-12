---
name: LangChain
url: https://github.com/langchain-ai/langchain
language: Python
category: LLM-Framework
tags: [agent, RAG, orchestration, llm]
stars: 95k
status: learned
rating: 4
date: 2026-06-13
---

# LangChain

> 用于构建 LLM 应用的编排框架，把模型、提示、工具、检索、记忆等串成可组合的链与 agent。

## 核心功能 / 亮点
- **可组合**：Prompt / Model / Parser 等通过 LCEL（表达式语言）用 `|` 组合成链
- **Agent + Tools**：让 LLM 自主决定调用哪些工具，支持 ReAct、tool-calling 等范式
- **RAG 全家桶**：document loader、splitter、embedding、vectorstore、retriever 一条龙
- **生态广**：集成大量模型/向量库/工具，配套 LangSmith（可观测）、LangGraph（有状态图编排）

## 技术栈
- Python（亦有 JS/TS 版 langchainjs）
- 依赖各家 LLM SDK、向量数据库、嵌入模型

## 适用场景
- 快速搭 RAG 问答、知识库助手
- 需要多工具调用 / 多步推理的 agent 原型
- 想要标准化的 LLM 应用骨架，避免每次手写胶水代码

## 关键启发 / 可借鉴点
- **「一切皆可组合」的接口抽象**（Runnable 协议）值得借鉴：统一 invoke/stream/batch
- 复杂 agent 状态管理已下沉到 LangGraph —— 链式不够时用「图」建模更清晰
- 抽象多反而增加学习成本，小项目可只取其 RAG/agent 思路而非全量依赖

## 相关项目
- [[langgraph]]
