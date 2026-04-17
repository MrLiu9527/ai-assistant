"""Agent 测试"""

import uuid

import pytest

from src.agents.base import AgentContext
from src.agents.implementations.configurable_agent import ConfigurableAgent
from src.models.agent import AgentConfig, AgentScope, AgentStatus, AgentType


class TestConfigurableAgent:
    """ConfigurableAgent 测试"""

    @pytest.fixture
    def mock_config(self):
        """创建 Mock Agent 配置"""
        config = AgentConfig(
            id=uuid.uuid4(),
            agent_id="test_agent",
            name="测试助手",
            description="测试用的 Agent",
            type=AgentType.DIALOG,
            scope=AgentScope.SPACE,
            status=AgentStatus.PUBLISHED,
            version="1.0.0",
            space_id=uuid.uuid4(),
            model_provider="dashscope",
            model_name="qwen-turbo",
            system_prompt="你是一个测试助手。",
            welcome_message="欢迎使用测试助手！",
            skills=[],
            tools=[],
        )
        return config

    def test_create_agent_from_config(self, mock_config):
        """测试从配置创建 Agent"""
        agent = ConfigurableAgent(config=mock_config)

        assert agent.agent_id == "test_agent"
        assert agent.name == "测试助手"
        assert agent.model_provider == "dashscope"
        assert agent.model_name == "qwen-turbo"

    def test_agent_info(self, mock_config):
        """测试获取 Agent 信息"""
        agent = ConfigurableAgent(config=mock_config)
        info = agent.get_info()

        assert info["agent_id"] == "test_agent"
        assert info["name"] == "测试助手"
        assert info["scope"] == "space"

    def test_get_welcome_message(self, mock_config):
        """测试获取欢迎消息"""
        agent = ConfigurableAgent(config=mock_config)

        assert agent.get_welcome_message() == "欢迎使用测试助手！"

    @pytest.mark.asyncio
    async def test_initialize(self, mock_config):
        """测试初始化"""
        agent = ConfigurableAgent(config=mock_config)
        await agent.initialize()

        assert agent._initialized is True

    @pytest.mark.asyncio
    async def test_get_conversation_history(self, mock_config):
        """测试获取会话历史"""
        agent = ConfigurableAgent(config=mock_config)
        await agent.initialize()

        context = AgentContext(
            user_id=uuid.uuid4(),
            space_id=mock_config.space_id,
        )

        history = agent.get_conversation_history(context)

        # 应该包含系统消息
        assert len(history) == 1
        assert history[0]["role"] == "system"
        assert "测试助手" in history[0]["content"]
