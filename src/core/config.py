"""应用配置管理"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # 应用配置
    app_name: str = Field(default="all-in-ai", description="应用名称")
    app_env: Literal["development", "staging", "production"] = Field(
        default="development", description="运行环境"
    )
    debug: bool = Field(default=False, description="调试模式")
    log_level: str = Field(default="INFO", description="日志级别")

    # 数据库配置
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/all_in_ai",
        description="数据库连接URL(异步)",
    )
    database_sync_url: str = Field(
        default="postgresql+psycopg2://postgres:postgres@localhost:5432/all_in_ai",
        description="数据库连接URL(同步，用于迁移)",
    )
    database_pool_size: int = Field(default=5, description="数据库连接池大小")
    database_max_overflow: int = Field(default=10, description="数据库连接池最大溢出")

    # AgentScope 配置
    agentscope_model_config_path: str = Field(
        default="configs/model_config.json", description="AgentScope 模型配置路径"
    )

    # LLM 配置
    openai_api_key: str | None = Field(default=None, description="OpenAI API Key")
    openai_api_base: str = Field(
        default="https://api.openai.com/v1", description="OpenAI API Base URL"
    )
    dashscope_api_key: str | None = Field(
        default=None, description="阿里云 DashScope API Key"
    )

    # Redis 配置
    redis_url: str = Field(
        default="redis://localhost:6379/0", description="Redis 连接URL"
    )

    @property
    def is_development(self) -> bool:
        """是否为开发环境"""
        return self.app_env == "development"

    @property
    def is_production(self) -> bool:
        """是否为生产环境"""
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()


settings = get_settings()
