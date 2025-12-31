from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph  # type: ignore
from pydantic import SecretStr

from backend.agents.memories.vector_store import RagService
from backend.app.config import settings
from backend.app.logger import logger

from .nodes import WorkflowNodes
from .state import GraphState


class YamlAgentService:
    def __init__(self):
        api_key = settings.llm.api_key
        self.llm = ChatOpenAI(
            model=settings.llm.model_name,
            api_key=SecretStr(api_key) if api_key else None,
            base_url=settings.llm.base_url,
            temperature=0,
        )

        self.nodes = WorkflowNodes(self.llm)
        self.rag_service = self._init_rag()
        self.app = self._build_graph()

    def _init_rag(self) -> RagService | None:
        try:
            return RagService()
        except Exception as e:
            logger.warning(f"RAG Init Failed: {e}")
            return None

    def _build_graph(self):
        graph = StateGraph(GraphState)

        # Register Nodes
        graph.add_node("planner", self.nodes.planner)
        graph.add_node("yaml_architect", self.nodes.yaml_architect)
        graph.add_node("prompt_expert", self.nodes.prompt_expert)
        graph.add_node("assembler", self.nodes.assembler)
        graph.add_node("validator", self.nodes.validator)
        graph.add_node("repairer", self.nodes.repairer)
        graph.add_node("skipper", self.nodes.skipper)

        # Define Edges & Routing
        graph.set_entry_point("planner")

        graph.add_conditional_edges("planner", self._route_step)
        graph.add_conditional_edges("yaml_architect", self._route_step)
        graph.add_conditional_edges("prompt_expert", self._route_step)
        graph.add_conditional_edges("skipper", self._route_step)

        # Assembler -> Validator (Check)
        graph.add_edge("assembler", "validator")

        # Validator -> Repair or End
        graph.add_conditional_edges("validator", self._check_validation, {END: END, "repairer": "repairer"})

        # Repairer loop back to check
        graph.add_edge("repairer", "validator")

        return graph.compile()

    def _route_step(self, state: GraphState) -> str:
        """根据当前 Plan 的第一步决定路由"""
        if not state["plan"]:
            return "assembler"  # Fallback

        step = str(state["plan"][0]).lower()
        if "design" in step:
            return "yaml_architect"
        if "prompt" in step:
            return "prompt_expert"
        if "assemble" in step or "组装" in step:
            return "assembler"
        return "skipper"

    def _check_validation(self, state: GraphState) -> str:
        if not state.get("validation_errors"):
            return END
        if state.get("retry_count", 0) >= 3:
            logger.error("Max Retries Reached. Force Deliver.")
            return END
        return "repairer"

    def _load_example_yaml(self) -> str:
        try:
            with open("docs/references/basic_llm_chat_workflow.yml", encoding="utf-8") as f:
                return f.read()
        except Exception:
            return ""

    async def generate_yaml(self, user_request: str, context: str = "") -> str:
        logger.info("Start YAML Generation Workflow...")

        rag_context = ""
        if self.rag_service:
            try:
                refs = self.rag_service.search(user_request, k=2)
                rag_context = "\n".join([f"--- Ref ---\n{r.page_content}" for r in refs])
            except Exception as e:
                logger.warning(f"RAG Search Failed: {e}")

        initial_state: GraphState = {
            "user_request": user_request,
            "context": f"{context}\n\n{rag_context}".strip(),
            "yaml_example": self._load_example_yaml(),
            "plan": [],
            "yaml_skeleton": "",
            "generated_prompts": [],
            "final_yaml": "",
            "validation_errors": [],
            "retry_count": 0,
        }

        final = await self.app.ainvoke(initial_state)
        return final.get("final_yaml", "# Generation Failed")
