import os
import shutil
import zipfile
import yaml
from typing import List, Dict
from fastapi import APIRouter, UploadFile, File, HTTPException
from backend.app.logger import logger
from tempfile import NamedTemporaryFile

router = APIRouter(prefix="/files", tags=["Files"])


@router.post("/upload/datasource")
async def upload_datasource(file: UploadFile = File(...)) -> List[Dict]:
    """
    上传并解析资料包，提取文件名及其内容摘要。
    """
    if not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="请上传 ZIP 格式的资料包")

    try:
        with NamedTemporaryFile(delete=False, suffix=".zip") as tmp_zip:
            shutil.copyfileobj(file.file, tmp_zip)
            tmp_zip_path = tmp_zip.name

        file_data = []
        with zipfile.ZipFile(tmp_zip_path, "r") as zip_ref:
            for info in zip_ref.infolist():
                if info.filename.startswith("__MACOSX") or info.filename.endswith("/"):
                    continue

                fname = os.path.basename(info.filename)
                if not fname:
                    continue

                # 提取内容摘要 (前 1000 字符)
                content_snippet = ""
                try:
                    with zip_ref.open(info.filename) as f:
                        # 尝试读取文本内容
                        raw_content = f.read(2000).decode("utf-8", errors="ignore")
                        # 如果是 YML，尝试美化或提取关键 Key
                        if fname.endswith((".yml", ".yaml")):
                            try:
                                data = yaml.safe_load(raw_content)
                                content_snippet = str(data)[:1000]
                            except:
                                content_snippet = raw_content[:1000]
                        else:
                            content_snippet = raw_content[:1000]
                except Exception as e:
                    content_snippet = f"[无法读取内容: {str(e)}]"

                file_data.append({"name": fname, "snippet": content_snippet})

        os.unlink(tmp_zip_path)
        logger.info(f"成功提取 {len(file_data)} 个文件的语义概要")
        return file_data

    except Exception as e:
        logger.exception(f"资料包处理失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")
