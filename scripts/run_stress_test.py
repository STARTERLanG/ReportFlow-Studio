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
    print("🚀 正在执行 Agent 压力测试：[信贷风险自动化预警] 高级工作流生成...")
    service = YamlAgentService()

    # 使用精心设计的压力测试提问
    request = """
    任务：设计一个“信贷风险自动化预警”高级工作流

    需求详情：
    1. 输入节点：接收一段非结构化的企业近半年经营动态描述（OCR 提取文本）。
    2. 数据清洗与提取：
       - 使用第一个 LLM 节点提取关键事件（如：法人变更、诉讼、大额订单、停产等）。
       - 使用第二个 LLM 节点对文本进行降噪，去除 OCR 的乱码和无关的形容词。
    3. 逻辑判断：
       - 增加一个 条件分支 (If-Else)：
         - 路径 A：如果识别到“诉讼”或“停产”等重大风险词汇，进入“风险穿透分析”节点。
         - 路径 B：如果仅有一般经营变动，进入“标准经营总结”节点。
    4. 深度加工：
       - 风险穿透路径：LLM 节点需要模拟“资深审查官”语气，分析潜在偿债风险。
       - 标准总结路径：LLM 节点模拟“客户经理”语气，总结经营亮点。
    5. 聚合与格式化：使用 Template (模板转换) 节点，将上述分析结果合并，并输出为符合银行内报规范的 Markdown 格式。
    6. 结构化输出：最后输出节点返回一个包含 risk_level (高/中/低) 和 summary 的 JSON。

    质量要求：
    - 描述全部使用专业中文。
    - 必须参考知识库中其他报告的专业、严谨风格。
    - 节点连接逻辑必须闭环，变量引用（如 {{#node_id.output#}}）必须准确。
    """

    try:
        yaml_content = await service.generate_yaml(request)

        output_path = "output/workflows/信贷预警分析.yml"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(yaml_content)

        print("✨ 生成成功！")
        print(f"文件位置: {os.path.abspath(output_path)}")
        print("-" * 30)
        print("生成结果预览：")
        print(yaml_content[:500] + "...")

    except Exception as e:
        print(f"❌ 生成失败: {e}")


if __name__ == "__main__":
    asyncio.run(main())
