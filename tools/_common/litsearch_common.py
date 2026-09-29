# -*- coding: utf-8 -*-
"""
文献检索工具的共享工具函数 —— 各数据源(OpenAlex/Crossref/Semantic Scholar)复用。

统一结果结构(每条命中)：
  source, title, authors[list], year, date, venue, type, language,
  cited_by_count, doi, is_oa(bool|None), oa_url, landing_url, id, abstract

统一返回结构：
  {"query":..., "source":..., "total":N, "returned":M, "results":[...]}
  出错时： {"error":"...", ...}
"""

import json
import re
import urllib.error
import urllib.request
from typing import Any, Optional

DEFAULT_TIMEOUT = 20
USER_AGENT = "lit-navigator/1.0 (+https://github.com/RanR0909/literature-search-agent)"


def http_get_json(url: str, headers: Optional[dict] = None, timeout: int = DEFAULT_TIMEOUT):
    """GET 一个 JSON。返回 (data, None) 或 (None, 错误字符串)。不抛异常。"""
    h = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8")), None
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code}: {e.reason}"
    except Exception as e:
        return None, f"请求失败: {e}"


def clip(text: Optional[str], n: int = 600) -> str:
    """裁剪过长文本。"""
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text).strip()
    return text[:n].rstrip() + "…" if len(text) > n else text


def strip_jats(text: Optional[str]) -> str:
    """Crossref 的 abstract 常是 JATS/XML，去标签。"""
    if not text:
        return ""
    return re.sub(r"<[^>]+>", "", text)


def make_result(**kw) -> dict[str, Any]:
    """用统一字段建一条结果，缺省填空。"""
    base = {
        "source": "", "title": "(无标题)", "authors": [], "year": None, "date": None,
        "venue": None, "type": None, "language": None, "cited_by_count": 0,
        "doi": "", "is_oa": None, "oa_url": None, "landing_url": None, "id": None, "abstract": "",
    }
    base.update(kw)
    return base


def format_results_markdown(data: dict[str, Any]) -> str:
    """把统一结构渲染成 Markdown（用于展示或喂给 LLM）。"""
    if data.get("error"):
        return f"检索出错：{data['error']}"
    results = data.get("results", [])
    q = data.get("query", "")
    if not results:
        return f"未找到与「{q}」相关的文献。可换用更宽泛或英文关键词再试。"
    src = data.get("source", "")
    header = f"命中约 {data.get('total', 0)} 篇，展示前 {len(results)} 篇"
    header += f"（来源：{src}）：" if src and src != "all" else "："
    lines = [header, ""]
    for i, r in enumerate(results, 1):
        authors = ", ".join(r.get("authors", [])[:3])
        if len(r.get("authors", [])) > 3:
            authors += " 等"
        tag = f"[{r.get('source')}] " if r.get("source") and src in ("", "all") else ""
        lines.append(f"**{i}. {tag}{r.get('title')}**")
        meta = " · ".join(x for x in [
            authors or None,
            str(r["year"]) if r.get("year") else None,
            r.get("venue"),
            f"被引 {r.get('cited_by_count', 0)}" if r.get("cited_by_count") else None,
        ] if x)
        if meta:
            lines.append(f"   {meta}")
        if r.get("is_oa") is True:
            access = "🟢 开放获取"
        elif r.get("is_oa") is False:
            access = "🔒 订阅/未开放"
        else:
            access = "ℹ️ 获取方式见链接"
        link = r.get("oa_url") or r.get("landing_url") or r.get("doi") or r.get("id") or ""
        lines.append(f"   {access}" + (f" · {link}" if link else ""))
        if r.get("abstract"):
            lines.append(f"   摘要：{r['abstract']}")
        lines.append("")
    return "\n".join(lines).rstrip()


def norm_doi(doi: Optional[str]) -> str:
    """归一化 DOI 便于去重。"""
    if not doi:
        return ""
    d = doi.lower().strip()
    d = re.sub(r"^https?://(dx\.)?doi\.org/", "", d)
    return d


def dedupe(results: list[dict]) -> list[dict]:
    """按 DOI（优先）或标题去重，保留先出现的。"""
    seen_doi, seen_title, out = set(), set(), []
    for r in results:
        d = norm_doi(r.get("doi"))
        t = re.sub(r"\s+", " ", (r.get("title") or "").lower()).strip()
        if d and d in seen_doi:
            continue
        if not d and t and t in seen_title:
            continue
        if d:
            seen_doi.add(d)
        if t:
            seen_title.add(t)
        out.append(r)
    return out
