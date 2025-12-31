from typing import Any

import yaml
from deepagents import create_deep_agent
from langchain_openai import ChatOpenAI

from agents.prompts.library import (
    ARCHITECT_PROMPT,
    DSL_CODER_PROMPT,
    MAIN_AGENT_SYSTEM_PROMPT,
    PROMPT_EXPERT_PROMPT,
)
from app.server.config import settings
from app.server.logger import logger


class AgentService:
    def __init__(self, model_name: str = None):
        """
        初始化智能体生成服务。
        """
        # 优先使用参数，否则使用配置
        self.model_name = model_name or settings.llm.model_name

        logger.info(f"初始化 Agent 服务: Model={self.model_name}, BaseURL={settings.llm.base_url}")

        # 创建统一的 LLM 实例
        self.llm = ChatOpenAI(
            model=self.model_name,
            api_key=settings.llm.api_key,
            base_url=settings.llm.base_url,
            temperature=0,
        )

    def generate_workflow(self, user_request: str, reference_docs: list[Any]) -> str:
        """
        执行多智能体工作流生成。
        """
        # 构建上下文
        context_str = ""
        for i, doc in enumerate(reference_docs):
            context_str += f"\n--- 参考案例 #{i + 1} ---\n{doc.page_content}\n"

        # 填充 System Prompt
        system_prompt = MAIN_AGENT_SYSTEM_PROMPT.format(context_str=context_str)

        # 创建 Deep Agent
        agent = create_deep_agent(
            model=self.llm,
            system_prompt=system_prompt,
            subagents=[
                {
                    "name": "Architect",
                    "description": "专业的工作流架构师，负责规划节点的流向和逻辑结构。",
                    "system_prompt": ARCHITECT_PROMPT,
                    "model": self.llm,
                },
                {
                    "name": "PromptExpert",
                    "description": "专业的提示词工程师，负责为工作流中的 LLM 节点撰写高质量的 Prompt。",
                    "system_prompt": PROMPT_EXPERT_PROMPT,
                    "model": self.llm,
                },
                {
                    "name": "DSLCoder",
                    "description": "Dify DSL 专家，负责将设计图转化为标准的 Dify YAML 文件。",
                    "system_prompt": DSL_CODER_PROMPT,
                    "model": self.llm,
                },
            ],
        )

        logger.info("启动 Deep Agent 生成任务...")

        try:
            # 构造 DeepAgents 兼容的输入
            input_payload = {"messages": [("user", f"用户需求：{user_request}")]}
            response = agent.invoke(input_payload)

            # 结果提取逻辑
            final_output = ""
            if isinstance(response, dict) and "messages" in response:
                last_msg = response["messages"][-1]
                if hasattr(last_msg, "content"):
                    final_output = last_msg.content
                elif isinstance(last_msg, dict) and "content" in last_msg:
                    final_output = last_msg["content"]
                else:
                    final_output = str(last_msg)
            else:
                final_output = response.get("output", str(response))

            return self._post_process_yaml(final_output)

        except Exception as e:
            logger.error(f"生成任务失败: {e}")
            raise e

    def _post_process_yaml(self, yaml_str: str) -> str:
        """清理 YAML 并自动修复潜在的 DSL 问题。"""
        # 1. 清理 Markdown 标记
        yaml_str = yaml_str.strip()
        if yaml_str.startswith("```yaml"):
            yaml_str = yaml_str[7:]
        if yaml_str.startswith("```"):
            yaml_str = yaml_str[3:]
        if yaml_str.endswith("```"):
            yaml_str = yaml_str[:-3]
        yaml_str = yaml_str.strip()

        try:
            yaml_obj = yaml.safe_load(yaml_str)

            def process_node(obj):
                if isinstance(obj, dict):
                    # 移除 UI 坐标
                    for key in ["position", "width", "height"]:
                        if key in obj:
                            if key == "position":
                                obj[key] = {"x": 0, "y": 0}
                            else:
                                obj.pop(key, None)

                    # 自动修复 LLM 节点属性
                    if obj.get("type") == "llm" and "data" in obj:
                        data = obj["data"]
                        if "context" not in data:
                            data["context"] = {
                                "enabled": False,
                                "variable_selector": [],
                            }
                        if "vision" not in data:
                            data["vision"] = {"enabled": False}

                    for v in obj.values():
                        process_node(v)
                elif isinstance(obj, list):
                    for item in obj:
                        process_node(item)

            process_node(yaml_obj)
            return yaml.dump(yaml_obj, allow_unicode=True, sort_keys=False)
        except Exception as e:
            logger.warning(f"YAML 后处理解析失败，返回原始字符串: {e}")
            return yaml_str
