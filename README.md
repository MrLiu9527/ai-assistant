# AI-Assistant 数字员工平台

该项目是 AI-Assistant 数字员工平台。所有的功能和业务由 Cursor 完成！

## 项目简介

这是一个数字员工功能平台，每个数字员工是一个 Agent，根据挂载的工具（Tools）、MCP、Skills 等不同来负责不同的职能。

### 技术栈

- **框架**：阿里 AgentScope
- **语言**：Python 3.12
- **数据库**：PostgreSQL
- **API**：FastAPI
- **ORM**：SQLAlchemy 2.0 (异步)

### 核心特性

- **多租户架构**：支持平台级和空间级 Agent 管理
- **可配置 Agent**：所有 Agent 配置存储在数据库，支持动态加载
- **会话持久化**：会话和消息自动保存到数据库
- **权限管理**：基于角色的空间成员权限控制
- **RESTful API**：完整的 API 接口，支持前后端分离

## 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone https://github.com/MrLiu9527/ai-assistant.git
cd ai-assistant

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# 安装依赖
pip install -e ".[dev]"
```

### 2. 配置环境变量

```bash
# 复制配置模板
cp .env.example .env

# 编辑 .env 文件，配置以下内容：
# - DATABASE_URL: PostgreSQL 连接地址
# - DASHSCOPE_API_KEY: 阿里云 DashScope API Key（可选）
# - OPENAI_API_KEY: OpenAI API Key（可选）
```

### 3. 启动 PostgreSQL

```bash
# 使用 Docker 启动
docker run -d \
  --name postgres-allinai \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=all_in_ai \
  -p 5432:5432 \
  postgres:15
```

### 4. 初始化数据库

```bash
# 创建表并初始化数据
python scripts/init_db.py

# 可选参数：
# --drop     删除现有表（危险）
# --no-data  不初始化默认数据
```

初始化后会创建：
- 管理员用户：`admin`
- 系统空间：用于存放平台级 Agent
- 平台级 Agent：通用助手、工具助手

### 5. 启动 API 服务

```bash
# 开发模式（自动重载）
uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8000

# 或使用脚本
python -m src.api.run
```

API 文档地址：http://localhost:8000/docs

## 前端（微前端 + assistant-ui）

仓库内 `frontend/` 为 **pnpm workspace**，包含：

- **`packages/shell`**：qiankun 主应用（端口 **5173**），通过 `loadMicroApp` 加载子应用。
- **`packages/chat-app`**：子应用（端口 **5174**），使用 `@assistant-ui/react` 的 `useLocalRuntime` + `Thread` / `Composer` 等原语，请求后端 `X-User-Id` 与 `/api/v1/space/{spaceId}/...`。

本地联调示例：

```bash
cd frontend
pnpm install

# 终端 1：子应用
pnpm dev:chat

# 终端 2：主应用（在侧栏填写 Space ID、User UUID，需与数据库一致且用户为该空间成员）
pnpm dev:shell
```

也可单独运行子应用：复制 `frontend/.env.example` 为 `frontend/.env` 并填写 `VITE_SPACE_ID`、`VITE_USER_ID` 后执行 `pnpm dev:chat`。

生产环境将子应用构建产物部署后，把主应用的 `VITE_CHAT_ENTRY` 指向子应用入口 URL（与 `vite-plugin-qiankun` 的 `base` 一致）。

Docker 镜像构建时已默认使用同域：`VITE_API_BASE_URL=/`、`VITE_CHAT_ENTRY=/child/chat/`（由 Nginx 反代 FastAPI 与静态资源）。

## 部署到 EC2（Docker + GitHub Actions）

镜像内同时运行 **Nginx（80 端口）** 与 **Uvicorn（127.0.0.1:8000）**：静态站点提供微前端，`/api/` 与 `/health` 反代到后端。数据库请使用 **RDS 或自建 PostgreSQL**，在服务器上通过环境变量注入连接串（不要把 `.env` 提交到仓库）。

### 1. 准备 EC2

- 系统建议：Ubuntu 22.04 / 24.04，安全组放行 **80**（及 SSH **22**）。
- 安装 Docker 与 Compose 插件（官方文档：[Install Docker Engine on Ubuntu](https://docs.docker.com/engine/install/ubuntu/)）。
- 将部署用户加入 `docker` 组，或允许该用户执行 `docker` / `docker compose`。

### 2. 服务器目录与配置

在 EC2 上创建目录（示例 `/opt/ai-assistant`），放入 `deploy/.env.example` 为模板的 **`.env`**（与 `docker-compose.prod.yml` 同目录），至少包含：

- `DATABASE_URL`（`postgresql+asyncpg://...`）
- `DATABASE_SYNC_URL`（`postgresql+psycopg2://...`，供迁移/脚本使用）
- `APP_ENV=production`、`DEBUG=false`
- 按需填写 `DASHSCOPE_API_KEY` 等

首次部署若库为空，可临时设置 `INIT_DB=1` 执行一次 `scripts/init_db.py`（见 `docker/entrypoint.sh`），完成后改回 `0`。

### 3. 启用 GitHub Actions 部署

