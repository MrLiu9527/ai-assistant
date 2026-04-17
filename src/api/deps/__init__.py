"""API 依赖注入"""

from src.api.deps.auth import get_current_user, get_current_user_optional
from src.api.deps.database import get_db
from src.api.deps.space import check_space_permission, get_space

__all__ = [
    "get_db",
    "get_current_user",
    "get_current_user_optional",
    "get_space",
    "check_space_permission",
]
