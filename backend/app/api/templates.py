import os
import shutil
from fastapi import APIRouter, UploadFile, File, HTTPException
from backend.app.services.template_service import TemplateService
from backend.app.schemas.template import TemplateParseResponse
from backend.app.logger import logger
from tempfile import NamedTemporaryFile

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

        # 调用 AI 进行全量拆解
        tasks = template_service.parse_and_decompose(tmp_path)
        os.unlink(tmp_path)

        return TemplateParseResponse(
            filename=file.filename, tasks=tasks, total_tasks=len(tasks)
        )

    except Exception as e:
        logger.exception(f"解析模板失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"模板解析过程中发生错误: {str(e)}")
