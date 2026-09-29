#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenAlex 实时文献检索 — 核心库 + 命令行

OpenAlex（https://openalex.org）是覆盖 2.5 亿+ 学术作品、全学科全球的开放学术图谱，
免费、无需 API key。本模块把它封装成"文献检索智能体"可直接调用的检索函数：
输入自然语言/关键词，返回结构化的论文列表 + 一段适合喂给 LLM 的 Markdown 摘要。

设计要点：
  - 零第三方依赖（只用标准库 urllib），可在任何有 Python3 的环境直接跑。
  - 支持年份区间、语言、开放获取、文献类型过滤与排序。
  - 用 OpenAlex 的 `select` 只取需要的字段，减小返回体积。
  - abstract 从 OpenAlex 的倒排索引（abstract_inverted_index）还原为正常文本。
  - "礼貌池"邮箱通过环境变量 OPENALEX_MAILTO 提供（不硬编码任何人的邮箱）。

用法（命令行）：
  python openalex_search.py "laïcité french revolution" --limit 5 --lang fr --oa --since 2010
  python openalex_search.py "布尔迪厄 教育社会学" --sort cited_by_count:desc --format json

用法（库）：
  from openalex_search import search_works, format_results_markdown
  data = search_works("digital humanities", per_page=5, open_access_only=True)
  print(format_results_markdown(data))
