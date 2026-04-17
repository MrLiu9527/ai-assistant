"""会话和消息模型"""

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    pass


class MessageRole(str, enum.Enum):
    """消息角色"""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class MessageType(str, enum.Enum):
    """消息类型"""

    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    AUDIO = "audio"
    VIDEO = "video"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    ERROR = "error"


class Conversation(Base, TimestampMixin):
    """会话模型

    存储用户与 Agent 之间的会话信息
    """

    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="会话ID",
    )
    title: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="会话标题",
    )
    # 用户信息
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="用户ID",
    )
    # Agent 信息
    agent_config_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_configs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Agent配置ID",
    )
    agent_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        comment="Agent ID",
    )
    agent_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="Agent 类型",
    )
    # 空间信息
    space_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("spaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="空间ID",
    )
    # 会话状态
    is_active: Mapped[bool] = mapped_column(
        default=True,
        comment="是否活跃",
    )
    is_pinned: Mapped[bool] = mapped_column(
        default=False,
        comment="是否置顶",
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="结束时间",
    )
    # 统计
    message_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="消息数量",
    )
    total_tokens: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="总Token数",
    )
    # 元数据
    metadata_: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata",
        JSONB,
        nullable=True,
        default=dict,
        comment="会话元数据",
    )
    # 上下文快照（用于恢复会话）
    context_snapshot: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="上下文快照",
    )

    # 关系
    messages: Mapped[list["Message"]] = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_conversations_user_space", "user_id", "space_id"),
        Index("ix_conversations_agent_config", "agent_config_id"),
        Index("ix_conversations_created_at", "created_at"),
        Index("ix_conversations_active_pinned", "is_active", "is_pinned"),
    )

    def __repr__(self) -> str:
        return f"<Conversation(id={self.id}, user_id={self.user_id}, agent_id={self.agent_id})>"

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "id": str(self.id),
            "title": self.title,
            "user_id": str(self.user_id),
            "agent_config_id": str(self.agent_config_id) if self.agent_config_id else None,
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "space_id": str(self.space_id),
            "is_active": self.is_active,
            "is_pinned": self.is_pinned,
            "message_count": self.message_count,
            "total_tokens": self.total_tokens,
            "metadata": self.metadata_,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
        }


class Message(Base, TimestampMixin):
    """消息模型

    存储会话中的每条消息
    """

    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="消息ID",
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="会话ID",
    )
    role: Mapped[MessageRole] = mapped_column(
        Enum(MessageRole, name="message_role"),
        nullable=False,
        comment="消息角色",
    )
    type: Mapped[MessageType] = mapped_column(
        Enum(MessageType, name="message_type"),
        default=MessageType.TEXT,
        nullable=False,
        comment="消息类型",
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="消息内容",
    )
    # 工具调用相关
    tool_name: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        comment="工具名称",
    )
    tool_call_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="工具调用ID",
    )
    tool_args: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="工具调用参数",
    )
    tool_result: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="工具执行结果",
    )
    # Token 统计
    prompt_tokens: Mapped[int | None] = mapped_column(
        nullable=True,
        comment="Prompt Token 数",
    )
    completion_tokens: Mapped[int | None] = mapped_column(
        nullable=True,
        comment="Completion Token 数",
    )
    total_tokens: Mapped[int | None] = mapped_column(
        nullable=True,
        comment="总 Token 数",
    )
    # 其他元数据
    metadata_: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata",
        JSONB,
        nullable=True,
        default=dict,
        comment="消息元数据",
    )
    # 附件
    attachments: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="附件列表",
    )
    # 父消息（用于追踪回复链）
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("messages.id", ondelete="SET NULL"),
        nullable=True,
        comment="父消息ID",
    )
    # 反馈
    feedback: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="用户反馈",
    )

    # 关系
    conversation: Mapped["Conversation"] = relationship(
        "Conversation",
        back_populates="messages",
    )
    parent: Mapped["Message | None"] = relationship(
        "Message",
        remote_side="Message.id",
        backref="replies",
    )

    __table_args__ = (
        Index("ix_messages_conversation_created", "conversation_id", "created_at"),
        Index("ix_messages_role", "role"),
        Index("ix_messages_type", "type"),
    )

    def __repr__(self) -> str:
        return f"<Message(id={self.id}, role={self.role}, type={self.type})>"

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "id": str(self.id),
            "conversation_id": str(self.conversation_id),
            "role": self.role.value,
            "type": self.type.value,
            "content": self.content,
            "tool_name": self.tool_name,
            "tool_call_id": self.tool_call_id,
            "tool_args": self.tool_args,
            "tool_result": self.tool_result,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "metadata": self.metadata_,
            "attachments": self.attachments,
            "parent_id": str(self.parent_id) if self.parent_id else None,
            "feedback": self.feedback,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def to_llm_message(self) -> dict[str, str]:
        """转换为 LLM 消息格式"""
        return {
            "role": self.role.value,
            "content": self.content,
        }
