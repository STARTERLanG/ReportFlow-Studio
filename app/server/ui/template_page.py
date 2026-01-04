import asyncio
import os
import tempfile

from nicegui import events, ui

from app.server.logger import logger
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
        </style>
        """,
        shared=True,
    )

    # --- 状态管理 ---
    state = {"tasks": [], "filename": None}

    # --- 顶部导航 ---
    with ui.row().classes("w-full justify-center sticky top-0 z-50 pointer-events-none"):
        with ui.row().classes("nav-capsule items-center gap-6 pointer-events-auto"):
            with ui.row().classes("items-center gap-2"):
                ui.icon("auto_graph", size="20px", color="teal-500")
                ui.label("ReportFlow").classes("font-bold text-lg tracking-tight text-slate-800")

            ui.separator().props("vertical").classes("h-4 bg-slate-200")
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
                            result = await loop.run_in_executor(None, template_service.parse_and_decompose, tmp_path)
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
                        ui.label("个任务描述").classes("text-xs text-slate-500 font-bold")

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
                    with ui.element("div").classes("task-card-large p-8 flex flex-col gap-6 h-auto"):
                        # Card Header
                        with ui.row().classes("w-full justify-between items-center"):
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
