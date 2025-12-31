from typing import Any

from pydantic import BaseModel


class FlowNode(BaseModel):
    id: str
    type: str  # 'input', 'agent', 'output'
    data: dict[str, Any]
    position: dict[str, float]
    style: dict[str, Any] | None = None


class FlowEdge(BaseModel):
    id: str
    source: str
    target: str
    animated: bool | None = True
    label: str | None = None


class BlueprintResponse(BaseModel):
    nodes: list[FlowNode]
    edges: list[FlowEdge]
    confidence_scores: dict[str, float] | None = {}
    error: str | None = None
