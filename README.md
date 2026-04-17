# ALL-IN-AI 数字员工平台

该项目是 ALL-IN-AI 数字员工平台。所有的功能和业务由 Cursor 完成！

## 项目简介

这是一个数字员工功能平台，每个数字员工是一个 Agent，根据挂载的工具（Tools）、MCP、Skills 等不同来负责不同的职能。

- **框架**：阿里 AgentScope
- **语言**：Python 3.12
- **数据库**：PostgreSQL

## 项目结构

```
/workspace
├── src/
│   ├── agents/              # Agent 定义
│   │   ├── base.py          # Agent 基类
│   │   ├── registry.py      # Agent 注册中心
│   │   └── examples/        # 示例 Agents
│   │
│   ├── skills/              # Skills 技能模块
│   │   ├── base/            # Skill 基础设施
│   │   │   ├── decorator.py # @skill 装饰器
│   │   │   ├── registry.py  # Skill 注册中心
│   │   │   └── response.py  # Skill 响应定义
│   │   ├── common/          # 通用 Skills
│   │   └── domain/          # 领域特定 Skills
│   │
│   ├── tools/               # Tools 工具
│   ├── mcp/                 # MCP 协议
│   ├── models/              # 数据模型
│   │   ├── conversation.py  # 会话和消息模型
│   │   └── agent.py         # Agent 配置模型
│   │
│   ├── services/            # 服务层
│   ├── db/                  # 数据库
│   ├── core/                # 核心配置
│   └── utils/               # 工具函数
│
├── tests/                   # 测试
├── configs/                 # 配置文件
├── migrations/              # 数据库迁移
├── scripts/                 # 脚本
└── docs/                    # 文档
```

## 快速开始

### 1. 安装依赖

```bash
# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate  # Windows

# 安装依赖
pip install -e ".[dev]"
```

### 2. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，配置数据库和 API Key
```

### 3. 初始化数据库

```bash
# 创建数据库表
python scripts/init_db.py

# 或使用 Alembic 迁移
alembic upgrade head
```

### 4. 运行示例

```bash
python -m src.main
```

## 核心概念

### Agent（数字员工）

Agent 是一个具有特定职能的智能代理。每个 Agent 可以：

- 与用户进行对话
- 使用挂载的 Skills 和 Tools
- 维护会话历史（持久化到数据库）

```python
from src.agents import agent_registry
from src.agents.examples import EchoAgent

# 通过注册中心创建 Agent
agent = agent_registry.create_instance("echo_agent")

# 创建会话
context = await agent.create_conversation(user_id="user_123")

# 对话
response = await agent.chat("Hello!", context)
print(response.content)
```

### Skill（技能）

Skill 是 Agent 的能力模块，使用 `@skill` 装饰器定义：

```python
from src.skills import skill, SkillResponse

@skill(
    skill_id="my.custom.skill",
    name="自定义技能",
    description="这是一个自定义技能",
)
def my_skill(param1: str, param2: int) -> SkillResponse:
    result = do_something(param1, param2)
    return SkillResponse.success(content=result)
```

### 会话持久化

所有会话和消息都会自动保存到 PostgreSQL 数据库：

```python
# 创建新会话
context = await agent.create_conversation(
    user_id="user_123",
    title="咨询问题",
)

# 加载已有会话
context = await agent.load_conversation(conversation_id)

# 对话（自动保存消息）
response = await agent.chat("你好", context)
```

## 扩展开发

### 创建自定义 Agent

```python
from src.agents.base import BaseAgent, AgentContext, AgentResponse
from src.agents.registry import agent_registry

@agent_registry.register()
class MyCustomAgent(BaseAgent):
    agent_id = "my_custom_agent"
    agent_type = "custom"
    name = "自定义 Agent"
    description = "这是一个自定义 Agent"

    async def _process_message(
        self,
        message: str,
        context: AgentContext,
        **kwargs,
    ) -> AgentResponse:
        # 实现你的逻辑
        return AgentResponse(content="响应内容")
```

### 创建自定义 Skill

```python
from src.skills import skill, SkillResponse

@skill(
    skill_id="domain.my_skill",
    name="我的技能",
    description="技能描述",
    category="domain",
    retries=3,  # 失败重试
    timeout=30,  # 超时时间
)
async def my_async_skill(data: dict) -> SkillResponse:
    # 异步技能实现
    result = await process_data(data)
    return SkillResponse.success(content=result)
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

## 文档

- [Skills 开发规范](docs/SKILLS_DEVELOPMENT_GUIDE.md)

## License

MIT
