from pydantic import BaseModel
from typing import List, Optional


class GenerationTask(BaseModel):
    task_name: str
    description: str
    requirements: Optional[str] = None
    source_text_snippet: Optional[str] = None


class TemplateParseResponse(BaseModel):
    filename: str
    tasks: List[GenerationTask]
    total_tasks: int
