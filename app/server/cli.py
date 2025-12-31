import time
from pathlib import Path

import typer

from agents.core.orchestrator import AgentService
from agents.memories.vector_store import RagService
from app.server.logger import logger, set_debug_mode
from app.server.utils.network import configure_network_settings

# 初始化网络配置
configure_network_settings()

app = typer.Typer(help="Dify 工作流架构师智能体 (Enterprise Edition)")


@app.callback()
def global_config(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="开启详细调试日志"),
):
    """
    AnotherMe CLI - 基于 Deep Agents 的 Dify 工作流生成器。
    """
    if verbose:
        set_debug_mode(True)
        logger.info("已开启详细调试模式")


@app.command()
def generate(
    query: str = typer.Argument(..., help="用自然语言描述你想要的工作流。"),
    output: Path | None = typer.Option(None, "--output", "-o", help="输出文件路径。默认使用时间戳命名。"),
    k: int = typer.Option(3, "--k", "-k", help="检索参考案例的数量。"),
):
    """
    生成 Dify 工作流。
    """
    logger.info(f"收到生成请求: '{query}'")

    try:
        # 1. 检索 (只读操作)
        rag_service = RagService()
        references = rag_service.search(query, k=k)

        if not references:
            logger.warning("未找到相关参考案例，生成结果可能偏差较大")
            logger.info("提示：如果你还没导入数据，请先运行 'python ingest.py'。")
        else:
            logger.info(f"找到 {len(references)} 个参考案例:")
            for i, ref in enumerate(references):
                logger.info(f"  [{i + 1}] {ref.metadata.get('source', 'Unknown')}")

        # 2. 生成
        agent_service = AgentService()
        workflow_yaml = agent_service.generate_workflow(query, references)

        # 3. 保存
        if output is None:
            timestamp = int(time.time())
            safe_query = "".join([c if c.isalnum() else "_" for c in query[:20]])
            filename = f"generated_{safe_query}_{timestamp}.yml"
            output = Path(filename)

        with open(output, "w", encoding="utf-8") as f:
            f.write(workflow_yaml)

        logger.info(f"工作流生成成功并保存至: {output}")

    except Exception as e:
        logger.critical(f"生成流程失败: {e}")
        raise typer.Exit(code=1) from e


if __name__ == "__main__":
    app()
