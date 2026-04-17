"""对话 Agent

专门用于多轮对话的 Agent 实现
"""

from typing import Any

from loguru import logger

from src.agents.base import AgentContext, AgentResponse, BaseAgent
from src.agents.factory import register_agent_type
from src.models.agent import AgentType


@register_agent_type(AgentType.DIALOG)
class DialogAgent(BaseAgent):
    """对话 Agent

    专门用于多轮对话，支持：
    - 上下文记忆
    - 对话历史管理
    - 流式输出（可选）
    """

    agent_type = "dialog"
    default_name = "对话助手"
    default_description = "一个专注于对话交流的 AI 助手"
    default_version = "1.0.0"

    async def _process_message(
        self,
        message: str,
        context: AgentContext,
        stream: bool = False,
        **kwargs: Any,
    ) -> AgentResponse:
        """处理消息"""
        # 构建对话历史
        messages = self.get_conversation_history(context)
        messages.append({"role": "user", "content": message})

        # 调用 LLM
        try:
            if stream:
                # 流式输出
                response_text = await self._call_llm_stream(messages)
            else:
                response_text = await self._call_llm(messages)
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            response_text = f"抱歉，我遇到了一些问题：{str(e)}"

        return AgentResponse(
            content=response_text,
            conversation_id=context.conversation_id,
            metadata={
                "model_provider": self.model_provider,
                "model_name": self.model_name,
                "stream": stream,
            },
        )

    async def _call_llm(self, messages: list[dict[str, str]]) -> str:
        """调用 LLM"""
        try:
            from agentscope.models import load_model_by_config_name

            model = load_model_by_config_name(self.model_config_name)
            response = model(messages)
            return response.text if hasattr(response, "text") else str(response)

        except ImportError:
            return self._mock_response(messages)
        except Exception as e:
            logger.error(f"LLM error: {e}")
            return self._mock_response(messages)

    async def _call_llm_stream(self, messages: list[dict[str, str]]) -> str:
        """流式调用 LLM"""
        # TODO: 实现流式输出
        return await self._call_llm(messages)

    def _mock_response(self, messages: list[dict[str, str]]) -> str:
        """Mock 响应"""
        last_message = messages[-1]["content"] if messages else ""
        return f"[Mock Dialog Response] 您说：{last_message}"
