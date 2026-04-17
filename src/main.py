"""ALL-IN-AI 主入口

示例用法和快速启动
"""

import asyncio
from loguru import logger

from src.agents import agent_registry
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

    # 导入 Agents（会自动注册）
    from src.agents.examples import EchoAgent, DialogAgent

    # 列出所有注册的 Agents
    logger.info(f"Registered agents: {agent_registry.list_agent_ids()}")

    # 创建 Echo Agent 实例
    echo_agent = agent_registry.create_instance("echo_agent")
    if echo_agent:
        await echo_agent.initialize()
        info = echo_agent.get_info()
        logger.info(f"Echo Agent info: {info}")


async def main():
    """主函数"""
    logger.info("ALL-IN-AI 数字员工平台启动")

    # 演示 Skill
    await demo_skill()

    # 演示 Agent
    await demo_agent()

    logger.info("演示完成!")


if __name__ == "__main__":
    asyncio.run(main())