"""

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from typing import Any, Optional

OPENALEX_BASE = "https://api.openalex.org/works"
DEFAULT_TIMEOUT = 20

# 只取需要的字段，减小返回体积
SELECT_FIELDS = ",".join([
    "id", "doi", "title", "display_name", "publication_year", "publication_date",
    "language", "type", "cited_by_count", "authorships", "primary_location",
    "open_access", "abstract_inverted_index",
])


def _build_filter(
    year_from: Optional[int],
    year_to: Optional[int],
    language: Optional[str],
    open_access_only: bool,
    work_type: Optional[str],
    extra_filter: Optional[str],
) -> Optional[str]:
    """把结构化过滤条件拼成 OpenAlex 的 filter 串（逗号分隔=AND）。"""
    parts = []
    if year_from is not None and year_to is not None:
        parts.append(f"publication_year:{year_from}-{year_to}")
    elif year_from is not None:
        parts.append(f"from_publication_date:{year_from}-01-01")
    elif year_to is not None:
        parts.append(f"to_publication_date:{year_to}-12-31")
    if language:
        parts.append(f"language:{language}")
    if open_access_only:
        parts.append("is_oa:true")
    if work_type:
        parts.append(f"type:{work_type}")
    if extra_filter:
        parts.append(extra_filter)
    return ",".join(parts) if parts else None


def reconstruct_abstract(inverted_index: Optional[dict]) -> str:
    """OpenAlex 用倒排索引存 abstract：{词: [位置...]}。还原成正常文本。"""
    if not inverted_index:
        return ""
    positions: list[tuple[int, str]] = []
    for word, idxs in inverted_index.items():
        for i in idxs:
            positions.append((i, word))
    positions.sort(key=lambda x: x[0])
    return " ".join(word for _, word in positions)


def search_works(
    query: str,
    per_page: int = 5,
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
    language: Optional[str] = None,
    open_access_only: bool = False,
    work_type: Optional[str] = None,
    sort: str = "relevance_score:desc",
    extra_filter: Optional[str] = None,
    mailto: Optional[str] = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """
    检索 OpenAlex works，返回规整后的 dict：
      {"query":..., "total": N, "results": [ {title, authors, year, ...}, ... ]}
    出错时返回 {"error": "..."}，不抛异常，便于 agent 侧处理。
    """
    query = (query or "").strip()
    if not query:
        return {"error": "空查询：请提供检索词。", "query": query, "total": 0, "results": []}

    per_page = max(1, min(per_page, 25))  # OpenAlex 单页上限 200，这里限 25 够用且省 token
    params: dict[str, str] = {
        "search": query,
        "per-page": str(per_page),
        "sort": sort,
        "select": SELECT_FIELDS,
    }
    filt = _build_filter(year_from, year_to, language, open_access_only, work_type, extra_filter)
    if filt:
        params["filter"] = filt
    mailto = mailto or os.environ.get("OPENALEX_MAILTO", "")
    if mailto:
        params["mailto"] = mailto  # 进入礼貌池，更稳定的配额

    url = OPENALEX_BASE + "?" + urllib.parse.urlencode(params, safe=":,-")
    ua = "lit-navigator/1.0 (+https://github.com/RanR0909/literature-search-agent)"
    req = urllib.request.Request(url, headers={"User-Agent": ua, "Accept": "application/json"})

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return {"error": f"OpenAlex HTTP {e.code}: {e.reason}", "query": query, "total": 0, "results": []}
    except Exception as e:  # 网络/超时/解析
        return {"error": f"请求失败: {e}", "query": query, "total": 0, "results": []}

    results = [_shape_work(w) for w in raw.get("results", [])]
    return {
        "query": query,
        "total": raw.get("meta", {}).get("count", len(results)),
        "returned": len(results),
        "results": results,
    }


def _shape_work(w: dict) -> dict[str, Any]:
    """把一条 OpenAlex work 精简成 agent 友好的结构。"""
    authorships = w.get("authorships", []) or []
    authors = [a.get("author", {}).get("display_name", "") for a in authorships]
    pl = w.get("primary_location") or {}
    src = pl.get("source") or {}
    oa = w.get("open_access") or {}
    doi = w.get("doi") or ""
    abstract = reconstruct_abstract(w.get("abstract_inverted_index"))
    if len(abstract) > 600:
        abstract = abstract[:600].rstrip() + "…"
    return {
        "source": "openalex",
        "title": w.get("title") or w.get("display_name") or "(无标题)",
        "authors": authors[:8],
        "year": w.get("publication_year"),
        "date": w.get("publication_date"),
        "venue": src.get("display_name"),
        "type": w.get("type"),
        "language": w.get("language"),
        "cited_by_count": w.get("cited_by_count", 0),
        "doi": doi,
        "is_oa": bool(oa.get("is_oa")),
        "oa_url": oa.get("oa_url"),
        "landing_url": pl.get("landing_page_url"),
        "openalex_id": w.get("id"),
        "id": w.get("id"),
        "abstract": abstract,
    }


def format_results_markdown(data: dict[str, Any]) -> str:
    """把检索结果渲染成一段 Markdown，便于直接展示或喂给 LLM。"""
    if data.get("error"):
        return f"检索出错：{data['error']}"
    results = data.get("results", [])
    if not results:
        return f"未找到与「{data.get('query','')}」相关的文献。可换用更宽泛或英文关键词再试。"
    lines = [f"OpenAlex 命中约 {data.get('total', 0)} 篇，展示前 {len(results)} 篇：", ""]
    for i, r in enumerate(results, 1):
        authors = ", ".join(r["authors"][:3]) + (" 等" if len(r["authors"]) > 3 else "")
        head = f"**{i}. {r['title']}**"
        meta = " · ".join(filter(None, [
            authors or None,
            str(r["year"]) if r["year"] else None,
            r["venue"],
            f"被引 {r['cited_by_count']}",
        ]))
        access = "🟢 开放获取" if r["is_oa"] else "🔒 订阅/未开放"
        link = r["oa_url"] or r["landing_url"] or r["doi"] or r["openalex_id"] or ""
        lines.append(head)
        if meta:
            lines.append(f"   {meta}")
        lines.append(f"   {access}" + (f" · {link}" if link else ""))
        if r["abstract"]:
            lines.append(f"   摘要：{r['abstract']}")
        lines.append("")
    return "\n".join(lines).rstrip()


def _cli():
    p = argparse.ArgumentParser(description="OpenAlex 实时文献检索")
    p.add_argument("query", help="检索词（自然语言或关键词，中英文均可，英文命中更全）")
    p.add_argument("--limit", type=int, default=5, help="返回条数（1-25，默认 5）")
    p.add_argument("--since", type=int, default=None, help="起始年份，如 2010")
    p.add_argument("--until", type=int, default=None, help="截止年份，如 2024")
    p.add_argument("--lang", default=None, help="语言代码，如 en/fr/de/ja/zh")
    p.add_argument("--oa", action="store_true", help="只要开放获取")
    p.add_argument("--type", dest="work_type", default=None, help="文献类型，如 article/book/book-chapter")
    p.add_argument("--sort", default="relevance_score:desc",
                   help="排序，如 relevance_score:desc / cited_by_count:desc / publication_date:desc")
    p.add_argument("--filter", dest="extra_filter", default=None, help="附加 OpenAlex filter 串（高级）")
    p.add_argument("--format", choices=["md", "json"], default="md", help="输出格式")
    args = p.parse_args()

    data = search_works(
        args.query, per_page=args.limit, year_from=args.since, year_to=args.until,
        language=args.lang, open_access_only=args.oa, work_type=args.work_type,
        sort=args.sort, extra_filter=args.extra_filter,
    )
    if args.format == "json":
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(format_results_markdown(data))
    if data.get("error"):
        sys.exit(1)


if __name__ == "__main__":
    _cli()
