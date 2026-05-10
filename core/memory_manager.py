# agent/core/memory.py
from typing import List, Dict, Any, Optional


class MemoryManager:
    """
    存储完整的对话消息列表（标准 OpenAI 格式）。
    仅作为有序容器，不关心消息含义。
    """

    def __init__(self):
        self.messages: List[Dict[str, Any]] = []
        self._system_prompt: Optional[str] = None

    def set_system_prompt(self, system_prompt: str) -> None:
        """设置系统提示（单独存储，不在历史消息列表中）"""
        self._system_prompt = system_prompt

    def get_system_prompt(self) -> Optional[str]:
        """获取系统提示"""
        return self._system_prompt

    def add_message(self, role: str, content: Optional[str] = None,
                    tool_calls: Optional[List[Dict]] = None,
                    tool_call_id: Optional[str] = None) -> None:
        """
        添加一条消息到历史记录。
        支持标准 OpenAI 字段：role, content, tool_calls, tool_call_id。
        """
        msg: Dict[str, Any] = {"role": role}
        if content is not None:
            msg["content"] = content
        if tool_calls is not None:
            msg["tool_calls"] = tool_calls
        if tool_call_id is not None:
            msg["tool_call_id"] = tool_call_id
        self.messages.append(msg)

    def add_user_message(self, content: str) -> None:
        """添加用户消息"""
        self.add_message("user", content=content)

    def add_assistant_message(self, content: Optional[str] = None,
                              tool_calls: Optional[List[Dict]] = None) -> None:
        """添加助手消息（可能包含 tool_calls）"""
        self.add_message("assistant", content=content, tool_calls=tool_calls)

    def add_tool_message(self, tool_call_id: str, content: str) -> None:
        """添加工具响应消息"""
        self.add_message("tool", content=content, tool_call_id=tool_call_id)

    def get_conversation_messages(self) -> List[Dict[str, Any]]:
        """获取历史消息（不包含 system prompt）"""
        return self.messages.copy()

    def clear_conversation(self) -> None:
        """清空历史消息（保留 system prompt）"""
        self.messages.clear()
