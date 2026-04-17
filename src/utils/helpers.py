"""通用辅助函数"""

import re
import uuid
from datetime import datetime
from typing import Any, TypeVar

import orjson

T = TypeVar("T")


def generate_id(prefix: str = "") -> str:
    """生成唯一 ID

    Args:
        prefix: ID 前缀

    Returns:
        唯一 ID 字符串
    """
    uid = uuid.uuid4().hex[:12]
    timestamp = int(datetime.now().timestamp() * 1000) % 1000000
    if prefix:
        return f"{prefix}_{timestamp}_{uid}"
    return f"{timestamp}_{uid}"


def safe_json_parse(
    json_str: str,
    default: T = None,  # type: ignore
) -> T | dict[str, Any] | list[Any]:
    """安全解析 JSON 字符串

    Args:
        json_str: JSON 字符串
        default: 解析失败时的默认值

    Returns:
        解析后的对象或默认值
    """
    try:
        return orjson.loads(json_str)
    except (orjson.JSONDecodeError, TypeError):
        return default


def safe_json_dumps(obj: Any, default: str = "{}") -> str:
    """安全序列化为 JSON 字符串

    Args:
        obj: 要序列化的对象
        default: 序列化失败时的默认值

    Returns:
        JSON 字符串
    """
    try:
        return orjson.dumps(obj).decode("utf-8")
    except (TypeError, ValueError):
        return default


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """截断文本

    Args:
        text: 输入文本
        max_length: 最大长度
        suffix: 截断后缀

    Returns:
        截断后的文本
    """
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


def validate_email(email: str) -> bool:
    """验证邮箱格式

    Args:
        email: 邮箱地址

    Returns:
        是否为有效邮箱
    """
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def validate_phone(phone: str) -> bool:
    """验证手机号格式（中国大陆）

    Args:
        phone: 手机号

    Returns:
        是否为有效手机号
    """
    pattern = r"^1[3-9]\d{9}$"
    return bool(re.match(pattern, phone))


def format_datetime(
    dt: datetime | None = None,
    fmt: str = "%Y-%m-%d %H:%M:%S",
) -> str:
    """格式化日期时间

    Args:
        dt: 日期时间对象，None 表示当前时间
        fmt: 格式化字符串

    Returns:
        格式化后的字符串
    """
    if dt is None:
        dt = datetime.now()
    return dt.strftime(fmt)


def parse_datetime(
    dt_str: str,
    fmt: str = "%Y-%m-%d %H:%M:%S",
) -> datetime | None:
    """解析日期时间字符串

    Args:
        dt_str: 日期时间字符串
        fmt: 格式化字符串

    Returns:
        日期时间对象或 None
    """
    try:
        return datetime.strptime(dt_str, fmt)
    except ValueError:
        return None
