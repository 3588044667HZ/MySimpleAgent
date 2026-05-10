# agent/core/model_provider.py
import os
import json
from typing import Dict, Any, List, Optional
from openai import OpenAI


class ModelProvider:
    """
    封装模型 API 调用，统一接口。
    使用适配器模式，当前实现 OpenAI 兼容适配器。
    """

    def __init__(self, model_name: str = "gpt-4o-mini",
                 api_key: Optional[str] = None,
                 base_url: Optional[str] = None):
        self.model_name = model_name
        # 优先从参数获取，否则从环境变量读取
        api_key = api_key or os.environ.get("OPENAI_API_KEY")
        base_url = base_url or os.environ.get("OPENAI_BASE_URL")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required")
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def invoke(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        输入：包含 "messages" 和 "tools" 的字典
        输出：
            {
                "intent": "function_call" | "output" | "end",
                "content": Optional[str],
                "tool_calls": Optional[List[Dict]]
            }
        """
        messages = request.get("messages", [])
        tools = request.get("tools", [])

        try:
            # 调用 OpenAI 兼容的聊天补全接口
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                tools=tools if tools else None,
                tool_choice="auto" if tools else 'none',
                temperature=0.7,
                extra_body={"thinking": {"type": "disabled"}}  # 关键：禁用思考模式
            )
        except Exception as e:
            # 任何异常都视为终止意图
            return {
                "intent": "end",
                "content": f"Model invocation error: {e}",
                "tool_calls": None
            }

        choice = response.choices[0]
        message = choice.message
        finish_reason = choice.finish_reason

        # 意图解析规则
        if message.tool_calls and finish_reason == "tool_calls":
            # 转换为标准字典列表
            tool_calls = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                }
                for tc in message.tool_calls
            ]
            return {
                "intent": "function_call",
                "content": message.content,
                "tool_calls": tool_calls
            }
        elif message.content and finish_reason == "stop":
            return {
                "intent": "output",
                "content": message.content,
                "tool_calls": None
            }
        else:
            # 其他情况（空回复、长度超限等）视为终止
            return {
                "intent": "end",
                "content": message.content or "No valid response from model",
                "tool_calls": None
            }
