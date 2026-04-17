"""用户服务"""

import hashlib
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User, UserStatus


class UserService:
    """用户服务类"""

    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def hash_password(password: str) -> str:
        """哈希密码（简单实现，生产环境应使用 bcrypt）"""
        return hashlib.sha256(password.encode()).hexdigest()

    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """验证密码"""
        return UserService.hash_password(password) == password_hash

    async def create(
        self,
        username: str,
        email: str,
        password: str,
        phone: str | None = None,
        nickname: str | None = None,
        avatar: str | None = None,
        is_superuser: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> User:
        """创建用户

        Args:
            username: 用户名
            email: 邮箱
            password: 密码（明文）
            phone: 手机号
            nickname: 昵称
            avatar: 头像
            is_superuser: 是否超级管理员
            metadata: 元数据

        Returns:
            创建的用户
        """
        user = User(
            username=username,
            email=email,
            password_hash=self.hash_password(password),
            phone=phone,
            nickname=nickname or username,
            avatar=avatar,
            is_superuser=is_superuser,
            metadata_=metadata or {},
        )
        self.session.add(user)
        await self.session.flush()
        await self.session.refresh(user)
        return user

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        """根据ID获取用户"""
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> User | None:
        """根据用户名获取用户"""
        result = await self.session.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        """根据邮箱获取用户"""
        result = await self.session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def authenticate(
        self,
        username_or_email: str,
        password: str,
    ) -> User | None:
        """验证用户

        Args:
            username_or_email: 用户名或邮箱
            password: 密码

        Returns:
            验证成功返回用户，否则返回 None
        """
        # 尝试用户名
        user = await self.get_by_username(username_or_email)
        if not user:
            # 尝试邮箱
            user = await self.get_by_email(username_or_email)

        if user and self.verify_password(password, user.password_hash):
            if user.status == UserStatus.ACTIVE:
                # 更新登录时间
                await self.update_last_login(user.id)
                return user

        return None

    async def update(
        self,
        user_id: uuid.UUID,
        **kwargs: Any,
    ) -> User | None:
        """更新用户

        Args:
            user_id: 用户ID
            **kwargs: 要更新的字段

        Returns:
            更新后的用户
        """
        if "password" in kwargs:
            kwargs["password_hash"] = self.hash_password(kwargs.pop("password"))
        if "metadata" in kwargs:
            kwargs["metadata_"] = kwargs.pop("metadata")

        await self.session.execute(
            update(User)
            .where(User.id == user_id)
            .values(**kwargs)
        )
        return await self.get_by_id(user_id)

    async def update_last_login(self, user_id: uuid.UUID) -> None:
        """更新最后登录时间"""
        await self.session.execute(
            update(User)
            .where(User.id == user_id)
            .values(last_login_at=datetime.now())
        )

    async def change_password(
        self,
        user_id: uuid.UUID,
        old_password: str,
        new_password: str,
    ) -> bool:
        """修改密码

        Args:
            user_id: 用户ID
            old_password: 旧密码
            new_password: 新密码

        Returns:
            是否成功
        """
        user = await self.get_by_id(user_id)
        if user and self.verify_password(old_password, user.password_hash):
            await self.update(user_id, password=new_password)
            return True
        return False

    async def suspend(self, user_id: uuid.UUID) -> User | None:
        """停用用户"""
        return await self.update(user_id, status=UserStatus.SUSPENDED)

    async def activate(self, user_id: uuid.UUID) -> User | None:
        """激活用户"""
        return await self.update(user_id, status=UserStatus.ACTIVE)

    async def delete(self, user_id: uuid.UUID) -> bool:
        """删除用户（软删除）"""
        user = await self.get_by_id(user_id)
        if user:
            await self.update(user_id, status=UserStatus.INACTIVE)
            return True
        return False

    async def get_or_create_admin(
        self,
        username: str = "admin",
        email: str = "admin@all-in-ai.local",
        password: str = "admin123",
    ) -> User:
        """获取或创建管理员用户

        Args:
            username: 用户名
            email: 邮箱
            password: 密码

        Returns:
            管理员用户
        """
        user = await self.get_by_username(username)
        if user:
            return user

        return await self.create(
            username=username,
            email=email,
            password=password,
            nickname="系统管理员",
            is_superuser=True,
        )
