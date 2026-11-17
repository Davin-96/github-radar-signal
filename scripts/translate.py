# -*- coding: utf-8 -*-
"""免密钥翻译降级链：Google gtx → Google 备用域名 → MyMemory → 旧缓存 → 英文原文。

只在 GitHub Actions（境外服务器）运行，无需 API key。每个 provider 有超时与异常处理，
任一环节失败自动降级，绝不阻断数据抓取主流程。
"""
import io
import os
import re
import json
import time
import threading
import urllib.parse
import urllib.request

TIMEOUT = 20
CACHE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "translated.json")

_UA = {"User-Agent": "Mozilla/5.0 (compatible; GitHubRadar/1.0)"}


def _load_cache():
    if not os.path.exists(CACHE_PATH):
        return {}
    try:
        return json.load(io.open(CACHE_PATH, encoding="utf-8"))
    except Exception:
        return {}


def _save_cache(cache):
    tmp = CACHE_PATH + ".tmp"
    with io.open(tmp, "w", encoding="utf-8", newline="") as f:
        json.dump(cache, f, ensure_ascii=False, indent=1, sort_keys=True)
    os.replace(tmp, CACHE_PATH)


def _get(url):
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return r.read().decode("utf-8", "replace")


def _google(host, text):
    q = urllib.parse.quote(text)
    url = f"https://{host}/translate_a/single?client=gtx&sl=en&tl=zh-CN&dt=t&q={q}"
    raw = _get(url)
    data = json.loads(raw)
    parts = []
    for seg in data[0]:
        if isinstance(seg, list) and seg and isinstance(seg[0], str):
            parts.append(seg[0])
    out = "".join(parts).strip()
    if not out:
        raise ValueError("empty translation")
    return out


def _google_gtx(text):
    return _google("translate.googleapis.com", text)


def _google_alt(text):
    return _google("translate.google.com", text)


def _mymemory(text):
    q = urllib.parse.quote(text)
    url = f"https://api.mymemory.translated.net/get?q={q}&langpair=en|zh-CN"
    data = json.loads(_get(url))
    out = (data.get("responseData") or {}).get("translatedText", "").strip()
    if not out or "QUERY LENGTH LIMIT" in out.upper() or "INVALID" in out.upper():
        raise ValueError("bad mymemory result: " + out[:60])
    # MyMemory 偶尔原样返回英文，视为失败以触发下一级
    if out.lower() == text.strip().lower():
        raise ValueError("unchanged")
    return out


PROVIDERS = [
    ("google-gtx", _google_gtx),
    ("google-alt", _google_alt),
    ("mymemory", _mymemory),
]


class Translator:
    def __init__(self, enabled=True):
        self.enabled = enabled
        self.cache = _load_cache()
        self.stats = {name: 0 for name, _ in PROVIDERS}
        self.stats["cache"] = 0
        self.stats["fallback-en"] = 0
        self._dirty = False
        self._lock = threading.Lock()

    def translate(self, text):
        text = (text or "").strip()
        if not text:
            return "", "empty"
        # 纯符号 / 纯数字 / 无字母，不翻译
        if not re.search(r"[A-Za-z]{2}", text):
            return text, "skip"
        with self._lock:
            if text in self.cache:
                self.stats["cache"] += 1
                return self.cache[text], "cache"
        if not self.enabled:
            with self._lock:
                self.stats["fallback-en"] += 1
            return text, "fallback-en"
        for name, fn in PROVIDERS:
            try:
                out = fn(text)
                if out and out.strip():
                    with self._lock:
                        self.cache[text] = out.strip()
                        self._dirty = True
                        self.stats[name] += 1
                    return out.strip(), name
            except Exception:
                pass
            time.sleep(0.15)
        with self._lock:
            self.stats["fallback-en"] += 1
        return text, "fallback-en"

    def save(self):
        if self._dirty:
            _save_cache(self.cache)
            self._dirty = False

    def report(self):
        return dict(self.stats)


if __name__ == "__main__":
    import sys
    samples = sys.argv[1:] or [
        "AG-UI: the Agent-User Interaction Protocol. Bring Agents into Frontend Applications.",
        "The workspace to stay in the loop and on top of agents",
        "Model Context Protocol for connecting AI assistants to data sources",
    ]
    t = Translator()
    for s in samples:
        out, via = t.translate(s)
        print(f"[{via}] {s}\n  -> {out}")
    t.save()
    print("STATS:", json.dumps(t.report(), ensure_ascii=False))
