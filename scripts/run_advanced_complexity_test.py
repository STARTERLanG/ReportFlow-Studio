import asyncio
import os
import sys

# 确保能找到 backend 模块
sys.path.append(os.getcwd())

from backend.agents.workflows.yaml_generator import YamlAgentService
from backend.app.utils.network import configure_network_settings

# 初始化网络配置
configure_network_settings()


async def main():
    print("🚀 正在执行 Agent 极高复杂度测试：[企业授信多维综合评价] 工作流生成...")
    service = YamlAgentService()

    # 设计极高复杂度的需求
    request = """
    任务：设计一个“企业授信多维综合评价”高级工作流

    详细需求：
    1. 输入节点：接收三类信息：企业财务报表文本、银行近三个月流水描述、法律诉讼记录。
    2. 并行分析阶段：
       - 节点 A (LLM)：财务维度分析。提取资产负债率、利润增长率，并给出财务健康度评价。
       - 节点 B (LLM)：经营流水分析。识别是否存在大额异常资金往来，并计算平均月流。
       - 节点 C (LLM)：合规性分析。识别是否存在待执行案件或严重失信行为。
    3. 综合评估节点 (LLM)：
       - 该节点必须同时引用 A、B、C 三个节点的输出。
       - 模拟“信贷审批委员会主席”语气，给出综合评分（0-100）。
    4. 分支逻辑 (If-Else)：
       - 路径 1 (评分 >= 60)：进入“自动授信额度测算”节点（LLM），计算推荐额度。
       - 路径 2 (评分 < 60)：直接进入“风险退回建议”节点（Template），整理退回理由。
    5. 汇总输出：
       - 使用一个 End 节点，返回包含最终结论、评分、和建议额度（如果有）的结构化 JSON。

    约束：
    - 所有节点 ID 必须符合语义化规范（如 n1_start, n2_fin_analysis 等）。
    - 界面描述和 Prompt 必须使用专业中文。
    - 严禁出现断开的连线。
    """

    try:
        yaml_content = await service.generate_yaml(request)

        output_path = "output/workflows/企业授信综合评价.yml"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(yaml_content)

        print("✨ 生成成功！")
        print(f"文件位置: {os.path.abspath(output_path)}")
        print("-" * 30)
        print("连线逻辑检查：")
        if "edges:" in yaml_content:
            edge_count = yaml_content.count("- data:")
            print(f"检测到约 {edge_count} 条连线")

    except Exception as e:
        print(f"❌ 生成失败: {e}")


if __name__ == "__main__":
    asyncio.run(main())
