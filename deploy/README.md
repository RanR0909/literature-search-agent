# 部署套件 —— 把文献领航员搭在 Dify 上并上线

这份指南把项目从素材变成一个**公网可访问的智能体**:Dify 做底座,挂上本项目的知识库,接上 OpenAlex 实时检索工具。

## 目录内容

| 路径 | 作用 |
|---|---|
| `openalex/Dockerfile` | 把 OpenAlex 检索微服务打成容器 |
| `docker-compose.yml` | 编排本项目自有服务(目前是 OpenAlex 微服务) |
| `prepare_knowledge_base.py` | 把知识库素材整理成可直接拖进 Dify 的一批文件 |
| `.env.example` | 环境变量模板 |
| `dist/knowledge-base/` | 运行上面脚本后生成的待导入文件(不入库) |
| `../prompts/agent_system_prompt.md` | 去竞赛化的通用人设 prompt |

---

## 全流程(自托管)

### 1. 准备一台服务器
- 2C4G 以上,装好 Docker 与 docker compose。
- 一个域名(用于 HTTPS,可选但推荐)。

### 2. 起 Dify 本体
Dify 有自己的一套 compose(不在本仓库),按官方步骤:
```bash
git clone https://github.com/langgenius/dify.git
cd dify/docker
cp .env.example .env          # 按需改域名、密钥；向量库可选 pgvector
docker compose up -d
# 浏览器打开 http://<服务器IP>/install 完成初始化
```

### 3. 起 OpenAlex 检索微服务
在**本仓库根目录**:
```bash
cp deploy/.env.example deploy/.env      # 可选：填 OPENALEX_MAILTO
docker compose -f deploy/docker-compose.yml up -d --build
curl "http://localhost:8000/search?q=digital+humanities&limit=3"    # 自测
```
> 推荐让它和 Dify 同处一个 docker 网络,Dify 用内网地址 `http://openalex:8000` 调它,不必公网暴露(见 `docker-compose.yml` 注释)。

### 4. 在 Dify 配置模型
Dify 界面 → 设置 → 模型供应商 → 填 API key:
- 推荐 **Anthropic**(主力 `claude-sonnet-5-5`,难题 `claude-opus-5-5`),也可用 OpenAI / DeepSeek / Qwen 等降本。
- **Embedding 必须选多语言模型**(如 `bge-m3` / `multilingual-e5`)——知识库覆盖 11+ 语种。

### 5. 导入知识库
```bash
python deploy/prepare_knowledge_base.py      # 生成 deploy/dist/knowledge-base/
```
Dify → 知识库 → 创建 → 上传 `deploy/dist/knowledge-base/` 下所有 `.md`:
- 分段:按 Markdown 标题(`##` 平台名)切片,检索粒度最合适。
- Embedding:选第 4 步的多语言模型。
- 共 24 份(8 份公开平台 + 16 份订阅库),清单见该目录 `manifest.md`。

### 6. 接入 OpenAlex 工具
Dify → 工具 → 创建自定义工具 → 导入 `tools/openalex/dify_tool_openapi.yaml`:
- 把 schema 里 `servers.url` 改成第 3 步服务的地址(同网络填 `http://openalex:8000`)。

### 7. 建应用
Dify → 创建应用(Chatflow / Agent)→
- 人设/系统提示:粘贴 `prompts/agent_system_prompt.md`。
- 挂上第 5 步的知识库 + 第 6 步的 OpenAlex 工具。
- 编排:槽位追问 → 知识库检索 +（按需）OpenAlex 实时检索 → 方案组装。

### 8. 测试与发布
- 回归"黄金三问":检索引用是否准、能否追问细化、查不到时是否诚实降级。
- Dify 一键发布为 WebApp / 嵌入式 chatbot / API。
- 配域名 + HTTPS(Nginx/Caddy 反代 + Let's Encrypt)。

---

## 想更快验证?用 Dify 云版
不想开服务器,可先用 [dify.ai](https://dify.ai) 云版跳过第 1-2 步:直接建知识库(上传第 5 步文件)+ 建应用(贴 prompt)。
唯一差别:OpenAlex 工具需要一个公网可达地址——把 `tools/openalex/server.py` 部署到任意能公网访问的地方(一台小服务器 / Railway / Fly.io 均可),再把地址填进工具 schema。

---

## 安全提示
- 真实 API key 只填在 Dify 界面或服务器 `.env`,**不要提交到 Git**(本仓库已 gitignore `.env`)。
- 若公网暴露 OpenAlex 微服务,建议加反向代理与基本限流。
