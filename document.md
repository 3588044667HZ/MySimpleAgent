好的，以下是本次架构讨论的完整提炼文档，你可以直接在 DeepSeek 编码时用作参考。

---

# AI Agent 架构设计文档 (MVP CLI 版本)

## 核心理念
- **模型驱动控制**：Agent 行为完全由模型输出的意图决定，代码层面仅提供执行循环。
- **声明式工具注册**：使用类似 Flask 的 `@app.tool` 装饰器，从函数签名自动推导工具定义。
- **标准化协议**：内部通信基于原生 Function Call 格式；外部扩展遵循 MCP 协议。
- **极简可扩展**：用简单抽象隔离差异，核心组件均可独立替换。

---

## 1. 全局架构

```
┌──────────────────────────────────────────────────────┐
│                      Run Loop                        │
│  - while True 循环                                   │
│  - 根据 intent 决策：function_call → 执行工具        │
│                       output       → 输出并结束       │
│                       end          → 终止             │
└──────────┬───────────────────────────────┬───────────┘
           │                               │
      ┌────▼──────┐                  ┌─────▼─────┐
      │  Prompt   │                  │  Tool     │
      │ Assembler │                  │ Provider  │
      └────┬──────┘                  └─────┬─────┘
           │                               │
      ┌────▼──────┐                  ┌─────▼─────┐
      │  Memory   │                  │  Model    │
      │  Manager  │                  │  Provider │
      └───────────┘                  └───────────┘
```

---

## 2. 核心组件职责

### 2.1 Memory Manager
- 职责：**存完整的对话消息列表**（标准 OpenAI 格式：`system`, `user`, `assistant`, `tool` 角色）。
- 仅为有序容器，不关心消息含义。
- 对外暴露 `append(role, content, ...)` 和 `get_messages()`。

### 2.2 Tool Provider
- 统一管理所有工具（本地 + 远程 MCP）。
- 接口：
  - `list_tools()` → 返回标准化工具定义列表（name, description, parameters schema）
  - `execute(name, params)` → 执行工具并返回结果字符串
- 内部包含：
  - 本地注册表（通过 `@tool` 装饰器注册的函数）
  - MCP 客户端适配器（与远程 Flask MCP 服务器通信）
- **特殊工具约定**：`ask_user` 是一个普通的本地工具，内部调用 `input()` 阻塞等待用户输入。Run Loop 只将其视为一次 `function_call`，从而实现交互暂停。

### 2.3 Prompt Assembler
- 组装每次模型调用的完整请求体。
- 结构：
  1. `system` 消息（角色描述、行为准则）**首位固定**
  2. 历史消息（从 Memory Manager 获取）
  3. `tools` 数组（从 Tool Provider 获取的工具定义 JSON Schema）
- **不将工具描述混入 `system` 消息**，而是利用 API 原生的 `tools` 参数。

### 2.4 Model Provider
- 封装所有外部模型 API 调用，对外统一接口。
- 输入：`StandardRequest`（messages + tools + config）
- 输出：`StandardResponse`（intent + content + tool_calls）
- 内部用**适配器模式**：每个模型/API 对应一个适配器，负责翻译请求/响应。
- **意图解析规则**（适配器执行）：
  - 响应中有 `tool_calls` → `intent = "function_call"`
  - 响应中有 `content` 且无工具调用，`finish_reason = "stop"` → `intent = "output"`
  - 其他异常（空回复、长度超限、错误） → `intent = "end"`

### 2.5 Run Loop
- 核心控制流（伪代码）：
  ```
  while True:
      request = prompt_assembler.assemble(memory, tool_provider)
      response = model_provider.invoke(request)
      if response.intent == "function_call":
          for each tool_call in response.tool_calls:
              result = tool_provider.execute(tool_call.name, tool_call.args)
              memory.append(role="tool", content=result, tool_call_id=tool_call.id)
          // 继续循环
      elif response.intent == "output":
          print(response.content)
          break
      elif response.intent == "end":
          break (可能输出错误信息)
      ```

---

## 3. 声明式工具注册（`@app.tool`）

### 3.1 本地工具（Agent 进程内）
- 使用 **Registry 模式** 避免循环依赖。
- `ToolRegistry` 是一个独立模块，提供 `@registry.tool(name, desc)` 装饰器。
- 装饰器内部：
  - 记录函数名、描述、参数类型注解与默认值。
  - 自动将类型注解映射为 JSON Schema（`str → string`, `int → integer` 等）。
  - 将函数与元数据放入待注册列表。
- 在 Agent 入口文件中：
  ```
  registry = ToolRegistry()
  import local_tools  # 触发装饰器收集
  provider = ToolProvider()
  provider.load_from_registry(registry)
  ```

### 3.2 远程工具（Flask MCP 服务器）
- 定义 `McpServer(Flask)` 类，提供相同风格的 `@app.tool` 装饰器。
- 自动生成两个 MCP 标准端点：
  - `POST /tools/list` → 返回所有注册工具的 JSON Schema 数组。
  - `POST /tools/call` → 接收 `{name, arguments}`，执行对应函数并返回结果。
- Tool Provider 通过 `HttpMcpClient` 适配器在启动时调用 `/tools/list`，执行时调用 `/tools/call`。

---

## 4. 关键设计决策与避坑指南

### 4.1 多轮工具调用记忆
- **全量上下文策略**：将每一轮的 `assistant`（含 tool_calls）和 `tool` 消息原样保留在消息列表中。
- 不需要自定义 XML 标签，模型原生理解。
- MVP 阶段需配套：
  - Token 预算管理（逼近窗口上限时压缩早期轮次）。
  - 工具结果截断（超长内容只保留关键部分）。
  - 最大循环次数限制（如 50 次）。

### 4.2 消除循环依赖
- **工具模块绝不引用入口文件**。
- 通过 ToolRegistry 或懒加载实现解耦。

### 4.3 统一意图标签
- 不使用 `input_required` 专门意图，而是通过 `ask_user` 工具复用 `function_call` 流程，精简 Run Loop 分支。

### 4.4 MCP 协议标准
- Flask MCP 服务器必须严格暴露 `list` 和 `call` 端点。
- 不可自定义 REST 风格，否则工具定义无法被 Agent 自动发现。

---

## 5. 文件组织建议

```
agent/
├── core/
│   ├── memory.py          # MemoryManager
│   ├── tool_provider.py   # ToolProvider + ToolRegistry
│   ├── prompt.py          # PromptAssembler
│   ├── model_provider.py  # ModelProvider + adapters
│   └── loop.py            # RunLoop
├── tools/                 # 本地工具定义
│   └── file_tools.py      # 使用 @registry.tool
├── mcp_server/            # 远程 MCP 工具（可选）
│   └── flask_server.py    # 继承 McpServer，用 @app.tool
├── main.py                # 入口，组装所有组件
└── config.py              # 模型、MCP 端点等配置
```

此文档涵盖了从顶层架构到具体设计细节的全部共识，可以直接指导编码实现。