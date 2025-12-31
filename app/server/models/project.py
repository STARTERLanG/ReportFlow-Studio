from datetime import datetime

from sqlmodel import Field, Relationship, SQLModel


class ProjectBase(SQLModel):
    name: str
    description: str | None = None
    template_path: str | None = None
    source_files_path: str | None = None


class Project(ProjectBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    blueprints: list["Blueprint"] = Relationship(back_populates="project")


class BlueprintBase(SQLModel):
    name: str
    graph_data: str  # JSON string of the ReactFlow graph
    status: str = "draft"  # draft, confirmed, generated
    version: int = 1


class Blueprint(BlueprintBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    project: Project = Relationship(back_populates="blueprints")
