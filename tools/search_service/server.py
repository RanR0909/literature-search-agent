#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一文献检索微服务 —— 一个接口聚合 OpenAlex / Crossref / Semantic Scholar。

给 Dify（或任何 agent 平台）当"自定义工具"用：Dify 只需挂这一个工具。
  - GET /search?q=...&source=openalex|crossref|semanticscholar   单一数据源
  - GET /search_all?q=...                                        三源并查 + 去重

运行：
  pip install -r requirements.txt
  export OPENALEX_MAILTO=you@example.com     # 可选
  export S2_API_KEY=xxxx                     # 可选
  uvicorn server:app --host 0.0.0.0 --port 8000
  curl "http://localhost:8000/search?q=digital+humanities&source=openalex&limit=3"
  curl "http://localhost:8000/search_all?q=laicite&limit=3"
"""

import sys
from pathlib import Path
from typing import Optional

try:
    from fastapi import FastAPI, Query
except ImportError:
    raise SystemExit("缺少依赖，请先运行： pip install -r requirements.txt")

TOOLS = Path(__file__).resolve().parent.parent
for sub in ("_common", "openalex", "crossref", "semanticscholar"):
    sys.path.insert(0, str(TOOLS / sub))

from litsearch_common import format_results_markdown, dedupe  # noqa: E402
import openalex_search  # noqa: E402
import crossref_search  # noqa: E402
import s2_search  # noqa: E402

app = FastAPI(
    title="统一文献检索工具",
    description="聚合 OpenAlex / Crossref / Semantic Scholar 的实时学术检索接口。",
    version="1.0.0",
)


def _run_source(source: str, q: str, limit: int, since, until, oa, work_type, sort):
    if source == "crossref":
        return crossref_search.search_works(
            q, per_page=limit, year_from=since, year_to=until,
            work_type=work_type, sort=(sort if sort != "relevance_score:desc" else "relevance"))
    if source == "semanticscholar":
        return s2_search.search_works(
            q, per_page=limit, year_from=since, year_to=until, open_access_only=oa)
    # 默认 openalex
    return openalex_search.search_works(
        q, per_page=limit, year_from=since, year_to=until,
        open_access_only=oa, work_type=work_type,
        sort=(sort if ":" in sort else "relevance_score:desc"))


@app.get("/search", summary="检索学术文献（单一数据源）", operation_id="searchLiterature")
def search(
    q: str = Query(..., description="检索词（自然语言或关键词，中英文均可，英文命中更全）"),
    source: str = Query("openalex", description="数据源：openalex / crossref / semanticscholar"),
    limit: int = Query(5, ge=1, le=25, description="返回条数 1-25"),
    since: Optional[int] = Query(None, description="起始出版年份"),
    until: Optional[int] = Query(None, description="截止出版年份"),
    oa: bool = Query(False, description="只返回开放获取（OpenAlex/S2 有效）"),
    work_type: Optional[str] = Query(None, description="文献类型（OpenAlex/Crossref 有效）"),
    sort: str = Query("relevance_score:desc", description="排序（各源支持不同值，见文档）"),
):
    source = source.lower().strip()
    if source not in ("openalex", "crossref", "semanticscholar"):
        source = "openalex"
    data = _run_source(source, q, limit, since, until, oa, work_type, sort)
    data["markdown"] = format_results_markdown(data)
    return data


@app.get("/search_all", summary="三源并查并去重", operation_id="searchLiteratureAll")
def search_all(
    q: str = Query(..., description="检索词"),
    limit: int = Query(5, ge=1, le=15, description="每个数据源的返回条数 1-15"),
    since: Optional[int] = Query(None),
    until: Optional[int] = Query(None),
    oa: bool = Query(False),
):
    merged, errors = [], {}
    for source in ("openalex", "crossref", "semanticscholar"):
        d = _run_source(source, q, limit, since, until, oa, None, "relevance_score:desc")
        if d.get("error"):
            errors[source] = d["error"]
        merged.extend(d.get("results", []))
    merged = dedupe(merged)
    # 按被引降序，便于把高影响力的排前面
    merged.sort(key=lambda r: r.get("cited_by_count", 0) or 0, reverse=True)
    out = {"query": q, "source": "all", "total": len(merged),
           "returned": len(merged), "results": merged}
    if errors:
        out["source_errors"] = errors
    out["markdown"] = format_results_markdown(out)
    return out


@app.get("/health", include_in_schema=False)
def health():
    return {"status": "ok"}
