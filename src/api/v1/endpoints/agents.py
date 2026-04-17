"""Agent API 端点"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps.database import get_db
from src.api.deps.auth import CurrentUser
from src.api.deps.space import SpaceMember, SpaceAdmin
from src.api.schemas.common import ResponseModel, PaginatedResponse
from src.api.schemas.agent import (
    AgentCreate,
    AgentUpdate,
    AgentResponse,
    AgentListResponse,
)
from src.models.agent import AgentScope, AgentStatus
from src.models.user import User
from src.models.space import Space
from src.services.agent_service import AgentConfigService
from src.agents import agent_manager

router = APIRouter()


@router.get(
    "",
    response_model=PaginatedResponse[AgentListResponse],
    summary="获取 Agent 列表",
    description="获取空间内可用的 Agent 列表，包括平台级和空间级 Agent",
)
async def list_agents(
    space: SpaceMember,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    include_platform: bool = Query(True, description="是否包含平台级 Agent"),
    status: AgentStatus | None = Query(None, description="状态过滤"),
):
    """获取 Agent 列表"""
    service = AgentConfigService(db)

    # 获取空间级 Agent
    agents = await service.get_space_agents(
        space_id=space.id,
        status=status or AgentStatus.PUBLISHED,
        include_platform=include_platform,
        limit=page_size,
        offset=(page - 1) * page_size,
    )

    # 转换为响应格式
    items = []
    for agent in agents:
        items.append(AgentListResponse(
            id=agent.id,
            agent_id=agent.agent_id,
            name=agent.name,
            description=agent.description,
            avatar=agent.avatar,
            type=agent.type.value,
            scope=agent.scope.value,
            status=agent.status.value,
            welcome_message=agent.welcome_message,
            usage_count=agent.usage_count,
            created_at=agent.created_at,
        ))

    return PaginatedResponse(
        data=items,
        total=len(items),
        page=page,
        page_size=page_size,
        has_more=len(items) == page_size,
    )


@router.get(
    "/{agent_id}",
    response_model=ResponseModel[AgentResponse],
    summary="获取 Agent 详情",
)
async def get_agent(
    agent_id: str,
    space: SpaceMember,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """获取 Agent 详情"""
    service = AgentConfigService(db)

    # 先查空间级
    config = await service.get_by_agent_id(agent_id, space.id)

    # 再查平台级
    if not config:
        from src.services.space_service import SpaceService, SYSTEM_SPACE_CODE
        space_service = SpaceService(db)
        system_space = await space_service.get_by_code(SYSTEM_SPACE_CODE)
        if system_space:
            config = await service.get_by_agent_id(agent_id, system_space.id)

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )

    return ResponseModel(data=AgentResponse(
        id=config.id,
        agent_id=config.agent_id,
        name=config.name,
        description=config.description,
        avatar=config.avatar,
        type=config.type.value,
        scope=config.scope.value,
        status=config.status.value,
        version=config.version,
        space_id=config.space_id,
        model_provider=config.model_provider,
        model_name=config.model_name,
        system_prompt=config.system_prompt,
        welcome_message=config.welcome_message,
        skills=config.skills,
        tools=config.tools,
        max_context_messages=config.max_context_messages,
        max_context_tokens=config.max_context_tokens,
        usage_count=config.usage_count,
        created_at=config.created_at,
        updated_at=config.updated_at,
    ))


@router.post(
    "",
    response_model=ResponseModel[AgentResponse],
    status_code=status.HTTP_201_CREATED,
    summary="创建 Agent",
    description="在当前空间创建一个新的 Agent",
)
async def create_agent(
    data: AgentCreate,
    space: SpaceAdmin,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """创建 Agent"""
    service = AgentConfigService(db)

    # 检查 agent_id 是否已存在
    existing = await service.get_by_agent_id(data.agent_id, space.id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Agent with ID '{data.agent_id}' already exists in this space",
        )

    # 创建 Agent
    config = await service.create(
        agent_id=data.agent_id,
        name=data.name,
        description=data.description,
        avatar=data.avatar,
        space_id=space.id,
        type=data.type,
        scope=AgentScope.SPACE,
        status=AgentStatus.DRAFT,
        created_by=current_user.id,
        model_provider=data.model_provider,
        model_name=data.model_name,
        model_config=data.provider_model_options,
        system_prompt=data.system_prompt,
        welcome_message=data.welcome_message,
        skills=data.skills,
        tools=data.tools,
        mcp_servers=data.mcp_servers,
        knowledge_bases=data.knowledge_bases,
        behavior_config=data.behavior_config,
        max_context_messages=data.max_context_messages,
        max_context_tokens=data.max_context_tokens,
        config=data.config,
    )

    return ResponseModel(data=AgentResponse(
        id=config.id,
        agent_id=config.agent_id,
        name=config.name,
        description=config.description,
        avatar=config.avatar,
        type=config.type.value,
        scope=config.scope.value,
        status=config.status.value,
        version=config.version,
        space_id=config.space_id,
        model_provider=config.model_provider,
        model_name=config.model_name,
        system_prompt=config.system_prompt,
        welcome_message=config.welcome_message,
        skills=config.skills,
        tools=config.tools,
        max_context_messages=config.max_context_messages,
        max_context_tokens=config.max_context_tokens,
        usage_count=config.usage_count,
        created_at=config.created_at,
        updated_at=config.updated_at,
    ))


@router.put(
    "/{agent_id}",
    response_model=ResponseModel[AgentResponse],
    summary="更新 Agent",
)
async def update_agent(
    agent_id: str,
    data: AgentUpdate,
    space: SpaceAdmin,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """更新 Agent"""
    service = AgentConfigService(db)

    config = await service.get_by_agent_id(agent_id, space.id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )

    # 不能修改平台级 Agent
    if config.scope == AgentScope.PLATFORM:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot modify platform-level agent",
        )

    # 更新字段（API 仍使用 model_config 字段名）
    update_data = data.model_dump(exclude_unset=True, by_alias=True)
    if update_data:
        config = await service.update(config.id, **update_data)

    # 重新加载 Agent（如果已缓存）
    await agent_manager.reload_agent(agent_id, space.id)

    return ResponseModel(data=AgentResponse(
        id=config.id,
        agent_id=config.agent_id,
        name=config.name,
        description=config.description,
        avatar=config.avatar,
        type=config.type.value,
        scope=config.scope.value,
        status=config.status.value,
        version=config.version,
        space_id=config.space_id,
        model_provider=config.model_provider,
        model_name=config.model_name,
        system_prompt=config.system_prompt,
        welcome_message=config.welcome_message,
        skills=config.skills,
        tools=config.tools,
        max_context_messages=config.max_context_messages,
        max_context_tokens=config.max_context_tokens,
        usage_count=config.usage_count,
        created_at=config.created_at,
        updated_at=config.updated_at,
    ))


@router.post(
    "/{agent_id}/publish",
    response_model=ResponseModel[AgentResponse],
    summary="发布 Agent",
)
async def publish_agent(
    agent_id: str,
    space: SpaceAdmin,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """发布 Agent"""
    service = AgentConfigService(db)

    config = await service.get_by_agent_id(agent_id, space.id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )

    if config.scope == AgentScope.PLATFORM:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot modify platform-level agent",
        )

    config = await service.publish(config.id)

    return ResponseModel(
        message="Agent published successfully",
        data=AgentResponse(
            id=config.id,
            agent_id=config.agent_id,
            name=config.name,
            description=config.description,
            avatar=config.avatar,
            type=config.type.value,
            scope=config.scope.value,
            status=config.status.value,
            version=config.version,
            space_id=config.space_id,
            model_provider=config.model_provider,
            model_name=config.model_name,
            system_prompt=config.system_prompt,
            welcome_message=config.welcome_message,
            skills=config.skills,
            tools=config.tools,
            max_context_messages=config.max_context_messages,
            max_context_tokens=config.max_context_tokens,
            usage_count=config.usage_count,
            created_at=config.created_at,
            updated_at=config.updated_at,
        ),
    )


@router.delete(
    "/{agent_id}",
    response_model=ResponseModel[None],
    summary="删除 Agent",
)
async def delete_agent(
    agent_id: str,
    space: SpaceAdmin,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """删除 Agent"""
    service = AgentConfigService(db)

    config = await service.get_by_agent_id(agent_id, space.id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )

    if config.scope == AgentScope.PLATFORM:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete platform-level agent",
        )

    await service.delete(config.id)

    return ResponseModel(message="Agent deleted successfully")


@router.post(
    "/{agent_id}/clone",
    response_model=ResponseModel[AgentResponse],
    status_code=status.HTTP_201_CREATED,
    summary="克隆 Agent",
    description="克隆一个 Agent（包括平台级 Agent）到当前空间",
)
async def clone_agent(
    agent_id: str,
    space: SpaceAdmin,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    new_agent_id: str = Query(..., description="新 Agent ID"),
    new_name: str = Query(..., description="新 Agent 名称"),
):
    """克隆 Agent"""
    service = AgentConfigService(db)

    # 查找源 Agent
    config = await service.get_by_agent_id(agent_id, space.id)
    if not config:
        # 尝试平台级
        from src.services.space_service import SpaceService, SYSTEM_SPACE_CODE
        space_service = SpaceService(db)
        system_space = await space_service.get_by_code(SYSTEM_SPACE_CODE)
        if system_space:
            config = await service.get_by_agent_id(agent_id, system_space.id)

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source agent not found",
        )

    # 检查目标 ID 是否已存在
    existing = await service.get_by_agent_id(new_agent_id, space.id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Agent with ID '{new_agent_id}' already exists",
        )

    # 克隆
    new_config = await service.clone(
        config_id=config.id,
        new_agent_id=new_agent_id,
        new_name=new_name,
        target_space_id=space.id,
        created_by=current_user.id,
    )

    return ResponseModel(data=AgentResponse(
        id=new_config.id,
        agent_id=new_config.agent_id,
        name=new_config.name,
        description=new_config.description,
        avatar=new_config.avatar,
        type=new_config.type.value,
        scope=new_config.scope.value,
        status=new_config.status.value,
        version=new_config.version,
        space_id=new_config.space_id,
        model_provider=new_config.model_provider,
        model_name=new_config.model_name,
        system_prompt=new_config.system_prompt,
        welcome_message=new_config.welcome_message,
        skills=new_config.skills,
        tools=new_config.tools,
        max_context_messages=new_config.max_context_messages,
        max_context_tokens=new_config.max_context_tokens,
        usage_count=new_config.usage_count,
        created_at=new_config.created_at,
        updated_at=new_config.updated_at,
    ))
