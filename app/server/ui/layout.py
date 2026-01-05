from nicegui import ui


def render_home_page():
    ui.query("body").classes("bg-slate-50")

    ui.add_head_html("""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
            body { font-family: 'Plus Jakarta Sans', sans-serif; }
            
            .header-glass {
                background: rgba(255, 255, 255, 0.7) !important;
                backdrop-filter: blur(20px) saturate(180%);
                border-bottom: 1px solid rgba(226, 232, 240, 0.5) !important;
                box-shadow: 0 4px 30px rgba(0, 0, 0, 0.02) !important;
            }
            .logo-text {
                font-weight: 800;
                letter-spacing: -0.02em;
                background: linear-gradient(90deg, #0F172A 0%, #334155 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }
            .nav-btn {
                border-radius: 12px !important;
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
                font-weight: 600 !important;
                color: #64748B !important;
            }
            .nav-btn:hover {
                background: rgba(99, 102, 241, 0.08) !important;
                color: #6366F1 !important;
                transform: translateY(-1px);
            }
        </style>
    """)

    # --- 顶栏 ---
    with ui.header().classes("header-glass flex justify-center p-0"):
        # 整体扩容：py-4，提升大气感
        with ui.row().classes("w-full max-w-[1400px] items-center px-12 py-4 m-0"):
            # Logo Group
            with ui.row().classes("items-center gap-3.5 cursor-pointer m-0").on("click", lambda: ui.navigate.to("/")):
                with ui.element("div").classes("p-2.5 bg-slate-900 rounded-2xl shadow-xl shadow-slate-200"):
                    ui.icon("hub", size="1.6rem").classes("text-white")
                with ui.column().classes("gap-0 p-0 m-0"):
                    ui.label("ReportFlow").classes("text-2xl logo-text leading-none mb-1")
                    ui.label("STUDIO v0.1").classes(
                        "text-[11px] font-black text-indigo-400 tracking-[0.25em] leading-none"
                    )

            # Navigation Actions
            with ui.row().classes("ml-auto items-center gap-3 m-0"):
                ui.button("API 文档", icon="api", on_click=lambda: ui.navigate.to("/docs")).classes(
                    "nav-btn px-5 py-2 text-base"
                ).props("flat")
                ui.button("系统设置", icon="settings", on_click=lambda: ui.navigate.to("/settings")).classes(
                    "nav-btn px-5 py-2 text-base"
                ).props("flat")

                ui.separator().props("vertical").classes("mx-4 h-7 bg-slate-200")

                with ui.button(icon="help_outline").props("flat round color=slate-400 size=md"):
                    ui.tooltip("查看帮助")

    # --- 主体内容 ---
    with ui.column().classes("w-full max-w-[1400px] mx-auto px-12 pt-12 pb-32 gap-10 items-start"):
        # 欢迎标语 - 改为 items-start 对齐左侧
        with ui.column().classes("w-full gap-3 mt-2 items-start"):
            ui.label("欢迎回到工作台").classes("text-5xl font-black text-slate-900 tracking-tight")
            ui.label("选择一个工具开始你的工作，让 AI 释放你的生产力。").classes("text-xl text-slate-500 font-medium")

        # 功能卡片网格
        with ui.grid(columns=3).classes("w-full gap-10 mt-4"):
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
