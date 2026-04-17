"""Agent Schema"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.models.agent import AgentType, AgentScope, AgentStatus


class AgentBase(BaseModel):
    """Agent 基础字段."""

    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(..., min_length=1, max_length=128, description="Agent 名称")
    description: str | None = Field(None, max_length=1000, description="Agent 描述")
    avatar: str | None = Field(None, max_length=500, description="头像 URL")
    type: AgentType = Field(default=AgentType.DIALOG, description="Agent 类型")


class AgentCreate(AgentBase):
    """创建 Agent."""

    agent_id: str = Field(..., min_length=1, max_length=64, pattern=r"^[a-z][a-z0-9_]*$", description="Agent ID（小写字母开头，仅含小写字母、数字、下划线）")
    model_provider: str = Field(default="dashscope", description="模型提供商")
    model_name: str = Field(default="qwen-turbo", description="模型名称")
    provider_model_options: dict[str, Any] | None = Field(
        default=None,
        alias="model_config",
        description="模型配置",
    )
    system_prompt: str | None = Field(None, description="系统提示词")
    welcome_message: str | None = Field(None, description="欢迎消息")
    skills: list[str] | None = Field(default=None, description="Skill ID 列表")
    tools: list[str] | None = Field(default=None, description="Tool ID 列表")
    mcp_servers: list[dict[str, Any]] | None = Field(default=None, description="MCP 服务器配置")
    knowledge_bases: list[str] | None = Field(default=None, description="知识库 ID 列表")
    behavior_config: dict[str, Any] | None = Field(default=None, description="行为配置")
    max_context_messages: int = Field(default=20, ge=1, le=100, description="最大上下文消息数")
    max_context_tokens: int = Field(default=4000, ge=100, le=128000, description="最大上下文 Token 数")
    config: dict[str, Any] | None = Field(default=None, description="其他配置")


class AgentUpdate(BaseModel):
    """更新 Agent."""

    model_config = ConfigDict(populate_by_name=True)

    name: str | None = Field(None, min_length=1, max_length=128, description="Agent 名称")
    description: str | None = Field(None, max_length=1000, description="Agent 描述")
    avatar: str | None = Field(None, max_length=500, description="头像 URL")
    type: AgentType | None = Field(None, description="Agent 类型")
    status: AgentStatus | None = Field(None, description="Agent 状态")
    model_provider: str | None = Field(None, description="模型提供商")
    model_name: str | None = Field(None, description="模型名称")
    provider_model_options: dict[str, Any] | None = Field(
        None,
        alias="model_config",
        description="模型配置",
    )
    system_prompt: str | None = Field(None, description="系统提示词")
    welcome_message: str | None = Field(None, description="欢迎消息")
    skills: list[str] | None = Field(None, description="Skill ID 列表")
    tools: list[str] | None = Field(None, description="Tool ID 列表")
    mcp_servers: list[dict[str, Any]] | None = Field(None, description="MCP 服务器配置")
    knowledge_bases: list[str] | None = Field(None, description="知识库 ID 列表")
    behavior_config: dict[str, Any] | None = Field(None, description="行为配置")
    max_context_messages: int | None = Field(None, ge=1, le=100, description="最大上下文消息数")
    max_context_tokens: int | None = Field(None, ge=100, le=128000, description="最大上下文 Token 数")
    config: dict[str, Any] | None = Field(None, description="其他配置")


class AgentResponse(BaseModel):
    """Agent 响应."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="配置 ID")
    agent_id: str = Field(..., description="Agent ID")
    name: str = Field(..., description="Agent 名称")
    description: str | None = Field(None, description="Agent 描述")
    avatar: str | None = Field(None, description="头像 URL")
    type: str = Field(..., description="Agent 类型")
    scope: str = Field(..., description="作用域")
    status: str = Field(..., description="状态")
    version: str = Field(..., description="版本")
    space_id: UUID = Field(..., description="空间 ID")
    model_provider: str = Field(..., description="模型提供商")
    model_name: str = Field(..., description="模型名称")
    system_prompt: str | None = Field(None, description="系统提示词")
    welcome_message: str | None = Field(None, description="欢迎消息")
    skills: list[str] | None = Field(None, description="Skill 列表")
    tools: list[str] | None = Field(None, description="Tool 列表")
    max_context_messages: int = Field(..., description="最大上下文消息数")
    max_context_tokens: int = Field(..., description="最大上下文 Token 数")
    usage_count: int = Field(default=0, description="使用次数")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")


class AgentListResponse(BaseModel):
    """Agent 列表响应."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="配置 ID")
    agent_id: str = Field(..., description="Agent ID")
    name: str = Field(..., description="Agent 名称")
    description: str | None = Field(None, description="Agent 描述")
    avatar: str | None = Field(None, description="头像 URL")
    type: str = Field(..., description="Agent 类型")
    scope: str = Field(..., description="作用域")
    status: str = Field(..., description="状态")
    welcome_message: str | None = Field(None, description="欢迎消息")
    usage_count: int = Field(default=0, description="使用次数")
    created_at: datetime = Field(..., description="创建时间")
