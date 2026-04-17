"""Agent 配置模型"""

import enum
import uuid
from typing import Any

from sqlalchemy import (
    Boolean,
    Enum,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base, TimestampMixin


class AgentType(str, enum.Enum):
    """Agent 类型"""

    DIALOG = "dialog"  # 对话型
    REACT = "react"  # ReAct 型
    TOOL = "tool"  # 工具调用型
    WORKFLOW = "workflow"  # 工作流型
    CUSTOM = "custom"  # 自定义


class AgentConfig(Base, TimestampMixin):
    """Agent 配置模型

    存储 Agent 的配置信息，支持动态注册和配置
    """

    __tablename__ = "agent_configs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="配置ID",
    )
    agent_id: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
        comment="Agent 唯一标识",
    )
    name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="Agent 名称",
    )
    type: Mapped[AgentType] = mapped_column(
        Enum(AgentType, name="agent_type"),
        default=AgentType.DIALOG,
        nullable=False,
        comment="Agent 类型",
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Agent 描述",
    )
    version: Mapped[str] = mapped_column(
        String(32),
        default="1.0.0",
        nullable=False,
        comment="版本号",
    )
    # 系统提示词
    system_prompt: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="系统提示词",
    )
    # 模型配置
    model_config_name: Mapped[str] = mapped_column(
        String(64),
        default="default",
        nullable=False,
        comment="模型配置名称",
    )
    # 挂载的 Skills
    skills: Mapped[list[str] | None] = mapped_column(
        JSONB,
        nullable=True,
        default=list,
        comment="挂载的 Skill ID 列表",
    )
    # 挂载的 Tools
    tools: Mapped[list[str] | None] = mapped_column(
        JSONB,
        nullable=True,
        default=list,
        comment="挂载的 Tool ID 列表",
    )
    # 挂载的 MCP
    mcp_servers: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSONB,
        nullable=True,
        default=list,
        comment="MCP 服务器配置",
    )
    # Agent 特定配置
    config: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        default=dict,
        comment="Agent 特定配置",
    )
    # 元数据
    metadata_: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata",
        JSONB,
        nullable=True,
        default=dict,
        comment="元数据",
    )
    # 状态
    is_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        comment="是否启用",
    )
    is_public: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="是否公开",
    )

    __table_args__ = (
        Index("ix_agent_configs_type", "type"),
        Index("ix_agent_configs_enabled", "is_enabled"),
    )

    def __repr__(self) -> str:
        return f"<AgentConfig(agent_id={self.agent_id}, name={self.name}, type={self.type})>"

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "id": str(self.id),
            "agent_id": self.agent_id,
            "name": self.name,
            "type": self.type.value,
            "description": self.description,
            "version": self.version,
            "system_prompt": self.system_prompt,
            "model_config_name": self.model_config_name,
            "skills": self.skills,
            "tools": self.tools,
            "mcp_servers": self.mcp_servers,
            "config": self.config,
            "metadata": self.metadata_,
            "is_enabled": self.is_enabled,
            "is_public": self.is_public,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
