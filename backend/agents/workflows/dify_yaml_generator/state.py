from typing import TypedDict


class GraphState(TypedDict):
    """定义工作流的状态结构"""

    user_request: str
    context: str
    yaml_example: str
    plan: list[str]
    yaml_skeleton: str  # 存储 Blueprint JSON 字符串
    generated_prompts: list[dict[str, str]]
    final_yaml: str
    validation_errors: list[str]
    retry_count: int