仓库 **Settings → Secrets and variables → Actions** 中新建 Secret：

| Secret | 说明 |
|--------|------|
| `EC2_HOST` | 服务器公网 IP 或域名 |
| `EC2_USER` | SSH 用户名（如 `ubuntu`） |
| `EC2_SSH_KEY` | 对应私钥全文（`-----BEGIN ...` 起） |
| `DEPLOY_PATH` | 服务器上部署目录绝对路径（如 `/opt/ai-assistant`，该目录下需已有 `.env`） |

在 **Settings → Secrets and variables → Actions → Variables** 中新增：

| Variable | 值 |
|----------|-----|
| `EC2_DEPLOY_ENABLED` | `true` |

向 `main` 推送代码将触发 **Deploy to EC2**：在 Runner 上构建镜像、`docker save` 后经 SSH 传到 `DEPLOY_PATH`，再 `docker load` 与 `docker compose -f docker-compose.prod.yml up -d`。未设置 `EC2_DEPLOY_ENABLED=true` 时该工作流会跳过，避免误部署。

### 4. 本地构建与 compose 试跑

```bash
docker compose up --build
```

默认映射 **8080:80**，数据库使用 compose 内 PostgreSQL；生产请改用外部数据库并只部署 `deploy/docker-compose.prod.yml` 流程。

## 项目结构

```
ai-assistant/
├── frontend/                     # 微前端（qiankun + assistant-ui）
│   ├── packages/shell/           # 主应用
│   └── packages/chat-app/        # 对话子应用
├── src/
│   ├── api/                      # API 层
│   │   ├── app.py                # FastAPI 应用入口
│   │   ├── deps/                 # 依赖注入
│   │   │   ├── auth.py           # 认证依赖
│   │   │   ├── database.py       # 数据库依赖
│   │   │   └── space.py          # 空间权限依赖
│   │   ├── schemas/              # Pydantic 模型
│   │   └── v1/endpoints/         # API 端点
│   │       ├── agents.py         # Agent API
│   │       ├── chat.py           # 聊天 API
│   │       ├── conversations.py  # 会话 API
│   │       └── spaces.py         # 空间 API
│   │
│   ├── agents/                   # Agent 模块
│   │   ├── base.py               # Agent 基类
│   │   ├── factory.py            # Agent 工厂
│   │   ├── manager.py            # Agent 管理器
│   │   ├── registry.py           # Agent 注册中心
│   │   └── implementations/      # Agent 实现
│   │       ├── configurable_agent.py
│   │       ├── dialog_agent.py
│   │       └── tool_agent.py
│   │
│   ├── skills/                   # Skills 技能模块
│   │   ├── base/                 # 基础设施
│   │   │   ├── decorator.py      # @skill 装饰器
│   │   │   ├── registry.py       # Skill 注册中心
│   │   │   └── response.py       # 响应定义
│   │   ├── common/               # 通用 Skills
│   │   └── domain/               # 领域 Skills
│   │
│   ├── models/                   # 数据模型
│   │   ├── user.py               # 用户模型
│   │   ├── space.py              # 空间模型
│   │   ├── agent.py              # Agent 配置模型
│   │   └── conversation.py       # 会话/消息模型
│   │
│   ├── services/                 # 服务层
│   │   ├── user_service.py
│   │   ├── space_service.py
│   │   ├── agent_service.py
│   │   ├── conversation_service.py
│   │   └── message_service.py
│   │
│   ├── db/                       # 数据库
│   │   ├── base.py               # 模型基类
│   │   └── session.py            # 会话管理
│   │
│   ├── core/                     # 核心配置
│   │   └── config.py             # 应用配置
│   │
│   └── utils/                    # 工具函数
│
├── tests/                        # 测试
├── configs/                      # 配置文件
│   └── model_config.json         # LLM 模型配置
├── migrations/                   # 数据库迁移
├── scripts/                      # 脚本
│   └── init_db.py                # 数据库初始化
├── docs/                         # 文档
│   └── SKILLS_DEVELOPMENT_GUIDE.md
├── pyproject.toml                # 项目配置
├── alembic.ini                   # Alembic 配置
├── Dockerfile                    # 生产镜像（Nginx + API + 前端静态）
├── docker-compose.yml            # 本地一体化试跑（可选内置 Postgres）
├── docker/                       # 镜像内 Nginx 与入口脚本
├── deploy/                       # EC2 生产 compose 与 env 示例
├── .github/workflows/            # CI 与 EC2 部署
└── .env.example                  # 环境变量模板
```

## 数据库设计

### 表结构

| 表名 | 说明 |
|------|------|
| `users` | 用户表 |
| `spaces` | 空间表（工作区） |
| `space_members` | 空间成员关系表 |
| `agent_configs` | Agent 配置表 |
| `conversations` | 会话表 |
| `messages` | 消息表 |

### 核心概念

- **用户 (User)**：系统用户，可以属于多个空间
- **空间 (Space)**：工作区，分为系统空间和用户空间
- **Agent**：数字员工，分为平台级（所有用户可用）和空间级（仅空间成员可用）
- **会话 (Conversation)**：用户与 Agent 的对话会话
- **消息 (Message)**：会话中的消息记录

