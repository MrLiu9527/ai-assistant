"""空间服务"""

import uuid
from typing import Any

from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.space import MemberRole, Space, SpaceMember, SpaceStatus, SpaceType

# 系统空间编码
SYSTEM_SPACE_CODE = "system"


class SpaceService:
    """空间服务类"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        code: str,
        name: str,
        owner_id: uuid.UUID,
        type: SpaceType = SpaceType.PERSONAL,
        description: str | None = None,
        is_system: bool = False,
        settings: dict[str, Any] | None = None,
        quota: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Space:
        """创建空间

        Args:
            code: 空间编码
            name: 空间名称
            owner_id: 所有者ID
            type: 空间类型
            description: 描述
            is_system: 是否为系统空间
            settings: 空间设置
            quota: 配额限制
            metadata: 元数据

        Returns:
            创建的空间
        """
        space = Space(
            code=code,
            name=name,
            owner_id=owner_id,
            type=type,
            description=description,
            is_system=is_system,
            settings=settings or {},
            quota=quota or {},
            metadata_=metadata or {},
        )
        self.session.add(space)
        await self.session.flush()
        await self.session.refresh(space)

        # 添加所有者为成员
        await self.add_member(space.id, owner_id, MemberRole.OWNER)

        return space

    async def get_by_id(self, space_id: uuid.UUID) -> Space | None:
        """根据ID获取空间"""
        result = await self.session.execute(
            select(Space).where(Space.id == space_id)
        )
        return result.scalar_one_or_none()

    async def get_by_code(self, code: str) -> Space | None:
        """根据编码获取空间"""
        result = await self.session.execute(
            select(Space).where(Space.code == code)
        )
        return result.scalar_one_or_none()

    async def get_system_space(self) -> Space | None:
        """获取系统空间"""
        return await self.get_by_code(SYSTEM_SPACE_CODE)

    async def get_or_create_system_space(self, admin_user_id: uuid.UUID) -> Space:
        """获取或创建系统空间

        Args:
            admin_user_id: 管理员用户ID

        Returns:
            系统空间
        """
        space = await self.get_system_space()
        if space:
            return space

        return await self.create(
            code=SYSTEM_SPACE_CODE,
            name="系统空间",
            owner_id=admin_user_id,
            type=SpaceType.ENTERPRISE,
            description="系统平台级空间，存放平台通用 Agent",
            is_system=True,
        )

    async def get_user_spaces(
        self,
        user_id: uuid.UUID,
        include_system: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Space]:
        """获取用户可访问的空间列表

        Args:
            user_id: 用户ID
            include_system: 是否包含系统空间
            limit: 返回数量
            offset: 偏移量

        Returns:
            空间列表
        """
        # 查询用户是成员的空间
        query = (
            select(Space)
            .join(SpaceMember, Space.id == SpaceMember.space_id)
            .where(
                and_(
                    SpaceMember.user_id == user_id,
                    SpaceMember.is_active.is_(True),
                    Space.status == SpaceStatus.ACTIVE,
                )
            )
        )

        if not include_system:
            query = query.where(Space.is_system.is_(False))

        query = query.order_by(Space.created_at.desc())
        query = query.limit(limit).offset(offset)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update(
        self,
        space_id: uuid.UUID,
        **kwargs: Any,
    ) -> Space | None:
        """更新空间

        Args:
            space_id: 空间ID
            **kwargs: 要更新的字段

        Returns:
            更新后的空间
        """
        if "metadata" in kwargs:
            kwargs["metadata_"] = kwargs.pop("metadata")

        await self.session.execute(
            update(Space)
            .where(Space.id == space_id)
            .values(**kwargs)
        )
        return await self.get_by_id(space_id)

    async def delete(self, space_id: uuid.UUID) -> bool:
        """删除空间（软删除）

        Args:
            space_id: 空间ID

        Returns:
            是否成功
        """
        space = await self.get_by_id(space_id)
        if space and not space.is_system:
            await self.update(space_id, status=SpaceStatus.ARCHIVED)
            return True
        return False

    # 成员管理
    async def add_member(
        self,
        space_id: uuid.UUID,
        user_id: uuid.UUID,
        role: MemberRole = MemberRole.MEMBER,
    ) -> SpaceMember:
        """添加成员

        Args:
            space_id: 空间ID
            user_id: 用户ID
            role: 角色

        Returns:
            成员关系
        """
        # 检查是否已存在
        existing = await self.get_member(space_id, user_id)
        if existing:
            if not existing.is_active:
                await self.update_member(space_id, user_id, is_active=True, role=role)
                return await self.get_member(space_id, user_id)
            return existing

        member = SpaceMember(
            space_id=space_id,
            user_id=user_id,
            role=role,
        )
        self.session.add(member)
        await self.session.flush()
        return member

    async def get_member(
        self,
        space_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> SpaceMember | None:
        """获取成员关系

        Args:
            space_id: 空间ID
            user_id: 用户ID

        Returns:
            成员关系或 None
        """
        result = await self.session.execute(
            select(SpaceMember).where(
                and_(
                    SpaceMember.space_id == space_id,
                    SpaceMember.user_id == user_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_members(
        self,
        space_id: uuid.UUID,
        role: MemberRole | None = None,
        is_active: bool = True,
    ) -> list[SpaceMember]:
        """获取空间成员列表

        Args:
            space_id: 空间ID
            role: 角色过滤
            is_active: 是否只获取活跃成员

        Returns:
            成员列表
        """
        query = select(SpaceMember).where(SpaceMember.space_id == space_id)

        if role:
            query = query.where(SpaceMember.role == role)
        if is_active:
            query = query.where(SpaceMember.is_active.is_(True))

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update_member(
        self,
        space_id: uuid.UUID,
        user_id: uuid.UUID,
        **kwargs: Any,
    ) -> SpaceMember | None:
        """更新成员

        Args:
            space_id: 空间ID
            user_id: 用户ID
            **kwargs: 要更新的字段

        Returns:
            更新后的成员关系
        """
        await self.session.execute(
            update(SpaceMember)
            .where(
                and_(
                    SpaceMember.space_id == space_id,
                    SpaceMember.user_id == user_id,
                )
            )
            .values(**kwargs)
        )
        return await self.get_member(space_id, user_id)

    async def remove_member(
        self,
        space_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bool:
        """移除成员（软删除）

        Args:
            space_id: 空间ID
            user_id: 用户ID

        Returns:
            是否成功
        """
        member = await self.get_member(space_id, user_id)
        if member and member.role != MemberRole.OWNER:
            await self.update_member(space_id, user_id, is_active=False)
            return True
        return False

    async def is_member(
        self,
        space_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bool:
        """检查是否为成员

        Args:
            space_id: 空间ID
            user_id: 用户ID

        Returns:
            是否为活跃成员
        """
        member = await self.get_member(space_id, user_id)
        return member is not None and member.is_active

    async def has_permission(
        self,
        space_id: uuid.UUID,
        user_id: uuid.UUID,
        required_role: MemberRole,
    ) -> bool:
        """检查权限

        Args:
            space_id: 空间ID
            user_id: 用户ID
            required_role: 需要的最低角色

        Returns:
            是否有权限
        """
        member = await self.get_member(space_id, user_id)
        if not member or not member.is_active:
            return False

        role_hierarchy = {
            MemberRole.OWNER: 4,
            MemberRole.ADMIN: 3,
            MemberRole.MEMBER: 2,
            MemberRole.VIEWER: 1,
        }

        return role_hierarchy.get(member.role, 0) >= role_hierarchy.get(required_role, 0)
