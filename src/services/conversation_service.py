"""会话服务"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.conversation import Conversation


class ConversationService:
    """会话服务类"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        user_id: str,
        agent_id: str,
        agent_type: str,
        title: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Conversation:
        """创建新会话

        Args:
            user_id: 用户ID
            agent_id: Agent ID
            agent_type: Agent 类型
            title: 会话标题
            metadata: 元数据

        Returns:
            创建的会话对象
        """
        conversation = Conversation(
            user_id=user_id,
            agent_id=agent_id,
            agent_type=agent_type,
            title=title,
            metadata_=metadata or {},
        )
        self.session.add(conversation)
        await self.session.flush()
        await self.session.refresh(conversation)
        return conversation

    async def get_by_id(self, conversation_id: uuid.UUID) -> Conversation | None:
        """根据ID获取会话

        Args:
            conversation_id: 会话ID

        Returns:
            会话对象或 None
        """
        result = await self.session.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        return result.scalar_one_or_none()

    async def get_by_user(
        self,
        user_id: str,
        agent_id: str | None = None,
        is_active: bool | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Conversation]:
        """获取用户的会话列表

        Args:
            user_id: 用户ID
            agent_id: Agent ID（可选）
            is_active: 是否只获取活跃会话
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            会话列表
        """
        query = select(Conversation).where(Conversation.user_id == user_id)

        if agent_id:
            query = query.where(Conversation.agent_id == agent_id)

        if is_active is not None:
            query = query.where(Conversation.is_active == is_active)

        query = query.order_by(Conversation.updated_at.desc())
        query = query.limit(limit).offset(offset)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update_title(
        self, conversation_id: uuid.UUID, title: str
    ) -> Conversation | None:
        """更新会话标题

        Args:
            conversation_id: 会话ID
            title: 新标题

        Returns:
            更新后的会话对象
        """
        await self.session.execute(
            update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(title=title, updated_at=datetime.now())
        )
        return await self.get_by_id(conversation_id)

    async def end_conversation(self, conversation_id: uuid.UUID) -> Conversation | None:
        """结束会话

        Args:
            conversation_id: 会话ID

        Returns:
            更新后的会话对象
        """
        now = datetime.now()
        await self.session.execute(
            update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(is_active=False, ended_at=now, updated_at=now)
        )
        return await self.get_by_id(conversation_id)

    async def update_metadata(
        self, conversation_id: uuid.UUID, metadata: dict[str, Any]
    ) -> Conversation | None:
        """更新会话元数据

        Args:
            conversation_id: 会话ID
            metadata: 新元数据（会合并到现有元数据）

        Returns:
            更新后的会话对象
        """
        conversation = await self.get_by_id(conversation_id)
        if conversation:
            current_metadata = conversation.metadata_ or {}
            current_metadata.update(metadata)
            await self.session.execute(
                update(Conversation)
                .where(Conversation.id == conversation_id)
                .values(metadata=current_metadata, updated_at=datetime.now())
            )
            return await self.get_by_id(conversation_id)
        return None

    async def delete(self, conversation_id: uuid.UUID) -> bool:
        """删除会话

        Args:
            conversation_id: 会话ID

        Returns:
            是否删除成功
        """
        conversation = await self.get_by_id(conversation_id)
        if conversation:
            await self.session.delete(conversation)
            return True
        return False
