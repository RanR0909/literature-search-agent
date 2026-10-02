# 统一文献检索服务

把三个免费开放学术数据源聚合成**一个**给智能体调用的检索接口。Dify 只需挂这一个工具。

| 数据源 | 定位 | 强项 |
|---|---|---|
| **OpenAlex** | 广度综合(2.5 亿+ 作品) | 全学科全球覆盖、开放获取信息 |
| **Crossref** | 权威元数据(1.5 亿+ DOI) | 准确出处/DOI/出版信息、近年期刊 |
| **Semantic Scholar** | 语义与引文(2 亿+ 论文) | 语义相关、引文影响力 |

各数据源也有独立的核心库与命令行,见 `tools/openalex/`、`tools/crossref/`、`tools/semanticscholar/`。本服务把它们统一到一个 HTTP 接口。

## 接口

| 端点 | 说明 |
|---|---|
| `GET /search?q=&source=&limit=&since=&until=&oa=&work_type=&sort=` | 在**单一**数据源检索(`source`: openalex/crossref/semanticscholar,默认 openalex) |
| `GET /search_all?q=&limit=&since=&until=&oa=` | **多源聚合**,按 DOI/标题去重,按被引降序 |

两个端点都返回统一结构 + 一个现成的 `markdown` 字段。

## 运行

```bash
cd tools/search_service
pip install -r requirements.txt
export OPENALEX_MAILTO=you@example.com     # 可选,进礼貌池
export CROSSREF_MAILTO=you@example.com     # 可选(不填则复用 OPENALEX_MAILTO)
export S2_API_KEY=xxxx                     # 可选,Semantic Scholar 提额
uvicorn server:app --host 0.0.0.0 --port 8000

# 自测
curl "http://localhost:8000/search?q=digital+humanities&source=crossref&limit=3"
curl "http://localhost:8000/search_all?q=laicite&limit=3"
```

> 生产部署用仓库根的 `deploy/`(Docker + compose 已切到本统一服务)。

## 接入 Dify

工具 → 创建自定义工具 → 导入 `dify_tool_openapi.yaml` → 把 `servers.url` 改成本服务地址
(与 Dify 同 docker 网络填 `http://litsearch:8000`)。之后在应用里挂上,模型即可自动调用
`searchLiterature`(指定源)或 `searchLiteratureAll`(聚合)。

## 命令行(各源单独用)

```bash
python tools/openalex/openalex_search.py        "laïcité french revolution" --lang fr --oa
python tools/crossref/crossref_search.py        "digital humanities" --since 2015 --type journal-article
python tools/semanticscholar/s2_search.py       "large language models" --since 2020 --oa
```

## 统一返回字段(每条)
`source, title, authors, year, date, venue, type, language, cited_by_count, doi, is_oa, oa_url, landing_url, id, abstract`

## 说明:各源差异
- **OpenAlex / Semantic Scholar** 有开放获取(`is_oa`/`oa_url`)信息;**Crossref** 不可靠提供,`is_oa` 记为未知(展示为"获取方式见链接")。
- `oa`(只要开放获取)对 OpenAlex/S2 有效;`work_type` 对 OpenAlex/Crossref 有效。
- Crossref 的 `type` 取值如 `journal-article`;OpenAlex 如 `article`。

## 本会话内未联网实测
云端开发容器出站网络被策略限制,三个 API 域名均被拦,故**核心逻辑已用离线模拟数据测通**(结果整形、去重、统一服务的 `/search` 与 `/search_all` 接线),但未在会话内做真实联网检索。部署服务器/本地无此限制,按上面命令即可真跑。
