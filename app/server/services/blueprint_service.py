import json
from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from app.server.config import settings
from app.server.logger import logger

BLUEPRINT_DEEP_ALIGN_PROMPT = """
你是一名顶尖的软件架构师，任务是设计一个 AI Agent 工作流蓝图。

**严格模仿下面的微型示例**，根据用户提供的“任务列表”和“资料文件列表”，生成一个完整的、逻辑正确的 JSON 输出。

---
## 完整输出示例 (Few-Shot Example)
假设输入是：
- 任务列表: [任务#0: 分析收入, 任务#1: 分析负债, 任务#2: 核对法人信息]
- 资料文件列表: [文件#0: 银行流水.csv, 文件#1: 资产负债表.pdf, 文件#2: 营业执照.pdf]

你的输出应该是这样的结构：
```json
{{
  "mappings": [
    {{
      "agent_name": "财务分析师",
      "category": "财务数据",
      "file_indices": [0, 1],
      "task_indices": [0, 1],
      "reason": "该 Agent 统一处理所有财务相关的分析任务，依赖流水和资产负债表。"
    }},
    {{
      "agent_name": "工商信息核查员",
      "category": "基础信息",
      "file_indices": [2],
      "task_indices": [2],
      "reason": "该 Agent 负责核对营业执照上的基础信息。"
    }}
  ]
}}
```
**示例逻辑解释**:
- “财务分析师”这**一个** Agent 处理了**多个**相似的任务（分析收入、分析负债）。
- 多个文件（流水、资产负债表）被归纳到了**一个**“财务数据”分类下。
---

## 你的任务
现在，请根据下面的实际输入，生成类似的 JSON 输出。

### **实际输入**
1. **任务列表**: {tasks}
2. **资料文件列表**: {data_sources}

### **核心要求**
1. **合并 Agent**: **必须**将逻辑相关、依赖相似的“任务”分配给**同一个** `agent_name`。最终 `agent_name` 的数量应该明显少于“任务”的总数。
2. **文件归类**: 每个文件只应属于一个业务“分类”。
3. **严格格式**: 你的输出必须是**纯粹的、不含任何注释或 Markdown 标记的 JSON 对象**，且结构与上述示例完全一致。

### **你的输出**
```json
"""


