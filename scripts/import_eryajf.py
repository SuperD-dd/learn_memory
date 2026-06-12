#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
import_eryajf.py — 一次性/可重跑：把 eryajf「学习周刊」(wiki.eryajf.net) 推荐的
GitHub 项目批量导入 project-vault，存为轻量「归档」笔记（via: eryajf-weekly）。
仅标准库。不抓单个 GitHub repo；元数据用关键词推断。

枚举：sitemap.xml → 多线程抓每页 → <title> 命中「学习周刊-总第N期」且发布年在范围内。
解析：每个项目 = <li>项目地址：<a github>名称</a> + <li>项目说明：描述。
保护：已存在且非 archived 的「精选」笔记绝不覆盖。

用法:
    python import_eryajf.py --dry-run                 # 全量统计，不写文件（先跑这个）
    python import_eryajf.py                           # 正式写入 + 重建索引（不 push）
    python import_eryajf.py --only <issue-url> --dry-run   # 单期调试
    python import_eryajf.py --year-min 2026           # 缩范围
选项: --workers N  --no-index
"""
import argparse
import html as htmllib
import os
import re
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECTS_DIR = os.path.join(REPO_ROOT, "projects")
BUILD_INDEX = os.path.join(REPO_ROOT, "scripts", "build_index.py")
SITEMAP = "https://wiki.eryajf.net/sitemap.xml"
UA = {"User-Agent": "Mozilla/5.0 (project-vault import)"}

# 注意：侧边栏里每页都含「学习周刊-总第N期」文本，必须只看本页 <title> 标签判定，
# 否则会把所有页面都误判成周刊、且抓到侧边栏最新一期的编号。
TITLE_TAG = re.compile(r"<title>(.*?)</title>", re.S)
ISSUE = re.compile(r"学习周刊-总第(\d+)期")
PUB = re.compile(r'article:published_time" content="(\d{4})-(\d{2})-(\d{2})')
PROJ = re.compile(
    r"项目地址[：:]\s*<a href=\"(https://github\.com/[^\"]+)\"[^>]*>([^<]+)<.*?项目说明[：:]\s*(.*?)</li>",
    re.S,
)
# 噪声：周刊自身仓库与站点主题
BLACKLIST = {"eryajf/learning-weekly", "xugaoyi/vuepress-theme-vdoing"}

# ── 关键词推断（best-effort）。键命中即取值；按顺序，先命中先用。──
LANG_RULES = [
    ("Rust", ["rust"]),
    ("Go", ["golang", "go 语言", "go语言", "go 编写", "go 开发", "go 实现", "基于 go", "gin 框架"]),
    ("Python", ["python", "django", "flask", "fastapi"]),
    ("TypeScript", ["typescript", "javascript", "node.js", "nodejs", "vue", "react",
                    "next.js", "nuxt", "electron", "tauri", "前端"]),
    ("Java", ["springboot", "spring boot", " java ", "java 开发", "jvm"]),
    ("C++", ["c++", "cpp"]),
    ("Shell", ["shell 脚本", "bash 脚本"]),
    ("PHP", ["php"]),
]
CATEGORY_RULES = [
    ("LLM-Framework", ["大模型", "大语言模型", " llm", "提示词", "prompt"]),
    ("AI-Agent", ["agent", "智能体", "ai 助手", "智能助手", "rag"]),
    ("ML-Model", ["机器学习", "深度学习", "人工智能", "神经网络", "模型训练"]),
    ("DevOps", ["运维", "部署", "ci/cd", "kubernetes", "k8s", "docker", "容器",
                "监控", "调度", "cron", "定时任务", "日志"]),
    ("Database", ["数据库", "sql", "存储引擎", "向量库", "表格", "kv 存储"]),
    ("Security", ["安全", "加密", "渗透", "漏洞", "防火墙", "密码管理", "审计"]),
    ("Frontend-UI", ["前端", "ui 组件", "界面", "组件库", "插件", "主题", "可视化", "网页", "浏览器扩展"]),
    ("CLI-Tool", ["命令行", "cli", "终端", "tui"]),
    ("Mobile", ["android", "ios", "移动端", "app "]),
    ("Infra", ["网关", "代理", "网络", "中间件", "分布式", "消息队列", "服务发现"]),
    ("Web-Framework", ["web 框架", "后端框架", "全栈框架"]),
    ("Learning-Resource", ["教程", "面试", "学习资料", "文档站", "知识库", "awesome", "书籍"]),
]
TAG_KEYWORDS = ["go", "rust", "python", "vue", "react", "typescript", "node",
                "docker", "kubernetes", "k8s", "ai", "llm", "agent", "rag", "cli",
                "数据库", "监控", "运维", "安全", "前端", "插件", "自托管", "self-hosted"]


def get(url, tries=3):
    last = None
    for _ in range(tries):
        try:
            return urllib.request.urlopen(
                urllib.request.Request(url, headers=UA), timeout=25
            ).read().decode("utf-8", "replace")
        except Exception as e:          # 并发下偶发超时，重试几次
            last = e
    raise last


def clean_text(s):
    s = re.sub(r"<[^>]+>", "", s)          # 去标签（img/a/code…）
    s = htmllib.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


def norm_repo(url):
    """https://github.com/owner/repo/...  ->  ('owner/repo', canonical_url)"""
    m = re.match(r"https://github\.com/([^/?#]+)/([^/?#]+)", url)
    if not m:
        return None, None
    owner, repo = m.group(1), m.group(2)
    repo = repo[:-4] if repo.endswith(".git") else repo
    return f"{owner}/{repo}", f"https://github.com/{owner}/{repo}"


