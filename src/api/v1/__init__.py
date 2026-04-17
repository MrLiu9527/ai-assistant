"""API V1"""

from fastapi import APIRouter

from src.api.v1.endpoints import agents, chat, conversations, spaces

router = APIRouter()

# 注册路由 - 所有路由都在 /space/{space_id} 下
router.include_router(
    agents.router,
    prefix="/space/{space_id}/agents",
    tags=["agents"],
)
router.include_router(
    conversations.router,
    prefix="/space/{space_id}/conversations",
    tags=["conversations"],
)
router.include_router(
    chat.router,
    prefix="/space/{space_id}/chat",
    tags=["chat"],
)
router.include_router(
    spaces.router,
    prefix="/spaces",
    tags=["spaces"],
)
