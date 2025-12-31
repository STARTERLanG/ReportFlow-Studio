from pydantic import BaseModel


class GenerationTask(BaseModel):
    task_name: str
    description: str
    requirements: str | None = None
    source_text_snippet: str | None = None


class TemplateParseResponse(BaseModel):
    filename: str
    tasks: list[GenerationTask]
    total_tasks: int
