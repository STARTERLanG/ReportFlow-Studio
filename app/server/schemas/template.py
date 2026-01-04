from pydantic import BaseModel


class GenerationTask(BaseModel):
    task_name: str
    type: str  # extraction | generation
    description: str
    requirements: str | None = None
    # 针对提取任务：需要提取的字段名列表
    fields: list[str] = []
    # 针对生成任务：模板中的参考范文/原文
    reference_content: str | None = None


class TemplateVariable(BaseModel):
    name: str
    description: str | None = None
    type: str = "string"  # string, number, select


class TemplateParseResponse(BaseModel):
    filename: str
    tasks: list[GenerationTask]
    variables: list[TemplateVariable] = []
    total_tasks: int