## API 接口

### 认证

开发环境使用 `X-User-Id` Header 传递用户 ID：

```bash
curl -H "X-User-Id: <user-uuid>" http://localhost:8000/api/v1/...
```

### Agent API

路径前缀：`/api/v1/space/{spaceId}/agents`

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/` | 获取 Agent 列表 | member |
| GET | `/{agentId}` | 获取 Agent 详情 | member |
| POST | `/` | 创建 Agent | admin |
| PUT | `/{agentId}` | 更新 Agent | admin |
| DELETE | `/{agentId}` | 删除 Agent | admin |
| POST | `/{agentId}/publish` | 发布 Agent | admin |
| POST | `/{agentId}/clone` | 克隆 Agent | admin |

### Conversation API

路径前缀：`/api/v1/space/{spaceId}/conversations`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | 获取会话列表 |
| POST | `/` | 创建会话 |
| GET | `/{id}` | 获取会话详情 |
| PUT | `/{id}` | 更新会话（标题、置顶） |
| DELETE | `/{id}` | 删除会话 |
| GET | `/{id}/messages` | 获取消息列表 |
| POST | `/{id}/end` | 结束会话 |

### Chat API

路径前缀：`/api/v1/space/{spaceId}/chat`

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/{agentId}` | 快速聊天（自动创建会话） |
| POST | `/conversations/{id}/messages` | 在会话中发送消息 |

### Space API

路径前缀：`/api/v1/spaces`

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/` | 获取用户的空间列表 | - |
| POST | `/` | 创建空间 | - |
| GET | `/{spaceId}` | 获取空间详情 | member |
| PUT | `/{spaceId}` | 更新空间 | admin |
| DELETE | `/{spaceId}` | 删除空间 | owner |
| GET | `/{spaceId}/members` | 获取成员列表 | member |
| POST | `/{spaceId}/members` | 添加成员 | admin |
| PUT | `/{spaceId}/members/{userId}` | 更新成员角色 | admin |
| DELETE | `/{spaceId}/members/{userId}` | 移除成员 | admin |

## 使用示例

### 1. 获取用户和空间信息

```bash
# 从数据库获取 admin 用户 ID 和系统空间 ID
# 或查看 init_db.py 的输出日志
```

### 2. 查看可用的 Agent

```bash
curl -H "X-User-Id: $USER_ID" \
  "http://localhost:8000/api/v1/space/$SPACE_ID/agents"
```

### 3. 与 Agent 聊天

```bash
# 快速聊天（自动创建会话）
curl -X POST \
  -H "X-User-Id: $USER_ID" \
  -H "Content-Type: application/json" \
  -d '{"message": "你好，请介绍一下你自己"}' \
  "http://localhost:8000/api/v1/space/$SPACE_ID/chat/general_assistant"
```

### 4. 创建自定义 Agent

```bash
curl -X POST \
  -H "X-User-Id: $USER_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "my_assistant",
    "name": "我的助手",
    "description": "自定义的 AI 助手",
    "type": "dialog",
    "system_prompt": "你是一个专业的助手...",
    "model_provider": "dashscope",
    "model_name": "qwen-turbo"
  }' \
  "http://localhost:8000/api/v1/space/$SPACE_ID/agents"

# 发布 Agent
curl -X POST \
  -H "X-User-Id: $USER_ID" \
  "http://localhost:8000/api/v1/space/$SPACE_ID/agents/my_assistant/publish"
```

## 扩展开发

### 创建自定义 Skill

```python
from src.skills import skill, SkillResponse

@skill(
    skill_id="domain.my_skill",
    name="我的技能",
    description="技能描述",
    category="domain",
)
def my_skill(param1: str, param2: int) -> SkillResponse:
    result = process(param1, param2)
    return SkillResponse.success(content=result)
```

### 创建自定义 Agent 类型

```python
from src.agents.base import BaseAgent, AgentContext, AgentResponse
from src.agents.factory import register_agent_type
from src.models.agent import AgentType

@register_agent_type(AgentType.CUSTOM)
class MyCustomAgent(BaseAgent):
    agent_type = "custom"
    
    async def _process_message(
        self,
        message: str,
        context: AgentContext,
        **kwargs,
    ) -> AgentResponse:
        # 实现自定义逻辑
        return AgentResponse(content="响应内容")
```

## 测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/skills/

# 生成覆盖率报告
pytest --cov=src --cov-report=html
```

## 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `APP_ENV` | 运行环境 | development |
| `DEBUG` | 调试模式 | true |
| `DATABASE_URL` | 数据库连接（异步） | postgresql+asyncpg://... |
| `DATABASE_SYNC_URL` | 数据库连接（同步） | postgresql+psycopg2://... |
| `DASHSCOPE_API_KEY` | 阿里云 API Key | - |
| `OPENAI_API_KEY` | OpenAI API Key | - |

## 相关文档

- [Skills 开发规范](docs/SKILLS_DEVELOPMENT_GUIDE.md)
- [API 文档](http://localhost:8000/docs)（启动服务后访问）

## License

MIT
