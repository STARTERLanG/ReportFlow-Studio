from pathlib import Path
import warnings

import yaml
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_core.documents import Document

# Embeddings
from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams

# 引入新模块
from backend.app.config import settings
from backend.app.logger import logger
from backend.app.utils.file_io import load_all_yamls


class RagService:
    def __init__(self):
        """
        初始化 RAG 服务 (Qdrant + Embeddings)。
        """
        logger.info("正在初始化 RAG 服务...")

        # 1. 初始化 Qdrant 客户端
        logger.debug(f"连接 Qdrant: {settings.qdrant.url}")

        # 忽略不安全连接的警告（仅在本地开发时使用）
        if settings.qdrant.url.startswith("http://"):
            warnings.filterwarnings("ignore", message="Api key is used with an insecure connection.")
        

        self.client = QdrantClient(
            location=settings.qdrant.url,
            api_key=settings.qdrant.api_key,
            check_compatibility=False,
        )

        # 2. 初始化 Embeddings
        self._init_embeddings()

        # 3. 确保集合存在
        self._ensure_collection()

        # 4. 初始化 VectorStore
        self.vector_store = QdrantVectorStore(
            client=self.client,
            collection_name=settings.qdrant.collection_name,
            embedding=self.embedding_function,
        )
        logger.info("RAG 服务初始化完成")

    def _init_embeddings(self):
        """根据配置初始化 Embedding 模型。"""
        cfg = settings.embedding
        logger.debug(f"初始化 Embeddings: Provider={cfg.provider}, Model={cfg.model_name}")

        if cfg.provider == "dashscope":
            self.embedding_function = DashScopeEmbeddings(model=cfg.model_name, dashscope_api_key=cfg.api_key)
        else:
            self.embedding_function = OpenAIEmbeddings(
                model=cfg.model_name,
                api_key=cfg.api_key,
                base_url=settings.llm.base_url,  # 允许 Embedding 也使用相同的代理 Base URL
            )

    def _ensure_collection(self):
        """检查并创建 Qdrant 集合。"""
        name = settings.qdrant.collection_name
        if not self.client.collection_exists(name):
            logger.info(f"集合 '{name}' 不存在，正在创建...")
            try:
                # 获取维度
                dummy = self.embedding_function.embed_query("test")
                dim = len(dummy)
                logger.info(f"检测到向量维度: {dim}")

                self.client.create_collection(
                    collection_name=name,
                    vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
                )
                logger.info("集合创建成功")
            except Exception as e:
                logger.error(f"创建集合失败: {e}")
                # 不抛出异常，允许后续可能的重试或只读操作

    def recreate_index(self):
        """重建索引（删除旧集合）。"""
        name = settings.qdrant.collection_name
        logger.warning(f"正在删除集合: {name}")
        try:
            self.client.delete_collection(name)
        except Exception as e:
            logger.warning(f"删除集合时出错 (可能不存在): {e}")

        self._ensure_collection()

    def index_directory(self, directory: Path, rebuild: bool = False):
        """
        读取目录并构建索引。
        """
        if rebuild:
            self.recreate_index()

        data = load_all_yamls(directory)
        if not data:
            logger.warning("未找到可索引的数据")
            return

        documents = []
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=4000, chunk_overlap=400, separators=["\n\n", "\n", " ", ""]
        )

        for item in data:
            filename = item.get("__filename__", "unknown")
            description = item.get("description", "")

            # 清理元数据
            item_copy = item.copy()
            item_copy.pop("__filename__", None)

            yaml_content = yaml.dump(item_copy, allow_unicode=True, sort_keys=False)
            full_content = f"文件名: {filename}\n描述: {description}\n\n内容:\n{yaml_content}"

            raw_doc = Document(
                page_content=full_content,
                metadata={"source": filename, "description": description or "无描述"},
            )

            chunks = text_splitter.split_documents([raw_doc])
            documents.extend(chunks)

        if documents:
            logger.info(f"正在索引 {len(documents)} 个文档片段...")
            batch_size = 10
            for i in range(0, len(documents), batch_size):
                batch = documents[i : i + batch_size]
                self.vector_store.add_documents(batch)
            logger.info("索引构建完成")

    def search(self, query: str, k: int = 3):
        """执行相似度搜索。"""
        return self.vector_store.similarity_search(query, k=k)
