import asyncio
import os
import tempfile

from nicegui import events, ui
from sqlmodel import Session, select, desc

from app.server.database import engine
from app.server.logger import logger
from app.server.models.history import WorkflowHistory
from app.server.services.template_service import TemplateService

# 实例化 Service (单例)
template_service = TemplateService()


def render_template_page():
    # --- 样式定义 (Soft Modern - Refined Layout) ---
    ui.add_head_html(
        """
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');
            
            :root {
                --c-bg: #F8FAFC;
                --c-card: #FFFFFF;
                --c-text: #1E293B;
                --c-subtext: #64748B;
                --c-accent: #14B8A6; /* Teal 500 */
                --r-lg: 24px;
                --r-md: 20px;
                --r-sm: 12px;
                --s-card: 0 10px 30px -5px rgba(0, 0, 0, 0.04);
            }

            body { 
                background-color: var(--c-bg);
                font-family: 'Plus Jakarta Sans', sans-serif;
                color: var(--c-text);
            }

            /* 顶部导航 */
            .nav-capsule {
                background: rgba(255, 255, 255, 0.8);
                backdrop-filter: blur(16px);
                border: 1px solid rgba(255,255,255,0.5);
                box-shadow: 0 4px 24px rgba(0,0,0,0.04);
                border-radius: 100px;
                padding: 10px 24px;
                margin-top: 20px;
            }

            /* 任务大卡片 */
            .task-card-large {
                background: var(--c-card);
                border-radius: var(--r-md);
                box-shadow: var(--s-card);
                border: 1px solid rgba(255,255,255,0.8);
                transition: all 0.3s ease;
                width: 100%;
                max-width: 800px;
            }
            .task-card-large:hover {
                box-shadow: 0 20px 40px -10px rgba(0,0,0,0.08);
                transform: translateY(-2px);
            }

            /* 左侧大序号 */
            .index-label {
                font-size: 3rem;
                font-weight: 900;
                color: #94A3B8; /* Slate-400 */
                line-height: 1;
                width: 80px;
                text-align: right;
                padding-right: 20px;
                user-select: none;
            }

            /* 过渡分割条 */
            .transition-bar {
                background: #F1F5F9;
                border-radius: 16px;
                padding: 16px 24px;
                border: 1px solid #E2E8F0;
            }

            /* 标签胶囊 */
            .tag-pill {
                padding: 4px 12px;
                border-radius: 100px;
                font-size: 11px;
                font-weight: 700;
                text-transform: uppercase;
                letter-spacing: 0.05em;
            }
            .tag-extract { background: #F0FDFA; color: #0D9488; border: 1px solid #CCFBF1; }
            .tag-gen { background: #FFFBEB; color: #B45309; border: 1px solid #FEF3C7; }

            /* 上传区 */
            .upload-dropzone {
                border: 2px dashed #E2E8F0;
                border-radius: var(--r-lg);
                background: white;
                transition: all 0.3s;
            }
            .upload-dropzone:hover {
                border-color: var(--c-accent);
                background: #F0FDFA;
            }

            /* 历史记录侧边栏样式 */
            .history-drawer {
                background: rgba(248, 250, 252, 0.4) !important;
                backdrop-filter: blur(30px) saturate(150%);
                border-left: 1px solid rgba(255, 255, 255, 0.5);
            }
            .history-card {
                background: rgba(255, 255, 255, 0.6);
                backdrop-filter: blur(10px);
                border: 1px solid rgba(226, 232, 240, 0.8);
                border-radius: 24px;
                transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
                cursor: pointer;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03);
            }
            .history-card:hover {
                background: white;
                border-color: var(--c-accent);
                transform: translateY(-4px) scale(1.02);
                box-shadow: 0 20px 25px -5px rgba(20, 184, 166, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
            }
        </style>
        """,
        shared=True,
    )

    # --- 状态管理 ---
    state = {"tasks": [], "filename": None}

    # --- 侧边栏 ---
    with ui.drawer(value=False, fixed=False, side='right').classes('history-drawer p-0 w-80 shadow-2xl') as history_drawer:
        with ui.column().classes('w-full h-full p-6 gap-6'):
            with ui.row().classes('w-full items-center justify-between'):
                ui.label("解析历史").classes("text-xl font-bold text-slate-800")
                ui.button(icon="close", on_click=lambda: history_drawer.toggle()).props("flat round color=grey-7 size=sm")
            
            history_list_container = ui.column().classes('w-full gap-4')

    def load_history():
        history_list_container.clear()
        try:
            with Session(engine) as session:
                statement = select(WorkflowHistory).where(WorkflowHistory.category == "template-parse").order_by(desc(WorkflowHistory.created_at)).limit(20)
                results = session.exec(statement).all()
                
                if not results:
                    with history_list_container:
                        ui.label("暂无解析记录").classes("text-slate-400 text-sm mt-10 w-full text-center")
                    return

                for record in results:
                    with history_list_container:
                        with ui.card().classes('history-card w-full p-4 gap-2') as card:
                            card.on('click', lambda r=record: restore_history(r))
                            
                            with ui.row().classes('w-full items-center justify-between'):
                                with ui.row().classes('gap-3'):
                                    ui.label(record.created_at.strftime("%Y-%m-%d")).classes("text-[10px] font-bold text-slate-400 uppercase tracking-tighter")
                                    ui.label(record.created_at.strftime("%H:%M")).classes("text-[10px] font-bold text-teal-400 uppercase tracking-tighter")
                                ui.icon("circle", size="8px", color="green")
                            
                            ui.label(record.user_request).classes("text-sm text-slate-700 font-medium line-clamp-1")
                            
                            with ui.row().classes('w-full items-center gap-1'):
                                ui.icon("article", size="12px", color="slate-400")
                                tasks_count = len(record.blueprint.get("tasks", [])) if record.blueprint else 0
                                ui.label(f"{tasks_count} 个任务").classes("text-[10px] text-slate-400")

        except Exception as e:
            logger.error(f"加载历史记录失败: {e}")
            with history_list_container:
                ui.label("数据库连接异常").classes("text-red-400 text-sm mt-10 w-full text-center")

    def restore_history(record: WorkflowHistory):
        if record.blueprint and "tasks" in record.blueprint:
            state["tasks"] = record.blueprint["tasks"]
            state["filename"] = record.user_request
            refresh_ui()
            ui.notify(f"已恢复历史版本: {record.user_request}")
            history_drawer.hide()

    # --- 顶部导航 ---
    with ui.row().classes("w-full justify-center sticky top-0 z-50 pointer-events-none"):
        with ui.row().classes("nav-capsule items-center gap-6 pointer-events-auto"):
            with ui.row().classes("items-center gap-2"):
                ui.icon("auto_graph", size="20px", color="teal-500")
                ui.label("ReportFlow").classes("font-bold text-lg tracking-tight text-slate-800")

            ui.separator().props("vertical").classes("h-4 bg-slate-200")
            
            with ui.row().classes("items-center gap-2"):
                ui.button("历史", icon="history", on_click=lambda: (load_history(), history_drawer.toggle())).props("flat dense color=teal-5 size=sm").classes("px-4 font-medium")
                ui.button("返回首页", on_click=lambda: ui.navigate.to("/")).props(
                    "flat dense color=grey-7 size=sm"
                ).classes("font-medium")

    # --- 主体容器 ---
    with ui.column().classes("w-full max-w-5xl mx-auto px-6 pt-16 pb-32 gap-12 items-center"):
        # 1. 英雄区 (Hero Section)
        with ui.column().classes("w-full items-center text-center gap-4"):
            ui.label("智能报告解构").classes("text-4xl font-extrabold text-slate-900 tracking-tight")
            ui.label("上传 Word 模板，AI 将深度解析业务逻辑并自动拆解为一系列可执行的任务描述。").classes(
                "text-lg text-slate-500 max-w-2xl leading-relaxed"
            )

            # 上传区域
            with ui.card().classes(
                "upload-dropzone w-full max-w-xl h-40 flex flex-col items-center justify-center cursor-pointer relative group"
            ):
                ui.icon("upload_file", size="3rem").classes(
                    "text-slate-300 mb-2 group-hover:text-teal-500 transition-colors"
                )
                ui.label("点击选择 Word 模板 (.docx)").classes("font-bold text-slate-600 group-hover:text-teal-600")

                async def handle_upload(e: events.UploadEventArguments):
                    try:
                        filename = e.file.name
                        loading_layer.classes(
                            replace="fixed inset-0 z-[9999] bg-white/90 backdrop-blur-md flex flex-col items-center justify-center opacity-100 transition-opacity duration-300"
                        )
                        await asyncio.sleep(0.1)

                        content_bytes = await e.file.read()
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
                            tmp.write(content_bytes)
                            tmp_path = tmp.name

                        try:
                            loop = asyncio.get_running_loop()
                            result = await loop.run_in_executor(
                                None, 
                                template_service.parse_and_decompose, 
                                tmp_path, 
                                filename
                            )
                            state["tasks"] = result.get("tasks", [])
                            state["filename"] = filename
                            refresh_ui()
                            ui.notify(f"解析成功: {filename}", color="teal")
                        finally:
                            if os.path.exists(tmp_path):
                                os.unlink(tmp_path)
                    except Exception as err:
                        logger.exception("解析失败")
                        ui.notify(f"解析失败: {str(err)}", type="negative")
                    finally:
                        loading_layer.classes(
                            replace="fixed inset-0 z-[9999] bg-white/80 backdrop-blur-md flex flex-col items-center justify-center opacity-0 pointer-events-none transition-opacity duration-300"
                        )
                        upload_element.run_method("reset")

                upload_element = (
                    ui.upload(auto_upload=True, on_upload=handle_upload, max_files=1)
                    .props('accept=".docx" flat')
                    .classes("hidden")
                )
                ui.button(on_click=lambda: upload_element.run_method("pickFiles")).classes(
                    "absolute inset-0 w-full h-full opacity-0 z-10"
                )

        # 2. 解析后过渡区 (Overview Bar)
        overview_container = ui.column().classes("w-full items-center gap-0")

        # 3. 任务列表 (Card List)
        results_container = ui.column().classes("w-full items-center gap-8")

    # --- 全屏加载层 ---
    loading_layer = ui.element("div").classes(
        "fixed inset-0 z-[9999] bg-white/90 backdrop-blur-md flex flex-col items-center justify-center opacity-0 pointer-events-none"
    )
    with loading_layer:
        ui.spinner(size="4rem", color="teal-500", thickness=2)
        ui.label("AI 正在解析业务逻辑...").classes("mt-6 text-xl font-bold text-slate-800")

    def open_edit_dialog(index=None):
        is_new = index is None
        # 如果是新建，初始化一个空任务模板
        if is_new:
            task = {
                "task_name": "新任务",
                "type": "generation",  # 默认类型
                "description": "",
                "requirements": "",
                "reference_content": ""
            }
        else:
            task = state["tasks"][index]

        with ui.dialog() as dialog, ui.card().classes("w-full max-w-2xl p-6"):
            ui.label("新建任务" if is_new else "编辑任务").classes("text-xl font-bold mb-4")
            
            with ui.column().classes("w-full gap-4"):
                name_input = ui.input("任务名称", value=task["task_name"]).classes("w-full")
                
                type_select = ui.select(
                    {"extraction": "数据提取", "generation": "智能写作"}, 
                    value=task["type"], 
                    label="任务类型"
                ).classes("w-full")
                
                desc_input = ui.textarea("任务描述", value=task.get("description", "")).classes("w-full").props("autogrow")
                req_input = ui.textarea("执行要求", value=task.get("requirements", "")).classes("w-full").props("autogrow")
                
                # 动态内容容器
                content_container = ui.column().classes("w-full")
                
                def update_content_fields():
                    content_container.clear()
                    with content_container:
                        if type_select.value == "extraction":
                            fields_str = ", ".join(task.get("fields", [])) if not is_new and "fields" in task else ""
                            # 如果是新建且切到 extraction，fields_temp 可能还没值，默认为空
                            current_val = task.get("fields_temp", fields_str)
                            ui.textarea("待提取字段 (用逗号分隔)", value=current_val).bind_value(task, "fields_temp").classes("w-full").props("autogrow")
                        else:
                            ref_str = task.get("reference_content", "") if not is_new else ""
                            current_val = task.get("ref_temp", ref_str)
                            ui.textarea("参考原文内容", value=current_val).bind_value(task, "ref_temp").classes("w-full").props("autogrow")
                
                # 初始化临时变量
                if not is_new:
                    task["fields_temp"] = ", ".join(task.get("fields", []))
                    task["ref_temp"] = task.get("reference_content", "")
                else:
                    task["fields_temp"] = ""
                    task["ref_temp"] = ""
                
                type_select.on_value_change(update_content_fields)
                update_content_fields() # 初始渲染

            with ui.row().classes("w-full justify-end mt-6 gap-2"):
                ui.button("取消", on_click=dialog.close).props("flat color=grey")
                def save_changes():
                    # 更新/填充数据
                    task["task_name"] = name_input.value
                    task["type"] = type_select.value
                    task["description"] = desc_input.value
                    task["requirements"] = req_input.value
                    
                    if task["type"] == "extraction":
                        fields_raw = task.get("fields_temp", "")
                        fields_raw = fields_raw.replace("，", ",")
                        task["fields"] = [f.strip() for f in fields_raw.split(",") if f.strip()]
                        task.pop("reference_content", None)
                    else:
                        task["reference_content"] = task.get("ref_temp", "")
                        task.pop("fields", None)
                    
                    # 清理临时键
                    task.pop("fields_temp", None)
                    task.pop("ref_temp", None)
                    
                    if is_new:
                        state["tasks"].append(task)
                        ui.notify("新任务已添加", type="positive")
                    else:
                        ui.notify("任务已更新", type="positive")
                    
                    dialog.close()
                    refresh_ui()
                
                ui.button("保存", on_click=save_changes).props("unelevated color=teal")
        
        dialog.open()

    def delete_task(index):
        # 简单确认 (这里直接删，实际项目可以加 Dialog 确认)
        state["tasks"].pop(index)
        ui.notify("任务已删除", type="negative")
        refresh_ui()

    def refresh_ui():
        results_container.clear()
        overview_container.clear()
        if not state["tasks"]:
            return

        # 渲染过渡区
        with overview_container:
            with ui.row().classes("transition-bar w-full max-w-[880px] justify-between items-center mb-4"):
                with ui.row().classes("items-center gap-4"):
                    ui.icon("description", size="24px", color="teal-600")
                    with ui.column().classes("gap-0"):
                        ui.label(state["filename"]).classes("font-bold text-slate-800")
                        ui.label("文档结构解析已完成").classes("text-xs text-slate-400 font-medium")

                with ui.row().classes("items-center gap-6"):
                    # 统计
                    with ui.row().classes("items-center gap-2"):
                        ui.label(str(len(state["tasks"]))).classes("font-bold text-xl text-teal-600")
                        ui.label("个任务").classes("text-xs text-slate-500 font-bold")

                    ui.separator().props("vertical").classes("h-6 bg-slate-300")

                    # 导出组
                    with ui.row().classes("gap-2"):
                        ui.button("导出 JSON", on_click=lambda: export_data("json")).props(
                            "unelevated color=slate-800 size=sm"
                        ).classes("rounded-lg px-4")
                        ui.button("导出 Excel", on_click=lambda: export_data("xlsx")).props(
                            "outline color=slate-800 size=sm"
                        ).classes("rounded-lg px-4")

        # 渲染任务卡片
        with results_container:
            for i, task in enumerate(state["tasks"]):
                is_extract = task.get("type") == "extraction"

                # 单个任务行布局： [序号] + [卡片]
                with ui.row().classes("w-full max-w-[880px] no-wrap items-start justify-center"):
                    # 序号
                    ui.label(f"{i + 1:02d}").classes("index-label pt-8")

                    # 卡片
                    with ui.element("div").classes("task-card-large p-8 flex flex-col gap-6 h-auto relative group"):
                        # 操作按钮组 (悬浮显示)
                        with ui.row().classes("absolute top-4 right-4 opacity-0 group-hover:opacity-100 transition-opacity gap-1"):
                            with ui.button(icon="edit", on_click=lambda _, idx=i: open_edit_dialog(idx)).props("flat round color=grey-5 size=sm"):
                                ui.tooltip("编辑任务")
                            with ui.button(icon="delete", on_click=lambda _, idx=i: delete_task(idx)).props("flat round color=grey-5 size=sm"):
                                ui.tooltip("删除任务")

                        # Card Header
                        with ui.row().classes("items-center gap-3 pr-20"): # 移除了 w-full justify-between，改为靠左紧凑排列
                            ui.label(task["task_name"]).classes("text-2xl font-bold text-slate-800 tracking-tight")
                            # 类型标签
                            with ui.element("div").classes(f"tag-pill {'tag-extract' if is_extract else 'tag-gen'}"):
                                ui.label("数据提取" if is_extract else "智能写作")

                        # Description
                        ui.label(task.get("description", "")).classes(
                            "text-base text-slate-500 leading-relaxed break-words"
                        )

                        # Requirements
                        if task.get("requirements"):
                            with ui.row().classes(
                                "bg-orange-50/50 p-4 rounded-xl border border-orange-100 items-start gap-3"
                            ):
                                ui.icon("lightbulb", size="16px", color="orange-500").classes("mt-1")
                                with ui.column().classes("gap-1 flex-1"):
                                    ui.label("执行要求").classes(
                                        "text-[10px] font-bold text-orange-400 uppercase tracking-widest"
                                    )
                                    ui.label(task["requirements"]).classes(
                                        "text-sm text-orange-800 font-medium break-words"
                                    )

                        # Details (Bottom Section)
                        ui.separator().classes("bg-slate-100")

                        if is_extract:
                            with ui.column().classes("gap-3 w-full"):
                                ui.label("待提取字段").classes(
                                    "text-[10px] font-bold text-slate-300 uppercase tracking-widest"
                                )
                                with ui.row().classes("flex-wrap gap-2"):
                                    for f in task.get("fields", []):
                                        ui.label(f).classes(
                                            "bg-slate-100 text-slate-600 px-3 py-1 rounded-lg text-xs font-bold border border-slate-200"
                                        )
                        else:
                            with ui.column().classes("gap-3 w-full"):
                                ui.label("参考原文内容").classes(
                                    "text-[10px] font-bold text-slate-300 uppercase tracking-widest"
                                )
                                ui.label(task.get("reference_content", "")).classes(
                                    "text-xs text-slate-500 italic leading-loose p-4 bg-slate-50 rounded-xl border border-slate-100 break-words whitespace-pre-wrap"
                                )
            
            # 底部添加按钮
            with ui.button("添加新任务", icon="add", on_click=lambda: open_edit_dialog(None)).classes("w-full max-w-[880px] h-16 text-lg font-bold border-2 border-dashed border-slate-300 text-slate-400 hover:border-teal-500 hover:text-teal-500 hover:bg-teal-50 transition-colors rounded-2xl mt-4").props("flat"):
                pass

    def export_data(fmt: str):
        if not state["tasks"]:
            return
        filename = f"{state['filename']}_{fmt}"
        if fmt == "json":
            import json

            content = json.dumps(state["tasks"], ensure_ascii=False, indent=2)
            ui.download(content.encode(), f"{filename}.json", "application/json")
        elif fmt == "xlsx":
            try:
                import io

                from openpyxl import Workbook

                wb = Workbook()
                ws = wb.active
                ws.title = "解析任务"
                ws.append(["ID", "任务名称", "类型", "描述", "要求", "详情"])
                for i, t in enumerate(state["tasks"]):
                    data = (
                        ", ".join(t.get("fields", []))
                        if t.get("type") == "extraction"
                        else t.get("reference_content", "")
                    )
                    ws.append([i + 1, t["task_name"], t["type"], t["description"], t.get("requirements", ""), data])
                out = io.BytesIO()
                wb.save(out)
                ui.download(
                    out.getvalue(),
                    f"{filename}.xlsx",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            except:
                ui.notify("导出失败", type="negative")

    refresh_ui()
