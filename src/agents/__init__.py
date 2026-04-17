"""Agent 模块"""

from src.agents.base import AgentContext, AgentResponse, BaseAgent
from src.agents.factory import AgentFactory, register_agent_type

# 导入实现类以触发注册
from src.agents.implementations import (
    ConfigurableAgent,
    DialogAgent,
    ToolAgent,
)
from src.agents.manager import AgentManager, agent_manager
from src.agents.registry import AgentRegistry, agent_registry

__all__ = [
    # 基类
    "BaseAgent",
    "AgentContext",
    "AgentResponse",
    # 注册中心
    "AgentRegistry",
    "agent_registry",
    # 工厂
    "AgentFactory",
    "register_agent_type",
    # 管理器
    "AgentManager",
    "agent_manager",
    # 实现类
    "ConfigurableAgent",
    "DialogAgent",
    "ToolAgent",
]
