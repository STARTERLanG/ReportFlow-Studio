import asyncio
from nicegui import ui
from agents.workflows.dify_yaml_generator import YamlAgentService
from app.server.logger import logger
from app.server.utils.visualizer import dify_yaml_to_mermaid

# 初始化服务
agent_service = YamlAgentService()

def render_yaml_generator_page():
    # --- 样式定义 ---
    ui.add_head_html(
        """
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
            
            :root {
                --c-bg: #F8FAFC;
                --c-accent: #6366F1;
                --c-text: #1E293B;
            }

            body { 
                background-color: var(--c-bg);
                font-family: 'Plus Jakarta Sans', sans-serif;
                color: var(--c-text);
            }

            .nav-capsule {
                background: rgba(255, 255, 255, 0.85);
                backdrop-filter: blur(12px);
                border: 1px solid rgba(255,255,255,0.6);
                box-shadow: 0 4px 20px rgba(0,0,0,0.03);
                border-radius: 100px;
                padding: 10px 24px;
            }

            /* 输入框卡片容器 - 基础状态 */
            .input-glass {
                background: white;
                border-radius: 24px;
                box-shadow: 0 10px 30px -5px rgba(0, 0, 0, 0.05);
                border: 2px solid #CBD5E1;
                transition: all 0.5s cubic-bezier(0.4, 0, 0.2, 1);
                display: flex !important;
                flex-direction: column !important;
                overflow: hidden !important;
                max-height: 800px;
            }
            
            /* 展开状态 (默认/聚焦) */
            .input-expanded {
                max-height: 800px !important;
                border-color: #6366F1 !important;
                box-shadow: 0 20px 50px -10px rgba(99, 102, 241, 0.15) !important;
            }
            .input-expanded textarea {
                max-height: 600px !important;
            }

            /* 强制折叠状态 (生成中/失焦结果态) */
            .input-collapsed {
                max-height: 250px !important;
                border-color: #E2E8F0;
            }
            .input-collapsed textarea {
                max-height: 140px !important; /* 关键：压缩高度为按钮留出空间 */
                overflow-y: auto !important;
            }

            .input-glass textarea {
                scrollbar-width: none;
                -ms-overflow-style: none;
            }
            .input-glass textarea::-webkit-scrollbar { display: none; }

            .compact-tabs {
                min-height: 36px !important;
                height: 36px !important;
            }
            .compact-tabs .q-tab {
                min-height: 36px !important;
                padding: 0 20px !important;
            }
            .compact-tabs .q-tab__icon { font-size: 18px !important; }
            .compact-tabs .q-tab__label { font-size: 13px !important; font-weight: 600 !important; }

            .terminal-window {
                background: #1E293B;
                color: #E2E8F0;
                font-family: 'JetBrains Mono', monospace;
                border-radius: 20px;
                overflow: hidden;
                box-shadow: 0 20px 40px -15px rgba(15, 23, 42, 0.2);
            }

            .result-panel {
                background: white;
                border-radius: 24px;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
                border: 1px solid #E2E8F0;
                overflow: hidden;
            }
            
            .yaml-code-box pre {
                background: #F8FAFC !important;
                margin: 0 !important;
                padding: 2rem !important;
            }
            .yaml-code-box code {
                color: #1E293B !important;
                text-shadow: none !important;
                font-family: 'JetBrains Mono', monospace !important;
            }
        </style>
        """,
        shared=True,
    )

    state = {
        "is_generating": False,
        "has_result": False,
        "is_focused": False
    }

    # --- 导航栏 ---
    with ui.row().classes("w-full justify-center sticky top-4 z-50 pointer-events-none"):
        with ui.row().classes("nav-capsule items-center gap-6 pointer-events-auto"):
            with ui.row().classes("items-center gap-2"):
                ui.icon("hub", size="20px", color="indigo-500")
                ui.label("Workflow Architect").classes("font-bold text-lg text-slate-800")
            ui.separator().props("vertical").classes("h-4 bg-slate-200")
            ui.button("返回首页", on_click=lambda: ui.navigate.to("/")).props("flat dense color=grey-7 size=sm")

    # --- 主容器 ---
    with ui.column().classes("w-full max-w-6xl mx-auto px-6 pt-20 pb-32 items-center gap-16 transition-all duration-500"):
        
        # 1. 标题与输入区
        hero_section = ui.column().classes("w-full max-w-3xl items-center text-center gap-8 transition-all duration-500")
        with hero_section:
            with ui.column().classes("gap-2 transition-all items-center") as title_group:
                ui.label("Dify 工作流架构师").classes("text-4xl md:text-5xl font-extrabold text-slate-900 tracking-tight")
                ui.label("描述您的业务场景，AI 将自动推演逻辑并生成 YAML 蓝图。").classes("text-lg text-slate-500")

            # 输入框卡片
            input_card = ui.card().classes("input-glass w-full p-4 pb-2 relative transition-all duration-500")
            
            def update_card_style():
                # 核心逻辑：只要没聚焦，就折叠
                if state["is_focused"]:
                    input_card.classes(add="input-expanded", remove="input-collapsed")
                else:
                    input_card.classes(add="input-collapsed", remove="input-expanded")

            with input_card:
                query_input = ui.textarea(
                    placeholder="在此输入您的工作流需求..."
                ).classes("w-full text-lg text-slate-700 mb-2").props("borderless autogrow rows=1")
                
                with ui.row().classes("w-full justify-end"):
                    send_btn = ui.button(icon="arrow_upward", on_click=lambda: run_design()).classes("rounded-xl w-10 h-10 transition-transform active:scale-95 flex-shrink-0 mb-1 shadow-md shadow-indigo-500/20").props("unelevated color=indigo-500")

            # 聚焦与失焦事件
            def on_focus():
                state["is_focused"] = True
                update_card_style()
            
            def on_blur():
                state["is_focused"] = False
                ui.timer(0.1, update_card_style, once=True)

            query_input.on("focus", on_focus)
            query_input.on("blur", on_blur)


        # 2. 状态与日志
        status_container = ui.column().classes("w-full max-w-3xl hidden gap-4 transition-all")
        with status_container:
            with ui.row().classes("w-full items-center gap-3 px-2"):
                ui.spinner(size="sm", color="indigo-500").bind_visibility_from(state, "is_generating")
                status_label = ui.label("Ready").classes("font-bold text-slate-400 text-sm uppercase tracking-widest")

            with ui.element('div').classes("terminal-window w-full flex flex-col h-[320px]"):
                log_scroll = ui.scroll_area().classes("w-full h-full p-6")
                with log_scroll:
                    log_content = ui.column().classes("w-full gap-2")


        # 3. 结果展示区
        result_section = ui.column().classes("w-full max-w-3xl transition-all duration-700 hidden")
        with result_section:
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
                        ui.button(icon="content_copy", on_click=lambda: ui.clipboard.write(yaml_display.content)).props("flat round color=grey-6 size=sm").classes("absolute top-6 right-6 opacity-40 hover:opacity-100")

    # --- 逻辑处理 ---
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
        
        with log_content:
            ui.label("> Architect Engine Initialized.").classes("text-slate-500 font-mono text-xs")

        async def ui_callback(message: str):
            status_label.text = "Thinking..." 
            with log_content:
                ui.label(f">> {message}").classes("text-indigo-300 font-mono text-xs leading-relaxed break-all")
            log_scroll.scroll_to(percent=1.0)

        try:
            yaml_output = await agent_service.generate_yaml(user_request=query_input.value, status_callback=ui_callback)
            
            state["is_generating"] = False
            status_label.text = "Build Complete"
            
            yaml_display.content = yaml_output
            yaml_display.update()
            
            mermaid_syntax = dify_yaml_to_mermaid(yaml_output)
            mermaid_display.set_content(mermaid_syntax)
            
            result_section.classes(remove="hidden")
            await asyncio.sleep(0.2) 
            
            ui.notify("工作流架构已构建完成", type="positive", color="indigo")

        except Exception as e:
            logger.exception("生成失败")
            state["is_generating"] = False
            status_label.text = "Process Failed"
            ui.notify(f"系统错误: {str(e)}", type="negative")
            with log_content:
                ui.label(f"!! ERROR: {str(e)}").classes("text-red-400 font-mono text-xs")
