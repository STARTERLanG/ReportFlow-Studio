import json
import re
import asyncio
from typing import Any

import yaml
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from agents.prompts.library import (
    DEEPAGENT_PLANNER_PROMPT,
    DSL_FIXER_PROMPT,
    PROMPT_EXPERT_PROMPT,
    YAML_ARCHITECT_PROMPT,
)
from app.server.logger import logger
from app.server.schemas.dsl import WorkflowBlueprint
from app.server.services.dify_builder import DifyBuilder
from app.server.utils.dsl_validator import DifyDSLValidator
from app.server.utils.context import status_callback_var

from .state import GraphState


# 配置 YAML 输出格式
def str_presenter(dumper, data):
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


yaml.add_representer(str, str_presenter)


class WorkflowNodes:
    def __init__(self, llm: ChatOpenAI):
        self.llm = llm

    def _clean_block(self, text: str) -> str:
        """清理 Markdown 代码块标记"""
        text = text.strip()
        if "```" in text:
            text = re.sub(r"```\w*\n", "", text).replace("```", "")
        return text

    async def _log(self, message: str, level: str = "info"):
        """同时记录后端日志并推送到前端"""
        if level == "error":
            logger.error(message)
        elif level == "warning":
            logger.warning(message)
        else:
            logger.info(message)
        
        # 尝试获取上下文中的回调
        callback = status_callback_var.get()
        if callback:
            try:
                # 确保是可等待对象
                if asyncio.iscoroutinefunction(callback):
                    await callback(message)
                else:
                    callback(message)
            except Exception as e:
                logger.warning(f"Failed to execute UI callback: {e}")

    async def planner(self, state: GraphState) -> dict[str, Any]:
        await self._log("DeepAgent: Planner Start")
        chain = ChatPromptTemplate.from_template(DEEPAGENT_PLANNER_PROMPT) | self.llm
        try:
            # 使用 ainvoke 异步调用 LLM
            resp = await chain.ainvoke({"user_request": state["user_request"], "context": state["context"]})
            content = self._clean_block(str(resp.content))
            plan = json.loads(content).get("plan", [])
            await self._log(f"Plan Generated: {len(plan)} steps")
            return {"plan": plan}
        except Exception as e:
            await self._log(f"Planner Error: {e}", level="error")
            return {"plan": []}

    async def yaml_architect(self, state: GraphState) -> dict[str, Any]:
        await self._log("DeepAgent: Architect Start")
        chain = ChatPromptTemplate.from_template(YAML_ARCHITECT_PROMPT) | self.llm
        resp = await chain.ainvoke(
            {
                "user_request": state["user_request"],
                "context": state["context"],
                "yaml_example": state["yaml_example"],
            }
        )
        json_str = self._clean_block(str(resp.content))

        try:
            # Pydantic 校验是同步的，但很快
            WorkflowBlueprint(**json.loads(json_str))
            await self._log("Blueprint JSON Validated")
        except Exception as e:
            await self._log(f"Blueprint Validation Failed: {e}", level="error")

        return {"yaml_skeleton": json_str, "plan": state["plan"][1:]}

    async def prompt_expert(self, state: GraphState) -> dict[str, Any]:
        await self._log("DeepAgent: Prompt Expert Start")
        try:
            bp_data = json.loads(state["yaml_skeleton"])
        except Exception:
            return {"plan": state["plan"][1:]}

        updated = False
        nodes = bp_data.get("nodes", [])

        chain = ChatPromptTemplate.from_template(PROMPT_EXPERT_PROMPT) | self.llm

        # 并行优化所有节点的 Prompt 会更快，但为了日志清晰，这里先保持顺序或使用 asyncio.gather
        # 这里演示顺序调用
        for node in nodes:
            if node.get("type") == "llm":
                task_desc = f"Title: {node.get('title')}\nDraft: {node.get('system_prompt', '')}"
                try:
                    await self._log(f"Optimizing Prompt for Node: {node.get('id')}...")
                    resp = await chain.ainvoke({"task_description": task_desc, "context": state["context"]})
                    node["system_prompt"] = self._clean_block(str(resp.content))
                    updated = True
                except Exception as e:
                    logger.warning(f"Prompt Optimization Failed for {node.get('id')}: {e}")

        if updated:
            return {"yaml_skeleton": json.dumps(bp_data, ensure_ascii=False), "plan": state["plan"][1:]}
        return {"plan": state["plan"][1:]}

    async def assembler(self, state: GraphState) -> dict[str, Any]:
        await self._log("DeepAgent: Assembler Start")
        try:
            if not state["yaml_skeleton"]:
                raise ValueError("Empty Blueprint")

            blueprint = WorkflowBlueprint(**json.loads(state["yaml_skeleton"]))
            # 同步构建逻辑
            final_yaml = DifyBuilder().build(blueprint)

            # Internal Validation Check
            validator = DifyDSLValidator()
            if validator.load_from_string(final_yaml):
                is_valid, errors = validator.validate()
                if not is_valid:
                    error_msg = "\n".join([f"# [Error] {e}" for e in errors])
                    await self._log(f"Validation Failed: {len(errors)} errors found", level="error")
                    final_yaml = f"# ⚠️ Validation Failed:\n{error_msg}\n\n{final_yaml}"
                    return {"final_yaml": final_yaml, "validation_errors": errors, "retry_count": 0}

            await self._log("✅ Builder Output Validated")
            return {"final_yaml": final_yaml, "validation_errors": [], "retry_count": 0}

        except Exception as e:
            await self._log(f"Assembler Error: {e}", level="error")
            return {
                "final_yaml": f"# Build Error: {e}\n# Source:\n{state.get('yaml_skeleton')}",
                "validation_errors": [str(e)],
            }

    async def validator(self, state: GraphState) -> dict[str, Any]:
        """Re-check validator node"""
        await self._log("DeepAgent: Validator Check")
        yaml_content = state.get("final_yaml", "")
        if not yaml_content or yaml_content.startswith("# Build Error"):
            return {"validation_errors": ["Build Failed"]}

        validator = DifyDSLValidator()
        if validator.load_from_string(yaml_content):
            is_valid, errors = validator.validate()
            return {"validation_errors": [] if is_valid else errors}
        return {"validation_errors": ["Parse Failed"]}

    async def repairer(self, state: GraphState) -> dict[str, Any]:
        await self._log("DeepAgent: Repairer Start")
        retry = state.get("retry_count", 0) + 1

        chain = ChatPromptTemplate.from_template(DSL_FIXER_PROMPT) | self.llm
        resp = await chain.ainvoke(
            {"yaml": state.get("final_yaml", ""), "errors": "\n".join(state.get("validation_errors", []))}
        )

        return {"final_yaml": self._clean_block(str(resp.content)), "retry_count": retry}

    async def skipper(self, state: GraphState) -> dict[str, Any]:
        return {"plan": state["plan"][1:]}