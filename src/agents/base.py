"""Agent 基类定义"""

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, TypeVar

from loguru import logger

from src.models.agent import AgentConfig, AgentScope
from src.models.conversation import Conversation, Message


@dataclass
class AgentContext:
    """Agent 执行上下文

    包含会话信息和运行时状态
    """

    user_id: uuid.UUID
    space_id: uuid.UUID
    conversation_id: uuid.UUID | None = None
    conversation: Conversation | None = None
    messages: list[Message] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "user_id": str(self.user_id),
            "space_id": str(self.space_id),
            "conversation_id": str(self.conversation_id) if self.conversation_id else None,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "message_count": len(self.messages),
        }


@dataclass
class AgentResponse:
    """Agent 响应"""

    content: str
    message_id: uuid.UUID | None = None
    conversation_id: uuid.UUID | None = None
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "content": self.content,
            "message_id": str(self.message_id) if self.message_id else None,
            "conversation_id": str(self.conversation_id) if self.conversation_id else None,
            "tool_calls": self.tool_calls,
            "metadata": self.metadata,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
        }


T = TypeVar("T", bound="BaseAgent")


class BaseAgent(ABC):
    """Agent 基类

    所有 Agent 必须继承此类并实现必要的方法。
    支持：
    - 从数据库配置加载
    - 会话和消息持久化
    - 可扩展的 Skill 和 Tool 挂载
    - 上下文管理
    """

    # 类属性，子类可以覆盖
    agent_type: str = "base"
    default_name: str = "Base Agent"
    default_description: str = "基础 Agent"
    default_version: str = "1.0.0"

    def __init__(
        self,
        config: AgentConfig | None = None,
        system_prompt: str | None = None,
        model_config_name: str | None = None,
        skills: list[str] | None = None,
        tools: list[str] | None = None,
        agent_config: dict[str, Any] | None = None,
    ):
        """初始化 Agent

        Args:
            config: 数据库中的 Agent 配置（优先使用）
            system_prompt: 系统提示词（config 为空时使用）
            model_config_name: 模型配置名称
            skills: 挂载的 Skill ID 列表
            tools: 挂载的 Tool ID 列表
            agent_config: Agent 特定配置
        """
        # 如果有数据库配置，从配置加载
        if config:
            self._load_from_config(config)
        else:
            # 使用参数初始化
            self.agent_id = agent_config.get("agent_id", self.__class__.__name__.lower()) if agent_config else self.__class__.__name__.lower()
            self.name = agent_config.get("name", self.default_name) if agent_config else self.default_name
            self.description = agent_config.get("description", self.default_description) if agent_config else self.default_description
            self.version = agent_config.get("version", self.default_version) if agent_config else self.default_version
            self.scope = AgentScope.SPACE
            self.space_id: uuid.UUID | None = None
            self.config_id: uuid.UUID | None = None

            self.system_prompt = system_prompt or self._default_system_prompt()
            self.model_config_name = model_config_name or "default"
            self.model_provider = "dashscope"
            self.model_name = "qwen-turbo"
            self.model_config: dict[str, Any] = {}

            self.skills = skills or []
            self.tools = tools or []
            self.mcp_servers: list[dict[str, Any]] = []

            self.behavior_config: dict[str, Any] = {}
            self.max_context_messages = 20
            self.max_context_tokens = 4000
            self.welcome_message: str | None = None
            self.config = agent_config or {}

        # 运行时状态
        self._initialized = False
        self._skill_instances: dict[str, Any] = {}
        self._tool_instances: dict[str, Any] = {}
        self._db_config: AgentConfig | None = config

        logger.info(
            f"Agent created: {self.agent_id} (type={self.agent_type}, scope={self.scope})"
        )

    def _load_from_config(self, config: AgentConfig) -> None:
        """从数据库配置加载"""
        self.agent_id = config.agent_id
        self.name = config.name
        self.description = config.description or self.default_description
        self.version = config.version
        self.scope = config.scope
        self.space_id = config.space_id
        self.config_id = config.id

        self.system_prompt = config.system_prompt or self._default_system_prompt()
        self.model_config_name = f"{config.model_provider}_{config.model_name}"
        self.model_provider = config.model_provider
        self.model_name = config.model_name
        self.model_config = config.model_config_ or {}

        self.skills = config.skills or []
        self.tools = config.tools or []
        self.mcp_servers = config.mcp_servers or []

        self.behavior_config = config.behavior_config or {}
        self.max_context_messages = config.max_context_messages
        self.max_context_tokens = config.max_context_tokens
        self.welcome_message = config.welcome_message
        self.config = config.config or {}

    def _default_system_prompt(self) -> str:
        """默认系统提示词"""
        return f"""你是一个名为 {self.name} 的 AI 助手。

{self.description}

请根据用户的需求提供帮助。"""

    async def initialize(self) -> None:
        """初始化 Agent

        子类可以覆盖此方法进行自定义初始化
        """
        if self._initialized:
            return

        # 加载 Skills
        await self._load_skills()

        # 加载 Tools
        await self._load_tools()

        self._initialized = True
        logger.info(f"Agent initialized: {self.agent_id}")

    async def _load_skills(self) -> None:
        """加载挂载的 Skills"""
        from src.skills import skill_registry

        for skill_id in self.skills:
            skill = skill_registry.get(skill_id)
            if skill:
                self._skill_instances[skill_id] = skill
                logger.debug(f"Loaded skill: {skill_id}")
            else:
                logger.warning(f"Skill not found: {skill_id}")

    async def _load_tools(self) -> None:  # noqa: B027
        """加载挂载的 Tools"""
        # TODO: 实现 Tool 加载逻辑
        pass

    async def create_conversation(
        self,
        user_id: uuid.UUID,
        space_id: uuid.UUID,
        title: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AgentContext:
        """创建新会话

        Args:
            user_id: 用户ID
            space_id: 空间ID
            title: 会话标题
            metadata: 元数据

        Returns:
            Agent 上下文
        """
        from src.db.session import async_session_scope
        from src.services.conversation_service import ConversationService

        async with async_session_scope() as session:
            service = ConversationService(session)
            conversation = await service.create(
                user_id=user_id,
                space_id=space_id,
                agent_config_id=self.config_id,
                agent_id=self.agent_id,
                agent_type=self.agent_type,
                title=title,
                metadata=metadata,
            )

            context = AgentContext(
                user_id=user_id,
                space_id=space_id,
                conversation_id=conversation.id,
                conversation=conversation,
                messages=[],
                metadata=metadata or {},
            )

            logger.info(
                f"Conversation created: {conversation.id} "
                f"(agent={self.agent_id}, user={user_id}, space={space_id})"
            )

            return context

    async def load_conversation(
        self,
        conversation_id: uuid.UUID,
        load_messages: bool = True,
        message_limit: int | None = None,
    ) -> AgentContext | None:
        """加载已有会话

        Args:
            conversation_id: 会话ID
            load_messages: 是否加载消息历史
            message_limit: 消息数量限制（默认使用配置的 max_context_messages）

        Returns:
            Agent 上下文或 None
        """
        from src.db.session import async_session_scope
        from src.services.conversation_service import ConversationService
        from src.services.message_service import MessageService

        async with async_session_scope() as session:
            conv_service = ConversationService(session)
            conversation = await conv_service.get_by_id(conversation_id)

            if not conversation:
                logger.warning(f"Conversation not found: {conversation_id}")
                return None

            messages = []
            if load_messages:
                msg_service = MessageService(session)
                limit = message_limit or self.max_context_messages
                messages = await msg_service.get_recent_messages(
                    conversation_id, limit=limit
                )

            context = AgentContext(
                user_id=conversation.user_id,
                space_id=conversation.space_id,
                conversation_id=conversation.id,
                conversation=conversation,
                messages=messages,
                metadata=conversation.metadata_ or {},
            )

            logger.info(
                f"Conversation loaded: {conversation_id} "
                f"(messages={len(messages)})"
            )

            return context

    async def chat(
        self,
        message: str,
        context: AgentContext,
        **kwargs: Any,
    ) -> AgentResponse:
        """处理用户消息

        Args:
            message: 用户消息
            context: Agent 上下文
            **kwargs: 其他参数

        Returns:
            Agent 响应
        """
        if not self._initialized:
            await self.initialize()

        # 保存用户消息
        user_message = await self._save_user_message(context, message)
        context.messages.append(user_message)

        # 执行对话逻辑
        try:
            response = await self._process_message(message, context, **kwargs)
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            response = AgentResponse(
                content=f"抱歉，处理您的消息时出现错误: {str(e)}",
                conversation_id=context.conversation_id,
            )

        # 保存助手消息
        assistant_message = await self._save_assistant_message(context, response)
        response.message_id = assistant_message.id
        context.messages.append(assistant_message)

        # 更新会话统计
        await self._update_conversation_stats(context, response)

        return response

    async def _save_user_message(
        self,
        context: AgentContext,
        content: str,
    ) -> Message:
        """保存用户消息"""
        from src.db.session import async_session_scope
        from src.services.message_service import MessageService

        async with async_session_scope() as session:
            service = MessageService(session)
            message = await service.create_user_message(
                conversation_id=context.conversation_id,
                content=content,
            )
            return message

    async def _save_assistant_message(
        self,
        context: AgentContext,
        response: AgentResponse,
    ) -> Message:
        """保存助手消息"""
        from src.db.session import async_session_scope
        from src.services.message_service import MessageService

        async with async_session_scope() as session:
            service = MessageService(session)
            parent_id = context.messages[-1].id if context.messages else None
            message = await service.create_assistant_message(
                conversation_id=context.conversation_id,
                content=response.content,
                prompt_tokens=response.prompt_tokens,
                completion_tokens=response.completion_tokens,
                total_tokens=response.total_tokens,
                metadata=response.metadata,
                parent_id=parent_id,
            )
            return message

    async def _update_conversation_stats(
        self,
        context: AgentContext,
        response: AgentResponse,
    ) -> None:
        """更新会话统计"""
        from src.db.session import async_session_scope
        from src.services.conversation_service import ConversationService

        async with async_session_scope() as session:
            service = ConversationService(session)
            await service.increment_stats(
                context.conversation_id,
                message_count=2,  # 用户消息 + 助手消息
                tokens=response.total_tokens or 0,
            )

    @abstractmethod
    async def _process_message(
        self,
        message: str,
        context: AgentContext,
        **kwargs: Any,
    ) -> AgentResponse:
        """处理消息的核心逻辑

        子类必须实现此方法

        Args:
            message: 用户消息
            context: Agent 上下文
            **kwargs: 其他参数

        Returns:
            Agent 响应
        """
        raise NotImplementedError

    def get_conversation_history(
        self,
        context: AgentContext,
        include_system: bool = True,
        max_messages: int | None = None,
    ) -> list[dict[str, str]]:
        """获取会话历史（用于 LLM 调用）

        Args:
            context: Agent 上下文
            include_system: 是否包含系统消息
            max_messages: 最大消息数

        Returns:
            消息历史列表
        """
        messages = []

        if include_system and self.system_prompt:
            messages.append({
                "role": "system",
                "content": self.system_prompt,
            })

        # 限制消息数量
        history_messages = context.messages
        if max_messages:
            history_messages = history_messages[-max_messages:]
        elif self.max_context_messages:
            history_messages = history_messages[-self.max_context_messages:]

        for msg in history_messages:
            messages.append(msg.to_llm_message())

        return messages

    async def end_conversation(self, context: AgentContext) -> None:
        """结束会话

        Args:
            context: Agent 上下文
        """
        if context.conversation_id:
            from src.db.session import async_session_scope
            from src.services.conversation_service import ConversationService

            async with async_session_scope() as session:
                service = ConversationService(session)
                await service.end_conversation(context.conversation_id)
                logger.info(f"Conversation ended: {context.conversation_id}")

    def get_info(self) -> dict[str, Any]:
        """获取 Agent 信息"""
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "scope": self.scope.value if isinstance(self.scope, AgentScope) else self.scope,
            "space_id": str(self.space_id) if self.space_id else None,
            "config_id": str(self.config_id) if self.config_id else None,
            "skills": self.skills,
            "tools": self.tools,
            "model_provider": self.model_provider,
            "model_name": self.model_name,
            "welcome_message": self.welcome_message,
        }

    def get_welcome_message(self) -> str | None:
        """获取欢迎消息"""
        return self.welcome_message
