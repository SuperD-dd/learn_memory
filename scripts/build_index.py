#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_index.py — 扫描 projects/*.md 的 frontmatter，生成多维索引页到 index/。
仅依赖 Python 标准库，无需安装任何第三方包。
可从任意目录运行：脚本内按自身位置定位仓库根。

用法:
    python build_index.py
"""
import json
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
        meta["body"] = body.strip()
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


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>project-vault</title>
<style>
/* ── 配色：冷调近黑中性基底 + 单一琥珀强调（全页锁定），OKLCH ── */
:root{
  --bg:oklch(0.165 0.004 270);
  --surface:oklch(0.205 0.006 270);
  --surface-2:oklch(0.245 0.007 270);
  --border:oklch(0.305 0.008 270);
  --border-strong:oklch(0.40 0.01 270);
  --ink:oklch(0.965 0.004 270);
  --muted:oklch(0.74 0.008 270);
  --faint:oklch(0.60 0.008 270);
  --accent:oklch(0.80 0.13 78);
  --accent-press:oklch(0.72 0.13 78);
  --accent-ink:oklch(0.22 0.03 80);
  /* 形状：卡片 14 / 输入 10 / 胶囊 full（已锁定，全页一致） */
  --r-card:14px; --r-input:10px;
  /* 字号阶梯：克制为 4 档，拉开对比（impeccable flat-type-hierarchy 修复）*/
  --fs-cap:12px; --fs-body:14px; --fs-title:18px; --fs-display:23px;
  --font-sans:ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,"PingFang SC","Microsoft YaHei",sans-serif;
  --font-mono:ui-monospace,"SF Mono","Cascadia Code","Segoe UI Mono",Consolas,monospace;
  /* z-index 语义层级 */
  --z-sticky:100; --z-scrim:200; --z-drawer:300;
}
*{box-sizing:border-box}
html,body{margin:0}
body{
  background:var(--bg); color:var(--ink);
  font-family:var(--font-sans); font-size:var(--fs-body); line-height:1.55;
  -webkit-font-smoothing:antialiased; text-rendering:optimizeLegibility;
}
a{color:inherit}
.mono{font-family:var(--font-mono)}
::selection{background:var(--accent); color:var(--accent-ink)}

/* ── 顶栏 ── */
.topbar{
  position:sticky; top:0; z-index:var(--z-sticky);
  display:flex; align-items:center; gap:20px;
  padding:14px clamp(16px,4vw,40px);
  background:color-mix(in oklch, var(--bg) 88%, transparent);
  backdrop-filter:saturate(140%) blur(8px);
  border-bottom:1px solid var(--border);
}
.brand{display:flex; align-items:center; gap:10px; font-weight:600; letter-spacing:-0.01em; white-space:nowrap}
.brand .mark{color:var(--accent); display:flex}
.brand .tag{color:var(--faint); font-weight:500; font-size:var(--fs-cap)}
.search{position:relative; flex:1; max-width:440px}
.search svg{position:absolute; left:12px; top:50%; transform:translateY(-50%); color:var(--faint); pointer-events:none}
.search input{
  width:100%; padding:9px 12px 9px 36px;
  background:var(--surface); color:var(--ink);
  border:1px solid var(--border); border-radius:var(--r-input);
  font:inherit; outline:none; transition:border-color .15s, box-shadow .15s;
}
.search input::placeholder{color:var(--faint)}
.search input:focus{border-color:var(--accent); box-shadow:0 0 0 3px color-mix(in oklch, var(--accent) 25%, transparent)}
/* 键盘焦点环（a11y）—— 所有可交互控件可见焦点 */
.chip:focus-visible,.sort select:focus-visible,.dclose:focus-visible,.dlinks a:focus-visible,.ext:focus-visible,.tag:focus-visible,#reset:focus-visible,.tagpill button:focus-visible{outline:none; box-shadow:0 0 0 3px color-mix(in oklch,var(--accent) 32%,transparent)}
.count{margin-left:auto; color:var(--faint); font-size:var(--fs-cap); white-space:nowrap}
.count b{color:var(--ink); font-weight:600}

/* ── 工具栏 / 筛选 ── */
.toolbar{
  display:flex; flex-wrap:wrap; align-items:center; gap:16px 24px;
  padding:14px clamp(16px,4vw,40px);
  border-bottom:1px solid var(--border);
}
.fgroup{display:flex; align-items:center; gap:8px; flex-wrap:wrap}
.flabel{color:var(--faint); font-size:var(--fs-cap); letter-spacing:.02em}
.chip{
  font-family:var(--font-mono); font-size:var(--fs-cap);
  padding:5px 12px; border-radius:999px; cursor:pointer;
  background:var(--surface); color:var(--muted);
  border:1px solid var(--border); transition:.14s;
}
.chip:hover{border-color:var(--border-strong); color:var(--ink)}
.chip.active{background:var(--accent); color:var(--accent-ink); border-color:var(--accent); font-weight:600}
.chip .n{opacity:.6; margin-left:5px}
.chip.active .n{opacity:.7}
.sort{margin-left:auto; display:flex; align-items:center; gap:8px; color:var(--faint); font-size:var(--fs-cap)}
.sort select{
  font:inherit; font-size:var(--fs-body); padding:6px 10px; border-radius:var(--r-input);
  background:var(--surface); color:var(--ink); border:1px solid var(--border); outline:none; cursor:pointer;
}
.sort select:focus{border-color:var(--accent)}

.tagbar{padding:0 clamp(16px,4vw,40px); margin-top:14px}
.tagbar[hidden]{display:none}
.tagpill{
  display:inline-flex; align-items:center; gap:8px; font-family:var(--font-mono); font-size:var(--fs-cap);
  padding:5px 8px 5px 12px; border-radius:999px;
  background:color-mix(in oklch, var(--accent) 14%, var(--surface));
  border:1px solid color-mix(in oklch, var(--accent) 40%, var(--border)); color:var(--ink);
}
.tagpill button{background:none; border:none; color:var(--faint); cursor:pointer; display:flex; padding:2px; border-radius:6px}
.tagpill button:hover{color:var(--ink); background:var(--surface-2)}

/* ── 网格 / 卡片 ── */
.grid{
  display:grid; grid-template-columns:repeat(auto-fill,minmax(300px,1fr));
  gap:18px; padding:22px clamp(16px,4vw,40px) 40px;
  max-width:1320px; margin:0 auto;
}
.card{
  display:flex; flex-direction:column; gap:12px;
  background:var(--surface); border:1px solid var(--border); border-radius:var(--r-card);
  padding:18px 18px 14px; cursor:pointer;
  transition:transform .16s cubic-bezier(.2,.7,.3,1), border-color .16s, box-shadow .16s;
}
.card:hover{transform:translateY(-3px); border-color:var(--border-strong);
  box-shadow:0 12px 28px -16px oklch(0 0 0 / .8), 0 2px 6px -4px oklch(0 0 0 / .6)}
.card:focus-visible{outline:none; border-color:var(--accent); box-shadow:0 0 0 3px color-mix(in oklch,var(--accent) 25%,transparent)}
.card .top{display:flex; align-items:flex-start; justify-content:space-between; gap:10px}
.card h2{margin:0; font-size:var(--fs-title); font-weight:650; letter-spacing:-0.01em; line-height:1.25; text-wrap:balance}
.card .ext{color:var(--faint); display:flex; padding:2px; border-radius:6px; flex:none; margin:-2px}
.card .ext:hover{color:var(--accent); background:var(--surface-2)}
.metarow{display:flex; align-items:center; gap:10px; flex-wrap:wrap; font-family:var(--font-mono); font-size:var(--fs-cap); color:var(--muted)}
.lang{color:var(--ink)}
.stars{color:var(--accent); letter-spacing:1px}
.kind{color:var(--faint)}
.kind::before{content:"·"; margin-right:10px; color:var(--border-strong)}
.summary{margin:0; color:var(--muted); font-size:var(--fs-body); line-height:1.5;
  display:-webkit-box; -webkit-line-clamp:3; -webkit-box-orient:vertical; overflow:hidden}
.tags{display:flex; flex-wrap:wrap; gap:6px}
.tag{font-family:var(--font-mono); font-size:var(--fs-cap); color:var(--faint);
  padding:2px 8px; border-radius:999px; border:1px solid var(--border); transition:.14s}
.tag:hover{color:var(--accent); border-color:color-mix(in oklch,var(--accent) 45%,var(--border))}
.cardfoot{margin-top:2px; padding-top:11px; border-top:1px solid var(--border);
  display:flex; justify-content:space-between; font-family:var(--font-mono); font-size:var(--fs-cap); color:var(--faint)}

/* ── 空状态 ── */
.empty{display:none; flex-direction:column; align-items:center; gap:14px; padding:80px 20px; text-align:center; color:var(--muted)}
.empty[data-show]{display:flex}
.empty .big{font-size:var(--fs-title); color:var(--ink); font-weight:600}
.empty button{font:inherit; padding:8px 16px; border-radius:999px; cursor:pointer;
  background:var(--accent); color:var(--accent-ink); border:none; font-weight:600}

/* ── 详情抽屉 ── */
.scrim{position:fixed; inset:0; z-index:var(--z-scrim); background:oklch(0 0 0 / .55);
  opacity:0; visibility:hidden; transition:opacity .2s, visibility .2s}
.scrim[data-show]{opacity:1; visibility:visible}
.drawer{position:fixed; top:0; right:0; bottom:0; z-index:var(--z-drawer);
  width:min(580px,94vw); background:var(--surface); border-left:1px solid var(--border);
  transform:translateX(100%); transition:transform .26s cubic-bezier(.2,.7,.2,1);
  display:flex; flex-direction:column; overflow:hidden}
.drawer[data-open]{transform:translateX(0)}
.dhead{padding:22px 24px 16px; border-bottom:1px solid var(--border)}
.dhead .row{display:flex; align-items:flex-start; justify-content:space-between; gap:12px}
.dhead h2{margin:0; font-size:var(--fs-display); letter-spacing:-0.02em; text-wrap:balance}
.dclose{background:var(--surface-2); border:1px solid var(--border); color:var(--muted);
  width:32px; height:32px; border-radius:8px; cursor:pointer; display:flex; align-items:center; justify-content:center; flex:none}
.dclose:hover{color:var(--ink); border-color:var(--border-strong)}
.dmeta{display:flex; align-items:center; gap:10px; flex-wrap:wrap; margin-top:12px; font-family:var(--font-mono); font-size:var(--fs-cap); color:var(--muted)}
.dlinks{display:flex; gap:10px; margin-top:16px; flex-wrap:wrap}
.dlinks a{font-family:var(--font-mono); font-size:var(--fs-cap); text-decoration:none;
  padding:7px 13px; border-radius:999px; border:1px solid var(--border); color:var(--muted); display:inline-flex; align-items:center; gap:7px; transition:.14s}
.dlinks a.primary{background:var(--accent); color:var(--accent-ink); border-color:var(--accent); font-weight:600}
.dlinks a:not(.primary):hover{color:var(--ink); border-color:var(--border-strong)}
.dbody{padding:8px 24px 40px; overflow-y:auto}
.dbody h3{font-size:var(--fs-cap); letter-spacing:.06em; text-transform:uppercase; color:var(--accent); margin:26px 0 10px; font-weight:600}
.dbody h4{font-size:var(--fs-body); margin:18px 0 8px}
.dbody p{margin:0 0 12px; color:var(--muted); max-width:62ch}
.dbody ul{margin:0 0 14px; padding-left:18px}
.dbody li{margin:0 0 6px; color:var(--muted); max-width:62ch}
.dbody blockquote{margin:0 0 18px; padding:12px 16px; border-radius:10px;
  background:var(--surface-2); color:var(--ink); font-size:var(--fs-body); line-height:1.55}
.dbody code{font-family:var(--font-mono); font-size:var(--fs-cap); background:var(--surface-2);
  padding:1px 6px; border-radius:5px; color:var(--ink)}
.dbody strong{color:var(--ink); font-weight:650}
.dbody .wikilink{color:var(--accent); text-decoration:none; border-bottom:1px dashed color-mix(in oklch,var(--accent) 50%,transparent); cursor:pointer}
.dbody .wikilink.dead{color:var(--faint); border-bottom-style:dotted; cursor:default}

footer{padding:22px clamp(16px,4vw,40px) 40px; border-top:1px solid var(--border);
  color:var(--faint); font-family:var(--font-mono); font-size:var(--fs-cap); display:flex; flex-wrap:wrap; gap:6px 16px; justify-content:space-between}

/* ── 入场动效（低档）：只做位移，不用 opacity 门控可见性
   （否则无头渲染/隐藏标签页里 reveal 不触发会整页空白 —— impeccable 规则）── */
@media (prefers-reduced-motion:no-preference){
  @keyframes rise{from{transform:translateY(10px)} to{transform:none}}
  .card{animation:rise .42s both cubic-bezier(.2,.7,.3,1)}
}
@media (prefers-reduced-motion:reduce){
  *{animation:none !important; transition:none !important}
}
@media (max-width:560px){
  .count{display:none}
  .sort{margin-left:0}
}
</style>
</head>
<body>
<header class="topbar">
  <div class="brand">
    <span class="mark" aria-hidden="true"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><rect x="3" y="4" width="18" height="6" rx="1.5"/><rect x="3" y="13" width="18" height="6" rx="1.5"/><path d="M7 7h.01M7 16h.01"/></svg></span>
    project-vault <span class="tag mono">notes</span>
  </div>
  <div class="search">
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.2-3.2"/></svg>
    <input id="q" type="search" placeholder="搜索项目、摘要、标签…" autocomplete="off" aria-label="搜索">
  </div>
  <div class="count"><b id="shown">0</b> / <span id="total">0</span></div>
</header>

<div class="toolbar">
  <div class="fgroup"><span class="flabel mono">language</span><div id="langF" class="fgroup"></div></div>
  <div class="fgroup"><span class="flabel mono">category</span><div id="catF" class="fgroup"></div></div>
  <label class="sort mono">sort
    <select id="sort">
      <option value="date">最近收藏</option>
      <option value="rating">评分</option>
      <option value="name">名称</option>
    </select>
  </label>
</div>
<div class="tagbar" id="tagbar" hidden></div>

<main class="grid" id="grid" aria-live="polite"></main>
<div class="empty" id="empty">
  <div class="big">没有匹配的项目</div>
  <div>试试别的关键词，或清掉筛选。</div>
  <button id="reset">清除全部筛选</button>
</div>

<div class="scrim" id="scrim"></div>
<aside class="drawer" id="drawer" role="dialog" aria-modal="true" aria-label="项目详情">
  <div class="dhead">
    <div class="row"><h2 id="dname"></h2>
      <button class="dclose" id="dclose" aria-label="关闭">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9"><path d="M6 6l12 12M18 6 6 18"/></svg></button>
    </div>
    <div class="dmeta" id="dmeta"></div>
    <div class="dlinks" id="dlinks"></div>
  </div>
  <div class="dbody" id="dbody"></div>
</aside>

<footer>
  <span>由 build_index.py 生成 · 数据源 projects/*.md · 改了笔记重跑脚本即更新</span>
  <span>__STATS__</span>
</footer>

<script>
const DATA = __DATA_JSON__;
const BY_SLUG = Object.fromEntries(DATA.map(p => [p.slug, p]));
const state = { q:"", lang:"all", cat:"all", tag:null, sort:"date" };

const esc = s => String(s==null?"":s).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const stars = n => { n = Math.max(0, Math.min(5, parseInt(n)||0)); return "★".repeat(n) + "☆".repeat(5-n); };

function counts(key){
  const m = {};
  for (const p of DATA){ const v = p[key]; if(v) m[v] = (m[v]||0)+1; }
  return m;
}
function chip(label, val, dim, n){
  const active = state[dim] === val;
  return `<button class="chip${active?" active":""}" data-dim="${dim}" data-val="${esc(val)}">${esc(label)}${n!=null?`<span class="n">${n}</span>`:""}</button>`;
}
function renderFilters(){
  const lc = counts("language"), cc = counts("category");
  document.getElementById("langF").innerHTML =
    chip("All","all","lang",DATA.length) + Object.keys(lc).sort().map(l=>chip(l,l,"lang",lc[l])).join("");
  document.getElementById("catF").innerHTML =
    chip("All","all","cat",DATA.length) + Object.keys(cc).sort().map(c=>chip(c,c,"cat",cc[c])).join("");
  const tb = document.getElementById("tagbar");
  if(state.tag){ tb.hidden=false;
    tb.innerHTML = `<span class="tagpill">#${esc(state.tag)} <button id="tagclr" aria-label="清除标签筛选"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M6 6l12 12M18 6 6 18"/></svg></button></span>`;
    document.getElementById("tagclr").onclick = ()=>{ state.tag=null; render(); };
  } else tb.hidden=true;
}
function filtered(){
  const q = state.q.trim().toLowerCase();
  let list = DATA.filter(p=>{
    if(state.lang!=="all" && p.language!==state.lang) return false;
    if(state.cat!=="all" && p.category!==state.cat) return false;
    if(state.tag && !(p.tags||[]).includes(state.tag)) return false;
    if(q){
      const hay = [p.name,p.summary,p.language,p.category,(p.tags||[]).join(" ")].join(" ").toLowerCase();
      if(!hay.includes(q)) return false;
    }
    return true;
  });
  const s = state.sort;
  list.sort((a,b)=> s==="rating" ? (b.rating||0)-(a.rating||0)
    : s==="name" ? String(a.name).localeCompare(b.name)
    : String(b.date).localeCompare(String(a.date)));
  return list;
}
function card(p,i){
  const tags = (p.tags||[]).map(t=>`<span class="tag" data-tag="${esc(t)}">#${esc(t)}</span>`).join("");
  return `<article class="card" data-slug="${esc(p.slug)}" tabindex="0" style="animation-delay:${Math.min(i,12)*32}ms">
    <div class="top">
      <h2>${esc(p.name)}</h2>
      <a class="ext" href="${esc(p.url)}" target="_blank" rel="noopener" aria-label="在 GitHub 打开" data-stop>
        <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M7 17 17 7M9 7h8v8"/></svg></a>
    </div>
    <div class="metarow"><span class="lang">${esc(p.language)}</span><span class="stars" title="${p.rating}/5">${stars(p.rating)}</span><span class="kind">${esc(p.category)}</span></div>
    <p class="summary">${esc(p.summary)}</p>
    <div class="tags">${tags}</div>
    <div class="cardfoot"><span>${p.stars?("★ "+esc(p.stars)):""}</span><span>${esc(p.date)}</span></div>
  </article>`;
}
function render(){
  renderFilters();
  const list = filtered();
  document.getElementById("grid").innerHTML = list.map(card).join("");
  document.getElementById("shown").textContent = list.length;
  document.getElementById("total").textContent = DATA.length;
  document.getElementById("empty").toggleAttribute("data-show", list.length===0);
}

/* 轻量 markdown 渲染（贴合笔记模板的子集） */
function inlineMd(t){
  return esc(t)
    .replace(/\*\*(.+?)\*\*/g,"<strong>$1</strong>")
    .replace(/`([^`]+?)`/g,"<code>$1</code>")
    .replace(/\[\[([^\]]+?)\]\]/g,(m,s)=>{ const ex=BY_SLUG[s];
      return `<a class="wikilink${ex?"":" dead"}" ${ex?`data-link="${esc(s)}"`:""}>${esc(ex?ex.name:s)}</a>`; });
}
function renderMd(md){
  const lines = String(md||"").split("\n"); let html="", ul=null, bq=null;
  const flush=()=>{ if(ul){html+="<ul>"+ul+"</ul>"; ul=null;} if(bq!=null){html+="<blockquote>"+bq+"</blockquote>"; bq=null;} };
  for(let raw of lines){
    const line = raw.replace(/\s+$/,"");
    if(/^#\s/.test(line)) continue;                       // 跳过 H1（与标题重复）
    if(/^###\s/.test(line)){ flush(); html+="<h4>"+inlineMd(line.slice(4))+"</h4>"; continue; }
    if(/^##\s/.test(line)){ flush(); html+="<h3>"+inlineMd(line.slice(3))+"</h3>"; continue; }
    if(/^>\s?/.test(line)){ if(ul){html+="<ul>"+ul+"</ul>"; ul=null;} bq=(bq?bq+" ":"")+inlineMd(line.replace(/^>\s?/,"")); continue; }
    if(/^[-*]\s/.test(line)){ if(bq!=null){html+="<blockquote>"+bq+"</blockquote>"; bq=null;} ul=(ul||"")+"<li>"+inlineMd(line.slice(2))+"</li>"; continue; }
    if(line.trim()===""){ flush(); continue; }
    flush(); html+="<p>"+inlineMd(line)+"</p>";
  }
  flush(); return html;
}

const scrim=document.getElementById("scrim"), drawer=document.getElementById("drawer");
function openDrawer(slug){
  const p=BY_SLUG[slug]; if(!p) return;
  document.getElementById("dname").textContent=p.name;
  document.getElementById("dmeta").innerHTML=
    `<span class="lang" style="color:var(--ink)">${esc(p.language)}</span><span class="stars" style="color:var(--accent)">${stars(p.rating)}</span><span class="kind">${esc(p.category)}</span>${p.stars?`<span class="kind">★ ${esc(p.stars)}</span>`:""}`;
  document.getElementById("dlinks").innerHTML=
    `<a class="primary" href="${esc(p.url)}" target="_blank" rel="noopener">在 GitHub 打开 ↗</a>`+
    `<a href="../projects/${esc(p.slug)}.md" target="_blank" rel="noopener">查看原始笔记 .md</a>`;
  document.getElementById("dbody").innerHTML=renderMd(p.body);
  scrim.setAttribute("data-show",""); drawer.setAttribute("data-open","");
  document.body.style.overflow="hidden";
}
function closeDrawer(){ scrim.removeAttribute("data-show"); drawer.removeAttribute("data-open"); document.body.style.overflow=""; }

document.addEventListener("click", e=>{
  const chipEl=e.target.closest(".chip");
  if(chipEl){ const d=chipEl.dataset.dim, v=chipEl.dataset.val; state[d]=(state[d]===v?"all":v); render(); return; }
  const tagEl=e.target.closest(".tag");
  if(tagEl){ e.stopPropagation(); state.tag=tagEl.dataset.tag; render(); return; }
  if(e.target.closest("[data-stop]")) return;            // 外链：不触发卡片
  const link=e.target.closest(".wikilink[data-link]");
  if(link){ openDrawer(link.dataset.link); return; }
  const c=e.target.closest(".card");
  if(c){ openDrawer(c.dataset.slug); return; }
});
document.addEventListener("keydown", e=>{
  if(e.key==="Escape") closeDrawer();
  const c=e.target.closest&&e.target.closest(".card");
  if(c && (e.key==="Enter"||e.key===" ")){ e.preventDefault(); openDrawer(c.dataset.slug); }
});
scrim.addEventListener("click", closeDrawer);
document.getElementById("dclose").addEventListener("click", closeDrawer);
document.getElementById("q").addEventListener("input", e=>{ state.q=e.target.value; render(); });
document.getElementById("sort").addEventListener("change", e=>{ state.sort=e.target.value; render(); });
document.getElementById("reset").addEventListener("click", ()=>{ state.q=state.lang=state.cat="all"; state.q=""; state.lang="all"; state.cat="all"; state.tag=null; document.getElementById("q").value=""; render(); });

render();
</script>
</body>
</html>
"""


def build_html(projects, stats):
    fields = ("slug", "name", "url", "language", "category", "tags",
              "stars", "rating", "status", "date", "summary", "body")
    data = [{k: p.get(k, "") for k in fields} for p in projects]
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    html = HTML_TEMPLATE.replace("__DATA_JSON__", payload).replace("__STATS__", stats)
    with open(os.path.join(INDEX_DIR, "vault.html"), "w", encoding="utf-8") as f:
        f.write(html)


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
    build_html(projects, stats)

    print(f"[build_index] 已生成 4 个索引页 + vault.html · {stats}")
    if warnings:
        print(f"[build_index] {len(warnings)} 条告警：", file=sys.stderr)
        for w in warnings:
            print(f"  ⚠ {w}", file=sys.stderr)


if __name__ == "__main__":
    main()
