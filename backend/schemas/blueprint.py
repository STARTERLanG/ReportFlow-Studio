from typing import List, Literal, Optional, Union, Dict, Any
from pydantic import BaseModel, Field

# --- 基础组件 ---

class VariableDefinition(BaseModel):
    name: str
    type: str = "string" # 允许任意字符串，由 Builder 映射
    description: Optional[str] = None

class BranchCondition(BaseModel):
    # 如果是 if-else
    operator: Optional[str] = "contains" # contains, equals, etc.
    variable: Optional[str] = None       # e.g., @{node.var}
    value: Optional[str] = None
    
    # 目标节点 ID
    next_step: str 

# --- 节点定义 ---

class BaseNode(BaseModel):

    id: str

    type: str

    title: Optional[str] = "Untitled Node"

    desc: Optional[str] = ""

    # 支持线性(str)或并行(List[str])连接

    next_step: Optional[Union[str, List[str]]] = None





class StartNode(BaseNode):

    type: Literal["start"]

    variables: List[VariableDefinition] = []



class EndNode(BaseNode):

    type: Literal["end"]

    outputs: Union[List[Dict[str, Any]], Dict[str, Any]] = [] # 支持列表或字典，提高鲁棒性



class LLMNode(BaseNode):

    type: Literal["llm"]

    model_config_key: Optional[str] = "default"

    system_prompt: str = "You are a helpful assistant."

    user_prompt: str



class CodeNode(BaseNode):

    type: Literal["code"]

    code_language: Literal["python3"] = "python3"

    code: str

    inputs: Dict[str, str] = {}

    outputs: List[VariableDefinition] = []



class TemplateNode(BaseNode):

    type: Literal["template-transform"]

    template: str



class IfElseNode(BaseNode):



    type: Literal["if-else"]



    logical_operator: Literal["and", "or"] = "and"



    branches: List[BranchCondition]







class QuestionClassifierNode(BaseNode):
    type: Literal["question-classifier"]
    query_variable: str # e.g. @{start.input}
    classes: List[Dict[str, str]] # [{"name": "Class A", "next_step": "step_x"}]

# --- 蓝图根对象 ---

class WorkflowBlueprint(BaseModel):
    name: str
    description: Optional[str] = ""
    nodes: List[Union[StartNode, EndNode, LLMNode, CodeNode, TemplateNode, IfElseNode, QuestionClassifierNode]]
