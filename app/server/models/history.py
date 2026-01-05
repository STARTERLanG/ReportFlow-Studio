from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Column, Text
from sqlmodel import Field, SQLModel


class WorkflowHistory(SQLModel, table=True):
    __tablename__ = "workflow_history"

    id: int | None = Field(default=None, primary_key=True)

    # 输入信息
    user_request: str = Field(sa_column=Column(Text))
    context: str | None = Field(default=None, sa_column=Column(Text))

    # 类别：'workflow' 或 'template-parse'
    category: str = Field(default="workflow", index=True)

    # 结构化蓝图 或 任务列表 (JSON 格式存储)
    blueprint: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))

    # 最终生成的 Dify YAML
    final_yaml: str = Field(sa_column=Column(Text))

    # 状态与耗时
    status: str = Field(default="success")
    error_msg: str | None = Field(default=None, sa_column=Column(Text))

    # 元数据
    created_at: datetime = Field(default_factory=datetime.now)

    # 扩展字段：记录使用的模型和版本
    model_name: str | None = None
    version: str = "0.1.0"
