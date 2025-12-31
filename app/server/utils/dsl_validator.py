import os

import yaml
from jsonschema import Draft202012Validator

from app.server.logger import logger

# ==========================================
# 1. 定义官方级 DSL Schema
# ==========================================
DIFY_DSL_SCHEMA = {
    "$id": "https://schema.dify.ai/dsl.json",
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Dify DSL Schema",
    "type": "object",
    "required": ["version", "kind", "workflow"],
    "properties": {
        "version": {
            "type": "string",
            "pattern": r"^\d+\.\d+\.\d+$",
            "description": "DSL 语义版本号",
        },
        "kind": {"type": "string", "description": "应用类型，例如 workflow, chatflow 或 app"},
        "metadata": {
            "type": "object",
            "additionalProperties": True,
        },
        "app": {
            "type": "object",
            "additionalProperties": True,
        },
        "workflow": {
            "type": "object",
            "required": ["graph"],
            "properties": {
                "graph": {
                    "type": "object",
                    "required": ["nodes", "edges"],
                    "properties": {
                        "nodes": {
                            "type": "array",
                            "minItems": 1,
                            "items": {
                                "type": "object",
                                "required": ["id", "data"],
                                "properties": {
                                    "id": {"type": "string"},
                                    "position": {
                                        "type": "object",
                                        "properties": {
                                            "x": {"type": "number"},
                                            "y": {"type": "number"},
                                        },
                                        "additionalProperties": True,
                                    },
                                    "data": {
                                        "type": "object",
                                        "required": ["type"],
                                        "properties": {
                                            "type": {"type": "string"},
                                            "title": {"type": "string"},
                                            "desc": {"type": "string"},
                                        },
                                        "additionalProperties": True,
                                    },
                                },
                                "additionalProperties": True,
                            },
                        },
                        "edges": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "required": ["id", "source", "target"],
                                "properties": {
                                    "id": {"type": "string"},
                                    "source": {"type": "string"},
                                    "target": {"type": "string"},
                                },
                                "additionalProperties": True,
                            },
                        },
                    },
                    "additionalProperties": True,
                }
            },
            "additionalProperties": True,
        },
    },
    "additionalProperties": True,
}


class DifyDSLValidator:
    """
    Dify DSL 校验器，支持 Schema 结构校验和业务逻辑校验。
    """

    def __init__(self):
        self.dsl_content = None
        self.validator = Draft202012Validator(DIFY_DSL_SCHEMA)

    def load_from_file(self, file_path: str) -> bool:
        """从 YAML 文件加载 DSL 内容"""
        if not os.path.exists(file_path):
            logger.error(f"文件不存在: {file_path}")
            return False
        try:
            with open(file_path, encoding="utf-8") as f:
                self.dsl_content = yaml.safe_load(f)
            return True
        except yaml.YAMLError as e:
            logger.error(f"YAML 语法解析失败: {e}")
            return False
        except Exception as e:
            logger.error(f"读取文件失败: {e}")
            return False

    def load_from_string(self, yaml_str: str) -> bool:
        """从字符串加载 DSL 内容"""
        try:
            self.dsl_content = yaml.safe_load(yaml_str)
            return True
        except yaml.YAMLError as e:
            logger.error(f"YAML 语法解析失败: {e}")
            return False
        except Exception as e:
            logger.error(f"解析字符串失败: {e}")
            return False

    def validate_structure(self) -> tuple[bool, list[str]]:
        """第一阶段：基于 JSON Schema 的静态结构校验"""
        if self.dsl_content is None:
            return False, ["未加载 DSL 内容"]

        errors = sorted(self.validator.iter_errors(self.dsl_content), key=lambda e: e.path)
        if errors:
            error_msgs = []
            for error in errors:
                path = " -> ".join([str(p) for p in error.path])
                error_msgs.append(f"位置: [{path}], 原因: {error.message}")
            return False, error_msgs

        return True, []

    def validate_logic(self) -> tuple[bool, list[str]]:
        """第二阶段：基于 Dify 业务逻辑的校验"""
        if self.dsl_content is None:
            return False, ["未加载 DSL 内容"]

        try:
            workflow = self.dsl_content.get("workflow", {})
            graph = workflow.get("graph", {})
            nodes = graph.get("nodes", [])
            edges = graph.get("edges", [])
        except AttributeError:
            return False, ["数据结构异常，无法进行逻辑校验"]

        logic_errors = []
        node_ids = {n.get("id") for n in nodes if n.get("id")}

        # 1. 检查是否存在 Start 节点
        has_start = any(n.get("data", {}).get("type") == "start" for n in nodes)
        if not has_start:
            logic_errors.append("缺少 'start' 类型的起始节点，工作流无法启动。")

        # 2. 检查连线完整性
        for edge in edges:
            e_id = edge.get("id")
            src = edge.get("source")
            tgt = edge.get("target")

            if src not in node_ids:
                logic_errors.append(f"连线 {e_id} 的起点 '{src}' 不存在。")
            if tgt not in node_ids:
                logic_errors.append(f"连线 {e_id} 的终点 '{tgt}' 不存在。")

        # 3. 孤立节点检测（作为警告，不一定判定为失败，但在此逻辑中我们记录它）
        connected_ids = set()
        for edge in edges:
            connected_ids.add(edge.get("source"))
            connected_ids.add(edge.get("target"))

        for node in nodes:
            node_id = node.get("id")
            if node_id and node_id not in connected_ids and len(nodes) > 1:
                node_type = node.get("data", {}).get("type", "Unknown")
                logger.warning(f"发现孤立节点 ID: {node_id} (Type: {node_type})")

        if logic_errors:
            return False, logic_errors

        return True, []

    def validate(self) -> tuple[bool, list[str]]:
        """执行完整校验流程"""
        struct_ok, struct_errors = self.validate_structure()
        if not struct_ok:
            return False, struct_errors

        logic_ok, logic_errors = self.validate_logic()
        if not logic_ok:
            return False, logic_errors

        return True, []
