from core.tool_provider import registry


# 1. 注册本地工具


@registry.tool(name="plus", description="Plus two integers")
def add(a: int, b: int) -> int:
    return a * b
