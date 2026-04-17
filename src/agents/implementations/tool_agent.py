"""工具调用 Agent

支持调用 Skills 和 Tools 的 Agent 实现
"""

from typing import Any

from loguru import logger

from src.agents.base import AgentContext, AgentResponse, BaseAgent
from src.agents.factory import register_agent_type
from src.models.agent import AgentConfig, AgentType
from src.skills import skill_registry


@register_agent_type(AgentType.TOOL)
@register_agent_type(AgentType.REACT)
class ToolAgent(BaseAgent):
    """工具调用 Agent

    支持 ReAct 模式的 Agent，可以：
    - 调用挂载的 Skills
    - 调用挂载的 Tools
    - 思考-行动-观察循环
    """

    agent_type = "tool"
    default_name = "工具助手"
    default_description = "一个可以使用各种工具的 AI 助手"
    default_version = "1.0.0"

    def __init__(self, config: AgentConfig | None = None, **kwargs: Any):
        super().__init__(config=config, **kwargs)
        self.max_iterations = self.config.get("max_iterations", 5)

    async def _process_message(
        self,
        message: str,
        context: AgentContext,
        **kwargs: Any,
    ) -> AgentResponse:
        """处理消息 - 使用 ReAct 模式"""
        # 构建对话历史
        messages = self.get_conversation_history(context)
        messages.append({"role": "user", "content": message})

        # 获取可用工具
        tool_schemas = self._get_tool_schemas()

        # ReAct 循环
        tool_calls = []
        final_response = ""

        for iteration in range(self.max_iterations):
            try:
                # 调用 LLM，让其决定是否需要使用工具
                response = await self._call_llm_with_tools(messages, tool_schemas)

                # 检查是否需要调用工具
                if response.get("tool_calls"):
                    # 执行工具调用
                    for tool_call in response["tool_calls"]:
                        tool_result = await self._execute_tool(tool_call)
                        tool_calls.append({
                            "tool": tool_call["name"],
                            "args": tool_call["arguments"],
                            "result": tool_result,
                        })

                        # 将工具结果添加到消息历史
                        messages.append({
                            "role": "tool",
                            "content": str(tool_result),
                            "tool_call_id": tool_call.get("id", ""),
                        })
                else:
                    # 没有工具调用，返回最终响应
                    final_response = response.get("content", "")
                    break

            except Exception as e:
                logger.error(f"ReAct iteration {iteration} failed: {e}")
                final_response = f"处理过程中出现错误：{str(e)}"
                break

        if not final_response:
            final_response = "已完成所有工具调用，但未生成最终响应。"

        return AgentResponse(
            content=final_response,
            conversation_id=context.conversation_id,
            tool_calls=tool_calls,
            metadata={
                "model_provider": self.model_provider,
                "model_name": self.model_name,
                "iterations": iteration + 1,
            },
        )

    def _get_tool_schemas(self) -> list[dict[str, Any]]:
        """获取工具 Schema"""
        schemas = []

        # 获取 Skill schemas
        if self.skills:
            schemas.extend(skill_registry.get_tool_schemas(self.skills))

        # TODO: 获取 Tool schemas

        return schemas

    async def _call_llm_with_tools(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """调用 LLM（带工具）"""
        try:
            from agentscope.models import load_model_by_config_name

            model = load_model_by_config_name(self.model_config_name)

            # 添加工具信息到系统提示
            if tools:
                tool_prompt = self._format_tool_prompt(tools)
                if messages and messages[0]["role"] == "system":
                    messages[0]["content"] += f"\n\n{tool_prompt}"
                else:
                    messages.insert(0, {"role": "system", "content": tool_prompt})

            response = model(messages)
            text = response.text if hasattr(response, "text") else str(response)

            # 解析工具调用（简单实现，实际需要更复杂的解析）
            return {"content": text, "tool_calls": []}

        except ImportError:
            return {"content": self._mock_response(messages), "tool_calls": []}
        except Exception as e:
            logger.error(f"LLM with tools error: {e}")
            return {"content": f"Error: {e}", "tool_calls": []}

    def _format_tool_prompt(self, tools: list[dict[str, Any]]) -> str:
        """格式化工具提示"""
        if not tools:
            return ""

        lines = ["你可以使用以下工具：\n"]
        for tool in tools:
            func = tool.get("function", {})
            name = func.get("name", "")
            desc = func.get("description", "")
            lines.append(f"- {name}: {desc}")

        lines.append("\n当需要使用工具时，请明确说明你要调用哪个工具。")
        return "\n".join(lines)

    async def _execute_tool(self, tool_call: dict[str, Any]) -> Any:
        """执行工具调用"""
        tool_name = tool_call.get("name", "")
        arguments = tool_call.get("arguments", {})

        # 尝试从 Skills 执行
        if tool_name in self._skill_instances:
            skill_info = self._skill_instances[tool_name]
            if skill_info.is_async:
                result = await skill_info.func(**arguments)
            else:
                result = skill_info.func(**arguments)
            return result.content if hasattr(result, "content") else result

        # 尝试从 skill_registry 执行
        result = await skill_registry.execute_async(tool_name, **arguments)
        return result.content if hasattr(result, "content") else result

    def _mock_response(self, messages: list[dict[str, str]]) -> str:
        """Mock 响应"""
        last_message = messages[-1]["content"] if messages else ""
        return f"[Mock Tool Response] 您说：{last_message}"
