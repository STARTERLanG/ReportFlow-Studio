import os
from dataclasses import dataclass

from dotenv import load_dotenv

# 加载环境变量，允许覆盖
load_dotenv(override=True)


@dataclass
class QdrantConfig:
    url: str
    api_key: str | None
    collection_name: str = "dify_workflows"


@dataclass
class LLMConfig:
    model_name: str
    base_url: str | None
    api_key: str | None


@dataclass
class DBConfig:
    host: str
    port: int
    user: str
    password: str
    database: str

    @property
    def url(self) -> str:
        # 使用 pymysql 驱动
        return f"mysql+pymysql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"


@dataclass
class EmbeddingConfig:
    provider: str
    model_name: str
    api_key: str | None


class Settings:
    def __init__(self):
        # Qdrant 配置
        q_url = os.getenv("QDRANT_URL", ":memory:")
        q_key = os.getenv("QDRANT_API_KEY")
        if not q_key:
            q_key = None
        self.qdrant = QdrantConfig(url=q_url, api_key=q_key)

        # LLM 配置
        l_model = os.getenv("LLM_MODEL_NAME", "gpt-4o")
        l_base = os.getenv("OPENAI_BASE_URL")
        l_key = os.getenv("OPENAI_API_KEY")
        self.llm = LLMConfig(model_name=l_model, base_url=l_base, api_key=l_key)

        # 数据库配置
        db_host = os.getenv("DB_HOST", "localhost")
        db_port = int(os.getenv("DB_PORT", "3306"))
        db_user = os.getenv("DB_USER", "root")
        db_pass = os.getenv("DB_PASSWORD", "")
        db_name = os.getenv("DB_NAME", "reportflow")
        self.db = DBConfig(host=db_host, port=db_port, user=db_user, password=db_pass, database=db_name)

        # Embedding 配置
        e_provider = os.getenv("EMBEDDING_PROVIDER", "openai").lower()
        e_model = os.getenv("EMBEDDING_MODEL_NAME")
        # 阿里云使用 DASHSCOPE_API_KEY，如果没配则复用 OPENAI_API_KEY
        ds_key = os.getenv("DASHSCOPE_API_KEY") or l_key
        self.embedding = EmbeddingConfig(
            provider=e_provider,
            model_name=e_model or ("text-embedding-v1" if e_provider == "dashscope" else "text-embedding-3-small"),
            api_key=ds_key,
        )


# 单例配置对象
settings = Settings()