def slugify(ownerrepo):
    s = ownerrepo.lower().replace("/", "-")
    s = re.sub(r"[^a-z0-9._-]+", "-", s).strip("-.")
    return s or "project"


def infer(name, desc):
    hay = (name + " " + desc).lower()
    lang = next((v for v, ks in LANG_RULES if any(k in hay for k in ks)), "Unknown")
    cat = next((v for v, ks in CATEGORY_RULES if any(k in hay for k in ks)), "Other")
    tags = [k for k in TAG_KEYWORDS if k in hay][:5]
    return lang, cat, tags


# 格式 B（2026 第18-20周等）：<h2>…项目：owner/repo</h2> + 🔗地址 + 🏷️标签 + 描述段
HEAD_B = re.compile(r"<h2\b[^>]*>.*?项目[：:].*?</h2>", re.S)
GH_HREF = re.compile(r'<a href="(https://github\.com/[^"]+)"')
TAG_B = re.compile(r"标签[^：:<]*[：:]\s*([^<]+)")
PARA = re.compile(r"<p>(.*?)</p>", re.S)


def parse_format_a(html):
    out = []
    for repo_url, name, desc in PROJ.findall(html):
        ownerrepo, canon = norm_repo(repo_url)
        if not ownerrepo or ownerrepo in BLACKLIST:
            continue
        out.append({"ownerrepo": ownerrepo, "url": canon,
                    "name": name.strip(), "desc": clean_text(desc), "hint": ""})
    return out


def parse_format_b(html):
    out, starts = [], [m.start() for m in HEAD_B.finditer(html)]
    for idx, s in enumerate(starts):
        block = html[s:(starts[idx + 1] if idx + 1 < len(starts) else len(html))]
        gm = GH_HREF.search(block)
        if not gm:
            continue
        ownerrepo, canon = norm_repo(gm.group(1))
        if not ownerrepo or ownerrepo in BLACKLIST:
            continue
        tg = TAG_B.search(block)
        hint = tg.group(1).strip() if tg else ""
        desc = ""
        for pm in PARA.finditer(block):
            txt = clean_text(pm.group(1))
            if len(txt) >= 12 and "地址" not in txt and "标签" not in txt and not txt.startswith("#"):
                desc = re.sub(r"^.{0,4}简介[：:]\s*", "", txt)   # 去掉「📝 简介：」前缀
                break
        out.append({"ownerrepo": ownerrepo, "url": canon,
                    "name": ownerrepo.split("/")[-1], "desc": desc, "hint": hint})
    return out


def parse_issue(num, date, url, html):
    base = parse_format_a(html) or parse_format_b(html)
    for p in base:
        p.update(issue=num, date=date, issue_url=url)
        p.setdefault("hint", "")
    return base


