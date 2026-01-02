# 产品需求文档 (PRD): ReportFlow Studio (智能体编排工作台)

| **项目名称** | ReportFlow Studio                               | **版本**     | **V3.1 (LangGraph Edition)** |
| ------------ | ----------------------------------------------- | ------------ | ---------------------------- |
| **核心逻辑** | AI 规划 (LangGraph) + 确定性构建 (Builder)      | **交付形态** | CLI / Web API                |
| **关键特性** | 自然语言生成、自动校验修复、双层架构设计        | **目标用户** | Dify 开发者 / 方案工程师     |

## 1. 核心流程图 (Architecture)

系统采用 **LangGraph** 驱动的状态机架构，实现从“模糊需求”到“精准代码”的闭环。

```mermaid
graph TD
    User[用户需求] --> Planner[Planner: 制定生成计划]
    Planner --> Architect[Architect: 设计逻辑蓝图 (Blueprint)]
    Architect --> PromptExpert[PromptExpert: 优化提示词]
    PromptExpert --> Assembler[Assembler: 确定性构建 (Builder)]
    Assembler --> Validator{Validator: DSL 校验}
    
    Validator -- Pass --> Final[输出 Dify YAML]
    Validator -- Fail --> Repairer[Repairer: 智能修复]
    Repairer --> Validator
```

## 2. 功能需求详情 (Functional Requirements)

### 2.1 智能蓝图决策引擎 (LangGraph Engine)

- **描述**：基于 `langgraph` 的有向循环图（DAG），负责控制生成的全流程。
- **状态节点**：
  - **Planner**：分析用户需求，拆解为 `Design` -> `Prompt` -> `Assemble` 的执行步骤。
  - **Architect**：生成中间态的 JSON 蓝图 (Blueprint)，不直接生成 YAML，专注于逻辑正确性。
  - **PromptExpert**：遍历蓝图中的 LLM 节点，根据上下文自动优化 System Prompt。
  - **Repairer**：当校验失败时，读取错误日志并尝试修复 YAML 结构。

### 2.2 确定性构建器 (Deterministic Builder)

- **描述**：为了解决 LLM 直接生成 YAML 格式不稳定的问题，采用 **Blueprint + Builder** 模式。
- **功能点**：
  - **DifyBuilder**：一个 Python 类，接收 JSON 蓝图，通过硬编码逻辑生成标准的 Dify YAML。
  - **版本兼容**：自动处理 Dify 0.5.x/0.6.x 的 DSL 差异（如 If-Else 节点的二元限制、Code 节点的 Output 字典格式）。
  - **变量自动映射**：支持 `@{node.var}` 语法，自动转换为 Dify 的 `{{#node.var#}}` 格式。

### 2.3 自动校验与自愈 (Self-Healing)

- **描述**：生成的代码必须经过严格校验才能交付。
- **流程**：
  1. **DSL Validator**：加载生成的 YAML，检查必填字段、节点连接完整性、变量引用有效性。
  2. **Feedback Loop**：如果有错误，将错误信息回传给 `Repairer` 智能体，进行最多 3 次的自动修复尝试。

### 2.4 知识库检索 (RAG)

- **描述**：复用现有的 RAG 模块，检索相似的 YAML 案例作为 Context。
- **策略**：在 Planner 和 Architect 阶段注入参考案例，指导 AI 模仿优秀的编排模式。

------

## 3. 待开发特性 (Roadmap)

### 3.1 Word 模板解析 (Pending)
- *当前状态*：暂未实现。
- *目标*：解析 Word 文档结构，自动提取字段并映射到 Dify 变量。

### 3.2 可视化审查界面 (Pending)
- *当前状态*：仅提供 API (`/yaml/generate`)。
- *目标*：ReactFlow 前端，支持可视化拖拽修改 Blueprint。

------

## 4. 技术栈 (Tech Stack)

- **Orchestration**: LangGraph, LangChain
- **LLM**: OpenAI / Aliyun Qwen (via OpenAI-Compatible API)
- **Builder**: Python Pydantic (Blueprint Definition)
- **Validation**: Custom Dify DSL Validator
- **API**: FastAPI
- **CLI**: Typer (Async Support)
