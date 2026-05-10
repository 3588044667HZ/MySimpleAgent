# agent/core/prompt.py
from typing import List, Dict, Any
from core.memory_manager import MemoryManager
from core.tool_provider import ToolProvider


class PromptAssembler:
    """
    组装每次模型调用的完整请求体。
    """

    def __init__(self, memory: MemoryManager, tool_provider: ToolProvider):
        self.memory = memory
        self.tool_provider = tool_provider

    def assemble(self) -> Dict[str, Any]:
        """
        返回一个包含 messages 和 tools 的字典，用于模型调用。
        """
        messages: List[Dict[str, Any]] = []

        # 1. system 消息（首位固定）
        system_prompt = self.memory.get_system_prompt()
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        # 2. 历史消息（标准 OpenAI 格式）
        messages.extend(self.memory.get_conversation_messages())

        # 3. 工具定义
        tools = self.tool_provider.list_tools()

        return {
            "messages": messages,
            "tools": tools
        }
