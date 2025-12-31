import os

import pytest
from fastapi.testclient import TestClient

from app.server.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "3.0.0"}


def test_parse_template_integration():
    """
    集成测试：上传真实 Word 文档并调用 LLM 解析。
    注意：这需要配置好 .env 且消耗 Token。
    """
    file_path = "docs/报告模板参考.docx"

    if not os.path.exists(file_path):
        pytest.skip(f"测试文件不存在: {file_path}")

    with open(file_path, "rb") as f:
        # 模拟文件上传
        response = client.post(
            "/templates/parse",
            files={
                "file": (
                    "report_template.docx",
                    f,
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )

    assert response.status_code == 200
    data = response.json()

    # 验证响应结构
    assert "filename" in data
    assert "tasks" in data
    assert "total_tasks" in data

    # 验证至少解析出了任务（AI 应该能识别出内容）
    assert data["total_tasks"] > 0
    assert len(data["tasks"]) > 0

    # 验证任务字段
    first_task = data["tasks"][0]
    assert "task_name" in first_task
    assert "description" in first_task
    assert "requirements" in first_task


def test_invalid_file_type():
    """
    测试上传非 docx 文件。
    """
    response = client.post("/templates/parse", files={"file": ("test.txt", b"dummy content", "text/plain")})
    assert response.status_code == 400
    assert "只支持 .docx" in response.json()["detail"]
