import asyncio
import os
import sys

sys.path.append(os.getcwd())

from backend.agents.workflows.yaml_generator import YamlAgentService
from backend.app.utils.network import configure_network_settings

# 初始化网络配置，确保绕过代理

configure_network_settings()


async def main():
    print("🚀 启动纯净 YAML 生成器 (YamlAgentService)...")
    service = YamlAgentService()

    # 现在只需要传入需求，平台和模型信息已在 System Prompt 中内置
    request = "设计一个尽调报告中对`主营产品、经营模式、行业前景`提取和生成总结的 YAML 工作流，输入源是各文件的OCR文本，各节点单独对信息做单独的分析，例如主营产品节点、经营模式节点等等，yml的输出是一个json"

    try:
        yaml_content = await service.generate_yaml(request)

        output_path = "output/workflows/经营分析.yml"
        # 确保目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(yaml_content)

        print("✨ 生成完成！")
        print(f"文件位置: {os.path.abspath(output_path)}")
        print("-" * 30)
        print(yaml_content[:300] + "...")

    except Exception as e:
        print(f"❌ 生成失败: {e}")


if __name__ == "__main__":
    asyncio.run(main())
