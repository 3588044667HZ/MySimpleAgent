from core.tool_provider import registry


# 1. 注册本地工具


@registry.tool(name="ask_user", description="Ask the user for input")
def ask_user(prompt: str) -> str:
    return input(prompt)


@registry.tool(name="add", description="Add two integers")
def add(a: int, b: int) -> int:
    return a + b
