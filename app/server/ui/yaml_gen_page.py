import asyncio

from nicegui import ui

from agents.workflows.dify_yaml_generator import YamlAgentService
from app.server.logger import logger
from app.server.utils.visualizer import dify_yaml_to_mermaid

# 初始化服务 (单例或按需)
agent_service = YamlAgentService()


def render_yaml_generator_page():
    # --- 页面样式注入 ---
    ui.add_head_html(
        """
        <style>
            @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Inter:wght@400;600;800&display=swap');
            .terminal-text { font-family: 'JetBrains Mono', monospace; }
            .glass-card {
                background: rgba(255, 255, 255, 0.8) !important;
                backdrop-filter: blur(12px);
                border: 1px solid rgba(255, 255, 255, 0.3);
            }
            .animate-fade-in {
                animation: fadeIn 0.5s ease-in-out forwards;
            }
            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(10px); }
                to { opacity: 1; transform: translateY(0); }
            }
        </style>
    """,
        shared=True,
    )

    ui.query("body").classes("bg-slate-100")

    # --- 顶栏：深邃极简 ---
    with ui.header().classes(
        "items-center justify-between bg-slate-900/90 backdrop-blur-md text-white border-b border-slate-700 px-8 py-3 shadow-2xl"
    ):
        with ui.row().classes("items-center gap-3"):
            with ui.element("div").classes("p-2 bg-blue-600 rounded-lg shadow-lg shadow-blue-500/50"):
                ui.icon("bolt", size="1.5rem")
            with ui.column().classes("gap-0"):
                ui.label("ReportFlow").classes("text-xl font-black tracking-tighter text-blue-50 leading-none")
                ui.label("YAML GENERATOR").classes("text-[10px] font-bold text-blue-400 tracking-widest leading-none")

        with ui.row().classes("items-center gap-4"):
            ui.button("返回首页", icon="home", on_click=lambda: ui.navigate.to("/")).props("flat color=white size=sm")
            ui.separator().props("vertical color=slate-600")
            ui.button(icon="dark_mode", on_click=lambda: ui.dark_mode().toggle()).props("flat color=white size=sm")

    # --- 主体：双栏布局 ---
    with ui.row().classes("w-full p-8 no-wrap gap-8 justify-center h-[calc(100vh-80px)]"):
        # --- 左侧：交互控制台 ---
        with ui.column().classes("w-[450px] gap-6 flex-shrink-0 h-full"):
            # 输入需求卡片
            with ui.card().classes("w-full p-8 shadow-xl border-none rounded-3xl glass-card flex-shrink-0"):
                with ui.row().classes("items-center gap-2 mb-4"):
                    ui.icon("auto_awesome", size="1.2rem").classes("text-blue-500")
                    ui.label("AI 架构师").classes("text-xl font-extrabold text-slate-800")

                query_input = ui.textarea(
                    label="输入业务场景或工作流需求",
                    placeholder="例如：设计一个针对信贷审批的自动化流程，需要识别风险并生成建议...",
                ).classes(
                    "w-full min-h-[150px] bg-white rounded-xl border-slate-200 focus:border-blue-500 transition-all text-base p-4 shadow-inner"
                )

                generate_btn = (
                    ui.button("开始构建架构", on_click=lambda: run_design())
                    .classes(
                        "w-full h-14 text-lg font-bold mt-6 hover:scale-[1.02] active:scale-[0.98] transition-transform shadow-lg shadow-blue-600/30"
                    )
                    .props("unelevated color=blue-7 rounded-xl")
                )

            # 终端日志卡片 (自适应高度填充剩余空间)
            with ui.card().classes(
                "w-full p-6 shadow-xl border-none rounded-3xl bg-slate-900 flex-grow border border-slate-700 overflow-hidden flex flex-col"
            ):
                with ui.row().classes("items-center justify-between w-full mb-2 flex-shrink-0"):
                    with ui.row().classes("items-center gap-2"):
                        ui.element("div").classes("w-3 h-3 rounded-full bg-red-500")
                        ui.element("div").classes("w-3 h-3 rounded-full bg-amber-500")
                        ui.element("div").classes("w-3 h-3 rounded-full bg-emerald-500")
                    ui.label("EXECUTION_LOG").classes("text-xs font-mono text-slate-500 font-bold tracking-widest")

                # 日志滚动区
                log_scroll = ui.scroll_area().classes("w-full flex-grow terminal-text pr-2")
                with log_scroll:
                    log_area = ui.column().classes("w-full gap-1.5")

                status_spinner = ui.spinner(size="md", color="blue-400").classes("self-center mt-4 flex-shrink-0")
                status_spinner.set_visibility(False)

        # --- 右侧：成果展示 ---
        with ui.column().classes("flex-grow max-w-[1200px] h-full"):
            with ui.tabs().classes("w-full rounded-2xl bg-white p-1 border-none shadow-sm shadow-slate-200") as tabs:
                tab_visual = ui.tab("架构蓝图", icon="dashboard").classes("rounded-xl text-slate-500 px-8 py-3")
                tab_code = ui.tab("Dify YAML", icon="data_array").classes("rounded-xl text-slate-500 px-8 py-3")

            with ui.tab_panels(tabs, value=tab_visual).classes(
                "w-full bg-white shadow-2xl rounded-3xl flex-grow border border-white overflow-hidden"
            ):
                # 绘图面板
                with ui.tab_panel(tab_visual).classes("p-0 relative bg-white w-full h-full"):
                    mermaid_display = ui.mermaid("").classes(
                        "w-full h-full border-none opacity-0 transition-opacity duration-700"
                    )
                    with ui.column().classes("absolute-center items-center text-slate-300 gap-4") as empty_hint:
                        ui.icon("architecture", size="6rem").classes("animate-bounce text-slate-200")
                        ui.label("架构设计完成后将在此渲染").classes("text-lg font-medium")

                # 源码面板
                with ui.tab_panel(tab_code).classes("p-0 bg-slate-950 w-full h-full"):
                    # 使用 ui.code 提供更好的代码展示
                    yaml_display = ui.code("", language="yaml").classes(
                        "w-full h-full text-sm text-slate-300 terminal-text p-6 overflow-auto"
                    )

    # --- 交互逻辑 ---
    async def run_design():
        if not query_input.value or len(query_input.value) < 5:
            ui.notify("需求描述太模糊了，请再多给一些细节。", type="warning", position="top")
            return

        # UI 状态初始化
        generate_btn.disable()
        status_spinner.set_visibility(True)
        log_area.clear()
        # yaml_display.content = "" # ui.code 使用 content 属性
        mermaid_display.set_content("")
        mermaid_display.classes("opacity-0")
        empty_hint.set_visibility(False)

        # 实时日志回调
        async def ui_callback(message: str):
            with log_area, ui.row().classes("items-start gap-3 w-full animate-fade-in"):
                ui.label("➜").classes("text-blue-400 font-mono mt-0.5 flex-shrink-0")
                ui.label(message).classes("text-sm text-slate-300 leading-tight break-all")
            # 自动滚动到最新日志
            log_scroll.scroll_to(percent=1.0)

        try:
            # 运行 Agent
            yaml_output = await agent_service.generate_yaml(user_request=query_input.value, status_callback=ui_callback)

            # 延迟一小下展示结果，增加“仪式感”
            await asyncio.sleep(0.5)

            # 更新代码显示
            yaml_display.content = yaml_output
            yaml_display.update()  # 强制刷新

            # 更新图表
            mermaid_syntax = dify_yaml_to_mermaid(yaml_output)
            mermaid_display.set_content(mermaid_syntax)
            mermaid_display.classes("opacity-100")

            ui.notify("工作流架构已构建完成！", type="positive", position="top", close_button=True)

        except Exception as e:
            logger.exception("UI 任务执行失败")
            ui.notify(f"构建失败: {str(e)}", type="negative", position="top")
            with log_area:
                ui.label(f"!! ERROR: {str(e)}").classes(
                    "text-red-400 font-bold py-2 px-4 border border-red-900 rounded bg-red-950/50 mt-2"
                )

        finally:
            generate_btn.enable()
            status_spinner.set_visibility(False)
