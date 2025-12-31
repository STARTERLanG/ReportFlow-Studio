from pathlib import Path
from typing import Any

import yaml

from backend.app.logger import logger


def load_yaml(file_path: Path) -> dict[str, Any]:
    """加载单个 YAML 文件。"""
    try:
        with open(file_path, encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"读取 YAML 文件失败: {file_path}, 错误: {e}")
        return {}


def load_all_yamls(directory: Path) -> list[dict[str, Any]]:
    """加载目录下所有的 .yml/.yaml 文件。"""
    if not directory.exists():
        logger.warning(f"目录不存在: {directory}")
        return []

    files = list(directory.glob("*.yml")) + list(directory.glob("*.yaml"))
    results = []

    for file in files:
        content = load_yaml(file)
        if isinstance(content, dict) and content:
            # 附加文件名作为元数据
            content["__filename__"] = file.name
            results.append(content)

    logger.info(f"从 {directory} 加载了 {len(results)} 个 YAML 文件")
    return results
