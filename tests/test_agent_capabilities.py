import pytest
import yaml
import asyncio
from backend.agents.workflows.yaml_generator import YamlAgentService
from backend.app.config import settings

# 检查是否有 API Key，如果没有则跳过测试
# 这是一个简单的检查，防止在没有配置环境的 CI/CD 中报错
has_creds = settings.llm.api_key and len(settings.llm.api_key) > 5


@pytest.mark.skipif(not has_creds, reason="需要配置真实 LLM API Key 才能运行此集成测试")
def test_yaml_workflow_generation_capability():
    """
    【能力验证测试】YamlAgentService 工作流生成能力
    (Wrapper for async test)
    """

    async def _run_test():
        # 1. 初始化服务
        print("\n[初始化] 正在启动 YamlAgentService...")
        service = YamlAgentService()

        # 2. 准备测试数据
        user_request = "设计一个简单的英汉翻译助手。用户输入英文，它直接输出中文翻译，不要有其他废话。"
        context = "该工作流将部署在 Dify 平台上，使用 gpt-3.5-turbo 模型。"

        print(f"[输入] 用户需求: {user_request}")

        try:
            # 3. 执行生成
            print(
                "[执行] 正在运行 Agent Workflow (Planner -> Architect -> PromptExpert -> Assembler)..."
            )
            yaml_content = await service.generate_yaml(user_request, context)

            print(f"[输出] 生成结果长度: {len(yaml_content)} 字符")

            # --- 验证环节 ---
            assert yaml_content is not None
            assert len(yaml_content) > 0, "Agent 生成了空内容"

            if "[PROMPT_FOR_TASK:" in yaml_content:
                print("!!! 检测到残留占位符，输出片段:")
                print(yaml_content[:500] + "...")
                pytest.fail(
                    "Agent 未能完成 Prompt 生成任务，YAML 中仍包含 '[PROMPT_FOR_TASK:' 占位符"
                )

            try:
                yaml_obj = yaml.safe_load(yaml_content)
                assert isinstance(yaml_obj, (dict, list)), "YAML 解析后应为字典或列表"
            except yaml.YAMLError as e:
                pytest.fail(f"生成的格式不是合法的 YAML: {e}")

            is_translation_related = (
                "translat" in yaml_content.lower()
                or "翻译" in yaml_content
                or "chinese" in yaml_content.lower()
            )
            assert is_translation_related, "生成的 YAML 中未检测到与'翻译'相关的关键词"

            print("\n✅ [测试通过] YamlAgentService 能力达标！")

        except Exception as e:
            print(f"\n❌ [测试失败] 执行过程中发生异常: {e}")
            raise e

    asyncio.run(_run_test())
