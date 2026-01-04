import os
import shutil
from tempfile import NamedTemporaryFile

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.server.logger import logger
from app.server.schemas.template import TemplateParseResponse
from app.server.services.template_service import TemplateService

router = APIRouter(prefix="/templates", tags=["Templates"])
template_service = TemplateService()


@router.post("/parse", response_model=TemplateParseResponse)
async def parse_template(file: UploadFile = File(...)):
    """
    上传并智能解析 Word 样本文件，生成撰写任务列表。
    """
    if not file.filename.endswith(".docx"):
        raise HTTPException(status_code=400, detail="只支持 .docx 格式的 Word 文档")

    try:
        with NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name

        # 调用 AI 进行全量拆解 (返回 {'variables': [], 'tasks': []})
        result = template_service.parse_and_decompose(tmp_path)
        os.unlink(tmp_path)

        # 兼容处理：如果 service 返回的是旧版 list (极端异常情况)，做适配
        if isinstance(result, list):
            tasks = result
            variables = []
        else:
            tasks = result.get("tasks", [])
            variables = result.get("variables", [])

        return TemplateParseResponse(
            filename=file.filename,
            tasks=tasks,
            variables=variables,
            total_tasks=len(tasks),
        )

    except Exception as e:
        logger.exception(f"解析模板失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"模板解析过程中发生错误: {str(e)}") from e
