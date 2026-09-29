# OpenAlex 实时文献检索工具

给"跨国文献检索智能体"补上**实时检索**能力:从"告诉你去哪找"升级到"直接帮你查到具体论文"。数据源是 [OpenAlex](https://openalex.org)——覆盖 2.5 亿+ 学术作品、全学科全球的开放学术图谱,**免费、无需 API key**。

## 文件

| 文件 | 作用 |
|---|---|
| `openalex_search.py` | 核心检索库 + 命令行。**零第三方依赖**,任何有 Python3 的环境直接跑 |
| `server.py` | FastAPI 微服务,把检索包成 HTTP 接口,给 Dify 等平台当"自定义工具" |
| `dify_tool_openapi.yaml` | Dify 导入用的 OpenAPI schema(指向 `server.py`) |
| `requirements.txt` | 仅 `server.py` 需要(fastapi + uvicorn) |

## 三种用法

### 1. 命令行(最快验证)
```bash
python openalex_search.py "laïcité french revolution" --limit 5 --lang fr --oa --since 2010
python openalex_search.py "布尔迪厄 教育社会学" --sort cited_by_count:desc
python openalex_search.py "digital humanities" --format json
```
可选:`export OPENALEX_MAILTO=you@example.com` 进入 OpenAlex "礼貌池",配额更稳。

### 2. 作为库(给纯代码 agent / LangGraph 用)
```python
from openalex_search import search_works, format_results_markdown
data = search_works("open access repositories", per_page=5, open_access_only=True, year_from=2018)
print(format_results_markdown(data))   # 现成 Markdown
# data["results"] 是结构化列表:title/authors/year/venue/cited_by_count/is_oa/oa_url/abstract...
```

### 3. 作为 Dify 自定义工具(推荐,配合本项目的 Dify 底座)
```bash
pip install -r requirements.txt
export OPENALEX_MAILTO=you@example.com     # 可选
uvicorn server:app --host 0.0.0.0 --port 8000
# 自测: curl "http://localhost:8000/search?q=digital+humanities&limit=3"
```
然后在 Dify:**工具 → 创建自定义工具 → 导入 `dify_tool_openapi.yaml`**,把里面 `servers.url` 改成本服务的公网地址。之后在你的 Chatflow/Agent 里把这个工具挂上,模型就能在对话中自动调用 `searchLiterature` 检索文献。

> 生产部署建议:把 `server.py` 和 Dify 放同一台服务器/同一 docker 网络,`servers.url` 用内网地址;若要公网暴露,加反向代理 + HTTPS。

## 检索参数

| 参数 | 说明 | 示例 |
|---|---|---|
| `q` / query | 检索词(中英文均可,英文命中更全) | `laïcité french revolution` |
| `limit` | 返回条数 1-25 | `5` |
| `since` / `until` | 出版年份区间 | `2010` / `2024` |
| `lang` | 语言代码 | `en` `fr` `de` `ja` `zh` |
| `oa` | 只要开放获取(可免费全文) | `true` |
| `work_type` | 文献类型 | `article` `book` `book-chapter` |
| `sort` | 排序 | `relevance_score:desc`(相关度)/ `cited_by_count:desc`(被引)/ `publication_date:desc`(最新) |

## 返回字段(每条)
`title, authors, year, date, venue, type, language, cited_by_count, doi, is_oa, oa_url, landing_url, openalex_id, abstract`

`server.py` 额外返回一个 `markdown` 字段,是渲染好的摘要,可直接展示给用户。

## 给智能体人设 prompt 的建议片段
> 当用户想查找关于某主题的具体论文/文献时,调用 `searchLiterature` 工具。若用户给的是中文主题,先在心里转成对应语言的学术关键词再检索(英文通常命中最全)。优先展示开放获取(🟢)的结果并给出可访问链接;订阅类结果提示用户"可查所在机构是否订阅"。引用时保留标题、作者、年份与链接,不要编造不存在的文献。

## 下一步可扩展
同一套封装模式可再接 **Crossref / Semantic Scholar / DOAJ / arXiv / CORE**(见 `方案/通用化改造与部署方案.md` 的"开放学术 API 速查"),按需在 `server.py` 增加对应端点即可。

## 关于本会话内未能实测
本项目的云端开发容器出站网络被策略限制,`api.openalex.org` 被拦(仅放行包管理源与 Anthropic),因此**核心逻辑已用离线模拟数据测通,但未在会话内做真实联网检索**。在你的本地或部署服务器上按上面命令即可真实调用。若希望在云端会话里直接联网实测,需在环境的网络设置里放行 `api.openalex.org`。
