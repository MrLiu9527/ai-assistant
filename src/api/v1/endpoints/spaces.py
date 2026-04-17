"""Space API 端点"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps.auth import CurrentUser
from src.api.deps.database import get_db
from src.api.deps.space import SpaceAdmin, SpaceMember, SpaceOwner
from src.api.schemas.common import PaginatedResponse, ResponseModel
from src.api.schemas.space import (
    MemberAdd,
    MemberResponse,
    MemberUpdate,
    SpaceCreate,
    SpaceResponse,
    SpaceUpdate,
)
from src.models.space import MemberRole
from src.services.space_service import SpaceService
from src.services.user_service import UserService

router = APIRouter()


@router.get(
    "",
    response_model=PaginatedResponse[SpaceResponse],
    summary="获取用户的空间列表",
)
async def list_spaces(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
):
    """获取当前用户可访问的空间列表"""
    service = SpaceService(db)

    spaces = await service.get_user_spaces(
        user_id=current_user.id,
        include_system=False,
        limit=page_size,
        offset=(page - 1) * page_size,
    )

    items = [
        SpaceResponse(
            id=space.id,
            code=space.code,
            name=space.name,
            description=space.description,
            type=space.type.value,
            status=space.status.value,
            owner_id=space.owner_id,
            is_system=space.is_system,
            settings=space.settings,
            created_at=space.created_at,
            updated_at=space.updated_at,
        )
        for space in spaces
    ]

    return PaginatedResponse(
        data=items,
        total=len(items),
        page=page,
        page_size=page_size,
        has_more=len(items) == page_size,
    )


@router.post(
    "",
    response_model=ResponseModel[SpaceResponse],
    status_code=status.HTTP_201_CREATED,
    summary="创建空间",
)
async def create_space(
    data: SpaceCreate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """创建新空间"""
    service = SpaceService(db)

    # 检查编码是否已存在
    existing = await service.get_by_code(data.code)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Space with code '{data.code}' already exists",
        )

    space = await service.create(
        code=data.code,
        name=data.name,
        description=data.description,
        type=data.type,
        owner_id=current_user.id,
        settings=data.settings,
    )

    return ResponseModel(data=SpaceResponse(
        id=space.id,
        code=space.code,
        name=space.name,
        description=space.description,
        type=space.type.value,
        status=space.status.value,
        owner_id=space.owner_id,
        is_system=space.is_system,
        settings=space.settings,
        created_at=space.created_at,
        updated_at=space.updated_at,
    ))


@router.get(
    "/{space_id}",
    response_model=ResponseModel[SpaceResponse],
    summary="获取空间详情",
)
async def get_space(
    space: SpaceMember,
    current_user: CurrentUser,
):
    """获取空间详情"""
    return ResponseModel(data=SpaceResponse(
        id=space.id,
        code=space.code,
        name=space.name,
        description=space.description,
        type=space.type.value,
        status=space.status.value,
        owner_id=space.owner_id,
        is_system=space.is_system,
        settings=space.settings,
        created_at=space.created_at,
        updated_at=space.updated_at,
    ))


@router.put(
    "/{space_id}",
    response_model=ResponseModel[SpaceResponse],
    summary="更新空间",
)
async def update_space(
    data: SpaceUpdate,
    space: SpaceAdmin,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """更新空间信息"""
    if space.is_system:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot modify system space",
        )

    service = SpaceService(db)

    update_data = data.model_dump(exclude_unset=True)
    if update_data:
        space = await service.update(space.id, **update_data)

    return ResponseModel(data=SpaceResponse(
        id=space.id,
        code=space.code,
        name=space.name,
        description=space.description,
        type=space.type.value,
        status=space.status.value,
        owner_id=space.owner_id,
        is_system=space.is_system,
        settings=space.settings,
        created_at=space.created_at,
        updated_at=space.updated_at,
    ))


@router.delete(
    "/{space_id}",
    response_model=ResponseModel[None],
    summary="删除空间",
)
async def delete_space(
    space: SpaceOwner,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """删除空间（归档）"""
    if space.is_system:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete system space",
        )

    service = SpaceService(db)
    await service.delete(space.id)

    return ResponseModel(message="Space deleted successfully")


# 成员管理
@router.get(
    "/{space_id}/members",
    response_model=PaginatedResponse[MemberResponse],
    summary="获取空间成员列表",
)
async def list_members(
    space: SpaceMember,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    role: MemberRole | None = Query(None, description="按角色筛选"),
):
    """获取空间成员列表"""
    service = SpaceService(db)

    members = await service.get_members(
        space_id=space.id,
        role=role,
        is_active=True,
    )

    # 获取用户信息
    user_service = UserService(db)
    items = []
    for member in members:
        user = await user_service.get_by_id(member.user_id)
        items.append(MemberResponse(
            id=member.id,
            space_id=member.space_id,
            user_id=member.user_id,
            role=member.role.value,
            is_active=member.is_active,
            created_at=member.created_at,
            username=user.username if user else None,
            nickname=user.nickname if user else None,
            avatar=user.avatar if user else None,
        ))

    return PaginatedResponse(
        data=items,
        total=len(items),
        page=1,
        page_size=100,
        has_more=False,
    )


@router.post(
    "/{space_id}/members",
    response_model=ResponseModel[MemberResponse],
    status_code=status.HTTP_201_CREATED,
    summary="添加成员",
)
async def add_member(
    data: MemberAdd,
    space: SpaceAdmin,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """添加空间成员"""
    # 检查用户是否存在
    user_service = UserService(db)
    user = await user_service.get_by_id(data.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    space_service = SpaceService(db)

    # 检查是否已是成员
    existing = await space_service.get_member(space.id, data.user_id)
    if existing and existing.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already a member",
        )

    # 不能添加 owner 角色
    if data.role == MemberRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot add member as owner",
        )

    member = await space_service.add_member(
        space_id=space.id,
        user_id=data.user_id,
        role=data.role,
    )

    return ResponseModel(data=MemberResponse(
        id=member.id,
        space_id=member.space_id,
        user_id=member.user_id,
        role=member.role.value,
        is_active=member.is_active,
        created_at=member.created_at,
        username=user.username,
        nickname=user.nickname,
        avatar=user.avatar,
    ))


@router.put(
    "/{space_id}/members/{user_id}",
    response_model=ResponseModel[MemberResponse],
    summary="更新成员角色",
)
async def update_member(
    user_id: UUID,
    data: MemberUpdate,
    space: SpaceAdmin,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """更新成员角色"""
    space_service = SpaceService(db)

    member = await space_service.get_member(space.id, user_id)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found",
        )

    # 不能修改 owner
    if member.role == MemberRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot modify owner role",
        )

    # 不能设置为 owner
    if data.role == MemberRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot set member as owner",
        )

    member = await space_service.update_member(
        space_id=space.id,
        user_id=user_id,
        role=data.role,
    )

    user_service = UserService(db)
    user = await user_service.get_by_id(user_id)

    return ResponseModel(data=MemberResponse(
        id=member.id,
        space_id=member.space_id,
        user_id=member.user_id,
        role=member.role.value,
        is_active=member.is_active,
        created_at=member.created_at,
        username=user.username if user else None,
        nickname=user.nickname if user else None,
        avatar=user.avatar if user else None,
    ))


@router.delete(
    "/{space_id}/members/{user_id}",
    response_model=ResponseModel[None],
    summary="移除成员",
)
async def remove_member(
    user_id: UUID,
    space: SpaceAdmin,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """移除空间成员"""
    space_service = SpaceService(db)

    member = await space_service.get_member(space.id, user_id)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found",
        )

    # 不能移除 owner
    if member.role == MemberRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot remove owner",
        )

    # 不能移除自己（管理员除外）
    if user_id == current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove yourself",
        )

    await space_service.remove_member(space.id, user_id)

    return ResponseModel(message="Member removed successfully")
