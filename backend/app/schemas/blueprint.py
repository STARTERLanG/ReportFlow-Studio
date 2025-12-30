from pydantic import BaseModel
from typing import List, Dict, Any, Optional


class FlowNode(BaseModel):
    id: str
    type: str  # 'input', 'agent', 'output'
    data: Dict[str, Any]
    position: Dict[str, float]
    style: Optional[Dict[str, Any]] = None


class FlowEdge(BaseModel):
    id: str
    source: str
    target: str
    animated: Optional[bool] = True
    label: Optional[str] = None


class BlueprintResponse(BaseModel):
    nodes: List[FlowNode]
    edges: List[FlowEdge]
    confidence_scores: Optional[Dict[str, float]] = {}
    error: Optional[str] = None
