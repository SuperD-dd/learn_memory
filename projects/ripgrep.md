---
name: ripgrep
url: https://github.com/BurntSushi/ripgrep
language: Rust
category: CLI-Tool
tags: [search, regex, cli]
stars: 48k
status: learned
rating: 5
date: 2026-06-10
---

# ripgrep

> 极快的命令行文本搜索工具（rg），按行递归搜目录，默认尊重 .gitignore。

## 核心功能 / 亮点
- 速度极快：基于 Rust 正则引擎，自动并行 + 智能跳过忽略文件
- 默认体验好：自动忽略二进制、隐藏文件、.gitignore 条目
- 丰富过滤：按文件类型、glob、多行模式搜索

## 技术栈
- Rust；核心依赖自研 regex crate、ignore crate

## 适用场景
- 大代码库里快速找符号/字符串，替代 grep/ack/ag
- CI 或脚本里做高性能批量匹配

## 关键启发 / 可借鉴点
- 「默认就对」的设计：尊重 .gitignore 是体验关键
- Rust 在 CLI 工具领域的性能 + 单文件分发优势

## 相关项目
- [[fd]]
