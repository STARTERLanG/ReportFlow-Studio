import os
import sys

from nicegui import app, ui

# 确保能找到根目录下的模块
sys.path.append(os.getcwd())

# 导入原有路由
from app.server.api.blueprints import router as blueprints_router
from app.server.api.files import router as files_router
from app.server.api.templates import router as templates_router
from app.server.api.yaml import router as yaml_router
from app.server.database import init_db
from app.server.logger import setup_logger
from app.server.ui.layout import render_home_page
from app.server.ui.settings_page import render_settings_page
from app.server.ui.template_page import render_template_page
from app.server.ui.yaml_gen_page import render_yaml_generator_page

# 初始化日志
setup_logger()

# 初始化数据库
try:
    init_db()
except Exception as e:
    from app.server.logger import logger

    logger.error(f"Database initialization failed: {e}")

# --- 挂载 FastAPI 路由 ---
app.include_router(templates_router, prefix="/api/v1")
app.include_router(blueprints_router, prefix="/api/v1")
app.include_router(files_router, prefix="/api/v1")
app.include_router(yaml_router, prefix="/api/v1")


# --- 页面路由挂载 ---


@ui.page("/")
def home_page():
    render_home_page()


@ui.page("/generator")
def generator_page():
    render_yaml_generator_page()


@ui.page("/template-parser")
def template_page():
    render_template_page()


@ui.page("/settings")
def settings_page():
    render_settings_page()


# 启动配置
if __name__ in {"__main__", "__mp_main__"}:
    ui.run(
        title="ReportFlow Studio",
        favicon="🤖",
        port=8000,
        reload=True,
        uvicorn_logging_level="info",
    )
