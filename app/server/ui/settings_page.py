import os
import shutil
import tempfile
from datetime import datetime
from nicegui import ui, events
from sqlmodel import Session, select
from app.server.database import engine
from app.server.models.settings import SystemSetting
from app.server.logger import logger
from agents.memories.vector_store import RagService
from app.server.ui.styles import SETTINGS_STYLE

def render_settings_page():
    ui.add_head_html(SETTINGS_STYLE)
    
    # 1. 配置预加载
    memo_configs = {}
    try:
        with Session(engine) as session:
            db_items = session.exec(select(SystemSetting)).all()
            memo_configs = {item.key: item.value for item in db_items}
    except Exception as e: logger.error(f"Preload failed: {e}")

    nav_buttons = {}
    
    # 2. 核心保存逻辑
    def save_all_to_db(configs_to_save):
        try:
            with Session(engine) as session:
                for k, v in configs_to_save.items():
                    db_item = session.get(SystemSetting, k)
                    if db_item: db_item.value = v
                    else: session.add(SystemSetting(key=k, value=v))
                    os.environ[k] = str(v)
                session.commit()
            ui.notify("设置已成功应用并保存", type="positive")
        except Exception as e: ui.notify(f"保存失败: {e}", type="negative")

    # 3. 标签控制
    current_tab_state = ui.tabs().classes('hidden')
    def set_tab(name):
        current_tab_state.value = name
        for tid, btn in nav_buttons.items():
            if tid == name: btn.classes(add='nav-active')
            else: btn.classes(remove='nav-active')

    # 4. UI 单元组件
    def kv_input(label, key, default="", is_password=False, store=None):
        with ui.element("div").classes("kv-row"):
            ui.label(label).classes("kv-key")
            val = str(memo_configs.get(key, os.getenv(key, default)))
            if store is not None: store[key] = val
            inp = ui.input(value=val).classes("glass-input").props(f"borderless dense {'type=password' if is_password else ''}")
            if is_password:
                with inp.add_slot('append'):
                    def toggle():
                        is_pwd = inp.props['type'] == 'password'
                        inp.props(f"type={'text' if is_pwd else 'password'}")
                        eye.props(f"icon={'visibility_off' if is_pwd else 'visibility'}")
                    eye = ui.button(on_click=toggle).props('flat round dense icon=visibility color=slate-200 size=8px').classes('opacity-60 hover:opacity-100')
                    ui.button(on_click=lambda: (ui.clipboard.write(inp.value), ui.notify("已复制"))).props('flat round dense icon=content_copy color=slate-200 size=8px').classes('opacity-60 hover:opacity-100 ml-1')
            if store is not None: inp.on("change", lambda e: store.update({key: e.value}))

    def render_file_manager(directory, extensions):
        os.makedirs(directory, exist_ok=True)
        container = ui.column().classes("w-full mt-8")
        def refresh():
            container.clear()
            files = [f for f in os.listdir(directory) if f.lower().endswith(tuple(extensions))]
            if not files:
                with container: ui.label("暂无文件记录").classes("text-slate-300 py-12 w-full text-center text-xs")
                return
            for f in files:
                with container, ui.row().classes("w-full items-center justify-between p-4 bg-white/40 rounded-2xl mb-2"):
                    ui.label(f).classes("text-sm font-bold text-slate-700")
                    def do_del(name=f):
                        os.remove(os.path.join(directory, name))
                        refresh(); ui.notify(f"已移除: {name}")
                    ui.button(icon="delete", on_click=do_del).props("flat round color=red-3")
        ui.upload(on_upload=lambda e: (open(os.path.join(directory,e.file.name),'wb').write(e.file.read()), refresh(), ui.notify("上传成功"))).props("flat bordered rounded").classes("w-full")
        refresh()

    # --- 布局结构 ---
    with ui.column().classes("w-full h-screen items-center justify-center p-6"):
        with ui.row().classes("settings-container w-full no-wrap gap-0"):
            # 左侧导航
            with ui.column().classes("settings-nav w-84 p-10 flex-shrink-0"):
                with ui.row().classes("items-center gap-4 mb-16 px-2"):
                    ui.button(icon="arrow_back", on_click=lambda: ui.navigate.to("/")).props("flat round color=slate-400 size=lg")
                    ui.label("设置").classes("text-3xl font-black text-slate-800")
                def n_btn(l, i, t):
                    btn = ui.row().classes(f"nav-item w-full items-center gap-4 {'nav-active' if t == 'general' else ''}")
                    with btn: ui.icon(i, size="24px"); ui.label(l)
                    btn.on("click", lambda: set_tab(t))
                    nav_buttons[t] = btn
                n_btn("通用配置", "tune", "general")
                n_btn("AI 引擎内核", "shutter_speed", "llm")
                ui.label("知识图谱").classes("text-[11px] font-black text-slate-400 mt-12 mb-6 ml-6 uppercase")
                n_btn("Dify 参考库", "auto_awesome_mosaic", "kb_dify")
                n_btn("分类知识库", "account_tree", "kb_classify")
                n_btn("业务 RAG", "menu_book", "kb_rag")

            # 右侧内容区 (TabPanels)
            with ui.column().classes("flex-grow h-full content-area-scroll bg-transparent"):
                with ui.tab_panels(current_tab_state, value='general').classes('bg-transparent w-full'):
                    with ui.tab_panel('general'):
                        gen_data = {}
                        with ui.column().classes("content-card w-full"):
                            ui.label("通用配置").classes("section-title")
                            kv_input("应用名称", "APP_NAME", "ReportFlow Studio", store=gen_data)
                            kv_input("调试模式", "DEBUG_MODE", "False", store=gen_data)
                            ui.button("保存通用配置", on_click=lambda: save_all_to_db(gen_data)).classes("save-btn bg-indigo-600 text-white mt-10")

                    with ui.tab_panel('llm'):
                        llm_data = {}
                        with ui.column().classes("content-card w-full"):
                            ui.label("AI 引擎内核").classes("section-title")
                            with ui.row().classes("config-group-label"): ui.label("认知模型 (LLM)")
                            kv_input("模型 ID", "LLM_MODEL_NAME", "gpt-4o", store=llm_data)
                            kv_input("API 路由地址", "OPENAI_BASE_URL", "https://api.openai.com/v1", store=llm_data)
                            kv_input("安全密钥", "OPENAI_API_KEY", is_password=True, store=llm_data)
                            kv_input("采样随机度", "LLM_TEMPERATURE", "0.0", store=llm_data)
                            with ui.row().classes("config-group-label"): ui.label("向量引擎 (Embedding)")
                            kv_input("提供商", "EMBEDDING_PROVIDER", "openai", store=llm_data)
                            kv_input("向量模型 ID", "EMBEDDING_MODEL_NAME", "text-embedding-3-small", store=llm_data)
                            kv_input("专用密钥", "EMBEDDING_API_KEY", is_password=True, store=llm_data)
                            with ui.row().classes("config-group-label"): ui.label("向量数据库 (Qdrant)")
                            kv_input("连接 URL", "QDRANT_URL", "http://localhost:6333", store=llm_data)
                            kv_input("访问令牌", "QDRANT_API_KEY", is_password=True, store=llm_data)
                            ui.button("应用引擎配置", on_click=lambda: save_all_to_db(llm_data)).classes("save-btn bg-indigo-600 text-white mt-10")

                    with ui.tab_panel('kb_dify'):
                        with ui.column().classes("content-card w-full"):
                            ui.label("Dify 参考库").classes("section-title")
                            directory = "docs/references"
                            os.makedirs(directory, exist_ok=True)
                            def get_data():
                                files = sorted([f for f in os.listdir(directory) if f.lower().endswith(('.yml', '.yaml'))])
                                return [{'index': i+1, 'name': f, 'size': f"{os.path.getsize(os.path.join(directory, f))/1024:.1f} KB", 'id': f} for i, f in enumerate(files)]
                            with ui.row().classes('w-full items-center justify-between mb-8'):
                                search = ui.input(placeholder='搜索...').props('rounded outlined dense').classes('w-64 bg-white')
                                ui.button('添加参考', icon='add', on_click=lambda: up_dlg.open()).props('unelevated color=indigo-600 rounded')
                            table = ui.table(columns=[
                                {'name': 'index', 'label': '', 'field': 'index', 'align': 'left'},
                                {'name': 'name', 'label': '文件名', 'field': 'name', 'align': 'left', 'sortable': True},
                                {'name': 'size', 'label': '大小', 'field': 'size', 'align': 'center'},
                                {'name': 'actions', 'label': '操作', 'field': 'id', 'align': 'right'}
                            ], rows=get_data()).classes('w-full nicegui-table')
                            table.bind_filter_from(search, 'value')
                            table.add_slot('body-cell-index', '<q-td :props="props"><div class="index-badge">{{props.value}}</div></q-td>')
                            table.add_slot('body-cell-actions', '<q-td :props="props" class="text-right"><q-btn flat round dense icon="edit_note" color="teal" @click="() => $parent.$emit(\'edit\', props.value)" /><q-btn flat round dense icon="delete" color="red-2" @click="() => $parent.$emit(\'delete\', props.value)" /></q-td>')
                            async def edit_fn(file_id):
                                path = os.path.join(directory, file_id)
                                with open(path, 'r', encoding='utf-8') as f: content = f.read()
                                with ui.dialog() as dlg, ui.card().classes('p-0 w-[1000px] max-w-[95vw] overflow-hidden rounded-3xl'):
                                    with ui.column().classes('w-full h-[80vh] gap-0'):
                                        with ui.row().classes('w-full p-6 items-center justify-between bg-slate-50/80 border-b'):
                                            ui.label(f'编辑文件: {file_id}').classes('text-lg font-bold')
                                            ui.button(icon='close', on_click=dlg.close).props('flat round dense')
                                        ed = ui.textarea(value=content).classes('w-full flex-grow full-height-editor font-mono text-sm').props('borderless autogrow=false')
                                        with ui.row().classes('p-6 justify-end w-full gap-3 border-t'):
                                            ui.button('保存更改', on_click=lambda: (open(path,'w',encoding='utf-8').write(ed.value), ui.notify("已保存"), dlg.close())).props('unelevated color=teal-500 rounded')
                                dlg.open()
                            table.on('edit', lambda e: edit_fn(e.args))
                            table.on('delete', lambda e: (os.remove(os.path.join(directory, e.args)), ui.notify("已删除"), setattr(table, 'rows', get_data())))
                            with ui.dialog() as up_dlg, ui.card().classes('p-6'):
                                ui.upload(on_upload=lambda e: (open(os.path.join(directory,e.file.name),'wb').write(e.file.read()), setattr(table, 'rows', get_data()), up_dlg.close())).props('accept=.yml,.yaml flat rounded')

                    with ui.tab_panel('kb_classify'):
                        with ui.column().classes("content-card w-full"):
                            ui.label("分类参考库").classes("section-title")
                            render_file_manager("docs/classify_refs", [".txt", ".json"])

                    with ui.tab_panel('kb_rag'):
                        with ui.column().classes("content-card w-full"):
                            ui.label("业务 RAG 知识库").classes("section-title")
                            render_file_manager("docs/rag_docs", [".pdf", ".docx", ".txt"])
