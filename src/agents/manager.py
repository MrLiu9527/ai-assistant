"""Agent 管理器

负责 Agent 的运行时管理，包括：
- 从数据库加载配置
- 创建和缓存 Agent 实例
- 管理 Agent 生命周期
"""

import uuid
from typing import Any

from loguru import logger

from src.agents.base import AgentContext, AgentResponse, BaseAgent
from src.agents.factory import AgentFactory
from src.db.session import async_session_scope
from src.models.agent import AgentConfig, AgentStatus
from src.services.agent_service import AgentConfigService
from src.services.space_service import SYSTEM_SPACE_CODE, SpaceService


class AgentManager:
    """Agent 管理器

    单例模式，管理所有运行中的 Agent 实例
    """

    _instance = None
    _initialized = False

    def __new__(cls) -> "AgentManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._agents: dict[str, BaseAgent] = {}
            cls._instance._configs: dict[str, AgentConfig] = {}
        return cls._instance

    async def initialize(self) -> None:
        """初始化管理器，加载平台级 Agent"""
        if self._initialized:
            return

        logger.info("Initializing AgentManager...")

        # 加载平台级 Agent
        await self._load_platform_agents()

        self._initialized = True
        logger.info(f"AgentManager initialized with {len(self._agents)} agents")

    async def _load_platform_agents(self) -> None:
        """加载平台级 Agent"""
        async with async_session_scope() as session:
            service = AgentConfigService(session)
            configs = await service.get_platform_agents(status=AgentStatus.PUBLISHED)

            for config in configs:
                await self._create_agent_from_config(config)

    async def _create_agent_from_config(self, config: AgentConfig) -> BaseAgent | None:
        """从配置创建 Agent 实例"""
        cache_key = self._get_cache_key(config.agent_id, config.space_id)

        agent = AgentFactory.create_from_config(config)
        if agent:
            await agent.initialize()
            self._agents[cache_key] = agent
            self._configs[cache_key] = config
            logger.info(f"Agent loaded: {config.agent_id} (scope={config.scope.value})")
            return agent
        return None

    def _get_cache_key(self, agent_id: str, space_id: uuid.UUID) -> str:
        """生成缓存键"""
        return f"{space_id}:{agent_id}"

    async def get_agent(
        self,
        agent_id: str,
        space_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
    ) -> BaseAgent | None:
        """获取 Agent 实例

        Args:
            agent_id: Agent ID
            space_id: 空间ID
            user_id: 用户ID（用于权限检查）

        Returns:
            Agent 实例或 None
        """
        cache_key = self._get_cache_key(agent_id, space_id)

        # 检查缓存
        if cache_key in self._agents:
            return self._agents[cache_key]

        # 尝试加载空间级 Agent
        async with async_session_scope() as session:
            service = AgentConfigService(session)

            # 先尝试空间级
            config = await service.get_by_agent_id(agent_id, space_id)

            # 如果没有，尝试平台级
            if not config:
                space_service = SpaceService(session)
                system_space = await space_service.get_by_code(SYSTEM_SPACE_CODE)
                if system_space:
                    config = await service.get_by_agent_id(agent_id, system_space.id)

            if config and config.status == AgentStatus.PUBLISHED:
                return await self._create_agent_from_config(config)

        return None

    async def get_platform_agent(self, agent_id: str) -> BaseAgent | None:
        """获取平台级 Agent

        Args:
            agent_id: Agent ID

        Returns:
            Agent 实例或 None
        """
        async with async_session_scope() as session:
            space_service = SpaceService(session)
            system_space = await space_service.get_by_code(SYSTEM_SPACE_CODE)
            if system_space:
                return await self.get_agent(agent_id, system_space.id)
        return None

    async def create_conversation(
        self,
        agent_id: str,
        space_id: uuid.UUID,
        user_id: uuid.UUID,
        title: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AgentContext | None:
        """创建会话

        Args:
            agent_id: Agent ID
            space_id: 空间ID
            user_id: 用户ID
            title: 会话标题
            metadata: 元数据

        Returns:
            Agent 上下文或 None
        """
        agent = await self.get_agent(agent_id, space_id, user_id)
        if not agent:
            logger.warning(f"Agent not found: {agent_id}")
            return None

        return await agent.create_conversation(
            user_id=user_id,
            space_id=space_id,
            title=title,
            metadata=metadata,
        )

    async def chat(
        self,
        agent_id: str,
        space_id: uuid.UUID,
        conversation_id: uuid.UUID,
        message: str,
        **kwargs: Any,
    ) -> AgentResponse | None:
        """发送消息

        Args:
            agent_id: Agent ID
            space_id: 空间ID
            conversation_id: 会话ID
            message: 用户消息
            **kwargs: 其他参数

        Returns:
            Agent 响应或 None
        """
        agent = await self.get_agent(agent_id, space_id)
        if not agent:
            logger.warning(f"Agent not found: {agent_id}")
            return None

        # 加载会话上下文
        context = await agent.load_conversation(conversation_id)
        if not context:
            logger.warning(f"Conversation not found: {conversation_id}")
            return None

        return await agent.chat(message, context, **kwargs)

    async def list_available_agents(
        self,
        space_id: uuid.UUID,
        user_id: uuid.UUID,
        include_platform: bool = True,
    ) -> list[dict[str, Any]]:
        """列出可用的 Agent

        Args:
            space_id: 空间ID
            user_id: 用户ID
            include_platform: 是否包含平台级 Agent

        Returns:
            Agent 信息列表
        """
        async with async_session_scope() as session:
            service = AgentConfigService(session)
            configs = await service.get_space_agents(
                space_id=space_id,
                status=AgentStatus.PUBLISHED,
                include_platform=include_platform,
            )

            return [
                {
                    "id": str(config.id),
                    "agent_id": config.agent_id,
                    "name": config.name,
                    "description": config.description,
                    "type": config.type.value,
                    "scope": config.scope.value,
                    "avatar": config.avatar,
                    "welcome_message": config.welcome_message,
                }
                for config in configs
            ]

    async def reload_agent(
        self,
        agent_id: str,
        space_id: uuid.UUID,
    ) -> BaseAgent | None:
        """重新加载 Agent（配置更新后调用）

        Args:
            agent_id: Agent ID
            space_id: 空间ID

        Returns:
            重新加载的 Agent 实例
        """
        cache_key = self._get_cache_key(agent_id, space_id)

        # 移除旧实例
        if cache_key in self._agents:
            del self._agents[cache_key]
        if cache_key in self._configs:
            del self._configs[cache_key]

        # 重新加载
        return await self.get_agent(agent_id, space_id)

    def clear_cache(self) -> None:
        """清空缓存"""
        self._agents.clear()
        self._configs.clear()
        self._initialized = False
        logger.info("AgentManager cache cleared")


# 全局 Agent 管理器实例
agent_manager = AgentManager()
