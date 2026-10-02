#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Crossref 实时文献检索 —— 核心库 + 命令行

Crossref（https://www.crossref.org）是 DOI 注册机构，提供约 1.5 亿条学术作品的
权威书目元数据（期刊论文、图书、会议论文等）。免费、无需 key。
强项：准确的出处/DOI/出版信息与被引数；对近年期刊论文覆盖尤佳。

用法（命令行）：
  python crossref_search.py "digital humanities" --limit 5 --since 2015 --type journal-article
  python crossref_search.py "布尔迪厄 教育" --sort is-referenced-by-count --format json

礼貌池：export CROSSREF_MAILTO=you@example.com （或 OPENALEX_MAILTO 也会被读取）
"""

import argparse
import json
import os
import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "_common"))
from litsearch_common import (  # noqa: E402
    http_get_json, clip, strip_jats, make_result, format_results_markdown,
)

CROSSREF_BASE = "https://api.crossref.org/works"
SELECT = ",".join([
    "DOI", "title", "author", "issued", "container-title", "type",
    "is-referenced-by-count", "abstract", "URL", "language",
])


def _build_filter(year_from, year_to, work_type):
    parts = []
    if year_from:
        parts.append(f"from-pub-date:{year_from}-01-01")
    if year_to:
        parts.append(f"until-pub-date:{year_to}-12-31")
    if work_type:
        parts.append(f"type:{work_type}")
    return ",".join(parts) if parts else None


def _shape(item: dict) -> dict:
    title = (item.get("title") or ["(无标题)"])[0] if item.get("title") else "(无标题)"
    authors = []
    for a in item.get("author", []) or []:
        name = " ".join(x for x in [a.get("given"), a.get("family")] if x) or a.get("name", "")
        if name:
            authors.append(name)
    issued = (item.get("issued", {}) or {}).get("date-parts", [[None]])
    year = issued[0][0] if issued and issued[0] else None
    venue = (item.get("container-title") or [None])[0] if item.get("container-title") else None
    doi = item.get("DOI", "")
    return make_result(
        source="crossref",
        title=title,
        authors=authors[:8],
        year=year,
        venue=venue,
        type=item.get("type"),
        language=item.get("language"),
        cited_by_count=item.get("is-referenced-by-count", 0),
        doi=f"https://doi.org/{doi}" if doi else "",
        is_oa=None,  # Crossref 不可靠地提供 OA 状态
        landing_url=item.get("URL"),
        id=f"https://doi.org/{doi}" if doi else None,
        abstract=clip(strip_jats(item.get("abstract"))),
    )


def search_works(query, per_page=5, year_from=None, year_to=None, work_type=None,
                 sort="relevance", mailto=None, timeout=20):
    query = (query or "").strip()
    if not query:
        return {"error": "空查询：请提供检索词。", "query": query, "source": "crossref",
                "total": 0, "results": []}
    per_page = max(1, min(per_page, 25))
    params = {"query": query, "rows": str(per_page), "select": SELECT}
    # Crossref 的相关度排序值是 score(不是 relevance);相关度为默认,省略即可。
    # 只有按被引/出版时间排序时才显式传 sort+order,避免无效值导致 400。
    sort_map = {"is-referenced-by-count": "is-referenced-by-count", "published": "published"}
    if sort in sort_map:
        params["sort"] = sort_map[sort]
        params["order"] = "desc"
    filt = _build_filter(year_from, year_to, work_type)
    if filt:
        params["filter"] = filt
    mailto = mailto or os.environ.get("CROSSREF_MAILTO") or os.environ.get("OPENALEX_MAILTO")
    if mailto:
        params["mailto"] = mailto
    url = CROSSREF_BASE + "?" + urllib.parse.urlencode(params, safe=":,-")
    data, err = http_get_json(url, timeout=timeout)
    if err:
        return {"error": f"Crossref {err}", "query": query, "source": "crossref",
                "total": 0, "results": []}
    msg = data.get("message", {})
    results = [_shape(it) for it in msg.get("items", [])]
    return {"query": query, "source": "crossref",
            "total": msg.get("total-results", len(results)),
            "returned": len(results), "results": results}


def _cli():
    p = argparse.ArgumentParser(description="Crossref 实时文献检索")
    p.add_argument("query")
    p.add_argument("--limit", type=int, default=5)
    p.add_argument("--since", type=int, default=None)
    p.add_argument("--until", type=int, default=None)
    p.add_argument("--type", dest="work_type", default=None,
                   help="如 journal-article / book / proceedings-article")
    p.add_argument("--sort", default="relevance",
                   help="relevance / is-referenced-by-count / published")
    p.add_argument("--format", choices=["md", "json"], default="md")
    a = p.parse_args()
    data = search_works(a.query, per_page=a.limit, year_from=a.since, year_to=a.until,
                        work_type=a.work_type, sort=a.sort)
    print(json.dumps(data, ensure_ascii=False, indent=2) if a.format == "json"
          else format_results_markdown(data))
    if data.get("error"):
        sys.exit(1)


if __name__ == "__main__":
    _cli()
