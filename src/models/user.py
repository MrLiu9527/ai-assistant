"""用户模型"""

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Index,
    String,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, TimestampMixin


class UserStatus(str, enum.Enum):
    """用户状态"""

    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class User(Base, TimestampMixin):
    """用户模型"""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="用户ID",
    )
    username: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
        comment="用户名",
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        comment="邮箱",
    )
    phone: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="手机号",
    )
    nickname: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="昵称",
    )
    avatar: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="头像URL",
    )
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="密码哈希",
    )
    status: Mapped[UserStatus] = mapped_column(
        Enum(UserStatus, name="user_status"),
        default=UserStatus.ACTIVE,
        nullable=False,
        comment="用户状态",
    )
    is_superuser: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="是否超级管理员",
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="最后登录时间",
    )
    metadata_: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata",
        JSONB,
        nullable=True,
        default=dict,
        comment="用户元数据",
    )

    # 关系
    space_members: Mapped[list["SpaceMember"]] = relationship(
        "SpaceMember",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    owned_spaces: Mapped[list["Space"]] = relationship(
        "Space",
        back_populates="owner",
        foreign_keys="Space.owner_id",
    )

    __table_args__ = (
        Index("ix_users_status", "status"),
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username})>"

    def to_dict(self, include_sensitive: bool = False) -> dict[str, Any]:
        """转换为字典"""
        data = {
            "id": str(self.id),
            "username": self.username,
            "email": self.email,
            "phone": self.phone,
            "nickname": self.nickname,
            "avatar": self.avatar,
            "status": self.status.value,
            "is_superuser": self.is_superuser,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
            "metadata": self.metadata_,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_sensitive:
            data["password_hash"] = self.password_hash
        return data


# 延迟导入避免循环依赖
from src.models.space import Space, SpaceMember  # noqa: E402
