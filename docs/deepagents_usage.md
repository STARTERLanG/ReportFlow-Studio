# DeepAgents 官方用法参考 (基于 Context7 文档)

本文档整理自 `/langchain-ai/deepagents` 的官方文档，涵盖了核心 API 的真实用法。

## 1. 基础用法：创建 Deep Agent
`deepagents` 的核心入口是 `create_deep_agent` 函数。它会自动为 Agent 配备文件系统工具（如 `read_file`, `write_file` 等）和计划管理能力。

```python
from langchain.chat_models import init_chat_model
from deepagents import create_deep_agent

# 1. 初始化模型 (支持任何 LangChain 兼容模型)
model = init_chat_model("openai:gpt-4o", temperature=0)

# 2. 创建 Agent
agent = create_deep_agent(
    model=model,
    system_prompt="你是一个专业的 Python 编码助手。",
    # 自动包含文件系统工具和 TodoList 管理工具
)

# 3. 运行 Agent
response = agent.invoke({
    "messages": [{"role": "user", "content": "创建一个斐波那契数列函数并保存到 fib.py"}]
})

print(response["messages"][-1].content)
```

## 2. 高级用法：子智能体 (Sub-Agents)
这是 `deepagents` 的核心特性，允许主 Agent 将任务委派给专用的子 Agent。

```python
from deepagents import create_deep_agent
from langchain_core.tools import tool

# 定义工具
@tool
def get_weather(city: str) -> str:
    """获取城市天气"""
    return f"{city} 的天气是晴朗，25度。"

# 定义子智能体配置
subagents = [
    {
        "name": "weather_expert",
        "description": "负责处理所有与天气查询相关的任务",
        "system_prompt": "你是一个气象专家，只负责查询天气。",
        "tools": [get_weather],
        # 可选：为子智能体指定不同模型
        # "model": "openai:gpt-3.5-turbo" 
    },
    {
        "name": "writer",
        "description": "负责撰写报告和总结",
        "system_prompt": "你是一个资深的报告撰写员。",
        # writer 继承主 Agent 的模型，没有额外工具
    }
]

# 创建主智能体
main_agent = create_deep_agent(
    model="openai:gpt-4o",
    subagents=subagents,
    system_prompt="你是一个协调员，请根据用户需求委派给合适的专家。"
)

# 运行
main_agent.invoke({
    "messages": [{"role": "user", "content": "查一下北京的天气，然后写一份简短的出行建议报告。"}]
})
```

## 3. 持久化文件系统 (Filesystem Backend)
默认情况下，Agent 的文件操作是临时的（内存中）。使用 `FilesystemBackend` 可以让 Agent 读写真实的本地文件。

```python
from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend

agent = create_deep_agent(
    model="openai:gpt-4o",
    # 指定本地根目录，Agent 的所有文件操作都将限制在此目录下
    backend=FilesystemBackend(root_dir="./agent_workspace"),
    system_prompt="你有权读写 ./agent_workspace 下的文件。"
)
```

## 4. 流式输出 (Streaming)
支持实时流式返回 Agent 的思考过程和结果。

```python
import asyncio

async def main():
    agent = create_deep_agent(model="openai:gpt-4o")

    async for chunk in agent.astream(
        {"messages": [{"role": "user", "content": "解释量子计算"}]},
        stream_mode="values" # 或 "messages"
    ):
        if "messages" in chunk:
            chunk["messages"][-1].pretty_print()

# asyncio.run(main())
```

## 5. 集成 MCP 工具 (Model Context Protocol)
通过 `langchain-mcp-adapters` 集成 MCP 工具。

```python
from langchain_mcp_adapters.client import MultiServerMCPClient
from deepagents import create_deep_agent

# 假设你已配置 MCP Client
mcp_client = MultiServerMCPClient(...)
mcp_tools = await mcp_client.get_tools()

agent = create_deep_agent(
    tools=mcp_tools,
    system_prompt="你可以使用通过 MCP 提供的外部工具。"
)
```

## 6. 核心数据结构参考

### SubAgent 配置 (TypedDict)
```python
class SubAgent(TypedDict):
    name: str
    description: str
    prompt: str
    tools: Sequence[BaseTool | Callable | dict[str, Any]]
    model: NotRequired[str | BaseChatModel]
    middleware: NotRequired[list[AgentMiddleware]]
    interrupt_on: NotRequired[dict[str, bool | InterruptOnConfig]]
```
