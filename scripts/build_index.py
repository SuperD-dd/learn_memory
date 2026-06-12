#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_index.py — 扫描 projects/*.md 的 frontmatter，生成多维索引页到 index/。
仅依赖 Python 标准库，无需安装任何第三方包。
可从任意目录运行：脚本内按自身位置定位仓库根。

用法:
    python build_index.py
"""
import os
import re
import sys
from collections import defaultdict

# Windows 默认控制台编码可能是 GBK，重设为 UTF-8 避免中文乱码 / UnicodeEncodeError
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECTS_DIR = os.path.join(REPO_ROOT, "projects")
INDEX_DIR = os.path.join(REPO_ROOT, "index")

REQUIRED_FIELDS = ("name", "url", "language", "category", "date")
AUTO_HEADER = "<!-- 本文件由 scripts/build_index.py 自动生成，请勿手改 -->\n"

# 去掉值后面的行内注释： 至少一个空格 + # ...（保留 "C#" 这类无空格的 #）
_COMMENT_RE = re.compile(r"\s+#.*$")


def strip_comment(value):
    return _COMMENT_RE.sub("", value).strip()


def parse_scalar(value):
    value = strip_comment(value)
    if len(value) >= 2 and value[0] in "\"'" and value[-1] == value[0]:
        value = value[1:-1]
    return value.strip()


def parse_list(value):
    # 形如 [a, b, c]
    inner = value.strip()[1:-1].strip()
    if not inner:
        return []
    return [parse_scalar(x) for x in inner.split(",") if parse_scalar(x)]


def parse_frontmatter(text):
    """返回 (meta_dict, body_str)。无 frontmatter 时返回 ({}, text)。"""
    if not text.startswith("---"):
        return {}, text
    lines = text.splitlines()
    # 找到第二个 '---'
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return {}, text
    meta = {}
    for line in lines[1:end]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, raw = line.partition(":")
        key = key.strip()
        raw = raw.strip()
        if raw.startswith("[") and raw.endswith("]"):
            meta[key] = parse_list(raw)
        else:
            meta[key] = parse_scalar(raw)
    body = "\n".join(lines[end + 1:])
    return meta, body


def extract_summary(body):
    """取正文中第一行以 '>' 开头的引用作为一句话简介。"""
    for line in body.splitlines():
        s = line.strip()
        if s.startswith(">"):
            return s.lstrip(">").strip()
    return ""


def load_projects():
    projects = []
    warnings = []
    if not os.path.isdir(PROJECTS_DIR):
        return projects, ["projects/ 目录不存在"]
    for fname in sorted(os.listdir(PROJECTS_DIR)):
        if not fname.endswith(".md") or fname.startswith("_"):
            continue
        slug = fname[:-3]
        path = os.path.join(PROJECTS_DIR, fname)
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        meta, body = parse_frontmatter(text)
        missing = [k for k in REQUIRED_FIELDS if not meta.get(k)]
        if missing:
            warnings.append(f"{fname}: 缺少必填字段 {', '.join(missing)}")
        meta.setdefault("tags", [])
        if isinstance(meta.get("tags"), str):
            meta["tags"] = [meta["tags"]]
        meta["slug"] = slug
        meta["summary"] = extract_summary(body)
        projects.append(meta)
    return projects, warnings


def entry_line(p):
    rel = f"../projects/{p['slug']}.md"
    name = p.get("name", p["slug"])
    parts = [f"- [{name}]({rel})"]
    if p.get("summary"):
        parts.append(f" — {p['summary']}")
    meta_bits = []
    if p.get("language"):
        meta_bits.append(f"`{p['language']}`")
    if p.get("rating"):
        meta_bits.append(f"⭐{p['rating']}")
    if p.get("status") and p["status"] != "learned":
        meta_bits.append(f"[{p['status']}]")
    if p.get("tags"):
        meta_bits.append(" ".join(f"#{t}" for t in p["tags"]))
    if meta_bits:
        parts.append("  ·  " + " · ".join(meta_bits))
    return "".join(parts)


def by_date_desc(projects):
    return sorted(projects, key=lambda p: (p.get("date", ""), p.get("name", "")), reverse=True)


def write_page(filename, title, lines, stats):
    path = os.path.join(INDEX_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(AUTO_HEADER)
        f.write(f"# {title}\n\n")
        f.write(stats + "\n\n")
        f.write("\n".join(lines) + "\n")


def build_flat(projects):
    lines = [entry_line(p) for p in by_date_desc(projects)]
    return lines


def build_grouped(projects, key, multi=False):
    groups = defaultdict(list)
    for p in projects:
        if multi:
            keys = p.get(key) or ["(无)"]
            for k in keys:
                groups[k].append(p)
        else:
            groups[p.get(key) or "(未分类)"].append(p)
    lines = []
    for g in sorted(groups.keys(), key=lambda s: s.lower()):
        items = by_date_desc(groups[g])
        lines.append(f"## {g}  ({len(items)})")
        lines.extend(entry_line(p) for p in items)
        lines.append("")
    return lines


def main():
    os.makedirs(INDEX_DIR, exist_ok=True)
    projects, warnings = load_projects()

    n = len(projects)
    langs = sorted({p.get("language", "") for p in projects if p.get("language")})
    cats = sorted({p.get("category", "") for p in projects if p.get("category")})
    all_tags = sorted({t for p in projects for t in p.get("tags", [])})
    stats = (f"共 {n} 个项目 · {len(langs)} 种语言 · {len(cats)} 个分类 · "
             f"{len(all_tags)} 个标签")

    write_page("INDEX.md", "全部项目（按日期）", build_flat(projects), stats)
    write_page("by-language.md", "按语言分类", build_grouped(projects, "language"), stats)
    write_page("by-category.md", "按功能分类", build_grouped(projects, "category"), stats)
    write_page("by-tag.md", "按标签分类", build_grouped(projects, "tags", multi=True), stats)

    print(f"[build_index] 已生成 4 个索引页 · {stats}")
    if warnings:
        print(f"[build_index] {len(warnings)} 条告警：", file=sys.stderr)
        for w in warnings:
            print(f"  ⚠ {w}", file=sys.stderr)


if __name__ == "__main__":
    main()
