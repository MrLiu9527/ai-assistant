"""Space Schema"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from src.models.space import MemberRole, SpaceType


class SpaceCreate(BaseModel):
    """创建空间"""

    code: str = Field(..., min_length=2, max_length=64, pattern=r"^[a-z][a-z0-9_-]*$", description="空间编码")
    name: str = Field(..., min_length=1, max_length=128, description="空间名称")
    description: str | None = Field(None, max_length=500, description="空间描述")
    type: SpaceType = Field(default=SpaceType.PERSONAL, description="空间类型")
    settings: dict[str, Any] | None = Field(default=None, description="空间设置")


class SpaceUpdate(BaseModel):
    """更新空间"""

    name: str | None = Field(None, min_length=1, max_length=128, description="空间名称")
    description: str | None = Field(None, max_length=500, description="空间描述")
    settings: dict[str, Any] | None = Field(None, description="空间设置")


class SpaceResponse(BaseModel):
    """空间响应"""

    id: UUID = Field(..., description="空间 ID")
    code: str = Field(..., description="空间编码")
    name: str = Field(..., description="空间名称")
    description: str | None = Field(None, description="空间描述")
    type: str = Field(..., description="空间类型")
    status: str = Field(..., description="空间状态")
    owner_id: UUID = Field(..., description="所有者 ID")
    is_system: bool = Field(..., description="是否系统空间")
    settings: dict[str, Any] | None = Field(None, description="空间设置")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    model_config = {"from_attributes": True}


class MemberAdd(BaseModel):
    """添加成员"""

    user_id: UUID = Field(..., description="用户 ID")
    role: MemberRole = Field(default=MemberRole.MEMBER, description="成员角色")


class MemberUpdate(BaseModel):
    """更新成员"""

    role: MemberRole = Field(..., description="成员角色")


class MemberResponse(BaseModel):
    """成员响应"""

    id: UUID = Field(..., description="成员关系 ID")
    space_id: UUID = Field(..., description="空间 ID")
    user_id: UUID = Field(..., description="用户 ID")
    role: str = Field(..., description="成员角色")
    is_active: bool = Field(..., description="是否活跃")
    created_at: datetime = Field(..., description="加入时间")

    # 可选的用户信息
    username: str | None = Field(None, description="用户名")
    nickname: str | None = Field(None, description="昵称")
    avatar: str | None = Field(None, description="头像")

    model_config = {"from_attributes": True}
