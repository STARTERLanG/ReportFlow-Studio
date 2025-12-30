from typing import Optional
from sqlmodel import SQLModel, Field


class AgentBase(SQLModel):
    name: str
    role: str
    prompt: str
    confidence: float = 1.0


class Agent(AgentBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    blueprint_id: Optional[int] = Field(default=None, foreign_key="blueprint.id")


class TaskBase(SQLModel):
    field_name: str
    context_before: Optional[str] = None
    context_after: Optional[str] = None
    requirement: Optional[str] = None


class Task(TaskBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    agent_id: Optional[int] = Field(default=None, foreign_key="agent.id")
