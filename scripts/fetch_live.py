# -*- coding: utf-8 -*-
"""GitHub 资源雷达 · 实时数据抓取（供 GitHub Actions 定时运行）。

产出 assets/live.json，结构与前端内嵌 DATA 完全一致：
  updated_at, source, trending_daily, trending_weekly,
  top_stars, newest, categories{texts,ai,dev,life,finance}, growth_7d

数据源：
  - GitHub Search API（用 GITHUB_TOKEN 认证，限流 5000/h）
  - GitHub Trending 页面（日榜 / 周榜，无官方 API，直接抓 HTML）
  - 中文简介：translate.py 降级链（免密钥）
"""
import io
import os
import re
import sys
import json
import time
import datetime
import urllib.parse
import urllib.request
import urllib.error

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from translate import Translator  # noqa: E402

TOKEN = os.environ.get("GITHUB_TOKEN", "").strip()
UA = {"User-Agent": "GitHubRadar/1.0 (+https://github.com/Davin-96/github-radar-signal)",
      "Accept": "application/vnd.github+json"}
if TOKEN:
    UA["Authorization"] = "Bearer " + TOKEN

OUTFILE = os.path.join(ROOT, "assets", "live.json")
SLIMFILE = os.path.join(ROOT, "assets", "data_slim.json")
TIMEOUT = 30
RETRIES = 3


def log(*a):
    print("[fetch_live]", *a, flush=True)


def http_get(url, headers=None, retries=RETRIES):
    """优先 curl（对代理/大响应兼容更好，Actions 与本地 runner 均自带），失败回退 urllib。"""
    import subprocess
    h = dict(UA)
    if headers:
        h.update(headers)
    cmd = ["curl", "-sS", "-L", "--max-time", str(TIMEOUT)]
    for k, v in h.items():
        cmd += ["-H", f"{k}: {v}"]
    cmd.append(url)
    last = None
    for i in range(retries):
        try:
            cp = subprocess.run(cmd, capture_output=True, timeout=TIMEOUT + 10)
            if cp.returncode == 0 and cp.stdout:
                text = cp.stdout.decode("utf-8", "replace")
                if text.strip():
                    return text
            last = RuntimeError(f"curl rc={cp.returncode}: {cp.stderr.decode('utf-8','replace')[:120]}")
        except Exception as e:
            last = e
        if i < retries - 1:
            time.sleep(2 * (i + 1))
    # urllib 回退
    try:
        req = urllib.request.Request(url, headers=h)
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.read().decode("utf-8", "replace")
    except Exception:
        raise last


# ---------- Search API ----------
def gh_search(q, n=25):
    url = ("https://api.github.com/search/repositories?q=" +
           urllib.parse.quote(q) +
           f"&sort=stars&order=desc&per_page={n}")
    data = json.loads(http_get(url))
    items = data.get("items", [])
    out = []
    for it in items:
        out.append({
            "full_name": it.get("full_name", ""),
            "description": it.get("description") or "",
            "language": it.get("language") or "",
            "stars": it.get("stargazers_count") or 0,
            "forks": it.get("forks_count") or 0,
            "url": it.get("html_url") or "",
            "desc_zh": "",
            "topics": (it.get("topics") or [])[:5],
        })
    return out


def merge_repos(a, b, limit=25):
    seen = set()
    out = []
    for r in a + b:
        if r["full_name"] in seen:
            continue
        seen.add(r["full_name"])
        out.append(r)
    out.sort(key=lambda r: r["stars"], reverse=True)
    return out[:limit]


