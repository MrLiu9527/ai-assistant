"""Skill 注册中心"""

import inspect
from dataclasses import dataclass
from typing import Any, Callable

from loguru import logger

from src.skills.base.decorator import SkillMetadata
from src.skills.base.response import SkillResponse


@dataclass
class SkillInfo:
    """Skill 信息"""

    metadata: SkillMetadata
    func: Callable[..., SkillResponse]
    signature: inspect.Signature
    is_async: bool

    @property
    def skill_id(self) -> str:
        return self.metadata.skill_id

    @property
    def name(self) -> str:
        return self.metadata.name

    @property
    def description(self) -> str:
        return self.metadata.description

    @property
    def category(self) -> str:
        return self.metadata.category

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            **self.metadata.to_dict(),
            "is_async": self.is_async,
            "parameters": [
                {
                    "name": name,
                    "annotation": str(param.annotation) if param.annotation != inspect.Parameter.empty else None,
                    "default": str(param.default) if param.default != inspect.Parameter.empty else None,
                    "kind": param.kind.name,
                }
                for name, param in self.signature.parameters.items()
            ],
        }

    def to_tool_schema(self) -> dict[str, Any]:
        """转换为 LLM Tool 调用 schema

        兼容 OpenAI function calling 格式
        """
        parameters = {
            "type": "object",
            "properties": {},
            "required": [],
        }

        for name, param in self.signature.parameters.items():
            if name in ("self", "cls"):
                continue

            param_info: dict[str, Any] = {"type": "string"}

            # 根据类型注解推断类型
            if param.annotation != inspect.Parameter.empty:
                annotation = param.annotation
                if annotation == int:
                    param_info["type"] = "integer"
                elif annotation == float:
                    param_info["type"] = "number"
                elif annotation == bool:
                    param_info["type"] = "boolean"
                elif annotation == list or str(annotation).startswith("list"):
                    param_info["type"] = "array"
                elif annotation == dict or str(annotation).startswith("dict"):
                    param_info["type"] = "object"

            # 添加默认值
            if param.default != inspect.Parameter.empty:
                param_info["default"] = param.default
            else:
                parameters["required"].append(name)

            parameters["properties"][name] = param_info

        return {
            "type": "function",
            "function": {
                "name": self.metadata.skill_id,
                "description": self.metadata.description,
                "parameters": parameters,
            },
        }


class SkillRegistry:
    """Skill 注册中心

    管理所有已注册的 Skills，支持按分类、标签查询
    """

    _instance = None

    def __new__(cls) -> "SkillRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._skills: dict[str, SkillInfo] = {}
        return cls._instance

    def register_func(self, func: Callable[..., SkillResponse]) -> None:
        """注册 Skill 函数

        Args:
            func: 被 @skill 装饰器装饰的函数
        """
        metadata: SkillMetadata | None = getattr(func, "_skill_metadata", None)
        if metadata is None:
            raise ValueError(
                f"Function '{func.__name__}' is not decorated with @skill"
            )

        skill_info = SkillInfo(
            metadata=metadata,
            func=func,
            signature=inspect.signature(func),
            is_async=inspect.iscoroutinefunction(func.__wrapped__ if hasattr(func, "__wrapped__") else func),
        )

        if metadata.skill_id in self._skills:
            logger.warning(f"Skill already registered, overwriting: {metadata.skill_id}")

        self._skills[metadata.skill_id] = skill_info
        logger.info(f"Skill registered: {metadata.skill_id} ({metadata.name})")

    def unregister(self, skill_id: str) -> bool:
        """注销 Skill

        Args:
            skill_id: Skill ID

        Returns:
            是否成功注销
        """
        if skill_id in self._skills:
            del self._skills[skill_id]
            logger.info(f"Skill unregistered: {skill_id}")
            return True
        return False

    def get(self, skill_id: str) -> SkillInfo | None:
        """获取 Skill 信息

        Args:
            skill_id: Skill ID

        Returns:
            Skill 信息或 None
        """
        return self._skills.get(skill_id)

    def get_func(self, skill_id: str) -> Callable[..., SkillResponse] | None:
        """获取 Skill 函数

        Args:
            skill_id: Skill ID

        Returns:
            Skill 函数或 None
        """
        skill_info = self.get(skill_id)
        return skill_info.func if skill_info else None

    def execute(self, skill_id: str, *args: Any, **kwargs: Any) -> SkillResponse:
        """执行 Skill（同步）

        Args:
            skill_id: Skill ID
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            Skill 执行结果
        """
        skill_info = self.get(skill_id)
        if skill_info is None:
            return SkillResponse.error(
                message=f"Skill not found: {skill_id}",
                code="SKILL_NOT_FOUND",
            )

        if skill_info.is_async:
            return SkillResponse.error(
                message=f"Skill '{skill_id}' is async, use execute_async instead",
                code="ASYNC_SKILL",
            )

        return skill_info.func(*args, **kwargs)

    async def execute_async(
        self, skill_id: str, *args: Any, **kwargs: Any
    ) -> SkillResponse:
        """执行 Skill（异步）

        Args:
            skill_id: Skill ID
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            Skill 执行结果
        """
        skill_info = self.get(skill_id)
        if skill_info is None:
            return SkillResponse.error(
                message=f"Skill not found: {skill_id}",
                code="SKILL_NOT_FOUND",
            )

        if skill_info.is_async:
            return await skill_info.func(*args, **kwargs)
        else:
            return skill_info.func(*args, **kwargs)

    def list_all(self) -> list[SkillInfo]:
        """列出所有 Skills

        Returns:
            Skill 信息列表
        """
        return list(self._skills.values())

    def list_by_category(self, category: str) -> list[SkillInfo]:
        """按分类列出 Skills

        Args:
            category: 分类名

        Returns:
            Skill 信息列表
        """
        return [s for s in self._skills.values() if s.category == category]

    def list_by_tag(self, tag: str) -> list[SkillInfo]:
        """按标签列出 Skills

        Args:
            tag: 标签名

        Returns:
            Skill 信息列表
        """
        return [s for s in self._skills.values() if tag in s.metadata.tags]

    def list_enabled(self) -> list[SkillInfo]:
        """列出所有启用的 Skills

        Returns:
            Skill 信息列表
        """
        return [s for s in self._skills.values() if s.metadata.enabled]

    def get_categories(self) -> list[str]:
        """获取所有分类

        Returns:
            分类列表
        """
        return list(set(s.category for s in self._skills.values()))

    def get_tags(self) -> list[str]:
        """获取所有标签

        Returns:
            标签列表
        """
        tags = set()
        for s in self._skills.values():
            tags.update(s.metadata.tags)
        return list(tags)

    def get_tool_schemas(
        self, skill_ids: list[str] | None = None
    ) -> list[dict[str, Any]]:
        """获取 Skills 的 Tool Schema 列表

        Args:
            skill_ids: Skill ID 列表，None 表示所有

        Returns:
            Tool Schema 列表
        """
        if skill_ids is None:
            skills = self.list_enabled()
        else:
            skills = [self.get(sid) for sid in skill_ids if self.get(sid)]

        return [s.to_tool_schema() for s in skills if s]

    def is_registered(self, skill_id: str) -> bool:
        """检查 Skill 是否已注册

        Args:
            skill_id: Skill ID

        Returns:
            是否已注册
        """
        return skill_id in self._skills

    def clear(self) -> None:
        """清空所有注册"""
        self._skills.clear()
        logger.info("Skill registry cleared")


# 全局 Skill 注册中心实例
skill_registry = SkillRegistry()
