import typer
import sys
from pathlib import Path

# 将项目根目录添加到 sys.path，确保在 scripts 目录下运行也能找到 src
root_path = Path(__file__).parent.parent
sys.path.append(str(root_path))

from backend.app.logger import logger, set_debug_mode
from backend.agents.memories.vector_store import RagService
from backend.app.utils.network import configure_network_settings

# 初始化网络配置 (绕过代理)
configure_network_settings()

app = typer.Typer(help="AnotherMe 知识库入库工具")


@app.command()
def main(
    directory: Path = typer.Argument(
        default=root_path / "knowledge_base",
        help="包含要索引的 .yml 工作流文件的目录。",
    ),
    rebuild: bool = typer.Option(
        False, "--rebuild", "-r", help="强制重建索引（清空旧数据）。"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="开启详细调试日志"),
):
    """
    [运维脚本] 将本地 YAML 工作流文件导入 Qdrant 向量数据库。
    """
    if verbose:
        set_debug_mode(True)
        logger.info("已开启详细调试模式")

    if not directory.exists():
        logger.error(f"目录不存在: {directory}")
        logger.info(f"请检查路径: {directory}")
        raise typer.Exit(code=1)

    logger.info(f"开始执行入库程序，目标目录: {directory}")

    try:
        service = RagService()
        service.index_directory(directory, rebuild=rebuild)
        logger.info("🎉 入库完成！现在你可以运行 main.py 进行生成了。")
    except Exception as e:
        logger.critical(f"入库失败: {e}")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
