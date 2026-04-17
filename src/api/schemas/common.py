"""通用 Schema"""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ResponseModel(BaseModel, Generic[T]):
    """通用响应模型"""

    code: int = Field(default=0, description="状态码，0 表示成功")
    message: str = Field(default="success", description="响应消息")
    data: T | None = Field(default=None, description="响应数据")


class PaginatedResponse(BaseModel, Generic[T]):
    """分页响应模型"""

    code: int = Field(default=0, description="状态码")
    message: str = Field(default="success", description="响应消息")
    data: list[T] = Field(default_factory=list, description="数据列表")
    total: int = Field(default=0, description="总数量")
    page: int = Field(default=1, description="当前页码")
    page_size: int = Field(default=20, description="每页数量")
    has_more: bool = Field(default=False, description="是否有更多")


class ErrorResponse(BaseModel):
    """错误响应模型"""

    code: int = Field(description="错误码")
    message: str = Field(description="错误消息")
    detail: Any | None = Field(default=None, description="详细信息")


class PaginationParams(BaseModel):
    """分页参数"""

    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页数量")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size
