"""Echo Agent 测试"""

import pytest

from src.agents.examples.echo_agent import EchoAgent
from src.agents.base import AgentContext


class TestEchoAgent:
    """EchoAgent 测试"""

    @pytest.fixture
    def agent(self):
        """创建 Echo Agent 实例"""
        return EchoAgent()

    def test_agent_info(self, agent):
        """测试 Agent 信息"""
        info = agent.get_info()

        assert info["agent_id"] == "echo_agent"
        assert info["agent_type"] == "echo"
        assert info["name"] == "Echo Agent"

    @pytest.mark.asyncio
    async def test_process_message(self, agent):
        """测试消息处理"""
        await agent.initialize()

        context = AgentContext(user_id="test_user")
        # 直接调用 _process_message 避免数据库操作
        response = await agent._process_message("Hello", context)

        assert "Hello" in response.content
        assert response.metadata.get("echo") is True

    @pytest.mark.asyncio
    async def test_custom_prefix(self):
        """测试自定义前缀"""
        agent = EchoAgent(config={"prefix": "Reply: "})
        await agent.initialize()

        context = AgentContext(user_id="test_user")
        response = await agent._process_message("Test", context)

        assert response.content.startswith("Reply: ")
