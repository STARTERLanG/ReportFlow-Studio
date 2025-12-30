import json
import re
import yaml
from typing import List, Dict, TypedDict

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END

from backend.app.config import settings
from backend.app.logger import logger
from backend.agents.memories.vector_store import RagService
from backend.agents.prompts.library import (
    DEEPAGENT_PLANNER_PROMPT,
    YAML_ARCHITECT_PROMPT,
    PROMPT_EXPERT_PROMPT,
)


def str_presenter(dumper, data):
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


yaml.add_representer(str, str_presenter)


class GraphState(TypedDict):
    user_request: str
    context: str
    yaml_example: str
    plan: List[str]
    yaml_skeleton: str
    generated_prompts: List[Dict[str, str]]
    final_yaml: str


class YamlAgentService:
    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.llm.model_name,
            api_key=settings.llm.api_key,
            base_url=settings.llm.base_url,
            temperature=0,
        )
        try:
            self.rag_service = RagService()
        except Exception as e:
            logger.warning(f"RAG 服务初始化失败，将降级为无参考模式: {e}")
            self.rag_service = None
        self.app = self._build_graph()

    def _build_graph(self):
        def planner(state: GraphState):
            logger.info("DeepAgent: 进入 Planner 节点")
            prompt = ChatPromptTemplate.from_template(DEEPAGENT_PLANNER_PROMPT)
            chain = prompt | self.llm
            response = chain.invoke(
                {"user_request": state["user_request"], "context": state["context"]}
            )
            try:
                content = response.content.strip()
                if "```" in content:
                    content = re.sub(r"```\w*\n", "", content).replace("```", "")
                result = json.loads(content)
                plan = result.get("plan", [])
                logger.info(f"DeepAgent: 生成计划 -> {json.dumps(plan, ensure_ascii=False)}")
                return {"plan": plan}
            except Exception as e:
                logger.error(f"Planner 解析失败: {e}")
                return {"plan": []}

        def yaml_architect(state: GraphState):
            logger.info("DeepAgent: 进入 YAML Architect 节点")
            prompt = ChatPromptTemplate.from_template(YAML_ARCHITECT_PROMPT)
            chain = prompt | self.llm
            response = chain.invoke(
                {
                    "user_request": state["user_request"],
                    "context": state["context"],
                    "yaml_example": state["yaml_example"],
                }
            )
            skeleton = response.content.strip()
            if "```" in skeleton:
                skeleton = re.sub(r"```\w*\n", "", skeleton).replace("```", "")

            # 自动修复常用的节点类型关键词
            replacements = {
                "template_transform": "template-transform",
                "if_else": "if-else",
                "variable_assigner": "variable-assigner",
                "parameter_extractor": "parameter-extractor",
                "http_request": "http-request",
                "knowledge_retrieval": "knowledge-retrieval",
                "question_classifier": "question-classifier",
                "document_extractor": "document-extractor"
            }
            for old, new in replacements.items():
                skeleton = skeleton.replace(f'"{old}"', f'"{new}"').replace(f"'{old}'", f"'{new}'").replace(f": {old}", f": {new}")

            return {"yaml_skeleton": skeleton, "plan": state["plan"][1:]}

        def prompt_expert_node(state: GraphState):
            logger.info("DeepAgent: 进入 Prompt Expert 节点")
            if not state["plan"]:
                return {"generated_prompts": state["generated_prompts"]}
            current_task = state["plan"][0]
            task_goal = current_task.get("goal") or current_task.get("description", "") if isinstance(current_task, dict) else str(current_task)

            prompt_template = ChatPromptTemplate.from_template(PROMPT_EXPERT_PROMPT)
            chain = prompt_template | self.llm
            response = chain.invoke({"task_description": task_goal, "context": state["context"]})

            clean_prompt = response.content.strip()
            if "```" in clean_prompt:
                clean_prompt = re.sub(r"```\w*\n", "", clean_prompt).replace("```", "")

            new_prompts = state["generated_prompts"].copy()
            new_prompts.append({"task": task_goal, "prompt": clean_prompt})
            return {"generated_prompts": new_prompts, "plan": state["plan"][1:]}

        def assembler(state: GraphState):
            logger.info("DeepAgent: 进入 Assembler 节点执行智能组装")
            try:
                skeleton_text = state["yaml_skeleton"]
                skeleton_text = re.sub(r'__([\w\.]+?)__', r'SAFE_REF_START_\1_SAFE_REF_END', skeleton_text)
                skeleton_data = yaml.safe_load(skeleton_text)
                if not skeleton_data or not isinstance(skeleton_data, dict):
                    raise ValueError("骨架无效")

                def restore_dify_syntax(obj):
                    if isinstance(obj, str):
                        return obj.replace("SAFE_REF_START_", "{{#").replace("_SAFE_REF_END", "#}}")
                    elif isinstance(obj, dict):
                        return {k: restore_dify_syntax(v) for k, v in obj.items()}
                    elif isinstance(obj, list):
                        return [restore_dify_syntax(i) for i in obj]
                    return obj
                skeleton_data = restore_dify_syntax(skeleton_data)

                skeleton_data["kind"] = "app"
                skeleton_data["version"] = "0.5.0"
                if "app" not in skeleton_data or not isinstance(skeleton_data["app"], dict):
                    skeleton_data["app"] = {"name": "自动化工作流", "mode": "workflow", "icon": "🤖", "icon_background": "#FFEAD5"}

                if "workflow" not in skeleton_data: skeleton_data["workflow"] = {}
                wf = skeleton_data["workflow"]
                if "graph" not in wf: wf["graph"] = {}
                graph = wf["graph"]
                
                nodes = skeleton_data.pop("nodes", []) or wf.pop("nodes", []) or graph.get("nodes", [])
                edges = skeleton_data.pop("edges", []) or wf.pop("edges", []) or skeleton_data.pop("connections", []) or graph.get("edges", [])
                graph["nodes"], graph["edges"] = nodes, edges

                prompts = state["generated_prompts"]
                prompt_map = {p["task"].lower(): p["prompt"] for p in prompts}
                used_tasks = set()
                start_node = next((n for n in nodes if str(n.get("data", {}).get("type")).lower() in ["start", "开始"]), None)
                start_id = start_node["id"] if start_node else "start"

                for node in nodes:
                    node["id"] = str(node.get("id", "")).strip()
                    data = node.get("data", {})
                    real_type = data.get("type") or node.get("type")
                    if not real_type or real_type == "custom":
                        title = str(data.get("title", "")).lower()
                        if any(k in title for k in ["start", "开始"]): real_type = "start"
                        elif any(k in title for k in ["end", "结束"]): real_type = "end"
                        elif any(k in title for k in ["if", "判断", "else"]): real_type = "if-else"
                        elif any(k in title for k in ["code", "代码"]): real_type = "code"
                        elif any(k in title for k in ["template", "模板"]): real_type = "template-transform"
                        else: real_type = "llm"
                    
                    node["type"] = "custom"
                    data["type"] = real_type
                    
                    if "variables" in data and isinstance(data["variables"], list):
                        for v in data["variables"]:
                            if "selector" in v: v["value_selector"] = v.pop("selector")
                            if "name" in v: v["variable"] = v.pop("name")

                    if real_type == "llm":
                        title_key = data.get("title", "").lower()
                        matched_prompt = next((p for t, p in prompt_map.items() if t in title_key or title_key in t), None)
                        if not matched_prompt:
                            matched_prompt = next((p for t, p in prompt_map.items() if t not in used_tasks), None)
                        
                        if matched_prompt:
                            used_tasks.add(next(t for t, p in prompt_map.items() if p == matched_prompt))
                            user_text = "请根据指令执行。"
                            if start_node:
                                if not any(v.get("variable") == "input_text" for v in data.get("variables", [])):
                                    if "variables" not in data: data["variables"] = []
                                    data["variables"].append({"variable": "input_text", "value_selector": [start_id, "input_text"]})
                                user_text = f"# 输入数据\n\n{{{{#{start_id}.input_text#}}}}"
                            data["prompt_template"] = [{"role": "system", "text": matched_prompt}, {"role": "user", "text": user_text}]
                        data.update({"vision": {"enabled": False, "configs": {"variable_selector": []}}, "memory": {"enabled": False, "window": {"enabled": False, "size": 50}}, "context": {"enabled": False, "variable_selector": []}, "structured_output": {"enabled": False}})

                    if real_type == "if-else":
                        if "conditions" in data:
                            for idx, cond in enumerate(data["conditions"]):
                                cond["id"] = f"condition_{idx+1}"
                                if "expression" in cond: cond["expression"] = cond["expression"].replace("{{#", "").replace("#}}", "")

                    if real_type == "end":
                        raw_out = data.get("outputs", [])
                        new_outputs = []
                        if isinstance(raw_out, dict):
                            for k, v in raw_out.items():
                                vs = []
                                if isinstance(v, str) and "." in v:
                                    parts = v.split(".")
                                    vs = [parts[0].replace("{{#", ""), parts[1].replace("#}}", "")]
                                new_outputs.append({
                                    "variable": k,
                                    "value_type": "string",
                                    "value_selector": vs
                                })
                        elif isinstance(raw_out, list):
                            for o in raw_out:
                                if "value_selector" not in o and "value" in o:
                                    val = o["value"]
                                    if isinstance(val, str) and "." in val:
                                        parts = val.split(".")
                                        o["value_selector"] = [parts[0].replace("{{#", ""), parts[1].replace("#}}", "")]
                                o["value_type"] = o.get("value_type", "string")
                                new_outputs.append(o)
                        data["outputs"] = new_outputs

                for i, edge in enumerate(edges):
                    edge["id"] = f"edge_{i}"
                    if "source_node_id" in edge: edge["source"] = edge.pop("source_node_id")
                    if "target_node_id" in edge: edge["target"] = edge.pop("target_node_id")
                    edge["sourceHandle"] = edge.get("sourceHandle", "source")
                    edge["targetHandle"] = edge.get("targetHandle", "target")
                    edge["type"] = "custom"

                final_yaml = yaml.dump(skeleton_data, allow_unicode=True, sort_keys=False, default_flow_style=False, width=1000)
                return {"final_yaml": final_yaml, "plan": []}
            except Exception as e:
                logger.error(f"Assembler 最终清洗失败: {e}")
                return {"final_yaml": state["yaml_skeleton"], "plan": []}

        def skipper(state: GraphState):
            return {"plan": state["plan"][1:]}

        graph = StateGraph(GraphState)
        graph.add_node("planner", planner)
        graph.add_node("yaml_architect", yaml_architect)
        graph.add_node("prompt_expert", prompt_expert_node)
        graph.add_node("assembler", assembler)
        graph.add_node("skipper", skipper)

        def router(state: GraphState):
            if not state["plan"]:
                logger.info("DeepAgent: 计划已完成，结束流程。" )
                return END
            t = str(state["plan"][0]).lower()
            if "assemble" in t or "assembler" in t or "组装" in t: return "assembler"
            if "design" in t: return "yaml_architect"
            if "prompt" in t: return "prompt_expert"
            return "skipper"

        graph.set_entry_point("planner")
        graph.add_conditional_edges("planner", router)
        graph.add_conditional_edges("yaml_architect", router)
        graph.add_conditional_edges("prompt_expert", router)
        graph.add_conditional_edges("assembler", router)
        graph.add_conditional_edges("skipper", router)
        return graph.compile()

    def _load_example_yaml(self) -> str:
        try:
            with open("docs/references/basic_llm_chat_workflow.yml", "r", encoding="utf-8") as f:
                return f.read()
        except:
            return ""

    async def generate_yaml(self, user_request: str, context: str = "") -> str:
        logger.info("启动 YAML 生成流程...")
        rag_context = ""
        if self.rag_service:
            try:
                references = self.rag_service.search(user_request, k=2)
                rag_context = "\n".join([f"--- 案例 ---\n{r.page_content}" for r in references])
            except Exception as e:
                logger.warning(f"RAG 搜索失败: {e}")
        initial_state = {
            "user_request": user_request,
            "context": f"{context}\n\n{rag_context}".strip(),
            "yaml_example": self._load_example_yaml(),
            "plan": [],
            "yaml_skeleton": "",
            "generated_prompts": [],
            "final_yaml": "",
        }
        final_state = self.app.invoke(initial_state)
        return final_state.get("final_yaml", "YAML 生成失败。")
