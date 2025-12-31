import asyncio
import os
import sys

# 添加项目根目录到 sys.path
sys.path.append(os.getcwd())

from backend.agents.workflows.dify_yaml_generator import YamlAgentService
from backend.app.logger import logger

# 确保在测试环境中看到日志
logger.setLevel("INFO")


async def main():
    service = YamlAgentService()

    # 模拟用户请求
    user_request = "创建一个工作流，首先使用HTTP请求节点从 'https://api.example.com/data' 获取数据（GET方法），然后将获取的数据传给一个LLM节点。LLM节点使用通义千问模型（tongyi）对数据进行摘要总结。"

    # 显式注入依赖声明的要求作为上下文 (通常这是 RAG 的结果)
    context = """
    【系统要求】
    1. 必须使用 `langgenius/tongyi` 插件。
    2. 依赖的具体标识符为：`marketplace_plugin_unique_identifier: langgenius/tongyi:0.0.56@42a5fb7bc09b2f14f9d19f0ac79bec42c3c50dba07a52bf1b6d3abcd6906c739`。
    3. LLM 节点的 model 配置应使用 `provider: langgenius/tongyi/tongyi`, `name: qwen3-30b-a3b-instruct-2507`。
    4. HTTP 节点的超时时间设置为 30 秒。
    """

    print(f"User Request: {user_request}")
    print("生成 YAML 中...")

    try:
        yaml_content = await service.generate_yaml(user_request, context)

        # 将结果写入文件，避免控制台编码问题
        output_file = "output/debug/generated_tongyi_http.yml"
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(yaml_content)

        print(f"\nYAML 已生成并写入: {output_file}")

        # 验证逻辑 (简单检查字符串存在性)
        issues = []

        # 1. 验证 dependencies
        if "dependencies:" not in yaml_content:
            issues.append("MISSING: 'dependencies' section.")
        elif "langgenius/tongyi:0.0.56" not in yaml_content:
            issues.append("MISSING: Specific tongyi plugin identifier.")

        # 2. 验证 LLM model config
        if "provider: langgenius/tongyi/tongyi" not in yaml_content:
            issues.append("MISSING: Correct LLM provider 'langgenius/tongyi/tongyi'.")
        if "name: qwen3-30b-a3b-instruct-2507" not in yaml_content:
            issues.append("MISSING: Correct LLM model name 'qwen3-30b-a3b-instruct-2507'.")

        # 3. 验证 HTTP Node
        if "type: http-request" not in yaml_content:
            issues.append("MISSING: 'http-request' node type.")

        if issues:
            print("Validation Failed:")
            for issue in issues:
                print(f"  - {issue}")
        else:
            print("Validation Passed: YAML contains all required elements.")

    except Exception as e:
        # 简单的错误打印，避免复杂字符
        print(f"\nError during generation: {str(e)}")


if __name__ == "__main__":
    asyncio.run(main())
