from typing import Any

from sqlmodel import JSON, Column, Field, SQLModel


class SystemSetting(SQLModel, table=True):
    __tablename__ = "system_settings"

    key: str = Field(primary_key=True)
    value: Any = Field(sa_column=Column(JSON))
    description: str | None = None
    category: str = "general"  # general, llm, rag
