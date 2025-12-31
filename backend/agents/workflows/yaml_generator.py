import json
import re
from typing import TypedDict

import yaml
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph

from backend.agents.memories.vector_store import RagService
from backend.agents.prompts.library import (
    DEEPAGENT_PLANNER_PROMPT,
    DSL_FIXER_PROMPT,
    PROMPT_EXPERT_PROMPT,
    YAML_ARCHITECT_PROMPT,
)
from backend.app.config import settings
from backend.app.logger import logger
from backend.app.utils.dsl_validator import DifyDSLValidator
from backend.schemas.blueprint import WorkflowBlueprint
from backend.services.dify_builder import DifyBuilder


def str_presenter(dumper, data):
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


yaml.add_representer(str, str_presenter)


class GraphState(TypedDict):
    user_request: str
    context: str
    yaml_example: str
    plan: list[str]
    yaml_skeleton: str  # Now stores JSON Blueprint string
    generated_prompts: list[dict[str, str]]
    final_yaml: str
    validation_errors: list[str]
    retry_count: int


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
            response = chain.invoke({"user_request": state["user_request"], "context": state["context"]})
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
            logger.info("DeepAgent: 进入 Blueprint Architect 节点 (JSON 模式)")
            prompt = ChatPromptTemplate.from_template(YAML_ARCHITECT_PROMPT)
            chain = prompt | self.llm
            response = chain.invoke(
                {
                    "user_request": state["user_request"],
                    "context": state["context"],
                    "yaml_example": state["yaml_example"],
                }
            )
            json_str = response.content.strip()
            if "```" in json_str:
                json_str = re.sub(r"```\w*\n", "", json_str).replace("```", "")

            # 尝试校验 JSON 结构
            try:
                data = json.loads(json_str)
                # 简单校验：是否符合 Pydantic 模型
                # 这里不抛出异常，而是尽可能保留，交给 Builder 处理
                WorkflowBlueprint(**data)
                logger.info("Blueprint JSON 校验通过")
            except json.JSONDecodeError as e:
                logger.error(f"Blueprint JSON 解析失败: {e}")
                # 可以在这里增加重试逻辑，或者返回空
            except Exception as e:
                logger.error(f"Blueprint Schema 校验失败: {e}")

            return {"yaml_skeleton": json_str, "plan": state["plan"][1:]}

        def prompt_expert_node(state: GraphState):
            logger.info("DeepAgent: 进入 Prompt Expert 节点 - 开始精修提示词")
            
            # 1. 解析 Blueprint JSON
            try:
                bp_data = json.loads(state["yaml_skeleton"])
            except Exception as e:
                logger.error(f"Prompt Expert 解析 JSON 失败: {e}")
                return {"plan": state["plan"][1:]}

            nodes = bp_data.get("nodes", [])
            updated_count = 0

            # 2. 遍历节点，寻找 LLM 节点进行优化
            for node in nodes:
                if node.get("type") == "llm":
                    task_goal = node.get("title", "未命名任务")
                    # 如果有简略的 system_prompt，也可以作为参考
                    draft_prompt = node.get("system_prompt", "")
                    
                    logger.info(f"正在优化节点 [{node['id']}] 的提示词: {task_goal}")
                    
                    # 构造请求
                    prompt_template = ChatPromptTemplate.from_template(PROMPT_EXPERT_PROMPT)
                    chain = prompt_template | self.llm
                    
                    # 合并任务描述：标题 + 草稿
                    full_task_desc = f"节点标题：{task_goal}\n初步构思：{draft_prompt}"
                    
                    try:
                        response = chain.invoke({
                            "task_description": full_task_desc,
                            "context": state["context"] # 传入 RAG 上下文，这是关键！
                        })
                        
                        # 清洗输出
                        refined_prompt = response.content.strip()
                        if "```" in refined_prompt:
                            refined_prompt = re.sub(r"```\w*\n", "", refined_prompt).replace("```", "")
                        
                        # 回填优化后的 Prompt
                        node["system_prompt"] = refined_prompt
                        updated_count += 1
                        
                    except Exception as e:
                        logger.warning(f"优化节点 {node['id']} 失败: {e}")

            # 3. 保存回状态
            if updated_count > 0:
                logger.info(f"成功优化了 {updated_count} 个 LLM 节点的提示词")
                return {"yaml_skeleton": json.dumps(bp_data, ensure_ascii=False), "plan": state["plan"][1:]}
            else:
                logger.info("没有需要优化的 LLM 节点")
                return {"plan": state["plan"][1:]}

        def assembler(state: GraphState):
            logger.info("DeepAgent: 进入 Builder 组装模式")
            try:
                # 1. Load Blueprint
                if not state["yaml_skeleton"]:
                    raise ValueError("Blueprint 为空")
                
                bp_data = json.loads(state["yaml_skeleton"])
                blueprint = WorkflowBlueprint(**bp_data)
                
                # 2. Build YAML using DifyBuilder
                builder = DifyBuilder()
                final_yaml = builder.build(blueprint)
                
                # 3. DSL Validation
                validator = DifyDSLValidator()
                if validator.load_from_string(final_yaml):
                    is_valid, errors = validator.validate()
                    if not is_valid:
                        error_header = "\n".join([f"# [DSL Error] {e}" for e in errors])
                        logger.error(f"Builder 生成的 YAML 校验未通过:\n{error_header}")
                        final_yaml = f"# ⚠️ 该文件未通过 DSL 校验:\n{error_header}\n\n{final_yaml}"
                        # 触发修复流程
                        return {"final_yaml": final_yaml, "validation_errors": errors, "retry_count": 0}
                    else:
                        logger.info("✅ Builder 生成的 YAML 通过校验")

                return {"final_yaml": final_yaml, "validation_errors": [], "retry_count": 0}
            except Exception as e:
                logger.error(f"Assembler 构建失败: {e}")
                # 返回原始 JSON 以便调试
                return {"final_yaml": f"# Build Failed: {e}\n# Blueprint:\n{state.get('yaml_skeleton', '')}", "validation_errors": [str(e)]}

        def validator_node(state: GraphState):
            # Assembler 已经做了校验，这里作为 Re-check 节点
            # 或者用于 Repairer 后的校验
            logger.info("DeepAgent: 进入 Re-Validator 节点")
            validator = DifyDSLValidator()
            current_yaml = state.get("final_yaml", "")
            
            if not current_yaml or current_yaml.startswith("# Build Failed"):
                return {"validation_errors": ["构建失败"]}

            if validator.load_from_string(current_yaml):
                is_valid, errors = validator.validate()
                if is_valid:
                    return {"validation_errors": []}
                else:
                    return {"validation_errors": errors}
            return {"validation_errors": ["解析失败"]}

        def repairer_node(state: GraphState):
            logger.info("DeepAgent: 进入 DSL Repairer 节点")
            current_yaml = state.get("final_yaml", "")
            errors = state.get("validation_errors", [])
            retry = state.get("retry_count", 0) + 1

            prompt = ChatPromptTemplate.from_template(DSL_FIXER_PROMPT)
            chain = prompt | self.llm
            response = chain.invoke({"yaml": current_yaml, "errors": "\n".join(errors)})

            fixed_yaml = response.content.strip()
            if "```" in fixed_yaml:
                fixed_yaml = re.sub(r"```\w*\n", "", fixed_yaml).replace("```", "")

            return {"final_yaml": fixed_yaml, "retry_count": retry}

        def skipper(state: GraphState):
            return {"plan": state["plan"][1:]}

        graph = StateGraph(GraphState)
        graph.add_node("planner", planner)
        graph.add_node("yaml_architect", yaml_architect)
        graph.add_node("prompt_expert", prompt_expert_node)
        graph.add_node("assembler", assembler)
        graph.add_node("validator", validator_node)
        graph.add_node("repairer", repairer_node)
        graph.add_node("skipper", skipper)

        def router(state: GraphState):
            if not state["plan"]:
                return "validator" # 这里的 Validator 指的是 Re-Check
            t = str(state["plan"][0]).lower()
            if "assemble" in t or "assembler" in t or "组装" in t:
                return "assembler"
            if "design" in t:
                return "yaml_architect"
            if "prompt" in t:
                # 跳过 Prompt Expert，直接去下一个（通常是 assemble）
                return "prompt_expert" # 这里还是流转到 Prompt Expert 节点，但该节点现在只是透传
            return "skipper"

        def check_validation(state: GraphState):
            errors = state.get("validation_errors", [])
            if not errors:
                return END
            if state.get("retry_count", 0) >= 3:
                logger.error("DSL 修复达到最大重试次数，强制交付。")
                return END
            return "repairer"

        graph.set_entry_point("planner")
        graph.add_conditional_edges("planner", router)
        graph.add_conditional_edges("yaml_architect", router)
        graph.add_conditional_edges("prompt_expert", router)
        
        # Assembler -> (check errors) -> End or Repairer
        # 但原来的图是 Assembler -> Validator -> Check
        # 现在 Assembler 内部做了 Check，返回了 validation_errors
        # 所以 Assembler -> Check 即可？
        # 为了复用 Repairer 逻辑，我们让 Assembler 指向 Validator 节点（Re-check）
        graph.add_edge("assembler", "validator")
        
        graph.add_conditional_edges("skipper", router)

        graph.add_conditional_edges("validator", check_validation, {END: END, "repairer": "repairer"})
        graph.add_edge("repairer", "validator")

        return graph.compile()
    def _load_example_yaml(self) -> str:
        try:
            with open("docs/references/basic_llm_chat_workflow.yml", encoding="utf-8") as f:
                return f.read()
        except Exception:
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
