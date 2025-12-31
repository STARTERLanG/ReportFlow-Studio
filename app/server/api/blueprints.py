from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.server.schemas.flow import BlueprintResponse
from app.server.services.blueprint_service import BlueprintService

router = APIRouter(prefix="/blueprints", tags=["Blueprints"])
blueprint_service = BlueprintService()


class BlueprintRequest(BaseModel):
    tasks: list[dict]
    data_sources: list[dict[str, Any]] | list[str]


@router.post("/generate", response_model=BlueprintResponse)
async def generate_blueprint(request: BlueprintRequest):
    """
    基于任务和资料库生成 AI 蓝图。
    """
    try:
        graph = await blueprint_service.generate_graph(request.tasks, request.data_sources)
        return graph
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
