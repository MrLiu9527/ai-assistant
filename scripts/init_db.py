"""数据库初始化脚本

用于创建数据库表和初始数据
"""

import asyncio
import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger

from src.core.config import settings
from src.db.base import Base
from src.db.session import async_engine

# 导入所有模型
from src.models.user import User  # noqa: F401
from src.models.space import Space, SpaceMember  # noqa: F401
from src.models.agent import AgentConfig  # noqa: F401
from src.models.conversation import Conversation, Message  # noqa: F401


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


async def init_admin_user() -> None:
    """初始化管理员用户"""
    from src.db.session import async_session_scope
    from src.services.user_service import UserService

    admin_password = os.environ.get("ADMIN_PASSWORD", "admin123")

    async with async_session_scope() as session:
        service = UserService(session)
        admin = await service.get_or_create_admin(password=admin_password)
        logger.info(f"Admin user ready: {admin.username} ({admin.id})")


async def init_system_space() -> None:
    """初始化系统空间"""
    from src.db.session import async_session_scope
    from src.services.user_service import UserService
    from src.services.space_service import SpaceService

    async with async_session_scope() as session:
        # 获取管理员
        user_service = UserService(session)
        admin = await user_service.get_by_username("admin")
        if not admin:
            logger.error("Admin user not found, please init admin first")
            return

        # 创建系统空间
        space_service = SpaceService(session)
        system_space = await space_service.get_or_create_system_space(admin.id)
        logger.info(f"System space ready: {system_space.code} ({system_space.id})")


async def init_platform_agents() -> None:
    """初始化平台级 Agent"""
    from src.db.session import async_session_scope
    from src.services.user_service import UserService
    from src.services.space_service import SpaceService, SYSTEM_SPACE_CODE
    from src.services.agent_service import AgentConfigService
    from src.models.agent import AgentType, AgentScope, AgentStatus

    async with async_session_scope() as session:
        # 获取系统空间
        space_service = SpaceService(session)
        system_space = await space_service.get_by_code(SYSTEM_SPACE_CODE)
        if not system_space:
            logger.error("System space not found")
            return

        # 获取管理员
        user_service = UserService(session)
        admin = await user_service.get_by_username("admin")

        agent_service = AgentConfigService(session)

        # 平台级 Agent 定义
        platform_agents = [
            {
                "agent_id": "general_assistant",
                "name": "通用助手",
                "description": "一个通用的 AI 对话助手，可以回答各种问题、提供建议和帮助完成任务。",
                "type": AgentType.DIALOG,
                "system_prompt": """你是 AI-Assistant 平台的通用助手。

你的职责是：
1. 回答用户的各种问题
2. 提供有价值的建议和信息
3. 帮助用户完成日常任务
4. 以友好、专业的态度与用户交流

请用清晰、简洁的语言回应用户。如果遇到不确定的问题，请诚实告知用户。""",
                "welcome_message": "您好！我是通用助手，有什么可以帮助您的吗？",
                "model_provider": "dashscope",
                "model_name": "qwen-turbo",
                "sort_order": 1,
            },
            {
                "agent_id": "tool_assistant",
                "name": "工具助手",
                "description": "一个可以调用各种工具的 AI 助手，帮助用户完成需要使用工具的复杂任务。",
                "type": AgentType.TOOL,
                "system_prompt": """你是 AI-Assistant 平台的工具助手。

你的职责是：
1. 理解用户的需求
2. 选择合适的工具来完成任务
3. 执行工具调用并解释结果
4. 在需要时进行多步骤推理

你可以使用平台提供的各种工具，包括文本处理、数据分析等。
当需要使用工具时，请先说明你要做什么，然后调用相应的工具。""",
                "welcome_message": "您好！我是工具助手，可以帮您使用各种工具完成任务。请告诉我您需要做什么？",
                "model_provider": "dashscope",
                "model_name": "qwen-plus",
                "skills": [
                    "common.text.extract_keywords",
                    "common.text.summarize",
                ],
                "sort_order": 2,
            },
        ]

        for agent_data in platform_agents:
            # 检查是否已存在
            existing = await agent_service.get_by_agent_id(
                agent_data["agent_id"],
                system_space.id,
            )
            if existing:
                logger.info(f"Platform agent already exists: {agent_data['agent_id']}")
                continue

            # 创建 Agent
            await agent_service.create(
                agent_id=agent_data["agent_id"],
                name=agent_data["name"],
                description=agent_data["description"],
                space_id=system_space.id,
                type=agent_data["type"],
                scope=AgentScope.PLATFORM,
                status=AgentStatus.PUBLISHED,
                created_by=admin.id if admin else None,
                model_provider=agent_data.get("model_provider", "dashscope"),
                model_name=agent_data.get("model_name", "qwen-turbo"),
                system_prompt=agent_data.get("system_prompt"),
                welcome_message=agent_data.get("welcome_message"),
                skills=agent_data.get("skills", []),
                tools=agent_data.get("tools", []),
                config={"sort_order": agent_data.get("sort_order", 0)},
            )
            logger.info(f"Created platform agent: {agent_data['agent_id']}")

    logger.info("Platform agents initialized!")


async def main(
    drop: bool = False,
    create: bool = True,
    init_data: bool = True,
) -> None:
    """主函数

    Args:
        drop: 是否删除现有表
        create: 是否创建表
        init_data: 是否初始化数据
    """
    logger.info(f"Database URL: {settings.database_url}")

    if drop:
        await drop_tables()

    if create:
        await create_tables()

    if init_data:
        await init_admin_user()
        await init_system_space()
        await init_platform_agents()

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
        "--no-data",
        action="store_true",
        help="不初始化数据",
    )

    args = parser.parse_args()

    asyncio.run(
        main(
            drop=args.drop,
            create=not args.no_create,
            init_data=not args.no_data,
        )
    )
