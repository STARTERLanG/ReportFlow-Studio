import asyncio
import os
import sys

sys.path.append(os.getcwd())

from backend.agents.workflows.yaml_generator import YamlAgentService
from backend.app.utils.network import configure_network_settings

configure_network_settings()

async def main():
    print("🚀 执行企业画像分析工作流生成测试...")
    service = YamlAgentService()

    request = """
    任务：设计一个“企业全维画像分析”工作流。

    结构要求：
    1. **线性预处理**：
       - Start: 接收用户输入的公司名。
       - LLM (extract_entity): 标准化提取公司主体名称。
       - Code (mock_api): 模拟调用天眼查 API，返回公司的基本信息 JSON (包含 industry, products, location 等字段)。
    
    2. **并行分支处理 (重点)**：
       - 从 Code (mock_api) 节点后开始分叉，进入两条**并行**路径：
       - **上方分支 (Micro)**: 
         - LLM (analyze_products): 分析主营产品及模式。
         - LLM (analyze_operations): 串行连接，分析经营场所及运营概况。
       - **下方分支 (Macro)**:
         - LLM (extract_industry): 提取行业关键词。
         - LLM (analyze_industry): 串行连接，进行行业趋势分析。

    3. **结果聚合**：
       - Template (report): 作为一个汇聚节点，同时接收来自 `analyze_products`、`analyze_operations` 和 `analyze_industry` 的输出。
       - End: 输出最终报告。

    核心逻辑：
    - 请使用 `next_step: ["node_a", "node_b"]` 语法来实现从 API 节点到两个分支的并行连接。
    - 聚合节点需要引用多条路径的变量。
    """

    try:
        yaml_content = await service.generate_yaml(request)
        output_path = "output/workflows/企业全维画像.yml"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(yaml_content)
        print("✨ 生成成功！")
        print(yaml_content[:500] + "...")
    except Exception as e:
        print(f"❌ 失败: {e}")

if __name__ == "__main__":
    asyncio.run(main())
