import asyncio
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from pydantic import SecretStr
from sqlmodel import Session
from agents.memories.vector_store import RagService
from app.server.config import settings
from app.server.database import engine
from app.server.logger import logger
from app.server.models.history import WorkflowHistory
from app.server.utils.context import status_callback_var
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
        try: return RagService()
        except Exception as e:
            logger.warning(f"RAG 初始化失败: {e}")
            return None

    def _build_graph(self):
        graph = StateGraph(GraphState)
        graph.add_node("planner", self.nodes.planner)
        graph.add_node("yaml_architect", self.nodes.yaml_architect)
        graph.add_node("prompt_expert", self.nodes.prompt_expert)
        graph.add_node("assembler", self.nodes.assembler)
        graph.add_node("validator", self.nodes.validator)
        graph.add_node("repairer", self.nodes.repairer)
        graph.add_node("skipper", self.nodes.skipper)
        graph.set_entry_point("planner")
        graph.add_conditional_edges("planner", self._route_step)
        graph.add_conditional_edges("yaml_architect", self._route_step)
        graph.add_conditional_edges("prompt_expert", self._route_step)
        graph.add_conditional_edges("skipper", self._route_step)
        graph.add_edge("assembler", "validator")
        graph.add_conditional_edges("validator", self._check_validation, {END: END, "repairer": "repairer"})
        graph.add_edge("repairer", "validator")
        return graph.compile()

    def _route_step(self, state: GraphState) -> str:
        if not state["plan"]: return "assembler"
        step = str(state["plan"][0]).lower()
        if "design" in step: return "yaml_architect"
        if "prompt" in step: return "prompt_expert"
        if "assemble" in step or "组装" in step or "yaml" in step: return "assembler"
        return "skipper"

    def _check_validation(self, state: GraphState) -> str:
        if not state.get("validation_errors"): return END
        if state.get("retry_count", 0) >= 3:
            logger.error("达到最大重试次数。强制交付。")
            return END
        return "repairer"

    def _load_example_yaml(self) -> str:
        try:
            with open("docs/references/basic_llm_chat_workflow.yml", encoding="utf-8") as f: return f.read()
        except: return ""

    async def generate_yaml(self, user_request: str, context: str = "", status_callback=None) -> str:
        async def notify(msg: str):
            if status_callback:
                if asyncio.iscoroutinefunction(status_callback): await status_callback(msg)
                else: status_callback(msg)
        
        token = status_callback_var.set(notify)
        try:
            await notify("启动 YAML 生成工作流...")
            rag_context = ""
            if self.rag_service:
                try:
                    await notify("正在从知识库检索参考案例...")
                    refs = self.rag_service.search(user_request, k=2)
                    rag_context = "\n".join([f"--- 参考案例 ---\n{r.page_content}" for r in refs])
                except Exception as e:
                    logger.warning(f"RAG 检索失败: {e}")
                    await notify(f"系统提示: RAG 检索异常")

            initial_state: GraphState = {
                "user_request": user_request,
                "context": f"{context}\n\n{rag_context}".strip(),
                "yaml_example": self._load_example_yaml(),
                "plan": [], "yaml_skeleton": "", "generated_prompts": [], "final_yaml": "",
                "validation_errors": [], "retry_count": 0,
            }
            
            try:
                final = await self.app.ainvoke(initial_state)
            except Exception as e:
                logger.exception("Graph 执行致命错误")
                await notify(f"致命错误: 生成过程被异常中断 ({e})")
                return f"# 生成失败: {e}"

            if final.get("validation_errors"): 
                await notify(f"提示: 校验发现 {len(final['validation_errors'])} 个问题，已尝试自动修复")
            
            await notify("工作流组装完成。")
            result_yaml = final.get("final_yaml", "# 生成失败")
            
            try:
                with Session(engine) as session:
                    session.add(WorkflowHistory(
                        user_request=user_request, context=context, final_yaml=result_yaml,
                        model_name=settings.llm.model_name,
                        status="success" if "final_yaml" in final else "failed",
                        error_msg="\n".join(final.get("validation_errors", [])) if final.get("validation_errors") else None,
                    ))
                    session.commit()
            except Exception as e: 
                logger.error(f"历史记录保存失败: {e}")
                await notify(f"系统提示: 数据库保存异常 (记录已生成但未入库)")
            
            return result_yaml
        finally:
            status_callback_var.reset(token)
