from typing import Any, Literal

from pydantic import BaseModel

# --- 基础组件 ---


class VariableDefinition(BaseModel):
    name: str
    type: str = "string"  # 允许任意字符串，由 Builder 映射
    description: str | None = None


class BranchCondition(BaseModel):
    # 如果是 if-else
    operator: str | None = "contains"  # contains, equals, etc.
    variable: str | None = None  # e.g., @{node.var}
    value: str | None = None

    # 目标节点 ID
    next_step: str


# --- 节点定义 ---


class BaseNode(BaseModel):
    id: str

    type: str

    title: str | None = "Untitled Node"

    desc: str | None = ""

    # 支持线性(str)或并行(List[str])连接

    next_step: str | list[str] | None = None


class StartNode(BaseNode):
    type: Literal["start"]

    variables: list[VariableDefinition] = []


class EndNode(BaseNode):
    type: Literal["end"]

    outputs: list[dict[str, Any]] | dict[str, Any] = []  # 支持列表或字典，提高鲁棒性


class LLMModelConfig(BaseModel):
    provider: str = "openai"
    name: str = "gpt-4o"
    mode: str = "chat"
    completion_params: dict[str, Any] | None = None


class LLMNode(BaseNode):
    type: Literal["llm"]
    model_config_key: str | None = "default"
    model: LLMModelConfig | None = None
    system_prompt: str = "You are a helpful assistant."
    user_prompt: str


class CodeNode(BaseNode):
    type: Literal["code"]
    code_language: Literal["python3"] = "python3"
    code: str
    inputs: dict[str, str] = {}
    outputs: list[VariableDefinition] = []


class TemplateNode(BaseNode):
    type: Literal["template-transform"]
    template: str


class HTTPNode(BaseNode):
    type: Literal["http-request"]
    url: str
    method: Literal["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD"] = "GET"
    headers: str = ""
    params: str = ""
    body: str = ""
    timeout: dict | None = None  # {"connect": 5, "read": 60, "write": 60}


class IfElseNode(BaseNode):
    type: Literal["if-else"]
    logical_operator: Literal["and", "or"] = "and"
    branches: list[BranchCondition]


class QuestionClassifierNode(BaseNode):
    type: Literal["question-classifier"]
    query_variable: str  # e.g. @{start.input}
    classes: list[dict[str, str]]  # [{"name": "Class A", "next_step": "step_x"}]


class DependencyDef(BaseModel):
    type: str = "marketplace"
    value: dict[str, Any]


# --- 蓝图根对象 ---


class WorkflowBlueprint(BaseModel):
    name: str
    description: str | None = ""
    dependencies: list[DependencyDef] = []
    nodes: list[
        StartNode | EndNode | LLMNode | CodeNode | TemplateNode | IfElseNode | QuestionClassifierNode | HTTPNode
    ]
