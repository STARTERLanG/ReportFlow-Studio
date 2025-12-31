from sqlmodel import Field, SQLModel


class AgentBase(SQLModel):
    name: str
    role: str
    prompt: str
    confidence: float = 1.0


class Agent(AgentBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    blueprint_id: int | None = Field(default=None, foreign_key="blueprint.id")


class TaskBase(SQLModel):
    field_name: str
    context_before: str | None = None
    context_after: str | None = None
    requirement: str | None = None


class Task(TaskBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    agent_id: int | None = Field(default=None, foreign_key="agent.id")
