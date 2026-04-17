"""ALL-IN-AI 主入口

示例用法和快速启动
"""

import asyncio

from loguru import logger

from src.agents import agent_manager
from src.skills import skill_registry


async def demo_skill():
    """演示 Skill 使用"""
    logger.info("=== Skill Demo ===")

    # 导入 Skills（会自动注册）
    from src.skills.common import extract_keywords, summarize_text

    # 使用关键词提取 Skill
    text = "Python is a great programming language. Python is easy to learn and use."
    result = extract_keywords(text, top_k=5)

    if result.is_success:
        logger.info(f"Keywords: {result.content['keywords']}")
    else:
        logger.error(f"Error: {result.error_message}")

    # 使用摘要 Skill
    long_text = "这是一段很长的文本。" * 20
    result = summarize_text(long_text, max_length=50)

    if result.is_success:
        logger.info(f"Summary: {result.content['summary']}")

    # 列出所有注册的 Skills
    logger.info(f"Registered skills: {[s.skill_id for s in skill_registry.list_all()]}")


async def demo_agent():
    """演示 Agent 使用"""
    logger.info("=== Agent Demo ===")

    # 初始化 Agent 管理器（会加载平台级 Agent）
    await agent_manager.initialize()

    # 获取平台级通用助手
    general_assistant = await agent_manager.get_platform_agent("general_assistant")
    if general_assistant:
        logger.info(f"General Assistant: {general_assistant.get_info()}")
    else:
        logger.warning("General Assistant not found, please run init_db.py first")

    # 获取工具助手
    tool_assistant = await agent_manager.get_platform_agent("tool_assistant")
    if tool_assistant:
        logger.info(f"Tool Assistant: {tool_assistant.get_info()}")


async def demo_conversation():
    """演示会话功能（需要数据库）"""
    logger.info("=== Conversation Demo ===")

    try:
        from src.db.session import async_session_scope
        from src.services.space_service import SYSTEM_SPACE_CODE, SpaceService
        from src.services.user_service import UserService

        # 获取用户和空间
        async with async_session_scope() as session:
            user_service = UserService(session)
            admin = await user_service.get_by_username("admin")
            if not admin:
                logger.warning("Admin user not found, skipping conversation demo")
                return

            space_service = SpaceService(session)
            system_space = await space_service.get_by_code(SYSTEM_SPACE_CODE)
            if not system_space:
                logger.warning("System space not found, skipping conversation demo")
                return

            user_id = admin.id
            space_id = system_space.id

        # 创建会话
        context = await agent_manager.create_conversation(
            agent_id="general_assistant",
            space_id=space_id,
            user_id=user_id,
            title="测试会话",
        )

        if context:
            logger.info(f"Conversation created: {context.conversation_id}")

            # 发送消息
            response = await agent_manager.chat(
                agent_id="general_assistant",
                space_id=space_id,
                conversation_id=context.conversation_id,
                message="你好，请介绍一下你自己",
            )

            if response:
                logger.info(f"Response: {response.content[:100]}...")
        else:
            logger.warning("Failed to create conversation")

    except Exception as e:
        logger.warning(f"Conversation demo failed (database may not be ready): {e}")


async def main():
    """主函数"""
    logger.info("ALL-IN-AI 数字员工平台启动")

    # 演示 Skill
    await demo_skill()

    # 演示 Agent（需要先运行 init_db.py）
    await demo_agent()

    # 演示会话（需要数据库）
    # await demo_conversation()

    logger.info("演示完成!")


if __name__ == "__main__":
    asyncio.run(main())
