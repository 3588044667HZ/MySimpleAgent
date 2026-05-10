# agent/core/loop.py
from core.model_provider import ModelProvider
from core.memory_manager import MemoryManager
from core.prompt import PromptAssembler
from core.tool_provider import ToolProvider


class RunLoop:
    """
    核心控制流：循环调用模型 -> 执行工具 或 输出结果 -> 结束。
    """

    def __init__(self,
                 memory: MemoryManager,
                 tool_provider: ToolProvider,
                 model_provider: ModelProvider,
                 max_iterations: int = 50):
        self.memory = memory
        self.tool_provider = tool_provider
        self.model_provider = model_provider
        self.prompt_assembler = PromptAssembler(memory, tool_provider)
        self.max_iterations = max_iterations

    def run(self) -> str:
        """
        执行完整的 Agent 循环，直到输出最终结果或达到限制。
        返回最终输出的内容（如果有）。
        """
        iteration = 0
        final_output = None

        while iteration < self.max_iterations:
            iteration += 1

            # 1. 组装请求（messages + tools）
            request = self.prompt_assembler.assemble()

            # 2. 调用模型
            response = self.model_provider.invoke(request)

            if response["intent"] == "function_call":
                tool_calls = response.get("tool_calls", [])
                if not tool_calls:
                    # 没有实际工具调用但意图却是 function_call，视为异常
                    print("Warning: intent=function_call but no tool_calls provided")
                    continue

                # 先将 assistant 消息（含 tool_calls）加入 memory
                self.memory.add_assistant_message(
                    content=response.get("content"),
                    tool_calls=tool_calls
                )

                # 依次执行每个工具调用
                for tc in tool_calls:
                    tool_name = tc["function"]["name"]
                    # arguments 可能是 JSON 字符串，需要解析
                    args_str = tc["function"]["arguments"]
                    try:
                        import json
                        arguments = json.loads(args_str) if args_str else {}
                    except json.JSONDecodeError:
                        arguments = {}

                    # 执行工具
                    result = self.tool_provider.execute(tool_name, arguments)

                    # 将工具结果作为 tool 消息加入 memory
                    self.memory.add_tool_message(
                        tool_call_id=tc["id"],
                        content=result
                    )

                # 工具执行完毕后继续循环（让模型看到结果后决定下一步）
                continue

            elif response["intent"] == "output":
                output = response.get("content", "")
                # 将模型的最终输出加入 memory（作为 assistant 最后一条消息）
                self.memory.add_assistant_message(content=output)
                final_output = output
                break

            elif response["intent"] == "end":
                error_msg = response.get("content", "Agent terminated due to end intent")
                # 异常情况，可以打印错误信息
                print(f"Agent ended: {error_msg}")
                final_output = error_msg
                break

        else:
            # 达到最大循环次数
            final_output = "Agent reached maximum iterations without final output."

        return final_output
