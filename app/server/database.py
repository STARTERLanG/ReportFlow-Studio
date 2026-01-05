from sqlalchemy import create_engine
from sqlmodel import Session, SQLModel

from app.server.config import settings

# 创建数据库引擎
# 设置连接超时为 5 秒，避免应用启动时卡死
engine = create_engine(
    settings.db.url,
    pool_recycle=3600,
    pool_pre_ping=True,
    echo=False,
    connect_args={"connect_timeout": 5} if "mysql" in settings.db.url else {}
)


def init_db():
    """初始化数据库表"""
    try:
        # 这里导入模型是为了确保 SQLModel.metadata 包含所有表定义
        from app.server.models.history import WorkflowHistory  # noqa: F401
        
        # 尝试连接一下，看是否通畅
        with engine.connect() as conn:
            pass
            
        SQLModel.metadata.create_all(engine)
    except Exception as e:
        from app.server.logger import logger
        logger.error(f"MySQL 数据库连接失败（请检查 .env 配置或数据库服务是否启动）: {e}")
        # 这里不再向外抛出异常，允许应用以“无数据库模式”启动


def get_session():
    """获取数据库会话"""
    with Session(engine) as session:
        yield session
