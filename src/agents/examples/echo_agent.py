"""Echo Agent 示例

一个简单的回显 Agent，用于测试和演示
"""

from typing import Any

from src.agents.base import BaseAgent, AgentContext, AgentResponse
from src.agents.registry import agent_registry


@agent_registry.register()
class EchoAgent(BaseAgent):
    """Echo Agent

    简单的回显 Agent，将用户输入原样返回
    主要用于测试和演示
    """

    agent_id = "echo_agent"
    agent_type = "echo"
    name = "Echo Agent"
    description = "一个简单的回显 Agent，将用户输入原样返回"
    version = "1.0.0"

    def _default_system_prompt(self) -> str:
        return "你是一个回显机器人，会将用户的消息原样返回。"

    async def _process_message(
        self,
        message: str,
        context: AgentContext,
        **kwargs: Any,
    ) -> AgentResponse:
        """处理消息 - 简单回显"""
        prefix = self.config.get("prefix", "Echo: ")

        return AgentResponse(
            content=f"{prefix}{message}",
            conversation_id=context.conversation_id,
            metadata={
                "echo": True,
                "original_message": message,
            },
        )
