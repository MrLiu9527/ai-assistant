"""Agent 配置服务"""

import uuid
from typing import Any

from sqlalchemy import and_, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.agent import AgentConfig, AgentScope, AgentStatus, AgentType


class AgentConfigService:
    """Agent 配置服务类"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        agent_id: str,
        name: str,
        space_id: uuid.UUID,
        type: AgentType = AgentType.DIALOG,
        scope: AgentScope = AgentScope.SPACE,
        status: AgentStatus = AgentStatus.DRAFT,
        description: str | None = None,
        avatar: str | None = None,
        version: str = "1.0.0",
        created_by: uuid.UUID | None = None,
        model_provider: str = "dashscope",
        model_name: str = "qwen-turbo",
        model_config: dict[str, Any] | None = None,
        system_prompt: str | None = None,
        welcome_message: str | None = None,
        skills: list[str] | None = None,
        tools: list[str] | None = None,
        mcp_servers: list[dict[str, Any]] | None = None,
        knowledge_bases: list[str] | None = None,
        behavior_config: dict[str, Any] | None = None,
        max_context_messages: int = 20,
        max_context_tokens: int = 4000,
        config: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AgentConfig:
        """创建 Agent 配置

        Args:
            agent_id: Agent 唯一标识
            name: Agent 名称
            space_id: 所属空间ID
            type: Agent 类型
            scope: Agent 作用域
            status: Agent 状态
            description: 描述
            avatar: 头像
            version: 版本号
            created_by: 创建者ID
            model_provider: 模型提供商
            model_name: 模型名称
            model_config: 模型配置
            system_prompt: 系统提示词
            welcome_message: 欢迎消息
            skills: Skill ID 列表
            tools: Tool ID 列表
            mcp_servers: MCP 服务器配置
            knowledge_bases: 知识库ID列表
            behavior_config: 行为配置
            max_context_messages: 最大上下文消息数
            max_context_tokens: 最大上下文Token数
            config: 其他配置
            metadata: 元数据

        Returns:
            创建的 Agent 配置
        """
        agent_config = AgentConfig(
            agent_id=agent_id,
            name=name,
            space_id=space_id,
            type=type,
            scope=scope,
            status=status,
            description=description,
            avatar=avatar,
            version=version,
            created_by=created_by,
            model_provider=model_provider,
            model_name=model_name,
            model_config_=model_config or {},
            system_prompt=system_prompt,
            welcome_message=welcome_message,
            skills=skills or [],
            tools=tools or [],
            mcp_servers=mcp_servers or [],
            knowledge_bases=knowledge_bases or [],
            behavior_config=behavior_config or {},
            max_context_messages=max_context_messages,
            max_context_tokens=max_context_tokens,
            config=config or {},
            metadata_=metadata or {},
        )
        self.session.add(agent_config)
        await self.session.flush()
        await self.session.refresh(agent_config)
        return agent_config

    async def get_by_id(self, config_id: uuid.UUID) -> AgentConfig | None:
        """根据ID获取配置"""
        result = await self.session.execute(
            select(AgentConfig).where(AgentConfig.id == config_id)
        )
        return result.scalar_one_or_none()

    async def get_by_agent_id(
        self,
        agent_id: str,
        space_id: uuid.UUID | None = None,
    ) -> AgentConfig | None:
        """根据 agent_id 获取配置

        Args:
            agent_id: Agent ID
            space_id: 空间ID（可选，用于限定空间）

        Returns:
            Agent 配置或 None
        """
        query = select(AgentConfig).where(AgentConfig.agent_id == agent_id)
        if space_id:
            query = query.where(AgentConfig.space_id == space_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_platform_agents(
        self,
        status: AgentStatus | None = AgentStatus.PUBLISHED,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AgentConfig]:
        """获取平台级 Agent 列表

        Args:
            status: 状态过滤
            limit: 返回数量
            offset: 偏移量

        Returns:
            Agent 配置列表
        """
        query = select(AgentConfig).where(
            AgentConfig.scope == AgentScope.PLATFORM
        )
        if status:
            query = query.where(AgentConfig.status == status)

        query = query.order_by(AgentConfig.sort_order, AgentConfig.created_at)
        query = query.limit(limit).offset(offset)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_space_agents(
        self,
        space_id: uuid.UUID,
        status: AgentStatus | None = None,
        include_platform: bool = True,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AgentConfig]:
        """获取空间内可用的 Agent 列表

        Args:
            space_id: 空间ID
            status: 状态过滤
            include_platform: 是否包含平台级 Agent
            limit: 返回数量
            offset: 偏移量

        Returns:
            Agent 配置列表
        """
        conditions = []

        # 空间级 Agent
        space_condition = AgentConfig.space_id == space_id
        conditions.append(space_condition)

        # 平台级 Agent
        if include_platform:
            platform_condition = and_(
                AgentConfig.scope == AgentScope.PLATFORM,
                AgentConfig.status == AgentStatus.PUBLISHED,
            )
            conditions.append(platform_condition)

        query = select(AgentConfig).where(or_(*conditions))

        if status:
            query = query.where(AgentConfig.status == status)

        query = query.order_by(AgentConfig.scope, AgentConfig.sort_order, AgentConfig.created_at)
        query = query.limit(limit).offset(offset)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update(
        self,
        config_id: uuid.UUID,
        **kwargs: Any,
    ) -> AgentConfig | None:
        """更新 Agent 配置

        Args:
            config_id: 配置ID
            **kwargs: 要更新的字段

        Returns:
            更新后的配置
        """
        # 处理特殊字段名
        if "model_config" in kwargs:
            kwargs["model_config_"] = kwargs.pop("model_config")
        if "metadata" in kwargs:
            kwargs["metadata_"] = kwargs.pop("metadata")

        await self.session.execute(
            update(AgentConfig)
            .where(AgentConfig.id == config_id)
            .values(**kwargs)
        )
        return await self.get_by_id(config_id)

    async def publish(self, config_id: uuid.UUID) -> AgentConfig | None:
        """发布 Agent

        Args:
            config_id: 配置ID

        Returns:
            更新后的配置
        """
        return await self.update(config_id, status=AgentStatus.PUBLISHED)

    async def disable(self, config_id: uuid.UUID) -> AgentConfig | None:
        """禁用 Agent

        Args:
            config_id: 配置ID

        Returns:
            更新后的配置
        """
        return await self.update(config_id, status=AgentStatus.DISABLED)

    async def archive(self, config_id: uuid.UUID) -> AgentConfig | None:
        """归档 Agent

        Args:
            config_id: 配置ID

        Returns:
            更新后的配置
        """
        return await self.update(config_id, status=AgentStatus.ARCHIVED)

    async def increment_usage(self, config_id: uuid.UUID) -> None:
        """增加使用次数

        Args:
            config_id: 配置ID
        """
        config = await self.get_by_id(config_id)
        if config:
            await self.session.execute(
                update(AgentConfig)
                .where(AgentConfig.id == config_id)
                .values(usage_count=AgentConfig.usage_count + 1)
            )

    async def delete(self, config_id: uuid.UUID) -> bool:
        """删除 Agent 配置

        Args:
            config_id: 配置ID

        Returns:
            是否成功删除
        """
        config = await self.get_by_id(config_id)
        if config:
            await self.session.delete(config)
            return True
        return False

    async def clone(
        self,
        config_id: uuid.UUID,
        new_agent_id: str,
        new_name: str,
        target_space_id: uuid.UUID,
        created_by: uuid.UUID | None = None,
    ) -> AgentConfig | None:
        """克隆 Agent 配置

        Args:
            config_id: 源配置ID
            new_agent_id: 新 Agent ID
            new_name: 新名称
            target_space_id: 目标空间ID
            created_by: 创建者ID

        Returns:
            新创建的配置
        """
        source = await self.get_by_id(config_id)
        if not source:
            return None

        return await self.create(
            agent_id=new_agent_id,
            name=new_name,
            space_id=target_space_id,
            type=source.type,
            scope=AgentScope.SPACE,  # 克隆的都是空间级
            status=AgentStatus.DRAFT,
            description=source.description,
            avatar=source.avatar,
            created_by=created_by,
            model_provider=source.model_provider,
            model_name=source.model_name,
            model_config=source.model_config_,
            system_prompt=source.system_prompt,
            welcome_message=source.welcome_message,
            skills=source.skills,
            tools=source.tools,
            mcp_servers=source.mcp_servers,
            knowledge_bases=source.knowledge_bases,
            behavior_config=source.behavior_config,
            max_context_messages=source.max_context_messages,
            max_context_tokens=source.max_context_tokens,
            config=source.config,
            metadata={"cloned_from": str(config_id)},
        )
