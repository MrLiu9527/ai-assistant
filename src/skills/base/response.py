"""Skill 响应定义"""

import enum
from dataclasses import dataclass, field
from typing import Any


class SkillStatus(str, enum.Enum):
    """Skill 执行状态"""

    SUCCESS = "success"
    ERROR = "error"
    PENDING = "pending"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


@dataclass
class SkillResponse:
    """Skill 执行响应

    统一的 Skill 返回格式，兼容 AgentScope 的 ServiceResponse
    """

    status: SkillStatus
    content: Any = None
    error_message: str | None = None
    error_code: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    duration_ms: float | None = None

    @classmethod
    def success(
        cls,
        content: Any = None,
        metadata: dict[str, Any] | None = None,
    ) -> "SkillResponse":
        """创建成功响应"""
        return cls(
            status=SkillStatus.SUCCESS,
            content=content,
            metadata=metadata or {},
        )

    @classmethod
    def error(
        cls,
        message: str,
        code: str | None = None,
        content: Any = None,
        metadata: dict[str, Any] | None = None,
    ) -> "SkillResponse":
        """创建错误响应"""
        return cls(
            status=SkillStatus.ERROR,
            content=content,
            error_message=message,
            error_code=code,
            metadata=metadata or {},
        )

    @property
    def is_success(self) -> bool:
        """是否成功"""
        return self.status == SkillStatus.SUCCESS

    @property
    def is_error(self) -> bool:
        """是否错误"""
        return self.status == SkillStatus.ERROR

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "status": self.status.value,
            "content": self.content,
            "error_message": self.error_message,
            "error_code": self.error_code,
            "metadata": self.metadata,
            "duration_ms": self.duration_ms,
        }

    def to_agentscope_response(self):
        """转换为 AgentScope ServiceResponse

        Returns:
            ServiceResponse 对象
        """
        try:
            from agentscope.service import ServiceExecStatus, ServiceResponse

            if self.is_success:
                return ServiceResponse(
                    status=ServiceExecStatus.SUCCESS,
                    content=self.content,
                )
            else:
                return ServiceResponse(
                    status=ServiceExecStatus.ERROR,
                    content=self.error_message or str(self.content),
                )
        except ImportError:
            return self.to_dict()
