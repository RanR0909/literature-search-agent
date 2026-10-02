# 文献领航员 · lit-navigator

一个面向研究者(尤其做世界史、区域国别、跨文化研究)的**跨国文献检索智能体**。
它帮你解决人文社科研究里最常见的瓶颈:**不知道文献在哪、用什么语言的什么术语去检索、怎么拿到全文。**

- 📚 **分区域/学科的文献平台知识库** —— 按语区(德/法/日/俄/西葡…)和区域(北美/中东/南亚东南亚/非洲…)整理的开放获取平台与订阅数据库指南,含检索技巧、多语言术语词包、访问路径。
- 🔎 **实时学术检索** —— 聚合 OpenAlex、Crossref、Semantic Scholar 三大免费开放数据源,按主题直接查到论文(标题/作者/年份/被引/开放获取链接/摘要),可一次聚合去重(依次查询)。
- 🤖 **可搭在 Dify 上** —— 提供人设 prompt、知识库导入脚本、检索工具与容器化部署套件,几步搭出一个能对话、能分享的智能体。

> 项目机构无关,任何人、任何学校都可使用与部署。

## 目录结构

```
知识库条目/            # 订阅型数据库指南(机构无关,16 个区域/主题)
公开平台册/            # 开放获取平台指南(人人可用,8 个语区)
tools/                 # 实时检索工具
  ├─ openalex/         #   OpenAlex 检索(核心库 + CLI)
  ├─ crossref/         #   Crossref 检索
  ├─ semanticscholar/  #   Semantic Scholar 检索
  ├─ _common/          #   共享工具(HTTP/格式化/去重)
  └─ search_service/   #   统一检索微服务 + Dify 工具 OpenAPI
prompts/               # 智能体人设 prompt
deploy/                # 部署套件(Docker/compose、知识库导入脚本、部署指南)
eval/                  # 评测框架(黄金问题 + 7 项指标 + 运行脚本)
方案/                  # 部署技术栈总结
```

## 快速开始

### 试一下实时检索(零依赖,需能联网)
```bash
python tools/openalex/openalex_search.py "laïcité french revolution" --lang fr --oa --limit 5
python tools/crossref/crossref_search.py  "digital humanities" --since 2015
python tools/semanticscholar/s2_search.py "large language models" --oa
```

### 起统一检索服务(给 Dify 等平台调用)
```bash
cd tools/search_service
pip install -r requirements.txt
uvicorn server:app --host 0.0.0.0 --port 8000
curl "http://localhost:8000/search_all?q=digital+humanities&limit=3"
```

### 搭成完整智能体并上线
见 [`deploy/README.md`](deploy/README.md):自托管 Dify + 导入知识库 + 接入检索工具 + 建应用 + 发布的全流程。

## 技术栈
Dify(智能体底座) · Claude / DeepSeek / Qwen 等大模型(可替换) · 多语言 embedding(如 bge-m3) ·
OpenAlex / Crossref / Semantic Scholar(开放学术 API) · Docker。

## 数据来源与致谢
文献平台信息整理自各国国家图书馆、开放期刊/档案平台与公开学术数据库;实时检索由
[OpenAlex](https://openalex.org)、[Crossref](https://www.crossref.org)、
[Semantic Scholar](https://www.semanticscholar.org) 提供,在此致谢。

## 许可证
[MIT](LICENSE) © 2026 RanR0909
