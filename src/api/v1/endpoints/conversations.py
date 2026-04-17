"""Conversation API 端点"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps.auth import CurrentUser
from src.api.deps.database import get_db
from src.api.deps.space import SpaceMember
from src.api.schemas.common import PaginatedResponse, ResponseModel
from src.api.schemas.conversation import (
    ConversationCreate,
    ConversationResponse,
    ConversationUpdate,
    MessageResponse,
)
from src.services.agent_service import AgentConfigService
from src.services.conversation_service import ConversationService
from src.services.message_service import MessageService

router = APIRouter()


@router.get(
    "",
    response_model=PaginatedResponse[ConversationResponse],
    summary="获取会话列表",
)
async def list_conversations(
    space: SpaceMember,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    agent_id: str | None = Query(None, description="按 Agent 筛选"),
    is_active: bool | None = Query(None, description="是否活跃"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
):
    """获取当前用户在空间内的会话列表"""
    service = ConversationService(db)

    conversations = await service.get_by_user(
        user_id=current_user.id,
        space_id=space.id,
        agent_id=agent_id,
        is_active=is_active,
        limit=page_size,
        offset=(page - 1) * page_size,
    )

    items = [
        ConversationResponse(
            id=conv.id,
            title=conv.title,
            agent_id=conv.agent_id,
            agent_type=conv.agent_type,
            space_id=conv.space_id,
            is_active=conv.is_active,
            is_pinned=conv.is_pinned,
            message_count=conv.message_count,
            total_tokens=conv.total_tokens,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
            ended_at=conv.ended_at,
        )
        for conv in conversations
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
    response_model=ResponseModel[ConversationResponse],
    status_code=status.HTTP_201_CREATED,
    summary="创建会话",
)
async def create_conversation(
    data: ConversationCreate,
    space: SpaceMember,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """创建新会话"""
    # 验证 Agent 存在
    agent_service = AgentConfigService(db)
    config = await agent_service.get_by_agent_id(data.agent_id, space.id)

    # 尝试平台级
    if not config:
        from src.services.space_service import SYSTEM_SPACE_CODE, SpaceService
        space_service = SpaceService(db)
        system_space = await space_service.get_by_code(SYSTEM_SPACE_CODE)
        if system_space:
            config = await agent_service.get_by_agent_id(data.agent_id, system_space.id)

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )

    if config.status.value != "published":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Agent is not published",
        )

    # 创建会话
    conv_service = ConversationService(db)
    conversation = await conv_service.create(
        user_id=current_user.id,
        space_id=space.id,
        agent_id=config.agent_id,
        agent_type=config.type.value,
        agent_config_id=config.id,
        title=data.title,
        metadata=data.metadata,
    )

    # 增加 Agent 使用次数
    await agent_service.increment_usage(config.id)

    return ResponseModel(data=ConversationResponse(
        id=conversation.id,
        title=conversation.title,
        agent_id=conversation.agent_id,
        agent_type=conversation.agent_type,
        space_id=conversation.space_id,
        is_active=conversation.is_active,
        is_pinned=conversation.is_pinned,
        message_count=conversation.message_count,
        total_tokens=conversation.total_tokens,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        ended_at=conversation.ended_at,
    ))


@router.get(
    "/{conversation_id}",
    response_model=ResponseModel[ConversationResponse],
    summary="获取会话详情",
)
async def get_conversation(
    conversation_id: UUID,
    space: SpaceMember,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """获取会话详情"""
    service = ConversationService(db)
    conversation = await service.get_by_id(conversation_id)

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    # 检查权限
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

    return ResponseModel(data=ConversationResponse(
        id=conversation.id,
        title=conversation.title,
        agent_id=conversation.agent_id,
        agent_type=conversation.agent_type,
        space_id=conversation.space_id,
        is_active=conversation.is_active,
        is_pinned=conversation.is_pinned,
        message_count=conversation.message_count,
        total_tokens=conversation.total_tokens,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        ended_at=conversation.ended_at,
    ))


@router.put(
    "/{conversation_id}",
    response_model=ResponseModel[ConversationResponse],
    summary="更新会话",
)
async def update_conversation(
    conversation_id: UUID,
    data: ConversationUpdate,
    space: SpaceMember,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """更新会话（标题、置顶等）"""
    service = ConversationService(db)
    conversation = await service.get_by_id(conversation_id)

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

    # 更新
    if data.title is not None:
        conversation = await service.update_title(conversation_id, data.title)

    if data.is_pinned is not None:
        await service.toggle_pin(conversation_id)
        conversation = await service.get_by_id(conversation_id)

    if data.metadata is not None:
        conversation = await service.update_metadata(conversation_id, data.metadata)

    return ResponseModel(data=ConversationResponse(
        id=conversation.id,
        title=conversation.title,
        agent_id=conversation.agent_id,
        agent_type=conversation.agent_type,
        space_id=conversation.space_id,
        is_active=conversation.is_active,
        is_pinned=conversation.is_pinned,
        message_count=conversation.message_count,
        total_tokens=conversation.total_tokens,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        ended_at=conversation.ended_at,
    ))


@router.delete(
    "/{conversation_id}",
    response_model=ResponseModel[None],
    summary="删除会话",
)
async def delete_conversation(
    conversation_id: UUID,
    space: SpaceMember,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """删除会话"""
    service = ConversationService(db)
    conversation = await service.get_by_id(conversation_id)

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

    await service.delete(conversation_id)

    return ResponseModel(message="Conversation deleted successfully")


@router.get(
    "/{conversation_id}/messages",
    response_model=PaginatedResponse[MessageResponse],
    summary="获取会话消息",
)
async def list_messages(
    conversation_id: UUID,
    space: SpaceMember,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=100, description="每页数量"),
):
    """获取会话消息列表"""
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

    msg_service = MessageService(db)
    messages = await msg_service.get_by_conversation(
        conversation_id=conversation_id,
        limit=page_size,
        offset=(page - 1) * page_size,
    )

    items = [
        MessageResponse(
            id=msg.id,
            conversation_id=msg.conversation_id,
            role=msg.role.value,
            type=msg.type.value,
            content=msg.content,
            tool_name=msg.tool_name,
            tool_call_id=msg.tool_call_id,
            tool_args=msg.tool_args,
            tool_result=msg.tool_result,
            prompt_tokens=msg.prompt_tokens,
            completion_tokens=msg.completion_tokens,
            total_tokens=msg.total_tokens,
            metadata=msg.metadata_,
            created_at=msg.created_at,
        )
        for msg in messages
    ]

    return PaginatedResponse(
        data=items,
        total=len(items),
        page=page,
        page_size=page_size,
        has_more=len(items) == page_size,
    )


@router.post(
    "/{conversation_id}/end",
    response_model=ResponseModel[ConversationResponse],
    summary="结束会话",
)
async def end_conversation(
    conversation_id: UUID,
    space: SpaceMember,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """结束会话"""
    service = ConversationService(db)
    conversation = await service.get_by_id(conversation_id)

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

    conversation = await service.end_conversation(conversation_id)

    return ResponseModel(
        message="Conversation ended",
        data=ConversationResponse(
            id=conversation.id,
            title=conversation.title,
            agent_id=conversation.agent_id,
            agent_type=conversation.agent_type,
            space_id=conversation.space_id,
            is_active=conversation.is_active,
            is_pinned=conversation.is_pinned,
            message_count=conversation.message_count,
            total_tokens=conversation.total_tokens,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            ended_at=conversation.ended_at,
        ),
    )
