"""Agent 注册中心"""

from typing import Any, TypeVar

from loguru import logger

from src.agents.base import BaseAgent

T = TypeVar("T", bound=BaseAgent)


class AgentRegistry:
    """Agent 注册中心

    管理所有已注册的 Agent 类型，支持动态注册和实例化
    """

    _instance = None

    def __new__(cls) -> "AgentRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._agents: dict[str, type[BaseAgent]] = {}
            cls._instance._instances: dict[str, BaseAgent] = {}
        return cls._instance

    def register(
        self,
        agent_id: str | None = None,
    ):
        """注册 Agent 类的装饰器

        Args:
            agent_id: Agent ID，如果不提供则使用类的 agent_id 属性

        Returns:
            装饰器函数

        Example:
            >>> @agent_registry.register()
            ... class MyAgent(BaseAgent):
            ...     agent_id = "my_agent"
            ...     ...
        """
        def decorator(cls: type[T]) -> type[T]:
            nonlocal agent_id
            if agent_id is None:
                agent_id = getattr(cls, "agent_id", cls.__name__.lower())

            if agent_id in self._agents:
                logger.warning(f"Agent already registered, overwriting: {agent_id}")

            self._agents[agent_id] = cls
            logger.info(f"Agent registered: {agent_id} ({cls.__name__})")

            return cls

        return decorator

    def register_class(
        self,
        cls: type[BaseAgent],
        agent_id: str | None = None,
    ) -> None:
        """直接注册 Agent 类

        Args:
            cls: Agent 类
            agent_id: Agent ID
        """
        if agent_id is None:
            agent_id = getattr(cls, "agent_id", cls.__name__.lower())

        if agent_id in self._agents:
            logger.warning(f"Agent already registered, overwriting: {agent_id}")

        self._agents[agent_id] = cls
        logger.info(f"Agent registered: {agent_id} ({cls.__name__})")

    def unregister(self, agent_id: str) -> bool:
        """注销 Agent

        Args:
            agent_id: Agent ID

        Returns:
            是否成功注销
        """
        if agent_id in self._agents:
            del self._agents[agent_id]
            if agent_id in self._instances:
                del self._instances[agent_id]
            logger.info(f"Agent unregistered: {agent_id}")
            return True
        return False

    def get_class(self, agent_id: str) -> type[BaseAgent] | None:
        """获取 Agent 类

        Args:
            agent_id: Agent ID

        Returns:
            Agent 类或 None
        """
        return self._agents.get(agent_id)

    def create_instance(
        self,
        agent_id: str,
        **kwargs: Any,
    ) -> BaseAgent | None:
        """创建 Agent 实例

        Args:
            agent_id: Agent ID
            **kwargs: 传递给 Agent 构造函数的参数

        Returns:
            Agent 实例或 None
        """
        cls = self.get_class(agent_id)
        if cls is None:
            logger.error(f"Agent not found: {agent_id}")
            return None

        try:
            instance = cls(**kwargs)
            logger.info(f"Agent instance created: {agent_id}")
            return instance
        except Exception as e:
            logger.error(f"Failed to create agent instance: {agent_id}, error: {e}")
            return None

    def get_or_create_instance(
        self,
        agent_id: str,
        **kwargs: Any,
    ) -> BaseAgent | None:
        """获取或创建 Agent 单例实例

        Args:
            agent_id: Agent ID
            **kwargs: 传递给 Agent 构造函数的参数

        Returns:
            Agent 实例或 None
        """
        if agent_id not in self._instances:
            instance = self.create_instance(agent_id, **kwargs)
            if instance:
                self._instances[agent_id] = instance
        return self._instances.get(agent_id)

    def list_agents(self) -> list[dict[str, Any]]:
        """列出所有已注册的 Agent

        Returns:
            Agent 信息列表
        """
        agents = []
        for agent_id, cls in self._agents.items():
            agents.append({
                "agent_id": agent_id,
                "class_name": cls.__name__,
                "agent_type": getattr(cls, "agent_type", "unknown"),
                "name": getattr(cls, "name", agent_id),
                "description": getattr(cls, "description", ""),
                "version": getattr(cls, "version", "1.0.0"),
            })
        return agents

    def list_agent_ids(self) -> list[str]:
        """列出所有已注册的 Agent ID

        Returns:
            Agent ID 列表
        """
        return list(self._agents.keys())

    def is_registered(self, agent_id: str) -> bool:
        """检查 Agent 是否已注册

        Args:
            agent_id: Agent ID

        Returns:
            是否已注册
        """
        return agent_id in self._agents

    def clear(self) -> None:
        """清空所有注册"""
        self._agents.clear()
        self._instances.clear()
        logger.info("Agent registry cleared")


# 全局 Agent 注册中心实例
agent_registry = AgentRegistry()
