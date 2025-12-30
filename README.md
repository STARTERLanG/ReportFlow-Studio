# AnotherMe - Dify 工作流智能架构师 (Deep Agents 版)

这是一个基于 **Deep Agents** (LangChain) 和 **RAG (Retrieval-Augmented Generation)** 技术的智能体系统。它能像一位经验丰富的 Dify 开发者一样，根据你的自然语言需求，参考本地的最佳实践案例，自动生成可直接导入的 Dify 工作流配置文件 (`.yml`)。

## 核心特性

*   **🧠 多智能体协作 (Deep Agents)**：
    *   **架构师 (Architect)**：设计工作流逻辑骨架。
    *   **提示词专家 (PromptExpert)**：撰写高质量的节点 Prompt。
    *   **DSL 工程师 (DSLCoder)**：生成合规的 Dify YAML 代码。
*   **📚 智能检索 (RAG)**：支持 **OpenAI** 和 **阿里云 DashScope** 向量模型，基于 **Qdrant** 向量数据库检索。
*   **🔌 灵活配置**：
    *   支持 **OpenAI (GPT-4o)** 或 **阿里云百炼 (Qwen/通义千问)** 大模型。
    *   支持本地内存模式或远程 Qdrant 集群（支持 API Key 或账号密码）。
*   **🇨🇳 全中文支持**：指令、日志和交互界面完全汉化。

## 快速开始

### 1. 环境准备

确保你已安装 [uv](https://github.com/astral-sh/uv) (推荐) 或 Python 3.12+。

```bash
# 克隆项目（假设你已在项目根目录）
# 安装依赖
uv sync
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并根据你的模型服务商进行配置：

```bash
cp .env.example .env
```

#### 配置示例：使用阿里云百炼 (推荐国内用户)

编辑 `.env` 文件：

```ini
# 模型服务：阿里云兼容接口
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
OPENAI_API_KEY=sk-your-dashscope-key  # 你的百炼 API Key
LLM_MODEL_NAME=qwen-plus             # 模型名称 (qwen-turbo, qwen-max 等)

# 向量模型：使用阿里云
EMBEDDING_PROVIDER=dashscope
EMBEDDING_MODEL_NAME=text-embedding-v2
# DASHSCOPE_API_KEY=... (默认复用 OPENAI_API_KEY)

# 向量数据库：Qdrant
QDRANT_URL=http://localhost:6333
# QDRANT_API_KEY=...
```

### 3. 准备知识库

在项目根目录下创建一个名为 `knowledge_base` 的文件夹，并将你现有的优秀 Dify 工作流文件 (`.yml`) 放入其中。

```bash
mkdir knowledge_base
# 将你的 .yml 文件复制进去
```

## 使用指南

### 1. 构建索引 (Index)

在使用生成功能前，必须先将本地的工作流文件索引到数据库中。

```bash
uv run python main.py index
```

*   默认扫描 `knowledge_base` 目录。
*   如果使用远程 Qdrant，可在 `.env` 配置或通过参数指定：`--url http://...`

### 2. 生成工作流 (Generate)

使用自然语言描述你的需求，AI 将自动检索参考案例并生成新的工作流。

```bash
uv run python main.py generate "帮我做一个尽职调查工作流，先查工商信息，再用大模型分析风险"
```

*   **输出**：生成的 `.yml` 文件将保存在当前目录，文件名包含时间戳。
*   **参数**：
    *   `--k 3`: 指定参考案例的数量（默认为 3）。
    *   `--output my_flow.yml`: 指定输出文件名。

## 系统架构

```mermaid
graph TD
    User[用户需求] --> MainAgent[Deep Agent (主控)]
    
    MainAgent --> |1. 规划任务| Todo[Todo List 工具]
    
    MainAgent --> |2. 委派: 设计骨架| Architect[子智能体: 架构师]
    Architect --> |返回: 节点关系图| MainAgent
    
    MainAgent --> |3. 委派: 撰写提示词| PromptExpert[子智能体: 提示词专家]
    PromptExpert --> |返回: 优化后的 Prompt| MainAgent
    
    MainAgent --> |4. 整合代码| Coder[子智能体: DSL 工程师]
    Coder --> |返回: 最终 YAML| MainAgent
    
    MainAgent --> Final[输出 .yml 文件]
```

## 常见问题

*   **生成的 YAML 导入报错？**
    *   Deep Agents 模式已大幅降低语法错误率，但偶发 ID 冲突仍可能存在。建议重新生成一次，或手动微调生成的 YAML。
*   **如何连接远程 Qdrant？**
    *   可以在 `.env` 中设置 `QDRANT_URL` 和 `QDRANT_API_KEY`。
    *   如果使用账号密码（Basic Auth），请将 URL 设置为 `http://user:password@host:port` 格式。