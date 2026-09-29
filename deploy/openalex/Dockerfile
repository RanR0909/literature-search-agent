# OpenAlex 检索微服务容器 —— 与 Dify 部署在一起，供其自定义工具调用。
FROM python:3.12-slim

WORKDIR /app

# 只需 fastapi + uvicorn（openalex_search.py 本身零依赖）
COPY tools/openalex/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 拷入工具代码
COPY tools/openalex/openalex_search.py tools/openalex/server.py ./

EXPOSE 8000

# 可选：进入 OpenAlex 礼貌池（构建/运行时用 -e OPENALEX_MAILTO=you@example.com 覆盖）
ENV OPENALEX_MAILTO=""

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)" || exit 1

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
