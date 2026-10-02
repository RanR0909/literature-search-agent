#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Semantic Scholar 实时文献检索 —— 核心库 + 命令行

Semantic Scholar（https://www.semanticscholar.org，Allen AI 研究所）覆盖 2 亿+ 论文，
带引文图谱；特色是语义相关性与部分论文的 TLDR 摘要。免费；可选 API key 提额。

用法（命令行）：
  python s2_search.py "large language models" --limit 5 --since 2020 --oa
  python s2_search.py "digital humanities" --format json

可选 key：export S2_API_KEY=xxxx （无 key 也能用，只是配额较低）
"""

import argparse
import json
import os
import sys
import time
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "_common"))
from litsearch_common import (  # noqa: E402
    http_get_json, clip, make_result, format_results_markdown,
)

S2_BASE = "https://api.semanticscholar.org/graph/v1/paper/search"
FIELDS = ",".join([
    "title", "authors", "year", "publicationDate", "venue", "citationCount",
    "externalIds", "openAccessPdf", "abstract", "publicationTypes",
])


def _shape(item: dict) -> dict:
    authors = [a.get("name", "") for a in item.get("authors", []) or []]
    ext = item.get("externalIds", {}) or {}
    doi = ext.get("DOI", "")
    oa = item.get("openAccessPdf") or {}
    oa_url = oa.get("url") if isinstance(oa, dict) else None
    ptypes = item.get("publicationTypes") or []
    return make_result(
        source="semanticscholar",
        title=item.get("title") or "(无标题)",
        authors=authors[:8],
        year=item.get("year"),
        date=item.get("publicationDate"),
        venue=item.get("venue"),
        type=ptypes[0] if ptypes else None,
        cited_by_count=item.get("citationCount", 0),
        doi=f"https://doi.org/{doi}" if doi else "",
        is_oa=bool(oa_url) if oa is not None else None,
        oa_url=oa_url,
        landing_url=(f"https://www.semanticscholar.org/paper/{item.get('paperId')}"
                     if item.get("paperId") else None),
        id=item.get("paperId"),
        abstract=clip(item.get("abstract")),
    )


def search_works(query, per_page=5, year_from=None, year_to=None,
                 open_access_only=False, api_key=None, timeout=20):
    query = (query or "").strip()
    if not query:
        return {"error": "空查询：请提供检索词。", "query": query,
                "source": "semanticscholar", "total": 0, "results": []}
    per_page = max(1, min(per_page, 25))
    params = {"query": query, "limit": str(per_page), "fields": FIELDS}
    if year_from and year_to:
        params["year"] = f"{year_from}-{year_to}"
    elif year_from:
        params["year"] = f"{year_from}-"
    elif year_to:
        params["year"] = f"-{year_to}"
    if open_access_only:
        params["openAccessPdf"] = ""  # S2：仅返回有开放全文的
    url = S2_BASE + "?" + urllib.parse.urlencode(params, safe=":,-")
    api_key = api_key or os.environ.get("S2_API_KEY")
    headers = {"x-api-key": api_key} if api_key else None
    # 无 key 时 S2 限流严格,易触发 429:做有限重试(指数退避)。生产建议配 S2_API_KEY。
    data, err = None, None
    for attempt in range(3):
        data, err = http_get_json(url, headers=headers, timeout=timeout)
        if not err or "429" not in err:
            break
        time.sleep(1.5 * (attempt + 1))
    if err:
        hint = "(无 API Key 时限流严格,建议设置环境变量 S2_API_KEY)" if "429" in err and not api_key else ""
        return {"error": f"Semantic Scholar {err}{hint}", "query": query,
                "source": "semanticscholar", "total": 0, "results": []}
    results = [_shape(it) for it in data.get("data", []) or []]
    return {"query": query, "source": "semanticscholar",
            "total": data.get("total", len(results)),
            "returned": len(results), "results": results}


def _cli():
    p = argparse.ArgumentParser(description="Semantic Scholar 实时文献检索")
    p.add_argument("query")
    p.add_argument("--limit", type=int, default=5)
    p.add_argument("--since", type=int, default=None)
    p.add_argument("--until", type=int, default=None)
    p.add_argument("--oa", action="store_true", help="只返回有开放全文的")
    p.add_argument("--format", choices=["md", "json"], default="md")
    a = p.parse_args()
    data = search_works(a.query, per_page=a.limit, year_from=a.since, year_to=a.until,
                        open_access_only=a.oa)
    print(json.dumps(data, ensure_ascii=False, indent=2) if a.format == "json"
          else format_results_markdown(data))
    if data.get("error"):
        sys.exit(1)


if __name__ == "__main__":
    _cli()
