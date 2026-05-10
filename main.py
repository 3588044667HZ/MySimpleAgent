# agent/main.py
import sys
import os
from core.memory_manager import MemoryManager
from core.tool_provider import ToolProvider, registry
from core.model_provider import ModelProvider
# import core.tool_provider.registry
from core.loop import RunLoop
import local_tools
import local_tools2

# 配置（可通过环境变量或直接修改）
MCP_BASE_URL = os.environ.get("MCP_BASE_URL", "http://127.0.0.1:5000")
MODEL_NAME = os.environ.get("MODEL_NAME", "deepseek-v4-flash")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.deepseek.com/")  # 可选，用于代理或兼容服务


def load_system_prompt(file_path: str = "system.md") -> str:
    """从文件读取系统提示"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        print(f"Warning: {file_path} not found, using default system prompt.")
        return "You are a helpful assistant with access to tools. Use the ask_user tool when you need additional information from the user."


def main():
    # 1. 初始化组件
    memory = MemoryManager()
    # 初始化 ToolProvider（MCP 客户端）
    tool_provider = ToolProvider(local_registry=registry)

    # 加载系统提示
    system_prompt = load_system_prompt()
    memory.set_system_prompt(system_prompt)
    memory.add_message("system", content=f"目前的工具是：{tool_provider.list_tools()}")
    print(tool_provider.list_tools())

    # 初始化 ModelProvider
    model_provider = ModelProvider(
        model_name=MODEL_NAME,
        api_key=OPENAI_API_KEY,
        base_url=OPENAI_BASE_URL
    )

    # 2. 交互循环（支持多轮会话）
    print("AI Agent started. Type '/exit' to quit.\n")
    while True:
        # 获取用户输入
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye.")
            break

        if user_input.lower() in ("/exit", "/quit"):
            print("Goodbye.")
            break

        if not user_input:
            continue

        # 将用户消息加入 memory
        memory.add_user_message(user_input)

        # 运行 Agent 直到输出最终结果
        run_loop = RunLoop(memory, tool_provider, model_provider, max_iterations=50)
        final_output = run_loop.run()

        # 打印最终输出
        print(f"Agent: {final_output}\n")


if __name__ == "__main__":
    main()
