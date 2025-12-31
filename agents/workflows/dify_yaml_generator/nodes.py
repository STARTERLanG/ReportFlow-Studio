import json
import re
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
from app.server.utils.dsl_validator import DifyDSLValidator
from app.server.schemas.dsl import WorkflowBlueprint
from app.server.services.dify_builder import DifyBuilder

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

    def planner(self, state: GraphState) -> dict[str, Any]:
        logger.info("DeepAgent: Planner Start")
        chain = ChatPromptTemplate.from_template(DEEPAGENT_PLANNER_PROMPT) | self.llm
        try:
            resp = chain.invoke({"user_request": state["user_request"], "context": state["context"]})
            content = self._clean_block(str(resp.content))
            plan = json.loads(content).get("plan", [])
            logger.info(f"Plan Generated: {len(plan)} steps")
            return {"plan": plan}
        except Exception as e:
            logger.error(f"Planner Error: {e}")
            return {"plan": []}

    def yaml_architect(self, state: GraphState) -> dict[str, Any]:
        logger.info("DeepAgent: Architect Start")
        chain = ChatPromptTemplate.from_template(YAML_ARCHITECT_PROMPT) | self.llm
        resp = chain.invoke(
            {
                "user_request": state["user_request"],
                "context": state["context"],
                "yaml_example": state["yaml_example"],
            }
        )
        json_str = self._clean_block(str(resp.content))

        try:
            WorkflowBlueprint(**json.loads(json_str))
            logger.info("Blueprint JSON Validated")
        except Exception as e:
            logger.error(f"Blueprint Validation Failed: {e}")

        return {"yaml_skeleton": json_str, "plan": state["plan"][1:]}

    def prompt_expert(self, state: GraphState) -> dict[str, Any]:
        logger.info("DeepAgent: Prompt Expert Start")
        try:
            bp_data = json.loads(state["yaml_skeleton"])
        except Exception:
            return {"plan": state["plan"][1:]}

        updated = False
        nodes = bp_data.get("nodes", [])

        chain = ChatPromptTemplate.from_template(PROMPT_EXPERT_PROMPT) | self.llm

        for node in nodes:
            if node.get("type") == "llm":
                task_desc = f"Title: {node.get('title')}\nDraft: {node.get('system_prompt', '')}"
                try:
                    resp = chain.invoke({"task_description": task_desc, "context": state["context"]})
                    node["system_prompt"] = self._clean_block(str(resp.content))
                    updated = True
                except Exception as e:
                    logger.warning(f"Prompt Optimization Failed for {node.get('id')}: {e}")

        if updated:
            return {"yaml_skeleton": json.dumps(bp_data, ensure_ascii=False), "plan": state["plan"][1:]}
        return {"plan": state["plan"][1:]}

    def assembler(self, state: GraphState) -> dict[str, Any]:
        logger.info("DeepAgent: Assembler Start")
        try:
            if not state["yaml_skeleton"]:
                raise ValueError("Empty Blueprint")

            blueprint = WorkflowBlueprint(**json.loads(state["yaml_skeleton"]))
            final_yaml = DifyBuilder().build(blueprint)

            # Internal Validation Check
            validator = DifyDSLValidator()
            if validator.load_from_string(final_yaml):
                is_valid, errors = validator.validate()
                if not is_valid:
                    error_msg = "\n".join([f"# [Error] {e}" for e in errors])
                    logger.error(f"Validation Failed:\n{error_msg}")
                    final_yaml = f"# ⚠️ Validation Failed:\n{error_msg}\n\n{final_yaml}"
                    return {"final_yaml": final_yaml, "validation_errors": errors, "retry_count": 0}

            logger.info("✅ Builder Output Validated")
            return {"final_yaml": final_yaml, "validation_errors": [], "retry_count": 0}

        except Exception as e:
            logger.error(f"Assembler Error: {e}")
            return {
                "final_yaml": f"# Build Error: {e}\n# Source:\n{state.get('yaml_skeleton')}",
                "validation_errors": [str(e)],
            }

    def validator(self, state: GraphState) -> dict[str, Any]:
        """Re-check validator node"""
        logger.info("DeepAgent: Validator Check")
        yaml_content = state.get("final_yaml", "")
        if not yaml_content or yaml_content.startswith("# Build Error"):
            return {"validation_errors": ["Build Failed"]}

        validator = DifyDSLValidator()
        if validator.load_from_string(yaml_content):
            is_valid, errors = validator.validate()
            return {"validation_errors": [] if is_valid else errors}
        return {"validation_errors": ["Parse Failed"]}

    def repairer(self, state: GraphState) -> dict[str, Any]:
        logger.info("DeepAgent: Repairer Start")
        retry = state.get("retry_count", 0) + 1

        chain = ChatPromptTemplate.from_template(DSL_FIXER_PROMPT) | self.llm
        resp = chain.invoke(
            {"yaml": state.get("final_yaml", ""), "errors": "\n".join(state.get("validation_errors", []))}
        )

        return {"final_yaml": self._clean_block(str(resp.content)), "retry_count": retry}

    def skipper(self, state: GraphState) -> dict[str, Any]:
        return {"plan": state["plan"][1:]}
