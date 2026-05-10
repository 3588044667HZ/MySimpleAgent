import inspect
import json
from typing import Any, Callable, Dict, List, Optional, get_type_hints
import requests


# ----------------------------------------------
# 1. ToolRegistry – 声明式本地工具注册
# ----------------------------------------------
class ToolRegistry:
    """
    独立注册中心，提供 @registry.tool(name, desc) 装饰器。
    自动从函数签名推导 JSON Schema。
    """

    def __init__(self):
        self._tools: Dict[str, dict] = {}  # name -> {"func": ..., "definition": ...}

    def tool(self, name: Optional[str] = None, description: str = ""):
        """装饰器：注册一个本地工具函数。"""

        def decorator(func: Callable):
            nonlocal name
            if name is None:
                name = func.__name__

            # 推导参数 schema
            sig = inspect.signature(func)
            type_hints = get_type_hints(func) if hasattr(func, '__annotations__') else {}
            properties = {}
            required = []

            for param_name, param in sig.parameters.items():
                # 跳过 self/cls
                if param_name in ('self', 'cls'):
                    continue
                param_type = type_hints.get(param_name, str)
                json_type = self._python_type_to_json(param_type)
                properties[param_name] = {
                    "type": json_type,
                    "description": f"{param_name} argument"  # 可后续扩展更好描述
                }
                # 没有默认值就是必填
                if param.default is inspect.Parameter.empty:
                    required.append(param_name)
                else:
                    properties[param_name]["default"] = param.default

            parameters_schema = {
                "type": "object",
                "properties": properties,
                "required": required
            }

            tool_def = {
                "type": "function",
                "function": {
                    "name": name,
                    "description": description or func.__doc__ or "",
                    "parameters": parameters_schema
                }
            }

            self._tools[name] = {
                "func": func,
                "definition": tool_def
            }
            return func

        return decorator

    @staticmethod
    def _python_type_to_json(py_type) -> str:
        """简单的类型映射。"""
        if py_type is str:
            return "string"
        elif py_type is int:
            return "integer"
        elif py_type is float:
            return "number"
        elif py_type is bool:
            return "boolean"
        elif py_type is list:
            return "array"
        elif py_type is dict:
            return "object"
        else:
            return "string"  # fallback

    def get_tool_definitions(self) -> List[dict]:
        """返回所有已注册工具的 OpenAI 标准定义列表。"""
        return [t["definition"] for t in self._tools.values()]

    def has(self, name: str) -> bool:
        return name in self._tools

    def execute(self, name: str, arguments: dict) -> str:
        """执行本地工具，返回字符串结果。"""
        if not self.has(name):
            raise KeyError(f"Tool '{name}' not found in registry")
        func = self._tools[name]["func"]
        try:
            result = func(**arguments)
            # 确保返回字符串
            if not isinstance(result, str):
                result = json.dumps(result, ensure_ascii=False)
            return result
        except Exception as e:
            return f"Error executing tool '{name}': {str(e)}"


# ----------------------------------------------
# 2. HttpMcpClient – 远程 MCP 工具适配器
# ----------------------------------------------
class HttpMcpClient:
    """通过 HTTP 与远程 Flask MCP 服务器通信的客户端。"""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')

    def list_tools(self) -> List[dict]:
        """调用 POST /tools/list 获取远程工具定义列表。"""
        try:
            resp = requests.post(f"{self.base_url}/tools/list", json={}, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            # 期望返回格式：{"tools": [...]}
            return data.get("tools", [])
        except Exception as e:
            # 生产环境应记录日志
            print(f"MCP list_tools error: {e}")
            return []

    def call_tool(self, name: str, arguments: dict) -> str:
        """调用 POST /tools/call 执行远程工具，返回结果字符串。"""
        try:
            resp = requests.post(
                f"{self.base_url}/tools/call",
                json={"name": name, "arguments": arguments},
                timeout=30
            )
            resp.raise_for_status()
            data = resp.json()
            # 期望返回格式：{"result": "..."}
            return data.get("result", "")
        except Exception as e:
            return f"MCP call error for '{name}': {str(e)}"


registry = ToolRegistry()


# ----------------------------------------------
# 3. ToolProvider – 统一工具管理器
# ----------------------------------------------
class ToolProvider:
    """
    统一管理本地工具（ToolRegistry）与远程 MCP 工具（HttpMcpClient）。
    外部只需使用 list_tools() 和 execute()。
    """

    def __init__(self, local_registry: Optional[ToolRegistry] = None,
                 mcp_clients: Optional[List[HttpMcpClient]] = None):
        self.local_registry = local_registry or ToolRegistry()
        self.mcp_clients = mcp_clients or []

    def add_mcp_client(self, client: HttpMcpClient):
        self.mcp_clients.append(client)

    def list_tools(self) -> List[dict]:
        """返回所有工具（本地 + 所有 MCP 客户端）的标准定义列表。"""
        tools = []
        # 本地工具
        tools.extend(self.local_registry.get_tool_definitions())
        # 远程工具
        for client in self.mcp_clients:
            tools.extend(client.list_tools())
        return tools

    def execute(self, name: str, arguments: dict) -> str:
        """执行工具：先查本地，再查远程 MCP 客户端。"""
        # 1. 本地
        if self.local_registry.has(name):
            return self.local_registry.execute(name, arguments)

        # 2. 远程 MCP（按顺序尝试，通常第一个匹配即可）
        for client in self.mcp_clients:
            remote_tools = client.list_tools()
            for rt in remote_tools:
                rt_name = rt.get("function", {}).get("name")
                if rt_name == name:
                    return client.call_tool(name, arguments)

        raise KeyError(f"Tool '{name}' not found in any provider")
