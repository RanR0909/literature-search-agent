# 统一文献检索微服务容器（OpenAlex + Crossref + Semantic Scholar）。
# 与 Dify 部署在一起，供其自定义工具调用。
FROM python:3.12-slim

WORKDIR /app

# 依赖（各数据源核心库零依赖，只需 fastapi + uvicorn）
COPY tools/search_service/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 拷入统一服务 + 共享模块 + 三个数据源核心库（保持相对目录结构，server.py 按此加载）
COPY tools/_common/           ./tools/_common/
COPY tools/openalex/openalex_search.py        ./tools/openalex/openalex_search.py
COPY tools/crossref/crossref_search.py        ./tools/crossref/crossref_search.py
COPY tools/semanticscholar/s2_search.py       ./tools/semanticscholar/s2_search.py
COPY tools/search_service/server.py           ./tools/search_service/server.py

WORKDIR /app/tools/search_service

EXPOSE 8000

# 可选环境变量（运行时用 -e 覆盖）
ENV OPENALEX_MAILTO="" \
    CROSSREF_MAILTO="" \
    S2_API_KEY=""

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)" || exit 1

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
