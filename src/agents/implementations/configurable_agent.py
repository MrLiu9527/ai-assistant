"""可配置 Agent

通用的可配置 Agent 实现，支持从数据库配置加载所有参数
"""

from typing import Any

from loguru import logger

from src.agents.base import AgentContext, AgentResponse, BaseAgent
from src.agents.factory import register_agent_type
from src.models.agent import AgentConfig, AgentType


@register_agent_type(AgentType.DIALOG)
class ConfigurableAgent(BaseAgent):
    """可配置 Agent

    通用的 Agent 实现，所有配置从数据库加载。
    支持：
    - 自定义系统提示词
    - 多种 LLM 模型
    - Skill 和 Tool 挂载
    - 行为参数配置
    """

    agent_type = "configurable"
    default_name = "可配置助手"
    default_description = "一个可以根据配置自定义的 AI 助手"
    default_version = "1.0.0"

    def __init__(
        self,
        config: AgentConfig | None = None,
        **kwargs: Any,
    ):
        super().__init__(config=config, **kwargs)
        self._llm_client = None

    async def initialize(self) -> None:
        """初始化 Agent"""
        await super().initialize()
        await self._init_llm_client()

    async def _init_llm_client(self) -> None:
        """初始化 LLM 客户端"""
        try:
            import agentscope

            from src.core.config import settings

            model_config_path = settings.agentscope_model_config_path
            try:
                agentscope.init(model_configs=model_config_path)
                logger.info("AgentScope initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to init AgentScope: {e}")

        except ImportError:
            logger.warning("AgentScope not installed, using mock LLM")

    async def _process_message(
        self,
        message: str,
        context: AgentContext,
        **kwargs: Any,
    ) -> AgentResponse:
        """处理消息"""
        # 构建对话历史
        messages = self.get_conversation_history(context)
        messages.append({"role": "user", "content": message})

        # 调用 LLM
        try:
            response_text, token_info = await self._call_llm(messages)
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            response_text = f"抱歉，我遇到了一些问题：{str(e)}"
            token_info = {}

        return AgentResponse(
            content=response_text,
            conversation_id=context.conversation_id,
            prompt_tokens=token_info.get("prompt_tokens"),
            completion_tokens=token_info.get("completion_tokens"),
            total_tokens=token_info.get("total_tokens"),
            metadata={
                "model_provider": self.model_provider,
                "model_name": self.model_name,
            },
        )

    async def _call_llm(
        self, messages: list[dict[str, str]]
    ) -> tuple[str, dict[str, int]]:
        """调用 LLM

        Args:
            messages: 对话消息列表

        Returns:
            (响应文本, Token 信息)
        """
        try:
            from agentscope.models import load_model_by_config_name

            model = load_model_by_config_name(self.model_config_name)

            # 应用行为配置
            if self.behavior_config:
                # 例如设置 temperature, max_tokens 等
                pass

            response = model(messages)

            text = response.text if hasattr(response, "text") else str(response)
            token_info = {}

            if hasattr(response, "usage"):
                token_info = {
                    "prompt_tokens": response.usage.get("prompt_tokens", 0),
                    "completion_tokens": response.usage.get("completion_tokens", 0),
                    "total_tokens": response.usage.get("total_tokens", 0),
                }

            return text, token_info

        except ImportError:
            logger.warning("Using mock LLM response")
            return self._mock_llm_response(messages), {}

        except Exception as e:
            logger.error(f"Error calling LLM: {e}")
            return self._mock_llm_response(messages), {}

    def _mock_llm_response(self, messages: list[dict[str, str]]) -> str:
        """Mock LLM 响应"""
        last_message = messages[-1]["content"] if messages else ""

        return f"""这是一个模拟的 LLM 响应。

**Agent 信息**：
- 名称：{self.name}
- 类型：{self.agent_type}
- 模型：{self.model_provider}/{self.model_name}

**您的消息**：{last_message}

要使用真实的 LLM，请配置相应的 API Key。
"""
