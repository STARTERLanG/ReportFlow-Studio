import asyncio
import time
from pathlib import Path

import typer

from agents.workflows.dify_yaml_generator import YamlAgentService
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
    ReportFlow Studio CLI - 基于 Deep Agents 的 Dify 工作流生成器。
    """
    if verbose:
        set_debug_mode(True)
        logger.info("已开启详细调试模式")


@app.command()
def generate(
    query: str = typer.Argument(..., help="用自然语言描述你想要的工作流。"),
    output: Path | None = typer.Option(None, "--output", "-o", help="输出文件路径。默认使用时间戳命名。"),
):
    """
    生成 Dify 工作流。
    """
    logger.info(f"收到生成请求: '{query}'")

    async def run_async():
        try:
            # 1. 实例化新版服务
            service = YamlAgentService()

            # 2. 调用生成 (RAG 逻辑已封装在服务内部)
            workflow_yaml = await service.generate_yaml(user_request=query)

            # 3. 保存
            output_path = output
            if output_path is None:
                timestamp = int(time.time())
                safe_query = "".join([c if c.isalnum() else "_" for c in query[:20]])
                filename = f"generated_{safe_query}_{timestamp}.yml"
                output_path = Path(filename)

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(workflow_yaml)

            logger.info(f"工作流生成成功并保存至: {output_path}")

        except Exception as e:
            logger.critical(f"生成流程失败: {e}")
            raise typer.Exit(code=1) from e

    asyncio.run(run_async())


if __name__ == "__main__":
    app()