class BlueprintService:
    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.llm.model_name,
            api_key=settings.llm.api_key,
            base_url=settings.llm.base_url,
            temperature=0,
        )

    async def generate_graph(self, tasks: list[dict], file_data: list[dict]) -> dict[str, Any]:
        logger.info(f"启动蓝图生成: 任务数={len(tasks)}, 资料数={len(file_data)}")

        files_context = [f"文件 #{i}: {f['name']}\n内容摘要: {f['snippet']}" for i, f in enumerate(file_data)]
        tasks_context = [f"任务 #{i}: {t['task_name']}\n要求: {t['description']}" for i, t in enumerate(tasks)]

        prompt = ChatPromptTemplate.from_template(BLUEPRINT_DEEP_ALIGN_PROMPT)
        chain = prompt | self.llm

        try:
            response = await chain.ainvoke(
                {
                    "tasks": "\n---\n".join(tasks_context),
                    "data_sources": "\n---\n".join(files_context),
                }
            )

            logger.info(f"LLM Raw Response Content: {response.content}")
            content = response.content.replace("```json", "").replace("```", "").strip()
            decision = json.loads(content)

            return self._build_graph(decision, tasks, file_data)

        except Exception as e:
            logger.error(f"蓝图生成失败: {str(e)}")
            return {"nodes": [], "edges": [], "error": f"蓝图生成失败: {str(e)}"}

    def _build_graph(self, decision: dict, original_tasks: list[dict], original_files: list[dict]) -> dict:
        nodes = []
        edges = []

        # 1. 创建基础输入/输出节点
        for i, f in enumerate(original_files):
            nodes.append(
                {
                    "id": f"file-{i}",
                    "type": "input",
                    "data": {"label": f"📄 {f['name']}"},
                    "position": {"x": 0, "y": 0},
                }
            )

        for i, t in enumerate(original_tasks):
            nodes.append(
                {
                    "id": f"target-{i}",
                    "type": "output",
                    "data": {"label": f"📝 {t['task_name']}"},
                    "position": {"x": 0, "y": 0},
                }
            )

        mappings = decision.get("mappings")
        if not mappings or not isinstance(mappings, list):
            logger.warning("AI 返回的数据中没有找到有效的 'mappings' 数组，无法构建图。")
            return {"nodes": nodes, "edges": []}

        # 2. 遍历 mappings，创建唯一的 Category 和 Agent 节点
        cat_nodes = {}  # name -> id
        agent_nodes = {}  # name -> id

        for m in mappings:
            cat_name = m.get("category")
            agent_name = m.get("agent_name")

            if cat_name and cat_name not in cat_nodes:
                cat_id = f"cat-{len(cat_nodes)}"
                cat_nodes[cat_name] = cat_id
                nodes.append(
                    {
                        "id": cat_id,
                        "type": "default",
                        "data": {"label": f"📁 {cat_name}"},
                        "position": {"x": 0, "y": 0},
                    }
                )

            if agent_name and agent_name not in agent_nodes:
                agent_id = f"agent-{len(agent_nodes)}"
                agent_nodes[agent_name] = agent_id
                nodes.append(
                    {
                        "id": agent_id,
                        "type": "agent",
                        "data": {
                            "label": f"🤖 {agent_name}",
                            "description": m.get("reason"),
                        },
                        "position": {"x": 0, "y": 0},
                    }
                )

        # 3. 再次遍历 mappings，严格按照关系创建 Edges
        file_category_assignment = {}  # 用于确保一个文件只连接到一个分类

        for m in mappings:
            cat_name = m.get("category")
            agent_name = m.get("agent_name")

            cat_id = cat_nodes.get(cat_name)
            agent_id = agent_nodes.get(agent_name)

            if not cat_id or not agent_id:
                continue

            # 连接：Category -> Agent
            edge_cat_agent_id = f"e-{cat_id}-{agent_id}"
            if not any(e["id"] == edge_cat_agent_id for e in edges):
                edges.append({"id": edge_cat_agent_id, "source": cat_id, "target": agent_id})

            # 连接：File -> Category (多对一)
            for f_idx in m.get("file_indices", []):
                if 0 <= int(f_idx) < len(original_files):
                    file_id = f"file-{f_idx}"
                    # 严格执行多对一：仅当文件未被分配时才创建连接
                    if file_id not in file_category_assignment:
                        file_category_assignment[file_id] = cat_id
                        edges.append(
                            {
                                "id": f"e-{file_id}-{cat_id}",
                                "source": file_id,
                                "target": cat_id,
                                "animated": True,
                            }
                        )

            # 连接：Agent -> Target (一对多)
            for t_idx in m.get("task_indices", []):
                if 0 <= int(t_idx) < len(original_tasks):
                    target_id = f"target-{t_idx}"
                    edges.append(
                        {
                            "id": f"e-{agent_id}-{target_id}",
                            "source": agent_id,
                            "target": target_id,
                        }
                    )

        # 4. 过滤掉没有连接的孤儿节点 (除了最开始的输入和最末尾的输出)
        connected_node_ids = set(e["source"] for e in edges) | set(e["target"] for e in edges)
        # 始终保留所有输入和输出节点
        final_node_ids = connected_node_ids | {n["id"] for n in nodes if n["type"] in ["input", "output"]}

        final_nodes = [n for n in nodes if n["id"] in final_node_ids]

        # 如果没有任何边，则返回所有节点以供调试
        if not edges:
            return {"nodes": nodes, "edges": []}

        return {"nodes": final_nodes, "edges": edges}
