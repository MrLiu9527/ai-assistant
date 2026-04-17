"""API Schemas"""

from src.api.schemas.agent import (
    AgentCreate,
    AgentListResponse,
    AgentResponse,
    AgentUpdate,
)
from src.api.schemas.common import (
    ErrorResponse,
    PaginatedResponse,
    ResponseModel,
)
from src.api.schemas.conversation import (
    ChatRequest,
    ChatResponse,
    ConversationCreate,
    ConversationResponse,
    MessageCreate,
    MessageResponse,
)
from src.api.schemas.space import (
    MemberAdd,
    MemberResponse,
    MemberUpdate,
    SpaceCreate,
    SpaceResponse,
    SpaceUpdate,
)

__all__ = [
    # Common
    "ResponseModel",
    "PaginatedResponse",
    "ErrorResponse",
    # Agent
    "AgentCreate",
    "AgentUpdate",
    "AgentResponse",
    "AgentListResponse",
    # Conversation
    "ConversationCreate",
    "ConversationResponse",
    "MessageCreate",
    "MessageResponse",
    "ChatRequest",
    "ChatResponse",
    # Space
    "SpaceCreate",
    "SpaceUpdate",
    "SpaceResponse",
    "MemberAdd",
    "MemberUpdate",
    "MemberResponse",
]
