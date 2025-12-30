from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from backend.app.services.blueprint_service import BlueprintService
from backend.app.schemas.blueprint import BlueprintResponse
from pydantic import BaseModel

router = APIRouter(prefix="/blueprints", tags=["Blueprints"])
blueprint_service = BlueprintService()


class BlueprintRequest(BaseModel):
    tasks: List[Dict]
    data_sources: List[Dict[str, Any]] | List[str]


@router.post("/generate", response_model=BlueprintResponse)
async def generate_blueprint(request: BlueprintRequest):
    """
    基于任务和资料库生成 AI 蓝图。
    """
    try:
        graph = await blueprint_service.generate_graph(
            request.tasks, request.data_sources
        )
        return graph
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
