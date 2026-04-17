"""数据库初始化脚本

用于创建数据库表和初始数据
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger

from src.core.config import settings
from src.db.base import Base
from src.db.session import async_engine, sync_engine

# 导入所有模型
from src.models.conversation import Conversation, Message  # noqa: F401
from src.models.agent import AgentConfig  # noqa: F401


async def create_tables() -> None:
    """创建所有数据库表"""
    logger.info("Creating database tables...")
    
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("Database tables created successfully!")


async def drop_tables() -> None:
    """删除所有数据库表（危险操作）"""
    logger.warning("Dropping all database tables...")
    
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    logger.info("Database tables dropped!")


async def init_default_agents() -> None:
    """初始化默认 Agent 配置"""
    from sqlalchemy import select
    from src.db.session import async_session_scope
    from src.models.agent import AgentConfig, AgentType

    default_agents = [
        {
            "agent_id": "general_assistant",
            "name": "通用助手",
            "type": AgentType.DIALOG,
            "description": "一个通用的对话助手，可以回答各种问题",
            "version": "1.0.0",
            "system_prompt": """你是一个友好、专业的 AI 助手。

你的职责是：
1. 回答用户的问题
2. 帮助用户完成任务
3. 提供有价值的建议和信息

请用清晰、简洁的语言与用户交流。""",
            "model_config_name": "default",
            "skills": [],
            "tools": [],
            "is_enabled": True,
            "is_public": True,
        },
        {
            "agent_id": "data_analyst",
            "name": "数据分析师",
            "type": AgentType.REACT,
            "description": "专业的数据分析数字员工，可以处理数据分析任务",
            "version": "1.0.0",
            "system_prompt": """你是一个专业的数据分析师数字员工。

你的职责包括：
1. 根据用户需求查询和提取数据
2. 对数据进行统计分析
3. 生成分析报告
4. 创建数据可视化图表

请使用提供的工具来完成用户的数据分析任务。""",
            "model_config_name": "default",
            "skills": ["data.analytics.summarize", "data.analytics.aggregate"],
            "tools": [],
            "is_enabled": True,
            "is_public": True,
        },
    ]

    async with async_session_scope() as session:
        for agent_data in default_agents:
            # 检查是否已存在
            result = await session.execute(
                select(AgentConfig).where(
                    AgentConfig.agent_id == agent_data["agent_id"]
                )
            )
            existing = result.scalar_one_or_none()

            if existing:
                logger.info(f"Agent already exists: {agent_data['agent_id']}")
                continue

            agent = AgentConfig(**agent_data)
            session.add(agent)
            logger.info(f"Created default agent: {agent_data['agent_id']}")

        await session.commit()

    logger.info("Default agents initialized!")


async def main(
    drop: bool = False,
    create: bool = True,
    init_agents: bool = True,
) -> None:
    """主函数

    Args:
        drop: 是否删除现有表
        create: 是否创建表
        init_agents: 是否初始化默认 Agent
    """
    logger.info(f"Database URL: {settings.database_url}")

    if drop:
        await drop_tables()

    if create:
        await create_tables()

    if init_agents:
        await init_default_agents()

    logger.info("Database initialization completed!")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="数据库初始化脚本")
    parser.add_argument(
        "--drop",
        action="store_true",
        help="删除现有表（危险操作）",
    )
    parser.add_argument(
        "--no-create",
        action="store_true",
        help="不创建表",
    )
    parser.add_argument(
        "--no-agents",
        action="store_true",
        help="不初始化默认 Agent",
    )

    args = parser.parse_args()

    asyncio.run(
        main(
            drop=args.drop,
            create=not args.no_create,
            init_agents=not args.no_agents,
        )
    )
