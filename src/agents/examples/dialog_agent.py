"""对话 Agent 示例

基于 LLM 的对话 Agent，支持多轮对话
"""

from typing import Any

from loguru import logger

from src.agents.base import BaseAgent, AgentContext, AgentResponse
from src.agents.registry import agent_registry


@agent_registry.register()
class DialogAgent(BaseAgent):
    """对话 Agent

    基于 LLM 的通用对话 Agent，支持：
    - 多轮对话
    - 会话历史
    - 可配置的系统提示词
    """

    agent_id = "dialog_agent"
    agent_type = "dialog"
    name = "对话助手"
    description = "一个通用的对话助手，可以与用户进行自然语言对话"
    version = "1.0.0"

    def __init__(
        self,
        system_prompt: str | None = None,
        model_config_name: str = "default",
        skills: list[str] | None = None,
        tools: list[str] | None = None,
        config: dict[str, Any] | None = None,
    ):
        super().__init__(
            system_prompt=system_prompt,
            model_config_name=model_config_name,
            skills=skills,
            tools=tools,
            config=config,
        )

        # LLM 客户端（延迟初始化）
        self._llm_client = None

    async def initialize(self) -> None:
        """初始化 Agent"""
        await super().initialize()

        # 初始化 LLM 客户端
        await self._init_llm_client()

    async def _init_llm_client(self) -> None:
        """初始化 LLM 客户端"""
        try:
            # 尝试使用 AgentScope
            import agentscope
            from agentscope.models import ModelResponse

            # 加载模型配置
            model_config_path = self.config.get(
                "model_config_path",
                "configs/model_config.json",
            )

            try:
                agentscope.init(model_configs=model_config_path)
                logger.info("AgentScope initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to init AgentScope with config: {e}")

        except ImportError:
            logger.warning("AgentScope not installed, using mock LLM client")

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
            response_text = await self._call_llm(messages)
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            response_text = f"抱歉，我遇到了一些问题：{str(e)}"

        return AgentResponse(
            content=response_text,
            conversation_id=context.conversation_id,
            metadata={
                "model": self.model_config_name,
            },
        )

    async def _call_llm(self, messages: list[dict[str, str]]) -> str:
        """调用 LLM

        Args:
            messages: 对话消息列表

        Returns:
            LLM 响应文本
        """
        try:
            # 尝试使用 AgentScope
            import agentscope
            from agentscope.models import load_model_by_config_name

            model = load_model_by_config_name(self.model_config_name)
            response = model(messages)

            if hasattr(response, "text"):
                return response.text
            return str(response)

        except ImportError:
            # AgentScope 未安装，使用 mock 响应
            logger.warning("Using mock LLM response")
            return self._mock_llm_response(messages)

        except Exception as e:
            logger.error(f"Error calling LLM: {e}")
            return self._mock_llm_response(messages)

    def _mock_llm_response(self, messages: list[dict[str, str]]) -> str:
        """Mock LLM 响应（用于测试）"""
        last_message = messages[-1]["content"] if messages else ""

        return f"""这是一个模拟的 LLM 响应。

您的消息是：{last_message}

要使用真实的 LLM，请：
1. 安装 agentscope: pip install agentscope
2. 配置 configs/model_config.json
3. 设置相应的 API Key 环境变量
"""
