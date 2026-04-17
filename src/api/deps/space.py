"""空间依赖"""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps.auth import CurrentUser
from src.api.deps.database import get_db
from src.models.space import MemberRole, Space
from src.models.user import User
from src.services.space_service import SpaceService


async def get_space(
    space_id: Annotated[UUID, Path(description="空间 ID")],
    db: AsyncSession = Depends(get_db),
) -> Space:
    """获取空间"""
    service = SpaceService(db)
    space = await service.get_by_id(space_id)

    if not space:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Space not found",
        )

    if space.status.value != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Space is not active",
        )

    return space


async def check_space_permission(
    space: Space = Depends(get_space),
    current_user: User = Depends(CurrentUser),
    db: AsyncSession = Depends(get_db),
    required_role: MemberRole = MemberRole.MEMBER,
) -> Space:
    """检查空间权限

    确保当前用户是空间成员且有足够权限
    """
    # 超级管理员可以访问所有空间
    if current_user.is_superuser:
        return space

    service = SpaceService(db)
    has_permission = await service.has_permission(
        space_id=space.id,
        user_id=current_user.id,
        required_role=required_role,
    )

    if not has_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied",
        )

    return space


def require_space_role(required_role: MemberRole):
    """创建空间角色检查依赖

    Args:
        required_role: 需要的最低角色

    Returns:
        依赖函数
    """
    async def _check(
        space: Space = Depends(get_space),
        current_user: User = Depends(CurrentUser),
        db: AsyncSession = Depends(get_db),
    ) -> Space:
        if current_user.is_superuser:
            return space

        service = SpaceService(db)
        has_permission = await service.has_permission(
            space_id=space.id,
            user_id=current_user.id,
            required_role=required_role,
        )

        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires {required_role.value} role or higher",
            )

        return space

    return _check


# 预定义的权限检查
SpaceViewer = Annotated[Space, Depends(require_space_role(MemberRole.VIEWER))]
SpaceMember = Annotated[Space, Depends(require_space_role(MemberRole.MEMBER))]
SpaceAdmin = Annotated[Space, Depends(require_space_role(MemberRole.ADMIN))]
SpaceOwner = Annotated[Space, Depends(require_space_role(MemberRole.OWNER))]