# ── frontmatter 轻量读取（判断已存在笔记是否为 archived / 取 url）──
def read_meta(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            t = f.read()
    except OSError:
        return {}
    if not t.startswith("---"):
        return {}
    end = t.find("\n---", 3)
    meta = {}
    for line in t[3:end].splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            meta[k.strip()] = v.strip()
    return meta


def existing_index():
    """返回 (url->slug 已存在映射, 精选url集合)。用于跨笔记去重 + 保护精选。"""
    url2slug, curated_urls, archived_slugs = {}, set(), set()
    if not os.path.isdir(PROJECTS_DIR):
        return url2slug, curated_urls, archived_slugs
    for fn in os.listdir(PROJECTS_DIR):
        if not fn.endswith(".md") or fn.startswith("_"):
            continue
        meta = read_meta(os.path.join(PROJECTS_DIR, fn))
        u = (meta.get("url") or "").strip()
        is_archived = meta.get("via", "") == "eryajf-weekly" or meta.get("status", "") == "archived"
        if u:
            url2slug[u] = fn[:-3]
            if not is_archived:
                curated_urls.add(u)
        if is_archived:
            archived_slugs.add(fn[:-3])
    return url2slug, curated_urls, archived_slugs


def note_text(rec):
    sources = rec["sources"]            # list of (num, date, issue_url) sorted
    src_lines = "\n".join(
        f"- 学习周刊 [#{n}]({u})（{d}）" for n, d, u in sources
    )
    tags = "[" + ", ".join(rec["tags"]) + "]" if rec["tags"] else "[]"
    src_field = "；".join(f"#{n} ({d})" for n, d, u in sources)
    fm = [
        "---",
        f"name: {rec['name']}",
        f"url: {rec['url']}",
        f"language: {rec['language']}",
        f"category: {rec['category']}",
        f"tags: {tags}",
        'stars: ""',
        "status: archived",
        "rating: 0",
        f"date: {sources[0][1]}",
        "via: eryajf-weekly",
        f"source: {src_field}",
        "---",
        "",
        f"# {rec['name']}",
        "",
        f"> {rec['desc']}",
        "",
        "## 来源",
        src_lines,
        f"- GitHub：{rec['url']}",
        "",
    ]
    return "\n".join(fm)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only", action="append", help="只处理这些期 URL（可重复）")
    ap.add_argument("--year-min", type=int, default=2024)
    ap.add_argument("--year-max", type=int, default=2026)
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--no-index", action="store_true")
    args = ap.parse_args()

    # 1) 确定要解析的期 URL
    if args.only:
        issue_urls = args.only
    else:
        print("[import] 拉取 sitemap…")
        urls = re.findall(r"<loc>([^<]+)</loc>", get(SITEMAP))
        print(f"[import] sitemap 页面 {len(urls)} 个，扫描周刊期…")
        issue_urls = urls

    # 2) 抓取 + 判定周刊 + 解析项目（单次抓取复用）
    def work(u):
        try:
            t = get(u)
        except Exception as e:
            return ("ERR", u, str(e)[:40])
        tm = TITLE_TAG.search(t)
        m = ISSUE.search(tm.group(1)) if tm else None
        if not m:
            return None
        pm = PUB.search(t)
        if not pm:
            return None
        year = int(pm.group(1))
        if not (args.year_min <= year <= args.year_max):
            return None
        date = f"{pm.group(1)}-{pm.group(2)}-{pm.group(3)}"
        return ("WK", int(m.group(1)), date, u, parse_issue(int(m.group(1)), date, u, t))

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        results = list(ex.map(work, issue_urls))
    issues = [r for r in results if r and r[0] == "WK"]
    errs = [r for r in results if r and r[0] == "ERR"]
    issues.sort(key=lambda r: r[1])
    raw = sum(len(r[4]) for r in issues)
    print(f"[import] 命中周刊 {len(issues)} 期 · 抓取失败 {len(errs)} · 原始项目条目 {raw}")
    zero = [r for r in issues if not r[4]]
    if zero:
        print(f"[import] ⚠ {len(zero)} 期解析到 0 个项目（格式可能不同）：" +
              ", ".join(f"#{r[1]}" for r in zero[:12]), file=sys.stderr)

    # 3) 跨期去重（按 canonical url），合并来源，最早日期为 date
    merged = {}
    for _, num, date, u, projs in issues:
        for p in projs:
            key = p["url"]
            if key not in merged:
                lang, cat, tags = infer(p["name"], p["desc"] + " " + p.get("hint", ""))
                merged[key] = {
                    "name": p["name"], "url": p["url"], "desc": p["desc"],
                    "language": lang, "category": cat, "tags": tags,
                    "ownerrepo": p["ownerrepo"],
                    "sources": [(p["issue"], p["date"], p["issue_url"])],
                }
            else:
                merged[key]["sources"].append((p["issue"], p["date"], p["issue_url"]))
    for rec in merged.values():
        rec["sources"] = sorted(set(rec["sources"]), key=lambda s: s[1])
    print(f"[import] 去重后唯一项目 {len(merged)}")

    # 4) 写入（保护精选；跨笔记 url 去重）
    url2slug, curated_urls, _ = existing_index()
    written = skipped_curated = skipped_exist_curated = 0
    for rec in merged.values():
        if rec["url"] in curated_urls:        # 已是手动精选 → 跳过
            skipped_curated += 1
            continue
        slug = slugify(rec["ownerrepo"])
        path = os.path.join(PROJECTS_DIR, slug + ".md")
        if os.path.exists(path):
            meta = read_meta(path)
            if not (meta.get("via") == "eryajf-weekly" or meta.get("status") == "archived"):
                skipped_exist_curated += 1   # 同名精选笔记 → 保护，不覆盖
                continue
        if not args.dry_run:
            with open(path, "w", encoding="utf-8") as f:
                f.write(note_text(rec))
        written += 1

    mode = "DRY-RUN（未写文件）" if args.dry_run else "已写入"
    print(f"[import] {mode}：归档笔记 {written} 个 · "
          f"跳过(已精选收藏) {skipped_curated} · 跳过(同名精选保护) {skipped_exist_curated}")

    if not args.dry_run and not args.no_index:
        print("[import] 重建索引…")
        os.system(f'"{sys.executable}" "{BUILD_INDEX}"')
        print("[import] 完成。请人工抽查后再 `python scripts/sync.py push` 推送。")


if __name__ == "__main__":
    main()
