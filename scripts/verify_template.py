import json

from backend.app.services.template_service import TemplateService


def verify_template():
    file_path = "docs/报告模板参考.docx"
    service = TemplateService()

    print(f"正在分析模板: {file_path} ...")
    tasks = service.parse_and_decompose(file_path)

    print(f"\nAI 成功拆解出 {len(tasks)} 个撰写任务:")
    print("=" * 60)

    for i, task in enumerate(tasks):
        print(f"Task {i + 1}: {task.get('task_name', 'Unknown')}")
        print(f"  Desc: {task.get('description', '')[:60]}...")
        print(f"  Reqs: {task.get('requirements', '')[:60]}...")
        print("-" * 60)

    # 可选：保存到文件查看完整 JSON
    with open("decomposed_tasks.json", "w", encoding="utf-8") as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)
    print("完整结果已保存至 decomposed_tasks.json")


if __name__ == "__main__":
    verify_template()
