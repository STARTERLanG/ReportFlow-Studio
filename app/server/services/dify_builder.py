import re
from typing import Any

import yaml

from app.server.schemas.dsl import (
    CodeNode,
    EndNode,
    HTTPNode,
    IfElseNode,
    LLMNode,
    StartNode,
    TemplateNode,
    WorkflowBlueprint,
)


class DifyBuilder:
    def __init__(self):
        self.nodes = []
        self.edges = []
        self.node_map = {}  # id -> node_data
        self.edge_count = 0

    def build(self, blueprint: WorkflowBlueprint) -> str:
        """主入口：将蓝图转换为 YAML 字符串"""
        self.nodes = []
        self.edges = []
        self.node_map = {}

        # 1. 实例化节点
        for i, node_data in enumerate(blueprint.nodes):
            dify_node = self._create_node(node_data, index=i)
            self.nodes.append(dify_node)
            self.node_map[node_data.id] = dify_node

        # 2. 构建连线
        for node_data in blueprint.nodes:
            self._create_edges(node_data)

        # 3. 组装最终结构
        dsl = {
            "kind": "app",
            "version": "0.5.0",
            "app": {
                "name": blueprint.name,
                "description": blueprint.description,
                "mode": "workflow",
                "icon": "🤖",
                "icon_background": "#FFEAD5",
            },
            "dependencies": [d.model_dump() for d in blueprint.dependencies] if blueprint.dependencies else [],
            "workflow": {"graph": {"nodes": self.nodes, "edges": self.edges}},
        }

        return yaml.dump(dsl, allow_unicode=True, sort_keys=False, default_flow_style=False, width=1000)

    def _map_dify_type(self, t: str) -> str:
        t = str(t).lower()
        if t in ["integer", "int", "float", "number"]:
            return "number"
        if t in ["boolean", "bool"]:
            return "boolean"
        if t in ["object", "dict"]:
            return "object"
        if t in ["array", "list"]:
            return "array"
        return "string"

    def _create_node(self, node: Any, index: int) -> dict:
        """工厂方法：根据类型创建 Dify 节点"""
        # ...
        # 基础结构
        base = {
            "id": node.id,
            "type": "custom",  # Dify 内部统一用 custom，真实类型在 data.type
            "position": {"x": 200 * (index % 3), "y": 200 * (index // 3)},  # 简单网格布局
            "data": {"title": node.title, "desc": node.desc, "type": node.type},
        }

        # 类型特化处理
        if isinstance(node, StartNode):
            base["data"]["variables"] = []
            for v in node.variables:
                # Map simple types to Dify UI types
                standard_type = self._map_dify_type(v.type)
                dify_type = "text-input"
                if standard_type == "number":
                    dify_type = "number"
                elif standard_type == "boolean":
                    dify_type = "select"

                base["data"]["variables"].append(
                    {
                        "variable": v.name,
                        "label": v.name,
                        "type": dify_type,
                        "required": True,
                        "options": [],
                        "max_length": 48 if dify_type == "text-input" else None,
                    }
                )

        elif isinstance(node, EndNode):
            base["data"]["outputs"] = []
            for out in node.outputs:
                # 解析 value 中的 @{...}
                val = out.get("value", "")
                selector = []
                if isinstance(val, str):
                    val = self._resolve_vars(val)
                    if "{{" in str(val):
                        selector = self._extract_selector(val)

                # Determine value_type (default string)
                # Pydantic schema doesn't force type in Dict, so we infer or default
                v_type = out.get("type", "string")

                base["data"]["outputs"].append(
                    {"variable": out["var"], "value_selector": selector, "value_type": v_type}
                )

        elif isinstance(node, LLMNode):
            # 注入标准 LLM 配置
            model_conf = {"provider": "openai", "name": "gpt-4o", "mode": "chat"}
            if node.model:
                model_conf = {"provider": node.model.provider, "name": node.model.name, "mode": node.model.mode}
                if node.model.completion_params:
                    model_conf["completion_params"] = node.model.completion_params

            base["data"].update(
                {
                    "model": model_conf,
                    "vision": {"enabled": False},
                    "memory": {"window": {"enabled": False, "size": 10}},
                    "context": {"enabled": False, "variable_selector": []},
                    "prompt_template": [
                        {"role": "system", "text": node.system_prompt},
                        {"role": "user", "text": self._resolve_vars(node.user_prompt)},
                    ],
                }
            )
            # 自动提取变量到 variables (Dify 可能需要，虽然 LLM 节点主要靠 prompt_template)
            # Dify LLM 节点不需要 variables 字段，它是隐式的

        elif isinstance(node, HTTPNode):
            base["data"].update(
                {
                    "method": node.method,
                    "url": node.url,
                    "authorization": {"type": "no-auth"},
                    "headers": node.headers,
                    "params": node.params,
                    "body": {"type": "none", "data": node.body}
                    if not node.body
                    else {"type": "json", "data": node.body},  # Simple assumption
                    "timeout": node.timeout or {"connect": 5, "read": 60, "write": 60},
                }
            )

        elif isinstance(node, CodeNode):
            base["data"]["code"] = node.code
            base["data"]["code_language"] = node.code_language  # 必须包含语言选择
            # 处理 inputs 映射
            base["data"]["variables"] = []
            for k, v in node.inputs.items():
                resolved = self._resolve_vars(v)
                selector = self._extract_selector(resolved)
                if selector:
                    base["data"]["variables"].append({"variable": k, "value_selector": selector})

            # 处理 outputs: 转换为 Dify 要求的 Dict 格式
            outputs_dict = {}
            for out in node.outputs:
                outputs_dict[out.name] = {"type": self._map_dify_type(out.type), "children": None}
            base["data"]["outputs"] = outputs_dict

        elif isinstance(node, TemplateNode):
            # 自动提取变量
            resolved_tpl = self._resolve_vars(node.template)
            base["data"]["template"] = resolved_tpl
            base["data"]["variables"] = self._extract_template_vars(resolved_tpl)

        elif isinstance(node, IfElseNode):
            # Legacy DSL (0.5.x) format: No 'cases', direct 'conditions'
            # Only supports binary logic natively
            main_conditions = []
            for idx, branch in enumerate(node.branches):
                if branch.operator == "default":
                    continue

                var_str = self._resolve_vars(branch.variable)
                selector = self._extract_selector(var_str)

                # Normalize operator
                op = branch.operator
                if op == "==":
                    op = "="

                main_conditions.append(
                    {
                        "id": "true",  # Revert to 'true' based on legacy success
                        "variable_selector": selector,
                        "comparison_operator": op,
                        "value": branch.value,
                        "varType": "string",
                    }
                )
                # In legacy binary if-else, we only take the first condition group
                break

            base["data"]["logical_operator"] = "and"  # Default
            base["data"]["conditions"] = main_conditions

        return base

    def _create_edges(self, node: Any):
        """生成节点的出边"""
        # 1. 线性/并行连接 (Start, LLM, Code, Template)
        if hasattr(node, "next_step") and node.next_step:
            targets = node.next_step if isinstance(node.next_step, list) else [node.next_step]
            for target in targets:
                self._add_edge(node.id, target, "source")

        # 2. 分支连接 (IfElse)
        if isinstance(node, IfElseNode):
            for idx, branch in enumerate(node.branches):
                target = branch.next_step
                if not target:
                    continue

                # Legacy only supports one true path and one false path
                if branch.operator == "default":
                    handle = "false"
                else:
                    # All non-default conditions in legacy are merged into 'true'
                    # Or in this simplified builder, the first one is true
                    handle = "true"

                self._add_edge(node.id, target, handle)

    def _add_edge(self, source: str, target: str, source_handle: str):
        self.edges.append(
            {
                "id": f"edge_{self.edge_count}",
                "source": source,
                "target": target,
                "sourceHandle": source_handle,
                "targetHandle": "target",
                "type": "custom",
            }
        )
        self.edge_count += 1

    def _resolve_vars(self, text: str) -> str:
        """
        将 @{node.var} 转换为 {{#node.var#}}
        """
        if not text:
            return ""
        return re.sub(r"@\{([a-zA-Z0-9_]+)\.([a-zA-Z0-9_]+)\}", r"{{#\1.\2#}}", text)

    def _extract_selector(self, dify_var_str: str) -> list[str]:
        """
        从 {{#node.var#}} 中提取 [node, var]
        """
        match = re.search(r"\{\{#([a-zA-Z0-9_]+)\.([a-zA-Z0-9_]+)#\}\}", dify_var_str)
        if match:
            return [match.group(1), match.group(2)]
        return []

    def _extract_template_vars(self, template_str: str) -> list[dict]:
        """
        扫描模板中的变量引用，生成 variables 列表
        """
        refs = re.findall(r"\{\{#([a-zA-Z0-9_]+)\.([a-zA-Z0-9_]+)#\}\}", template_str)
        seen = set()
        vars_list = []
        for node, var in refs:
            key = (node, var)
            if key not in seen:
                vars_list.append(
                    {
                        "variable": f"{node}_{var}",  # 自动生成变量名
                        "value_selector": [node, var],
                    }
                )
                seen.add(key)
        return vars_list
