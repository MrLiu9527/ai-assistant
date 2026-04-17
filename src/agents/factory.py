"""Agent 工厂

根据配置动态创建 Agent 实例
"""

from typing import Any

from loguru import logger

from src.agents.base import BaseAgent
from src.agents.registry import agent_registry
from src.models.agent import AgentConfig, AgentType


class AgentFactory:
    """Agent 工厂

    负责根据数据库配置创建 Agent 实例
    """

    # Agent 类型到实现类的映射
    _type_mapping: dict[AgentType, type[BaseAgent]] = {}

    @classmethod
    def register_type(
        cls,
        agent_type: AgentType,
        agent_class: type[BaseAgent],
    ) -> None:
        """注册 Agent 类型实现

        Args:
            agent_type: Agent 类型
            agent_class: Agent 实现类
        """
        cls._type_mapping[agent_type] = agent_class
        logger.info(f"Agent type registered: {agent_type.value} -> {agent_class.__name__}")

    @classmethod
    def get_agent_class(cls, agent_type: AgentType) -> type[BaseAgent] | None:
        """获取 Agent 类型对应的实现类

        Args:
            agent_type: Agent 类型

        Returns:
            Agent 实现类或 None
        """
        return cls._type_mapping.get(agent_type)

    @classmethod
    def create_from_config(cls, config: AgentConfig) -> BaseAgent | None:
        """从数据库配置创建 Agent 实例

        Args:
            config: Agent 配置

        Returns:
            Agent 实例或 None
        """
        # 获取对应类型的实现类
        agent_class = cls.get_agent_class(config.type)

        if agent_class is None:
            # 尝试从注册中心获取
            agent_class = agent_registry.get_class(config.agent_id)

        if agent_class is None:
            # 使用默认实现
            from src.agents.implementations.configurable_agent import ConfigurableAgent
            agent_class = ConfigurableAgent

        try:
            agent = agent_class(config=config)
            logger.info(
                f"Agent created from config: {config.agent_id} "
                f"(type={config.type.value}, class={agent_class.__name__})"
            )
            return agent
        except Exception as e:
            logger.error(f"Failed to create agent from config: {config.agent_id}, error: {e}")
            return None

    @classmethod
    async def create_and_initialize(cls, config: AgentConfig) -> BaseAgent | None:
        """创建并初始化 Agent

        Args:
            config: Agent 配置

        Returns:
            初始化后的 Agent 实例或 None
        """
        agent = cls.create_from_config(config)
        if agent:
            await agent.initialize()
        return agent

    @classmethod
    def list_supported_types(cls) -> list[dict[str, Any]]:
        """列出支持的 Agent 类型

        Returns:
            类型信息列表
        """
        types = []
        for agent_type, agent_class in cls._type_mapping.items():
            types.append({
                "type": agent_type.value,
                "class_name": agent_class.__name__,
                "description": getattr(agent_class, "default_description", ""),
            })
        return types


def register_agent_type(agent_type: AgentType):
    """装饰器：注册 Agent 类型实现

    Args:
        agent_type: Agent 类型

    Example:
        >>> @register_agent_type(AgentType.DIALOG)
        ... class DialogAgent(BaseAgent):
        ...     pass
    """
    def decorator(cls: type[BaseAgent]) -> type[BaseAgent]:
        AgentFactory.register_type(agent_type, cls)
        return cls

    return decorator
