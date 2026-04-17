"""Agent 配置模型"""

import enum
import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.models.space import Space


class AgentType(str, enum.Enum):
    """Agent 类型"""

    DIALOG = "dialog"  # 对话型
    REACT = "react"  # ReAct 推理型
    TOOL = "tool"  # 工具调用型
    WORKFLOW = "workflow"  # 工作流型
    CUSTOM = "custom"  # 自定义


class AgentScope(str, enum.Enum):
    """Agent 作用域"""

    PLATFORM = "platform"  # 平台级（系统提供，所有用户可用）
    SPACE = "space"  # 空间级（用户创建，空间内可用）


class AgentStatus(str, enum.Enum):
    """Agent 状态"""

    DRAFT = "draft"  # 草稿
    PUBLISHED = "published"  # 已发布
    DISABLED = "disabled"  # 已禁用
    ARCHIVED = "archived"  # 已归档


class AgentConfig(Base, TimestampMixin):
    """Agent 配置模型

    存储 Agent 的完整配置信息，支持：
    - 平台级 Agent：系统空间中的 Agent，所有用户可用
    - 空间级 Agent：用户空间中的 Agent，仅空间成员可用
    """

    __tablename__ = "agent_configs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="配置ID",
    )
    # 基本信息
    agent_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        comment="Agent 唯一标识",
    )
    name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="Agent 名称",
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Agent 描述",
    )
    avatar: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Agent 头像",
    )
    # 类型和作用域
    type: Mapped[AgentType] = mapped_column(
        Enum(AgentType, name="agent_type"),
        default=AgentType.DIALOG,
        nullable=False,
        comment="Agent 类型",
    )
    scope: Mapped[AgentScope] = mapped_column(
        Enum(AgentScope, name="agent_scope"),
        default=AgentScope.SPACE,
        nullable=False,
        index=True,
        comment="Agent 作用域",
    )
    status: Mapped[AgentStatus] = mapped_column(
        Enum(AgentStatus, name="agent_status"),
        default=AgentStatus.DRAFT,
        nullable=False,
        index=True,
        comment="Agent 状态",
    )
    version: Mapped[str] = mapped_column(
        String(32),
        default="1.0.0",
        nullable=False,
        comment="版本号",
    )
    # 归属
    space_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("spaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属空间ID",
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="创建者ID",
    )
    # 模型配置
    model_provider: Mapped[str] = mapped_column(
        String(64),
        default="dashscope",
        nullable=False,
        comment="模型提供商",
    )
    model_name: Mapped[str] = mapped_column(
        String(64),
        default="qwen-turbo",
        nullable=False,
        comment="模型名称",
    )
    model_config_: Mapped[dict[str, Any] | None] = mapped_column(
        "model_config",
        JSONB,
        nullable=True,
        default=dict,
        comment="模型配置参数",
    )
    # 提示词
    system_prompt: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="系统提示词",
    )
    welcome_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="欢迎消息",
    )
    # 能力配置
    skills: Mapped[list[str] | None] = mapped_column(
        JSONB,
        nullable=True,
        default=list,
        comment="挂载的 Skill ID 列表",
    )
    tools: Mapped[list[str] | None] = mapped_column(
        JSONB,
        nullable=True,
        default=list,
        comment="挂载的 Tool ID 列表",
    )
    mcp_servers: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSONB,
        nullable=True,
        default=list,
        comment="MCP 服务器配置",
    )
    # 知识库配置
    knowledge_bases: Mapped[list[str] | None] = mapped_column(
        JSONB,
        nullable=True,
        default=list,
        comment="关联的知识库ID列表",
    )
    # 行为配置
    behavior_config: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        default=dict,
        comment="行为配置（如温度、最大token等）",
    )
    # 上下文配置
    max_context_messages: Mapped[int] = mapped_column(
        Integer,
        default=20,
        comment="最大上下文消息数",
    )
    max_context_tokens: Mapped[int] = mapped_column(
        Integer,
        default=4000,
        comment="最大上下文Token数",
    )
    # 其他配置
    config: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        default=dict,
        comment="其他扩展配置",
    )
    metadata_: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata",
        JSONB,
        nullable=True,
        default=dict,
        comment="元数据",
    )
    # 统计
    usage_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="使用次数",
    )
    # 排序
    sort_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="排序顺序",
    )

    # 关系
    space: Mapped["Space"] = relationship(
        "Space",
        back_populates="agents",
    )

    __table_args__ = (
        # 同一空间内 agent_id 唯一
        UniqueConstraint("space_id", "agent_id", name="uq_space_agent_id"),
        Index("ix_agent_configs_scope_status", "scope", "status"),
        Index("ix_agent_configs_type", "type"),
    )

    def __repr__(self) -> str:
        return f"<AgentConfig(agent_id={self.agent_id}, name={self.name}, scope={self.scope})>"

    @property
    def is_platform_agent(self) -> bool:
        """是否为平台级 Agent"""
        return self.scope == AgentScope.PLATFORM

    @property
    def is_published(self) -> bool:
        """是否已发布"""
        return self.status == AgentStatus.PUBLISHED

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "id": str(self.id),
            "agent_id": self.agent_id,
            "name": self.name,
            "description": self.description,
            "avatar": self.avatar,
            "type": self.type.value,
            "scope": self.scope.value,
            "status": self.status.value,
            "version": self.version,
            "space_id": str(self.space_id),
            "created_by": str(self.created_by) if self.created_by else None,
            "model_provider": self.model_provider,
            "model_name": self.model_name,
            "model_config": self.model_config_,
            "system_prompt": self.system_prompt,
            "welcome_message": self.welcome_message,
            "skills": self.skills,
            "tools": self.tools,
            "mcp_servers": self.mcp_servers,
            "knowledge_bases": self.knowledge_bases,
            "behavior_config": self.behavior_config,
            "max_context_messages": self.max_context_messages,
            "max_context_tokens": self.max_context_tokens,
            "config": self.config,
            "metadata": self.metadata_,
            "usage_count": self.usage_count,
            "sort_order": self.sort_order,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def to_agent_kwargs(self) -> dict[str, Any]:
        """转换为 Agent 构造函数参数"""
        return {
            "system_prompt": self.system_prompt,
            "model_config_name": f"{self.model_provider}_{self.model_name}",
            "skills": self.skills or [],
            "tools": self.tools or [],
            "config": {
                "agent_id": self.agent_id,
                "name": self.name,
                "description": self.description,
                "type": self.type.value,
                "scope": self.scope.value,
                "space_id": str(self.space_id),
                "model_provider": self.model_provider,
                "model_name": self.model_name,
                "model_config": self.model_config_,
                "behavior_config": self.behavior_config,
                "max_context_messages": self.max_context_messages,
                "max_context_tokens": self.max_context_tokens,
                "welcome_message": self.welcome_message,
                **(self.config or {}),
            },
        }