# ---------- Trending 页面 ----------
def _strip_tags(s):
    s = re.sub(r"<svg\b[^>]*>.*?</svg>", " ", s, flags=re.S | re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = s.replace("&amp;", "&").replace("&quot;", '"').replace("&#39;", "'")
    s = s.replace("&lt;", "<").replace("&gt;", ">").replace("&nbsp;", " ")
    return re.sub(r"\s+", " ", s).strip()


def _num(s):
    s = (s or "").replace(",", "").strip()
    m = re.search(r"([\d.]+)\s*([kKmM]?)", s)
    if not m:
        return 0
    v = float(m.group(1))
    if m.group(2).lower() == "k":
        v *= 1000
    elif m.group(2).lower() == "m":
        v *= 1000000
    return int(v)


def parse_trending(html, period="daily"):
    rows = re.split(r'<article class="Box-row">', html)[1:]
    out = []
    for row in rows:
        # 仓库全名：h2 内第一个指向 /owner/repo 的链接
        m = re.search(r'<h2[^>]*>\s*<a[^>]*href="/([^"/]+/[^"/]+)"[^>]*>', row, re.S)
        if not m:
            continue
        full_name = m.group(1)
        # 描述
        dm = re.search(r'<p class="col-9[^"]*"[^>]*>(.*?)</p>', row, re.S)
        desc = _strip_tags(dm.group(1)) if dm else ""
        # 语言
        lm = re.search(r'itemprop="programmingLanguage"[^>]*>(.*?)</span>', row, re.S)
        lang = _strip_tags(lm.group(1)) if lm else ""
        # 总星标 / fork
        sm = re.search(r'href="/' + re.escape(full_name) + r'/stargazers"[^>]*>(.*?)</a>', row, re.S)
        fm = re.search(r'href="/' + re.escape(full_name) + r'/forks"[^>]*>(.*?)</a>', row, re.S)
        stars = _num(_strip_tags(sm.group(1))) if sm else 0
        forks = _num(_strip_tags(fm.group(1))) if fm else 0
        # 周期增量："791 stars today" / "1,234 stars this week"
        pm = re.search(r'([\d,]+)\s+stars?\s+(?:today|this\s+week)', row, re.I)
        period_stars = _num(pm.group(1)) if pm else 0
        out.append({
            "full_name": full_name,
            "description": desc,
            "language": lang,
            "stars": stars,
            "forks": forks,
            "period_stars": period_stars,
            "url": "https://github.com/" + full_name,
            "desc_zh": "",
        })
    log(f"trending[{period}]: parsed {len(out)} rows")
    return out


def fetch_trending(period):
    url = f"https://github.com/trending?since={period}"
    html = http_get(url, headers={"Accept": "text/html,application/xhtml+xml"})
    return parse_trending(html, period)


# ---------- 中文简介 ----------
def apply_translations(data, existing_by_name, translator):
    """按 full_name 复用旧中文；新条目并发调翻译链。"""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    all_items = []
    for key in ("trending_daily", "trending_weekly", "top_stars", "newest"):
        all_items.extend(data.get(key) or [])
    for v in (data.get("categories") or {}).values():
        all_items.extend(v or [])

    reused = 0
    todo = []
    for r in all_items:
        old = existing_by_name.get(r["full_name"], {})
        old_zh = old.get("desc_zh", "")
        if old_zh:
            r["desc_zh"] = old_zh
            reused += 1
        elif r.get("description"):
            todo.append(r)

    def job(r):
        zh, via = translator.translate(r["description"])
        return r, zh, via

    new_count = 0
    if todo:
        with ThreadPoolExecutor(max_workers=8) as ex:
            futures = [ex.submit(job, r) for r in todo]
            for fu in as_completed(futures):
                try:
                    r, zh, via = fu.result()
                    r["desc_zh"] = zh
                    if via not in ("cache", "skip", "empty"):
                        new_count += 1
                except Exception:
                    pass
    log(f"translations: {len(all_items)} total, {reused} reused, {new_count} newly translated, {len(todo)} attempted")
    return data


def load_existing():
    """读现有内嵌数据，用于复用中文简介与保留 growth_7d。"""
    for p in (SLIMFILE, os.path.join(ROOT, "assets", "data.json")):
        try:
            d = json.load(io.open(p, encoding="utf-8"))
            by_name = {}
            for key in ("trending_daily", "trending_weekly", "top_stars", "newest"):
                for r in d.get(key, []):
                    by_name[r["full_name"]] = r
            for v in (d.get("categories") or {}).values():
                for r in v:
                    by_name[r["full_name"]] = r
            return d, by_name
        except Exception as e:
            log("load existing failed:", p, e)
    return {}, {}


# ---------- 主流程 ----------
def main():
    if not TOKEN:
        log("WARN: GITHUB_TOKEN 未设置，Search API 走未认证限流 60/h（可能 403）")
    existing, by_name = load_existing()
    translator = Translator()
    data = {"source": "live", "categories": {}}

    # 1) Trending 日榜 / 周榜
    for period, key in (("daily", "trending_daily"), ("weekly", "trending_weekly")):
        try:
            data[key] = fetch_trending(period)
        except Exception as e:
            log(f"WARN: trending {period} failed: {e}; keep snapshot")
            data[key] = existing.get(key, [])

    # 2) Search API（7 组，与前端原逻辑一致）
    since = (datetime.datetime.now(datetime.timezone.utc) -
             datetime.timedelta(days=14)).strftime("%Y-%m-%d")
    queries = {
        "top_stars": ("stars:>10000", 25),
        "newest": (f"created:>{since} stars:>50", 25),
    }
    cat_pairs = {
        "texts": ("topic:awesome stars:>500", "topic:tutorial stars:>500"),
        "ai": ("topic:ai stars:>500", "topic:llm stars:>500"),
        "dev": ("topic:developer-tools stars:>500", "topic:cli stars:>500"),
        "life": ("topic:psychology stars:>500", "topic:self-improvement stars:>500"),
        "finance": ("topic:quantitative-finance stars:>500", "topic:trading stars:>500"),
    }
    try:
        data["top_stars"] = gh_search(*queries["top_stars"])
        log("search top_stars:", len(data["top_stars"]))
    except Exception as e:
        log("WARN: search top_stars failed:", e)
        data["top_stars"] = existing.get("top_stars", [])
    try:
        data["newest"] = gh_search(*queries["newest"])
        log("search newest:", len(data["newest"]))
    except Exception as e:
        log("WARN: search newest failed:", e)
        data["newest"] = existing.get("newest", [])
    for cat, (qa, qb) in cat_pairs.items():
        result = None
        for attempt in range(3):
            try:
                a = gh_search(qa, 15)
                b = gh_search(qb, 15)
                result = merge_repos(a, b, 25)
                if result:
                    break
            except Exception as e:
                log(f"WARN: search category {cat} attempt {attempt + 1} failed:", str(e)[:120])
            time.sleep(2 * (attempt + 1))
        if result:
            data["categories"][cat] = result
            log(f"search category {cat}:", len(result))
        else:
            prev = (existing.get("categories") or {}).get(cat, [])
            data["categories"][cat] = prev
            log(f"WARN: category {cat} all attempts failed, kept {len(prev)} from snapshot")
        time.sleep(0.4)

    # 3) growth_7d：真实 7 日增速需连续抓取积累，暂时沿用快照值
    data["growth_7d"] = existing.get("growth_7d", {})

    # 4) 中文简介（旧库复用 + 新增走翻译链）
    apply_translations(data, by_name, translator)
    translator.save()
    log("translation stats:", json.dumps(translator.report(), ensure_ascii=False))

    # 5) 时间戳 + 写盘
    data["updated_at"] = datetime.datetime.now(
        datetime.timezone(datetime.timedelta(hours=8))
    ).isoformat(timespec="seconds")
    os.makedirs(os.path.dirname(OUTFILE), exist_ok=True)
    tmp = OUTFILE + ".tmp"
    with io.open(tmp, "w", encoding="utf-8", newline="") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, OUTFILE)

    size = os.path.getsize(OUTFILE)
    log(f"OK -> {OUTFILE} ({size:,} B)")
    log("summary: trending_daily=%d trending_weekly=%d top=%d newest=%d cats=%s updated=%s" % (
        len(data.get("trending_daily", [])), len(data.get("trending_weekly", [])),
        len(data.get("top_stars", [])), len(data.get("newest", [])),
        {k: len(v) for k, v in data["categories"].items()}, data["updated_at"]))


if __name__ == "__main__":
    main()
