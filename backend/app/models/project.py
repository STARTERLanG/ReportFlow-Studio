from datetime import datetime
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship


class ProjectBase(SQLModel):
    name: str
    description: Optional[str] = None
    template_path: Optional[str] = None
    source_files_path: Optional[str] = None


class Project(ProjectBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    blueprints: List["Blueprint"] = Relationship(back_populates="project")


class BlueprintBase(SQLModel):
    name: str
    graph_data: str  # JSON string of the ReactFlow graph
    status: str = "draft"  # draft, confirmed, generated
    version: int = 1


class Blueprint(BlueprintBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    project: Project = Relationship(back_populates="blueprints")
