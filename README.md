# ReportFlow Studio - Dify 工作流智能架构师 (LangGraph 版)

这是一个基于 **LangGraph** 和 **RAG (Retrieval-Augmented Generation)** 技术的智能体系统。它采用 **Blueprint + Builder** 双层架构，能够根据自然语言需求，生成高质量、无语法错误的 Dify 工作流配置文件 (`.yml`)。

## 核心特性

*   **🤖 全自动编排 (LangGraph)**：
    *   内置 Planner、Architect、PromptExpert、Repairer 等多个专业智能体。
    *   具备 **自愈能力 (Self-Healing)**：生成后自动校验，发现错误自动回滚修复。
*   **🏗️ 确定性构建 (Builder Mode)**：
    *   AI 仅负责设计逻辑蓝图 (Blueprint JSON)。
    *   Python Builder 负责生成最终 YAML，彻底解决 LLM 生成 YAML 格式错乱的问题。
*   **📚 智能检索 (RAG)**：基于 Qdrant 向量数据库，检索参考案例指导生成。
*   **🔌 灵活配置**：支持 OpenAI (GPT-4o) 或 阿里云百炼 (Qwen/通义千问)。

## 快速开始

### 1. 环境准备

确保你已安装 [uv](https://github.com/astral-sh/uv) (推荐) 或 Python 3.12+。

```bash
# 安装依赖
uv sync
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并配置：

```bash
cp .env.example .env
```

配置示例 (阿里云百炼):
```ini
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
OPENAI_API_KEY=sk-your-key
LLM_MODEL_NAME=qwen-plus
QDRANT_URL=http://localhost:6333
```

### 3. 运行生成 (CLI)

使用自然语言描述你的需求，系统会自动规划、设计、组装并校验工作流。

```bash
# 简单生成
uv run python app/server/cli.py generate "帮我做一个新闻摘要助手，先抓取网页，再用大模型总结"

# 指定输出文件
uv run python app/server/cli.py generate "尽职调查工作流" -o output.yml
```

### 4. 启动 API 服务

```bash
uv run python app/server/main.py
```
访问 `http://localhost:8000/docs` 查看 API 文档。

## 系统架构

```mermaid
graph TD
    User[用户需求] --> Planner[Planner]
    Planner --> Architect[Architect (设计蓝图)]
    Architect --> PromptExpert[PromptExpert (优化 Prompt)]
    PromptExpert --> Assembler[Assembler (Builder构建)]
    Assembler --> Validator{校验}
    Validator -- 通过 --> End[输出 YAML]
    Validator -- 失败 --> Repairer[Repairer (修复)]
    Repairer --> Validator
```

## 目录结构

*   `agents/workflows/dify_yaml_generator/`: LangGraph 核心逻辑 (Nodes, State, Graph)。
*   `app/server/services/dify_builder.py`: 确定性 YAML 构建器。
*   `app/server/schemas/dsl.py`: Dify 节点数据模型定义。
