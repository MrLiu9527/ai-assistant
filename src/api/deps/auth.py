"""认证依赖"""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps.database import get_db
from src.models.user import User
from src.services.user_service import UserService


async def get_current_user(
    x_user_id: Annotated[str | None, Header()] = None,
    authorization: Annotated[str | None, Header()] = None,
    db: AsyncSession = Depends(get_db),
) -> User:
    """获取当前用户

    注意：这是一个简化的实现，生产环境应该使用 JWT Token 认证

    支持两种方式：
    1. X-User-Id Header（开发/测试用）
    2. Authorization Bearer Token（生产用，待实现）
    """
    user_id: UUID | None = None

    # 方式1：直接传递用户 ID（开发/测试用）
    if x_user_id:
        try:
            user_id = UUID(x_user_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user ID format",
            ) from None

    # 方式2：Bearer Token（待实现完整的 JWT 验证）
    elif authorization and authorization.startswith("Bearer "):
        _token = authorization[7:]
        # TODO: 实现 JWT Token 验证
        # user_id = verify_token(_token)
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="JWT authentication not implemented yet",
        )

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 获取用户
    service = UserService(db)
    user = await service.get_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    if user.status.value != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not active",
        )

    return user


async def get_current_user_optional(
    x_user_id: Annotated[str | None, Header()] = None,
    authorization: Annotated[str | None, Header()] = None,
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """获取当前用户（可选）"""
    if not x_user_id and not authorization:
        return None

    try:
        return await get_current_user(x_user_id, authorization, db)
    except HTTPException:
        return None


# 类型别名
CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalUser = Annotated[User | None, Depends(get_current_user_optional)]
