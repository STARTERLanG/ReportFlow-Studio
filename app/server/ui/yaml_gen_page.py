import asyncio
import yaml as pyyaml
from nicegui import ui
from sqlmodel import Session, select, desc
from agents.workflows.dify_yaml_generator import YamlAgentService
from app.server.logger import logger
from app.server.utils.visualizer import dify_yaml_to_mermaid
from app.server.database import engine
from app.server.models.history import WorkflowHistory

# 初始化服务
agent_service = YamlAgentService()

def render_yaml_generator_page():
    # --- 状态与队列初始化 (必须放在最前) ---
    state = {
        "is_generating": False,
        "has_result": False,
        "is_focused": False
    }
    log_queue = [] # 日志队列

    # --- 1. 样式定义 ---
    ui.add_head_html(
        """
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
            :root { --c-bg: #F8FAFC; --c-accent: #6366F1; --c-text: #1E293B; }
            body { background-color: var(--c-bg); font-family: 'Plus Jakarta Sans', sans-serif; color: var(--c-text); }
            .nav-capsule { background: rgba(255, 255, 255, 0.85); backdrop-filter: blur(12px); border: 1px solid rgba(255,255,255,0.6); box-shadow: 0 4px 20px rgba(0,0,0,0.03); border-radius: 100px; padding: 10px 24px; }
            .input-glass { background: white; border-radius: 24px; box-shadow: 0 10px 30px -5px rgba(0, 0, 0, 0.05); border: 2px solid #CBD5E1; transition: all 0.5s cubic-bezier(0.4, 0, 0.2, 1); display: flex !important; flex-direction: column !important; overflow: hidden !important; max-height: 800px; }
            .input-expanded { max-height: 800px !important; border-color: #6366F1 !important; box-shadow: 0 20px 50px -10px rgba(99, 102, 241, 0.15) !important; }
            .input-expanded textarea { max-height: 600px !important; }
            .input-collapsed { max-height: 250px !important; border-color: #E2E8F0; }
            .input-collapsed textarea { max-height: 140px !important; overflow-y: auto !important; }
            .input-glass textarea { scrollbar-width: none; -ms-overflow-style: none; }
            .input-glass textarea::-webkit-scrollbar { display: none; }
            .compact-tabs { min-height: 36px !important; height: 36px !important; }
            .compact-tabs .q-tab { min-height: 36px !important; padding: 0 20px !important; }
            .compact-tabs .q-tab__icon { font-size: 18px !important; }
            .compact-tabs .q-tab__label { font-size: 13px !important; font-weight: 600 !important; }
            .terminal-window { background: #1E293B; color: #E2E8F0; font-family: 'JetBrains Mono', monospace; border-radius: 20px; overflow: hidden; box-shadow: 0 20px 40px -15px rgba(15, 23, 42, 0.2); }
            .result-panel { background: white; border-radius: 24px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); border: 1px solid #E2E8F0; overflow: hidden; }
            .yaml-code-box pre { background: #F8FAFC !important; margin: 0 !important; padding: 2rem !important; }
            .yaml-code-box code { color: #1E293B !important; text-shadow: none !important; font-family: 'JetBrains Mono', monospace !important; }
            .history-drawer { background: rgba(248, 250, 252, 0.4) !important; backdrop-filter: blur(30px) saturate(150%); border-left: 1px solid rgba(255, 255, 255, 0.5); }
            .history-card { background: rgba(255, 255, 255, 0.6); backdrop-filter: blur(10px); border: 1px solid rgba(226, 232, 240, 0.8); border-radius: 24px; transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1); cursor: pointer; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03); }
            .history-card:hover { background: white; border-color: #6366F1; transform: translateY(-4px) scale(1.02); box-shadow: 0 20px 25px -5px rgba(99, 102, 241, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04); }
            .history-card:active { transform: translateY(-2px) scale(0.98); }
        </style>
        """,
        shared=True,
    )

    # --- 2. 逻辑函数定义 (必须在 UI 组件之前) ---
    def update_card_style():
        if state["is_focused"]: input_card.classes(add="input-expanded", remove="input-collapsed")
        else: input_card.classes(add="input-collapsed", remove="input-expanded")

    def reset_ui():
        """重置页面到初始状态"""
        query_input.value = ""
        state["is_generating"] = False
        state["has_result"] = False
        status_container.classes(add="hidden")
        result_section.classes(add="hidden")
        log_content.clear()
        status_label.text = "Ready"
        ui.notify("已开启新对话", type="info")
        update_card_style()

    def update_ui_logs():
        if not log_queue: return
        while log_queue:
            message = log_queue.pop(0)
            status_label.text = "正在推演..."
            with log_content: ui.label(f">> {message}").classes("text-indigo-300 font-mono text-xs leading-relaxed break-all")
        log_scroll.scroll_to(percent=1.0)
        ui.timer(0.1, lambda: log_scroll.scroll_to(percent=1.0, duration=0.2), once=True)

    def load_history():
        history_list_container.clear()
        try:
            with Session(engine) as session:
                statement = select(WorkflowHistory).where(WorkflowHistory.category == "workflow").order_by(desc(WorkflowHistory.created_at)).limit(20)
                results = session.exec(statement).all()
                if not results:
                    with history_list_container: ui.label("暂无历史记录").classes("text-slate-400 text-sm mt-10 w-full text-center")
                    return
                for record in results:
                    with history_list_container:
                        with ui.card().classes('history-card w-full p-4 gap-2') as card:
                            card.on('click', lambda r=record: restore_history(r))
                            with ui.row().classes('w-full items-center justify-between'):
                                with ui.row().classes('gap-3'):
                                    ui.label(record.created_at.strftime("%Y-%m-%d")).classes("text-[10px] font-bold text-slate-400 uppercase tracking-tighter")
                                    ui.label(record.created_at.strftime("%H:%M")).classes("text-[10px] font-bold text-indigo-400 uppercase tracking-tighter")
                                status_color = "green" if record.status == "success" else "red"
                                ui.icon("circle", size="8px", color=status_color)
                            ui.label(record.user_request).classes("text-sm text-slate-700 font-medium line-clamp-2")
                            with ui.row().classes('w-full items-center gap-1'):
                                ui.icon("terminal", size="12px", color="slate-400")
                                ui.label(record.model_name or "unknown").classes("text-[10px] text-slate-400")
        except Exception as e:
            logger.error(f"加载历史记录失败: {e}")
            with history_list_container: ui.label("无法连接数据库").classes("text-red-400 text-sm mt-10 w-full text-center")

    async def restore_history(record: WorkflowHistory):
        ui.notify(f"正在恢复历史记录: {record.created_at.strftime('%H:%M')}")
        query_input.value = record.user_request
        yaml_display.content = record.final_yaml
        yaml_display.update()
        mermaid_display.set_content(dify_yaml_to_mermaid(record.final_yaml))
        result_section.classes(remove="hidden")
        history_drawer.hide()

    async def run_design():
        if not query_input.value or len(query_input.value) < 2:
            ui.notify("需求描述太短了", type="warning")
            return
        query_input.run_method('blur')
        state["is_generating"] = True
        state["has_result"] = True
        update_card_style()
        status_container.classes(remove="hidden")
        log_content.clear()
        with log_content: ui.label("> 推演引擎初始化完成").classes("text-slate-500 font-mono text-xs")
        async def ui_callback(message: str): log_queue.append(message)
        try:
            yaml_output = await agent_service.generate_yaml(user_request=query_input.value, status_callback=ui_callback)
            while log_queue: await asyncio.sleep(0.1)
            state["is_generating"] = False
            status_label.text = "构建完成"
            yaml_display.content = yaml_output
            yaml_display.update()
            mermaid_display.set_content(dify_yaml_to_mermaid(yaml_output))
            result_section.classes(remove="hidden")
            ui.notify("工作流架构已构建完成", type="positive", color="indigo")
        except Exception as e:
            logger.exception("生成失败")
            state["is_generating"] = False
            status_label.text = "Process Failed"
            ui.notify(f"系统错误: {str(e)}", type="negative")
            with log_content: ui.label(f"!! 错误: {str(e)}").classes("text-red-400 font-mono text-xs")

    # --- 3. UI 布局 ---
    with ui.drawer(value=False, fixed=False, side='right').classes('history-drawer p-0 w-80 shadow-2xl') as history_drawer:
        with ui.column().classes('w-full h-full p-6 gap-6'):
            with ui.row().classes('w-full items-center justify-between'):
                ui.label("历史推演").classes("text-xl font-bold text-slate-800")
                ui.button(icon="close", on_click=lambda: history_drawer.toggle()).props("flat round color=grey-7 size=sm")
            history_list_container = ui.column().classes('w-full gap-4')

    ui.timer(0.1, update_ui_logs)

    with ui.row().classes("w-full justify-center sticky top-4 z-50 pointer-events-none"):
        with ui.row().classes("nav-capsule items-center gap-6 pointer-events-auto"):
            with ui.row().classes("items-center gap-2"):
                ui.icon("hub", size="20px", color="indigo-500")
                ui.label("Workflow Architect").classes("font-bold text-lg text-slate-800")
            ui.separator().props("vertical").classes("h-4 bg-slate-200")
            with ui.row().classes("items-center gap-2"):
                ui.button("新对话", icon="add", on_click=reset_ui).props("flat dense color=indigo-5 size=sm").classes("px-4")
                ui.button("历史", icon="history", on_click=lambda: (load_history(), history_drawer.toggle())).props("flat dense color=indigo-5 size=sm").classes("px-4")
                ui.button("返回首页", on_click=lambda: ui.navigate.to("/")).props("flat dense color=grey-7 size=sm")

    with ui.column().classes("w-full max-w-6xl mx-auto px-6 pt-20 pb-32 items-center gap-16 transition-all duration-500"):
        with ui.column().classes("w-full max-w-3xl items-center text-center gap-8 transition-all duration-500") as hero_section:
            with ui.column().classes("gap-2 transition-all items-center"):
                ui.label("Dify 工作流架构师").classes("text-4xl md:text-5xl font-extrabold text-slate-900 tracking-tight")
                ui.label("描述您的业务场景，AI 将自动推演逻辑并生成 YAML 蓝图。").classes("text-lg text-slate-500")
            input_card = ui.card().classes("input-glass w-full p-4 pb-2 relative transition-all duration-500")
            with input_card:
                query_input = ui.textarea(placeholder="在此输入您的工作流需求...").classes("w-full text-lg text-slate-700 mb-2").props("borderless autogrow rows=1")
                with ui.row().classes("w-full justify-end"):
                    ui.button(icon="arrow_upward", on_click=lambda: run_design()).classes("rounded-xl w-10 h-10 transition-transform active:scale-95 flex-shrink-0 mb-1 shadow-md shadow-indigo-500/20").props("unelevated color=indigo-500")
            query_input.on("focus", lambda: (state.update({"is_focused": True}), update_card_style()))
            query_input.on("blur", lambda: (state.update({"is_focused": False}), ui.timer(0.1, update_card_style, once=True)))

        with ui.column().classes("w-full max-w-3xl hidden gap-4 transition-all") as status_container:
            with ui.row().classes("w-full items-center gap-3 px-2"):
                ui.spinner(size="sm", color="indigo-500").bind_visibility_from(state, "is_generating")
                status_label = ui.label("Ready").classes("font-bold text-slate-400 text-sm uppercase tracking-widest")
            with ui.element('div').classes("terminal-window w-full flex flex-col h-[320px]"):
                log_scroll = ui.scroll_area().classes("w-full h-full p-6")
                with log_scroll: log_content = ui.column().classes("w-full gap-2")

        with ui.column().classes("w-full max-w-3xl transition-all duration-700 hidden") as result_section:
            with ui.row().classes("w-full justify-center mb-6"):
                with ui.tabs().classes("bg-white p-1 rounded-full shadow-sm border border-slate-200 compact-tabs") as tabs:
                    tab_visual = ui.tab("架构蓝图", icon="account_tree")
                    tab_code = ui.tab("YAML 源码", icon="code")
            with ui.card().classes("result-panel w-full h-[800px] relative"):
                with ui.tab_panels(tabs, value=tab_visual).classes("w-full h-full"):
                    with ui.tab_panel(tab_visual).classes("p-0 w-full h-full bg-slate-50 relative overflow-hidden"):
                        mermaid_display = ui.mermaid("").classes("w-full h-full p-8")
                        ui.label("支持缩放与拖拽").classes("absolute bottom-6 right-6 text-[10px] font-bold text-slate-300 uppercase tracking-widest bg-white/80 px-3 py-1.5 rounded-full border border-slate-100")
                    with ui.tab_panel(tab_code).classes("p-0 w-full h-full"): 
                        yaml_display = ui.code("", language="yaml").classes("w-full h-full text-[13px] yaml-code-box")
                        def download_yaml():
                            if not yaml_display.content: return
                            try:
                                data = pyyaml.safe_load(yaml_display.content)
                                file_name = data.get('app', {}).get('name', 'workflow')
                            except: file_name = "workflow"
                            ui.download(yaml_display.content.encode('utf-8'), f"{file_name}.yml")
                            ui.notify(f"正在下载: {file_name}.yml", type="positive")
                        with ui.row().classes("absolute top-6 right-6 gap-2"):
                            ui.button(icon="download", on_click=download_yaml).props("flat round color=indigo-4 size=sm").classes("opacity-60 hover:opacity-100").tooltip("下载 YAML")
                            ui.button(icon="content_copy", on_click=lambda: (ui.clipboard.write(yaml_display.content), ui.notify("已复制到剪贴板"))).props("flat round color=grey-6 size=sm").classes("opacity-40 hover:opacity-100").tooltip("复制源码")
