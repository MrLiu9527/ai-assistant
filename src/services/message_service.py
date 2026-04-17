"""消息服务"""

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.conversation import Message, MessageRole, MessageType


class MessageService:
    """消息服务类"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        conversation_id: uuid.UUID,
        role: MessageRole,
        content: str,
        type: MessageType = MessageType.TEXT,
        tool_name: str | None = None,
        tool_call_id: str | None = None,
        tool_args: dict[str, Any] | None = None,
        tool_result: dict[str, Any] | None = None,
        prompt_tokens: int | None = None,
        completion_tokens: int | None = None,
        total_tokens: int | None = None,
        metadata: dict[str, Any] | None = None,
        parent_id: uuid.UUID | None = None,
    ) -> Message:
        """创建新消息

        Args:
            conversation_id: 会话ID
            role: 消息角色
            content: 消息内容
            type: 消息类型
            tool_name: 工具名称
            tool_call_id: 工具调用ID
            tool_args: 工具调用参数
            tool_result: 工具执行结果
            prompt_tokens: Prompt Token 数
            completion_tokens: Completion Token 数
            total_tokens: 总 Token 数
            metadata: 元数据
            parent_id: 父消息ID

        Returns:
            创建的消息对象
        """
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            type=type,
            tool_name=tool_name,
            tool_call_id=tool_call_id,
            tool_args=tool_args,
            tool_result=tool_result,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            metadata_=metadata or {},
            parent_id=parent_id,
        )
        self.session.add(message)
        await self.session.flush()
        await self.session.refresh(message)
        return message

    async def create_user_message(
        self,
        conversation_id: uuid.UUID,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> Message:
        """创建用户消息

        Args:
            conversation_id: 会话ID
            content: 消息内容
            metadata: 元数据

        Returns:
            创建的消息对象
        """
        return await self.create(
            conversation_id=conversation_id,
            role=MessageRole.USER,
            content=content,
            metadata=metadata,
        )

    async def create_assistant_message(
        self,
        conversation_id: uuid.UUID,
        content: str,
        prompt_tokens: int | None = None,
        completion_tokens: int | None = None,
        total_tokens: int | None = None,
        metadata: dict[str, Any] | None = None,
        parent_id: uuid.UUID | None = None,
    ) -> Message:
        """创建助手消息

        Args:
            conversation_id: 会话ID
            content: 消息内容
            prompt_tokens: Prompt Token 数
            completion_tokens: Completion Token 数
            total_tokens: 总 Token 数
            metadata: 元数据
            parent_id: 父消息ID

        Returns:
            创建的消息对象
        """
        return await self.create(
            conversation_id=conversation_id,
            role=MessageRole.ASSISTANT,
            content=content,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            metadata=metadata,
            parent_id=parent_id,
        )

    async def create_tool_call_message(
        self,
        conversation_id: uuid.UUID,
        tool_name: str,
        tool_call_id: str,
        tool_args: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> Message:
        """创建工具调用消息

        Args:
            conversation_id: 会话ID
            tool_name: 工具名称
            tool_call_id: 工具调用ID
            tool_args: 工具调用参数
            metadata: 元数据

        Returns:
            创建的消息对象
        """
        return await self.create(
            conversation_id=conversation_id,
            role=MessageRole.ASSISTANT,
            content=f"Calling tool: {tool_name}",
            type=MessageType.TOOL_CALL,
            tool_name=tool_name,
            tool_call_id=tool_call_id,
            tool_args=tool_args,
            metadata=metadata,
        )

    async def create_tool_result_message(
        self,
        conversation_id: uuid.UUID,
        tool_name: str,
        tool_call_id: str,
        tool_result: dict[str, Any],
        content: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Message:
        """创建工具结果消息

        Args:
            conversation_id: 会话ID
            tool_name: 工具名称
            tool_call_id: 工具调用ID
            tool_result: 工具执行结果
            content: 结果内容摘要
            metadata: 元数据

        Returns:
            创建的消息对象
        """
        return await self.create(
            conversation_id=conversation_id,
            role=MessageRole.TOOL,
            content=content or str(tool_result),
            type=MessageType.TOOL_RESULT,
            tool_name=tool_name,
            tool_call_id=tool_call_id,
            tool_result=tool_result,
            metadata=metadata,
        )

    async def get_by_id(self, message_id: uuid.UUID) -> Message | None:
        """根据ID获取消息

        Args:
            message_id: 消息ID

        Returns:
            消息对象或 None
        """
        result = await self.session.execute(
            select(Message).where(Message.id == message_id)
        )
        return result.scalar_one_or_none()

    async def get_by_conversation(
        self,
        conversation_id: uuid.UUID,
        limit: int | None = None,
        offset: int = 0,
        roles: list[MessageRole] | None = None,
    ) -> list[Message]:
        """获取会话的消息列表

        Args:
            conversation_id: 会话ID
            limit: 返回数量限制
            offset: 偏移量
            roles: 筛选消息角色

        Returns:
            消息列表
        """
        query = select(Message).where(Message.conversation_id == conversation_id)

        if roles:
            query = query.where(Message.role.in_(roles))

        query = query.order_by(Message.created_at.asc())

        if limit:
            query = query.limit(limit).offset(offset)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_recent_messages(
        self,
        conversation_id: uuid.UUID,
        limit: int = 10,
    ) -> list[Message]:
        """获取最近的消息

        Args:
            conversation_id: 会话ID
            limit: 返回数量

        Returns:
            消息列表（按时间正序）
        """
        query = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(query)
        messages = list(result.scalars().all())
        return list(reversed(messages))

    async def count_by_conversation(self, conversation_id: uuid.UUID) -> int:
        """统计会话的消息数量

        Args:
            conversation_id: 会话ID

        Returns:
            消息数量
        """
        result = await self.session.execute(
            select(func.count(Message.id)).where(
                Message.conversation_id == conversation_id
            )
        )
        return result.scalar_one()

    async def get_token_usage(
        self, conversation_id: uuid.UUID
    ) -> dict[str, int]:
        """获取会话的 Token 使用统计

        Args:
            conversation_id: 会话ID

        Returns:
            Token 使用统计
        """
        result = await self.session.execute(
            select(
                func.coalesce(func.sum(Message.prompt_tokens), 0).label("prompt_tokens"),
                func.coalesce(func.sum(Message.completion_tokens), 0).label(
                    "completion_tokens"
                ),
                func.coalesce(func.sum(Message.total_tokens), 0).label("total_tokens"),
            ).where(Message.conversation_id == conversation_id)
        )
        row = result.one()
        return {
            "prompt_tokens": row.prompt_tokens,
            "completion_tokens": row.completion_tokens,
            "total_tokens": row.total_tokens,
        }

    async def delete(self, message_id: uuid.UUID) -> bool:
        """删除消息

        Args:
            message_id: 消息ID

        Returns:
            是否删除成功
        """
        message = await self.get_by_id(message_id)
        if message:
            await self.session.delete(message)
            return True
        return False
