#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenAlex 检索微服务 — 给 Dify（或任何 agent 平台）当"自定义工具"调用。

它把 openalex_search.py 的检索能力包成一个干净的 HTTP 接口，返回精简 JSON +
一段现成的 Markdown 摘要，Dify 的自定义工具指向本服务的 /search 即可。

运行：
  pip install -r requirements.txt
  export OPENALEX_MAILTO=you@example.com      # 可选，进礼貌池
  uvicorn server:app --host 0.0.0.0 --port 8000
  # 健康检查： curl "http://localhost:8000/search?q=digital+humanities&limit=3"

在 Dify 里：工具 → 创建自定义工具 → 用同目录 dify_tool_openapi.yaml 导入，
把其中 servers.url 改成本服务的公网地址即可。
"""

from typing import Optional

try:
    from fastapi import FastAPI, Query
except ImportError:  # 友好提示
    raise SystemExit("缺少依赖，请先运行： pip install -r requirements.txt")

from openalex_search import search_works, format_results_markdown

app = FastAPI(
    title="OpenAlex 文献检索工具",
    description="供文献检索智能体调用的实时学术检索接口，数据源 OpenAlex（免费开放）。",
    version="1.0.0",
)


@app.get("/search", summary="检索学术文献", operation_id="searchLiterature")
def search(
    q: str = Query(..., description="检索词（自然语言或关键词，中英文均可，英文命中更全）"),
    limit: int = Query(5, ge=1, le=25, description="返回条数，1-25"),
    since: Optional[int] = Query(None, description="起始出版年份，如 2010"),
    until: Optional[int] = Query(None, description="截止出版年份，如 2024"),
    lang: Optional[str] = Query(None, description="语言代码，如 en/fr/de/ja/zh"),
    oa: bool = Query(False, description="是否只返回开放获取（可免费全文）的文献"),
    work_type: Optional[str] = Query(None, description="文献类型，如 article/book/book-chapter"),
    sort: str = Query(
        "relevance_score:desc",
        description="排序：relevance_score:desc（相关度）/ cited_by_count:desc（被引）/ publication_date:desc（最新）",
    ),
):
    """检索 OpenAlex 并返回结构化结果与 Markdown 摘要。"""
    data = search_works(
        q, per_page=limit, year_from=since, year_to=until,
        language=lang, open_access_only=oa, work_type=work_type, sort=sort,
    )
    data["markdown"] = format_results_markdown(data)
    return data


@app.get("/health", include_in_schema=False)
def health():
    return {"status": "ok"}
