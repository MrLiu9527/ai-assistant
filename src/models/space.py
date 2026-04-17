"""空间（工作区）模型"""

import enum
import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.models.agent import AgentConfig
    from src.models.user import User


class SpaceType(str, enum.Enum):
    """空间类型"""

    PERSONAL = "personal"  # 个人空间
    TEAM = "team"  # 团队空间
    ENTERPRISE = "enterprise"  # 企业空间


class SpaceStatus(str, enum.Enum):
    """空间状态"""

    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"


class MemberRole(str, enum.Enum):
    """成员角色"""

    OWNER = "owner"  # 所有者
    ADMIN = "admin"  # 管理员
    MEMBER = "member"  # 普通成员
    VIEWER = "viewer"  # 只读成员


class Space(Base, TimestampMixin):
    """空间模型

    空间是数字员工的归属单位，分为：
    - 平台级：system 空间，存放平台通用 Agent
    - 空间级：用户创建的空间，存放自定义 Agent
    """

    __tablename__ = "spaces"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="空间ID",
    )
    code: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
        comment="空间编码（唯一标识）",
    )
    name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="空间名称",
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="空间描述",
    )
    type: Mapped[SpaceType] = mapped_column(
        Enum(SpaceType, name="space_type"),
        default=SpaceType.PERSONAL,
        nullable=False,
        comment="空间类型",
    )
    status: Mapped[SpaceStatus] = mapped_column(
        Enum(SpaceStatus, name="space_status"),
        default=SpaceStatus.ACTIVE,
        nullable=False,
        comment="空间状态",
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="所有者ID",
    )
    # 是否为系统空间（平台级）
    is_system: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="是否为系统空间",
    )
    # 配置和限制
    settings: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        default=dict,
        comment="空间设置",
    )
    quota: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        default=dict,
        comment="配额限制",
    )
    metadata_: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata",
        JSONB,
        nullable=True,
        default=dict,
        comment="元数据",
    )

    # 关系
    owner: Mapped["User"] = relationship(
        "User",
        back_populates="owned_spaces",
        foreign_keys=[owner_id],
    )
    members: Mapped[list["SpaceMember"]] = relationship(
        "SpaceMember",
        back_populates="space",
        cascade="all, delete-orphan",
    )
    agents: Mapped[list["AgentConfig"]] = relationship(
        "AgentConfig",
        back_populates="space",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_spaces_type_status", "type", "status"),
        Index("ix_spaces_is_system", "is_system"),
    )

    def __repr__(self) -> str:
        return f"<Space(id={self.id}, code={self.code}, name={self.name})>"

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "id": str(self.id),
            "code": self.code,
            "name": self.name,
            "description": self.description,
            "type": self.type.value,
            "status": self.status.value,
            "owner_id": str(self.owner_id),
            "is_system": self.is_system,
            "settings": self.settings,
            "quota": self.quota,
            "metadata": self.metadata_,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class SpaceMember(Base, TimestampMixin):
    """空间成员模型"""

    __tablename__ = "space_members"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="成员关系ID",
    )
    space_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("spaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="空间ID",
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="用户ID",
    )
    role: Mapped[MemberRole] = mapped_column(
        Enum(MemberRole, name="member_role"),
        default=MemberRole.MEMBER,
        nullable=False,
        comment="成员角色",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        comment="是否活跃",
    )

    # 关系
    space: Mapped["Space"] = relationship(
        "Space",
        back_populates="members",
    )
    user: Mapped["User"] = relationship(
        "User",
        back_populates="space_members",
    )

    __table_args__ = (
        UniqueConstraint("space_id", "user_id", name="uq_space_member"),
        Index("ix_space_members_role", "role"),
    )

    def __repr__(self) -> str:
        return f"<SpaceMember(space_id={self.space_id}, user_id={self.user_id}, role={self.role})>"

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "id": str(self.id),
            "space_id": str(self.space_id),
            "user_id": str(self.user_id),
            "role": self.role.value,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
