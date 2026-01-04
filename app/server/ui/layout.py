from nicegui import ui


def render_home_page():
    ui.query("body").classes("bg-slate-50")

    # --- 顶栏 ---
    with ui.header().classes("bg-white border-b border-slate-200 px-8 py-4 shadow-sm"):
        with ui.row().classes("items-center gap-3"):
            with ui.element("div").classes("p-2 bg-slate-900 rounded-lg"):
                ui.icon("hub", size="1.5rem").classes("text-white")
            ui.label("ReportFlow Studio").classes("text-xl font-bold text-slate-800")

        ui.button("API 文档", icon="api", on_click=lambda: ui.navigate.to("/docs")).props("flat color=slate-600")

    # --- 主体内容 ---
    with ui.column().classes("w-full max-w-6xl mx-auto p-12 gap-12"):
        # 欢迎标语
        with ui.column().classes("gap-2"):
            ui.label("欢迎回到工作台").classes("text-4xl font-black text-slate-900 tracking-tight")
            ui.label("选择一个工具开始你的工作").classes("text-lg text-slate-500 font-medium")

        # 功能卡片网格
        with ui.grid(columns=3).classes("w-full gap-8"):
            # 卡片 1: YAML 生成器
            with (
                ui.card()
                .classes(
                    "group hover:shadow-xl transition-all duration-300 border-none bg-white p-0 overflow-hidden cursor-pointer"
                )
                .on("click", lambda: ui.navigate.to("/generator"))
            ):
                with ui.column().classes(
                    "h-32 bg-gradient-to-br from-blue-600 to-indigo-700 p-6 justify-between relative overflow-hidden"
                ):
                    ui.icon("auto_fix_high", size="4rem").classes(
                        "absolute -right-4 -bottom-4 text-white/20 group-hover:scale-110 transition-transform duration-500"
                    )
                    ui.icon("bolt", size="2rem").classes("text-white")
                    ui.label("AI 生成器").classes("text-white font-bold text-lg tracking-wide")

                with ui.column().classes("p-6 gap-4"):
                    ui.label("Dify 工作流架构师").classes("text-lg font-bold text-slate-800")
                    ui.label("基于自然语言快速生成高质量的 Dify YAML 配置文件。支持智能规划与自动校验。").classes(
                        "text-sm text-slate-500 leading-relaxed"
                    )

                    with ui.row().classes(
                        "items-center text-blue-600 font-bold text-sm group-hover:translate-x-1 transition-transform"
                    ):
                        ui.label("立即开始")
                        ui.icon("arrow_forward")

            # 卡片 2: Word 模板解析
            with (
                ui.card()
                .classes(
                    "group hover:shadow-xl transition-all duration-300 border-none bg-white p-0 overflow-hidden cursor-pointer"
                )
                .on("click", lambda: ui.navigate.to("/template-parser"))
            ):
                with ui.column().classes(
                    "h-32 bg-gradient-to-br from-indigo-600 to-purple-700 p-6 justify-between relative overflow-hidden"
                ):
                    ui.icon("description", size="4rem").classes(
                        "absolute -right-4 -bottom-4 text-white/20 group-hover:scale-110 transition-transform duration-500"
                    )
                    ui.icon("document_scanner", size="2rem").classes("text-white")
                    ui.label("模板解析器").classes("text-white font-bold text-lg tracking-wide")

                with ui.column().classes("p-6 gap-4"):
                    ui.label("智能文档结构化").classes("text-lg font-bold text-slate-800")
                    ui.label("上传 Word 报告模板，自动拆解撰写任务与变量依赖。支持无占位符的语义识别。").classes(
                        "text-sm text-slate-500 leading-relaxed"
                    )

                    with ui.row().classes(
                        "items-center text-indigo-600 font-bold text-sm group-hover:translate-x-1 transition-transform"
                    ):
                        ui.label("立即使用")
                        ui.icon("arrow_forward")

            # 卡片 3: 更多功能 (占位)
            with ui.card().classes(
                "border-2 border-dashed border-slate-200 bg-transparent p-0 flex items-center justify-center min-h-[300px]"
            ):
                with ui.column().classes("items-center gap-2 text-slate-300"):
                    ui.icon("add", size="3rem")
                    ui.label("更多功能开发中...").classes("font-medium")

    # --- 页脚 ---
    with ui.footer().classes("bg-transparent text-slate-400 text-sm justify-center py-6"):
        ui.label("© 2026 ReportFlow Studio. Powered by DeepAgents.")
