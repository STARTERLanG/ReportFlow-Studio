import asyncio
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
from app.server.schemas.dsl import WorkflowBlueprint
from app.server.services.dify_builder import DifyBuilder
from app.server.utils.context import status_callback_var
from app.server.utils.dsl_validator import DifyDSLValidator

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
        await self._log("规划阶段：开始生成任务计划")
        chain = ChatPromptTemplate.from_template(DEEPAGENT_PLANNER_PROMPT) | self.llm
        try:
            # 使用 ainvoke 异步调用 LLM
            resp = await chain.ainvoke({"user_request": state["user_request"], "context": state["context"]})
            content = self._clean_block(str(resp.content))
            plan = json.loads(content).get("plan", [])
            await self._log(f"规划完成：已生成 {len(plan)} 个执行步骤")
            return {"plan": plan}
        except Exception as e:
            await self._log(f"规划阶段错误：{e}", level="error")
            return {"plan": []}

    async def yaml_architect(self, state: GraphState) -> dict[str, Any]:
        await self._log("架构阶段：正在构建工作流逻辑蓝图...")
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
            # Pydantic 校验
            WorkflowBlueprint(**json.loads(json_str))
            await self._log("蓝图校验：JSON 结构合法，逻辑框架已就绪")
        except Exception as e:
            await self._log(f"蓝图校验预警：{e}", level="warning")

        # 彻底清扫：移除所有与“设计/架构”相关的计划步骤
        remaining_plan = [
            p for p in state["plan"] 
            if not any(k in str(p).lower() for k in ["design", "architect", "blueprint", "设计", "蓝图"])
        ]
        cleared_count = len(state["plan"]) - len(remaining_plan)
        if cleared_count > 0:
            await self._log(f"架构同步：已完成设计任务，从计划中清理了 {cleared_count} 个重复的设计步骤")

        return {"yaml_skeleton": json_str, "plan": remaining_plan}

    async def prompt_expert(self, state: GraphState) -> dict[str, Any]:
        try:
            bp_data = json.loads(state["yaml_skeleton"])
        except Exception:
            return {"plan": state["plan"][1:]}

        nodes = bp_data.get("nodes", [])
        llm_nodes = [n for n in nodes if n.get("type") == "llm"]
        
        await self._log(f"优化阶段：正在对 {len(llm_nodes)} 个 LLM 节点进行全局提示词精修...")

        updated_count = 0
        chain = ChatPromptTemplate.from_template(PROMPT_EXPERT_PROMPT) | self.llm

        for node in nodes:
            if node.get("type") == "llm":
                task_desc = f"标题: {node.get('title')}\n草案: {node.get('system_prompt', '')}"
                try:
                    await self._log(f"-> 正在微调节点 [{node.get('title', node.get('id'))}] 的指令...")
                    resp = await chain.ainvoke({"task_description": task_desc, "context": state["context"]})
                    node["system_prompt"] = self._clean_block(str(resp.content))
                    updated_count += 1
                except Exception as e:
                    logger.warning(f"提示词优化失败（节点：{node.get('id')}）：{e}")

        # 彻底清扫：移除所有与“提示词/优化”相关的计划步骤
        remaining_plan = [
            p for p in state["plan"] 
            if not any(k in str(p).lower() for k in ["prompt", "优化", "精修"])
        ]
        cleared_redundant = len(state["plan"]) - len(remaining_plan)
        
        await self._log(f"优化完成：已成功精修 {updated_count} 个节点，并清理了 {cleared_redundant} 个后续重复步骤")

        return {
            "yaml_skeleton": json.dumps(bp_data, ensure_ascii=False),
            "plan": remaining_plan,
        }

    async def assembler(self, state: GraphState) -> dict[str, Any]:
        await self._log("组装阶段：开始将蓝图编译为 Dify 标准 YAML...")
        try:
            if not state["yaml_skeleton"]:
                raise ValueError("蓝图内容为空，无法进行组装")

            blueprint = WorkflowBlueprint(**json.loads(state["yaml_skeleton"]))
            # 同步构建逻辑
            final_yaml = DifyBuilder().build(blueprint)

            # 内部校验
            validator = DifyDSLValidator()
            if validator.load_from_string(final_yaml):
                is_valid, errors = validator.validate()
                if not is_valid:
                    error_msg = "\n".join([f"# [错误] {e}" for e in errors])
                    await self._log(f"组装预校验失败：发现 {len(errors)} 个结构问题，已触发自动修复环节", level="error")
                    final_yaml = f"# 预校验未通过：\n{error_msg}\n\n{final_yaml}"
                    return {"final_yaml": final_yaml, "validation_errors": errors, "retry_count": 0}

            # 彻底清扫：移除所有与“组装/编译/YAML”相关的计划步骤
            remaining_plan = [
                p for p in state["plan"] 
                if not any(k in str(p).lower() for k in ["assemble", "yaml", "组装", "编译", "生成"])
            ]
            cleared_redundant = len(state["plan"]) - len(remaining_plan)
            
            await self._log(f"组装成功：YAML 已编译完成并符合 Dify DSL 规范。已清理 {cleared_redundant} 个后续冗余步骤。")
            return {"final_yaml": final_yaml, "validation_errors": [], "retry_count": 0, "plan": remaining_plan}

        except Exception as e:
            await self._log(f"组装阶段发生严重错误：{e}", level="error")
            return {
                "final_yaml": f"# 编译致命错误：{e}\n# 原始蓝图：\n{state.get('yaml_skeleton')}",
                "validation_errors": [str(e)],
            }

    async def validator(self, state: GraphState) -> dict[str, Any]:
        """重读校验节点"""
        await self._log("校验阶段：正在进行最终合规性检查")
        yaml_content = state.get("final_yaml", "")
        if not yaml_content or yaml_content.startswith("# 编译错误"):
            return {"validation_errors": ["编译失败"]}

        validator = DifyDSLValidator()
        if validator.load_from_string(yaml_content):
            is_valid, errors = validator.validate()
            return {"validation_errors": [] if is_valid else errors}
        return {"validation_errors": ["解析失败"]}

    async def repairer(self, state: GraphState) -> dict[str, Any]:
        await self._log("修复阶段：正在尝试自动修正 YAML 错误")
        retry = state.get("retry_count", 0) + 1

        chain = ChatPromptTemplate.from_template(DSL_FIXER_PROMPT) | self.llm
        resp = await chain.ainvoke(
            {"yaml": state.get("final_yaml", ""), "errors": "\n".join(state.get("validation_errors", []))}
        )

        return {"final_yaml": self._clean_block(str(resp.content)), "retry_count": retry}

    async def skipper(self, state: GraphState) -> dict[str, Any]:
        return {"plan": state["plan"][1:]}
