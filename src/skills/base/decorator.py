"""Skill 装饰器定义"""

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from functools import wraps
from typing import Any, ParamSpec, TypeVar

from loguru import logger

from src.skills.base.response import SkillResponse

P = ParamSpec("P")
R = TypeVar("R")


@dataclass
class SkillMetadata:
    """Skill 元数据"""

    skill_id: str
    name: str
    description: str
    version: str = "1.0.0"
    category: str = "common"
    enabled: bool = True
    timeout: float | None = None
    retries: int = 0
    retry_delay: float = 1.0
    tags: list[str] = field(default_factory=list)
    author: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "skill_id": self.skill_id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "category": self.category,
            "enabled": self.enabled,
            "timeout": self.timeout,
            "retries": self.retries,
            "retry_delay": self.retry_delay,
            "tags": self.tags,
            "author": self.author,
        }


def skill(
    skill_id: str,
    name: str,
    description: str,
    version: str = "1.0.0",
    category: str = "common",
    enabled: bool = True,
    timeout: float | None = None,
    retries: int = 0,
    retry_delay: float = 1.0,
    tags: list[str] | None = None,
    author: str | None = None,
    auto_register: bool = True,
) -> Callable[[Callable[P, R]], Callable[P, SkillResponse]]:
    """Skill 装饰器

    用于将函数标记为 Skill，并添加元数据、错误处理、重试等功能

    Args:
        skill_id: Skill 唯一标识
        name: Skill 名称
        description: Skill 描述
        version: 版本号
        category: 分类
        enabled: 是否启用
        timeout: 超时时间（秒）
        retries: 重试次数
        retry_delay: 重试间隔（秒）
        tags: 标签列表
        author: 作者
        auto_register: 是否自动注册到全局注册中心

    Returns:
        装饰器函数

    Example:
        >>> @skill(
        ...     skill_id="common.text.extract",
        ...     name="文本提取",
        ...     description="从文本中提取关键信息",
        ... )
        ... def extract_text(text: str) -> str:
        ...     return text.strip()
    """
    metadata = SkillMetadata(
        skill_id=skill_id,
        name=name,
        description=description,
        version=version,
        category=category,
        enabled=enabled,
        timeout=timeout,
        retries=retries,
        retry_delay=retry_delay,
        tags=tags or [],
        author=author,
    )

    def decorator(func: Callable[P, R]) -> Callable[P, SkillResponse]:
        # 检查是否为异步函数
        is_async = asyncio.iscoroutinefunction(func)

        if is_async:
            @wraps(func)
            async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> SkillResponse:
                return await _execute_async(func, metadata, *args, **kwargs)

            wrapper = async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> SkillResponse:
                return _execute_sync(func, metadata, *args, **kwargs)

            wrapper = sync_wrapper

        # 附加元数据
        wrapper._skill_metadata = metadata  # type: ignore
        wrapper._is_skill = True  # type: ignore

        # 自动注册
        if auto_register:
            from src.skills.base.registry import skill_registry
            skill_registry.register_func(wrapper)

        return wrapper

    return decorator


async def _execute_async(
    func: Callable[P, R],
    metadata: SkillMetadata,
    *args: P.args,
    **kwargs: P.kwargs,
) -> SkillResponse:
    """执行异步 Skill"""
    if not metadata.enabled:
        return SkillResponse.error(
            message=f"Skill '{metadata.skill_id}' is disabled",
            code="SKILL_DISABLED",
        )

    start_time = time.perf_counter()
    last_error: Exception | None = None

    for attempt in range(metadata.retries + 1):
        try:
            logger.debug(
                f"Executing skill: {metadata.skill_id}, attempt: {attempt + 1}"
            )

            # 执行带超时的异步函数
            if metadata.timeout:
                result = await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=metadata.timeout,
                )
            else:
                result = await func(*args, **kwargs)

            # 计算执行时间
            duration_ms = (time.perf_counter() - start_time) * 1000

            # 如果返回的已经是 SkillResponse，直接使用
            if isinstance(result, SkillResponse):
                result.duration_ms = duration_ms
                return result

            # 否则包装为成功响应
            response = SkillResponse.success(content=result)
            response.duration_ms = duration_ms

            logger.debug(
                f"Skill executed successfully: {metadata.skill_id}, "
                f"duration: {duration_ms:.2f}ms"
            )

            return response

        except TimeoutError:
            last_error = TimeoutError(
                f"Skill '{metadata.skill_id}' timed out after {metadata.timeout}s"
            )
            logger.warning(f"Skill timeout: {metadata.skill_id}")

        except Exception as e:
            last_error = e
            logger.warning(
                f"Skill execution failed: {metadata.skill_id}, "
                f"attempt: {attempt + 1}, error: {e}"
            )

        # 重试前等待
        if attempt < metadata.retries:
            await asyncio.sleep(metadata.retry_delay)

    # 所有重试都失败
    duration_ms = (time.perf_counter() - start_time) * 1000
    error_response = SkillResponse.error(
        message=str(last_error) if last_error else "Unknown error",
        code="EXECUTION_ERROR",
    )
    error_response.duration_ms = duration_ms

    logger.error(f"Skill failed after {metadata.retries + 1} attempts: {metadata.skill_id}")

    return error_response


def _execute_sync(
    func: Callable[P, R],
    metadata: SkillMetadata,
    *args: P.args,
    **kwargs: P.kwargs,
) -> SkillResponse:
    """执行同步 Skill"""
    if not metadata.enabled:
        return SkillResponse.error(
            message=f"Skill '{metadata.skill_id}' is disabled",
            code="SKILL_DISABLED",
        )

    start_time = time.perf_counter()
    last_error: Exception | None = None

    for attempt in range(metadata.retries + 1):
        try:
            logger.debug(
                f"Executing skill: {metadata.skill_id}, attempt: {attempt + 1}"
            )

            result = func(*args, **kwargs)

            # 计算执行时间
            duration_ms = (time.perf_counter() - start_time) * 1000

            # 如果返回的已经是 SkillResponse，直接使用
            if isinstance(result, SkillResponse):
                result.duration_ms = duration_ms
                return result

            # 否则包装为成功响应
            response = SkillResponse.success(content=result)
            response.duration_ms = duration_ms

            logger.debug(
                f"Skill executed successfully: {metadata.skill_id}, "
                f"duration: {duration_ms:.2f}ms"
            )

            return response

        except Exception as e:
            last_error = e
            logger.warning(
                f"Skill execution failed: {metadata.skill_id}, "
                f"attempt: {attempt + 1}, error: {e}"
            )

        # 重试前等待
        if attempt < metadata.retries:
            time.sleep(metadata.retry_delay)

    # 所有重试都失败
    duration_ms = (time.perf_counter() - start_time) * 1000
    error_response = SkillResponse.error(
        message=str(last_error) if last_error else "Unknown error",
        code="EXECUTION_ERROR",
    )
    error_response.duration_ms = duration_ms

    logger.error(f"Skill failed after {metadata.retries + 1} attempts: {metadata.skill_id}")

    return error_response
