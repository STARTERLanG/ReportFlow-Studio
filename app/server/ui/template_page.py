import asyncio
import os
import tempfile
from nicegui import events, ui
from sqlmodel import Session, select, desc
from app.server.database import engine
from app.server.logger import logger
from app.server.models.history import WorkflowHistory
from app.server.services.template_service import TemplateService

# 实例化 Service
template_service = TemplateService()

def render_template_page():
    # --- 1. 状态管理 ---
    state = {"tasks": [], "filename": None}

    # --- 2. 样式定义 ---
    ui.add_head_html(
        """
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');
            :root {
                --c-bg: #F8FAFC; --c-card: #FFFFFF; --c-text: #1E293B; --c-accent: #14B8A6;
                --r-lg: 24px; --r-md: 20px; --s-card: 0 10px 30px -5px rgba(0, 0, 0, 0.04);
            }
            body { background-color: var(--c-bg); font-family: 'Plus Jakarta Sans', sans-serif; color: var(--c-text); }
            .nav-capsule { background: rgba(255, 255, 255, 0.8); backdrop-filter: blur(16px); border: 1px solid rgba(255,255,255,0.5); box-shadow: 0 4px 24px rgba(0,0,0,0.04); border-radius: 100px; padding: 10px 24px; margin-top: 20px; }
            .task-card-large { background: var(--c-card); border-radius: var(--r-md); box-shadow: var(--s-card); border: 1px solid rgba(255,255,255,0.8); transition: all 0.3s ease; width: 100%; max-width: 800px; }
            .task-card-large:hover { box-shadow: 0 20px 40px -10px rgba(0,0,0,0.08); transform: translateY(-2px); }
            .index-label { font-size: 3rem; font-weight: 900; color: #94A3B8; width: 80px; text-align: right; padding-right: 20px; }
            .tag-pill { padding: 4px 12px; border-radius: 100px; font-size: 11px; font-weight: 700; text-transform: uppercase; }
            .tag-extract { background: #F0FDFA; color: #0D9488; border: 1px solid #CCFBF1; }
            .tag-gen { background: #FFFBEB; color: #B45309; border: 1px solid #FEF3C7; }
            .upload-dropzone { border: 2px dashed #E2E8F0; border-radius: var(--r-lg); background: white; transition: all 0.3s; }
            .upload-dropzone:hover { border-color: var(--c-accent); background: #F0FDFA; }
            .history-drawer { background: rgba(248, 250, 252, 0.4) !important; backdrop-filter: blur(30px) saturate(150%); border-left: 1px solid rgba(255, 255, 255, 0.5); }
            .history-card { background: rgba(255, 255, 255, 0.6); backdrop-filter: blur(10px); border: 1px solid rgba(226, 232, 240, 0.8); border-radius: 24px; transition: all 0.4s; cursor: pointer; }
            .history-card:hover { background: white; border-color: var(--c-accent); transform: translateY(-4px) scale(1.02); box-shadow: 0 20px 25px -5px rgba(20, 184, 166, 0.1); }

            /* 进入动画 */
            @keyframes fadeInUp {
                from { opacity: 0; transform: translateY(20px); }
                to { opacity: 1; transform: translateY(0); }
            }
            .animate-fade-in {
                animation: fadeInUp 0.8s cubic-bezier(0.4, 0, 0.2, 1) forwards;
            }
        </style>
        """,
        shared=True,
    )

    # --- 3. 逻辑函数 ---
    def refresh_ui():
        results_container.clear()
        overview_container.clear()
        if not state["tasks"]: return
        with overview_container:
            with ui.row().classes("w-full max-w-[880px] justify-between items-center mb-4 p-4 bg-slate-100 rounded-2xl"):
                ui.label(f"文档: {state['filename']}").classes("font-bold")
                ui.button("导出 JSON", on_click=lambda: export_data("json")).props("unelevated color=teal")
        with results_container:
            for i, task in enumerate(state["tasks"]):
                with ui.row().classes("w-full max-w-[880px] no-wrap items-start justify-center"):
                    ui.label(f"{i + 1:02d}").classes("index-label pt-8")
                    with ui.element("div").classes("task-card-large p-8 flex flex-col gap-4 relative group"):
                        ui.label(task["task_name"]).classes("text-2xl font-bold text-slate-800")
                        ui.label(task.get("description", "")).classes("text-slate-500")

    def reset_ui():
        state["tasks"] = []
        state["filename"] = None
        refresh_ui()
        ui.notify("已开启新解析任务", type="info")

    def load_history():
        history_list_container.clear()
        try:
            with Session(engine) as session:
                statement = select(WorkflowHistory).where(WorkflowHistory.category == "template-parse").order_by(desc(WorkflowHistory.created_at)).limit(20)
                results = session.exec(statement).all()
                if not results:
                    with history_list_container: ui.label("暂无解析记录").classes("text-slate-400 text-sm mt-10 w-full text-center")
                    return
                for record in results:
                    with history_list_container:
                        with ui.card().classes('history-card w-full p-4 gap-2') as card:
                            card.on('click', lambda r=record: restore_history(r))
                            with ui.row().classes('w-full items-center justify-between'):
                                ui.label(record.created_at.strftime("%Y-%m-%d")).classes("text-[10px] font-bold text-slate-400")
                                ui.icon("circle", size="8px", color="green")
                            ui.label(record.user_request).classes("text-sm font-bold line-clamp-1")
        except: ui.notify("数据库连接失败")

    def restore_history(record: WorkflowHistory):
        if record.blueprint and "tasks" in record.blueprint:
            state["tasks"] = record.blueprint["tasks"]
            state["filename"] = record.user_request
            refresh_ui()
            history_drawer.hide()

    def export_data(fmt):
        ui.notify(f"正在导出 {fmt}...")

    # --- 4. UI 布局 ---
    with ui.drawer(value=False, side='right').classes('history-drawer p-6') as history_drawer:
        ui.label("解析历史").classes("text-xl font-bold mb-6")
        history_list_container = ui.column().classes('w-full gap-4')

    with ui.row().classes("w-full justify-center sticky top-0 z-50 pointer-events-none"):
        with ui.row().classes("nav-capsule items-center gap-6 pointer-events-auto"):
            ui.label("ReportFlow").classes("font-bold text-lg text-slate-800")
            ui.separator().props("vertical").classes("h-4")
            ui.button("新对话", icon="add", on_click=reset_ui).props("flat dense color=teal-5")
            ui.button("历史", icon="history", on_click=lambda: (load_history(), history_drawer.toggle())).props("flat dense color=teal-5")
            ui.button("返回", on_click=lambda: ui.navigate.to("/")).props("flat dense color=grey-7")

    with ui.column().classes("w-full max-w-5xl mx-auto px-6 pt-16 pb-32 gap-12 items-center animate-fade-in"):
        with ui.column().classes("w-full items-center text-center gap-4"):
            ui.label("智能报告解构").classes("text-4xl md:text-5xl font-extrabold text-slate-900 tracking-tight")
            ui.label("上传 Word 报告模板，AI 将自动分析业务逻辑并拆解为可执行的子任务。").classes("text-lg text-slate-500 max-w-2xl")
            
            with ui.card().classes("upload-dropzone w-full max-w-xl h-48 flex items-center justify-center relative cursor-pointer mt-4"):
                ui.icon("upload_file", size="3rem").classes("text-slate-300")
                ui.label("点击上传 Word 模板 (.docx)").classes("font-bold text-slate-600")
                async def handle_upload(e: events.UploadEventArguments):
                    content = await e.file.read()
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
                        tmp.write(content); tmp_path = tmp.name
                    try:
                        res = await asyncio.get_running_loop().run_in_executor(None, template_service.parse_and_decompose, tmp_path, e.file.name)
                        state["tasks"] = res.get("tasks", []); state["filename"] = e.file.name
                        refresh_ui()
                    finally: os.unlink(tmp_path)
                ui.upload(on_upload=handle_upload, auto_upload=True).props('accept=".docx" flat').classes("absolute inset-0 opacity-0 z-10")

        overview_container = ui.column().classes("w-full items-center")
        results_container = ui.column().classes("w-full items-center gap-8")