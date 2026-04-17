"""Chat API 端点"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents import agent_manager
from src.api.deps.auth import CurrentUser
from src.api.deps.database import get_db
from src.api.deps.space import SpaceMember
from src.api.schemas.common import ResponseModel
from src.api.schemas.conversation import (
    ChatRequest,
    ChatResponse,
)
from src.services.conversation_service import ConversationService

router = APIRouter()


@router.post(
    "/{agent_id}",
    response_model=ResponseModel[ChatResponse],
    summary="快速聊天",
    description="与指定 Agent 进行聊天，自动创建会话",
)
async def quick_chat(
    agent_id: str,
    request: ChatRequest,
    space: SpaceMember,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    conversation_id: UUID | None = None,
):
    """快速聊天

    如果提供 conversation_id，则使用已有会话；
    否则自动创建新会话。
    """
    # 确保 Agent 管理器已初始化
    await agent_manager.initialize()

    # 获取或创建会话
    if conversation_id:
        # 使用已有会话
        conv_service = ConversationService(db)
        conversation = await conv_service.get_by_id(conversation_id)

        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found",
            )

        if conversation.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied",
            )

        if not conversation.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Conversation has ended",
            )

        context_conversation_id = conversation_id
    else:
        # 创建新会话
        context = await agent_manager.create_conversation(
            agent_id=agent_id,
            space_id=space.id,
            user_id=current_user.id,
        )

        if not context:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent not found or not available",
            )

        context_conversation_id = context.conversation_id

    # 发送消息
    response = await agent_manager.chat(
        agent_id=agent_id,
        space_id=space.id,
        conversation_id=context_conversation_id,
        message=request.message,
        stream=request.stream,
    )

    if not response:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get response from agent",
        )

    return ResponseModel(data=ChatResponse(
        message_id=response.message_id,
        conversation_id=context_conversation_id,
        content=response.content,
        role="assistant",
        tool_calls=response.tool_calls if response.tool_calls else None,
        prompt_tokens=response.prompt_tokens,
        completion_tokens=response.completion_tokens,
        total_tokens=response.total_tokens,
    ))


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=ResponseModel[ChatResponse],
    summary="发送消息",
    description="在已有会话中发送消息",
)
async def send_message(
    conversation_id: UUID,
    request: ChatRequest,
    space: SpaceMember,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """在已有会话中发送消息"""
    # 获取会话
    conv_service = ConversationService(db)
    conversation = await conv_service.get_by_id(conversation_id)

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    if conversation.user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied",
        )

    if conversation.space_id != space.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found in this space",
        )

    if not conversation.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Conversation has ended",
        )

    # 确保 Agent 管理器已初始化
    await agent_manager.initialize()

    # 发送消息
    response = await agent_manager.chat(
        agent_id=conversation.agent_id,
        space_id=space.id,
        conversation_id=conversation_id,
        message=request.message,
        stream=request.stream,
    )

    if not response:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get response from agent",
        )

    return ResponseModel(data=ChatResponse(
        message_id=response.message_id,
        conversation_id=conversation_id,
        content=response.content,
        role="assistant",
        tool_calls=response.tool_calls if response.tool_calls else None,
        prompt_tokens=response.prompt_tokens,
        completion_tokens=response.completion_tokens,
        total_tokens=response.total_tokens,
    ))
