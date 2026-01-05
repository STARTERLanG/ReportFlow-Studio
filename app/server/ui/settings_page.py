import os

from nicegui import events, ui
from sqlmodel import Session

from app.server.database import engine
from app.server.models.settings import SystemSetting

# --- 全局样式常量 ---
SETTINGS_STYLE = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
    body { background: linear-gradient(135deg, #F8FAFC 0%, #E0E7FF 100%); font-family: 'Plus Jakarta Sans', sans-serif; }
    .settings-container {
        width: 95%; max-width: 1600px; margin: 0 auto; height: 92vh; margin-top: 4vh;
        background: rgba(255, 255, 255, 0.4); backdrop-filter: blur(40px) saturate(180%);
        border-radius: 40px; border: 1px solid rgba(255, 255, 255, 0.7);
        overflow: hidden; box-shadow: 0 40px 100px -20px rgba(0, 0, 0, 0.1);
    }
    .settings-nav { background: rgba(255, 255, 255, 0.3); border-right: 1px solid rgba(255, 255, 255, 0.5); height: 100%; }
    .nav-item {
        border-radius: 20px; transition: all 0.4s; cursor: pointer;
        margin-bottom: 8px; font-weight: 600; color: #64748B; padding: 14px 24px;
    }
    .nav-item:hover { background: rgba(255, 255, 255, 0.8); color: #6366F1; transform: translateX(8px); }
    .nav-active { background: white !important; color: #6366F1 !important; box-shadow: 0 10px 20px -5px rgba(99, 102, 241, 0.15); }
    .content-area-scroll { height: 100%; overflow-y: auto; padding: 60px 80px; }
    .content-card {
        background: rgba(255, 255, 255, 0.65); border-radius: 32px;
        backdrop-filter: blur(15px); border: 1px solid white;
        padding: 64px; width: 100%; max-width: 1200px; margin: 0 auto;
        box-shadow: 0 10px 40px -10px rgba(0, 0, 0, 0.02);
    }
    .section-title { font-size: 2.5rem; font-weight: 900; color: #0F172A; letter-spacing: -0.04em; margin-bottom: 12px; }
    .section-desc { font-size: 1.1rem; color: #94A3B8; margin-bottom: 56px; }
    .kv-row {
        display: flex; align-items: center; justify-content: flex-start;
        padding: 10px 20px; border-radius: 20px; margin-bottom: 6px;
        transition: all 0.3s; gap: 40px; width: 100%;
    }
    .kv-row:hover { background: rgba(255, 255, 255, 0.6); }
    .kv-key { font-weight: 700; color: #475569; font-size: 0.95rem; width: 180px; flex-shrink: 0; }
    .glass-input { flex-grow: 1 !important; background: white !important; border-radius: 14px !important; }
    .glass-input .q-field__control {
        background: rgba(248, 250, 252, 0.8) !important; border-radius: 14px !important;
        border: 1px solid rgba(226, 232, 240, 0.8) !important; padding: 0 16px !important;
    }
    .glass-input .q-field__control:before, .glass-input .q-field__control:after { display: none !important; }
    .config-group-label {
        font-size: 0.75rem; font-weight: 800; color: #6366F1;
        text-transform: uppercase; letter-spacing: 0.2em; margin: 56px 0 24px 20px;
        display: flex; align-items: center; gap: 10px;
    }
    .save-btn { border-radius: 24px !important; height: 64px !important; padding: 0 56px !important; font-weight: 800 !important; }
    .nicegui-table thead tr { background: #F0FDFA !important; }
    .nicegui-table thead th { color: #0D9488 !important; font-weight: 800 !important; font-size: 0.8rem; padding: 16px !important; background: #F0FDFA !important; }
    .nicegui-table tbody tr { background: rgba(255, 255, 255, 0.3) !important; transition: background 0.3s !important; border-bottom: 4px solid transparent !important; }
    .nicegui-table tbody tr:hover { background: white !important; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03); }
    .index-badge { background: #EEF2FF; color: #6366F1; width: 28px; height: 28px; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 0.75rem; }
    
    /* 强制编辑器填充父容器 */
    .full-height-editor { height: 100% !important; display: flex !important; flex-direction: column !important; }
    .full-height-editor .q-field__control, 
    .full-height-editor .q-field__control-container, 
    .full-height-editor .q-field__native { 
        height: 100% !important; 
        padding: 32px !important;
    }
</style>
"""


def render_settings_page():
    ui.add_head_html(SETTINGS_STYLE)

    nav_buttons = {}
    config_values = {}

    def get_config(key, default=""):
        try:
            with Session(engine) as session:
                db_val = session.get(SystemSetting, key)
                if db_val:
                    return str(db_val.value)
        except:
            pass
        return os.getenv(key, default)

    def save_config(key, value):
        with Session(engine) as session:
            db_setting = session.get(SystemSetting, key)
            if db_setting:
                db_setting.value = value
            else:
                db_setting = SystemSetting(key=key, value=value)
            session.add(db_setting)
            session.commit()
        os.environ[key] = str(value)

    def set_tab(name):
        for tab_id, btn in nav_buttons.items():
            if tab_id == name:
                btn.classes(add="nav-active")
            else:
                btn.classes(remove="nav-active")
        content_area.clear()
        with content_area:
            if name == "general":
                render_general_settings()
            elif name == "llm":
                render_llm_settings()
            elif name == "kb_dify":
                render_kb_dify()
            elif name == "kb_classify":
                render_kb_classify()
            elif name == "kb_rag":
                render_kb_rag()

    def kv_input(label, key, default="", is_password=False):
        with ui.element("div").classes("kv-row"):
            ui.label(label).classes("kv-key")
            current_val = get_config(key, default)
            config_values[key] = current_val
            inp = (
                ui.input(value=current_val)
                .classes("glass-input")
                .props(f"borderless dense {'type=password' if is_password else ''}")
            )
            if is_password:
                with inp.add_slot("append"):

                    def toggle():
                        is_pwd = inp.props["type"] == "password"
                        inp.props(f"type={'text' if is_pwd else 'password'}")
                        eye.props(f"icon={'visibility_off' if is_pwd else 'visibility'}")

                    eye = (
                        ui.button(on_click=toggle)
                        .props("flat round dense icon=visibility color=slate-200 size=8px")
                        .classes("opacity-60 hover:opacity-100")
                    )
                    ui.button(on_click=lambda: (ui.clipboard.write(inp.value), ui.notify("已复制"))).props(
                        "flat round dense icon=content_copy color=slate-200 size=8px"
                    ).classes("opacity-60 hover:opacity-100 ml-1")
            inp.on("change", lambda e: config_values.update({key: e.value}))

    def render_general_settings():
        with ui.column().classes("w-full"):
            ui.label("通用配置").classes("section-title")
            ui.label("管理系统的全局运行环境。").classes("section-desc")
            kv_input("应用显示名称", "APP_NAME", "ReportFlow Studio")
            kv_input("调试模式", "DEBUG_MODE", "False")

            def save_all():
                for k, v in config_values.items():
                    save_config(k, v)
                ui.notify("配置已保存")

            ui.button("保存配置", on_click=save_all).classes("save-btn bg-indigo-600 text-white mt-10")

    def render_llm_settings():
        with ui.column().classes("w-full"):
            ui.label("AI 引擎内核").classes("section-title")
            ui.label("大模型与向量引擎参数设置。").classes("section-desc")
            with ui.row().classes("config-group-label"):
                ui.label("认知模型 (LLM)")
            kv_input("模型 ID", "LLM_MODEL_NAME", "gpt-4o")
            kv_input("API 路由地址", "OPENAI_BASE_URL", "https://api.openai.com/v1")
            kv_input("安全密钥", "OPENAI_API_KEY", is_password=True)
            kv_input("采样随机度", "LLM_TEMPERATURE", "0.0")
            with ui.row().classes("config-group-label"):
                ui.label("向量引擎 (Embedding)")
            kv_input("提供商", "EMBEDDING_PROVIDER", "openai")
            kv_input("向量模型 ID", "EMBEDDING_MODEL_NAME", "text-embedding-3-small")
            kv_input("专用密钥", "EMBEDDING_API_KEY", is_password=True)
            with ui.row().classes("config-group-label"):
                ui.label("向量数据库 (Qdrant)")
            kv_input("连接 URL", "QDRANT_URL", "http://localhost:6333")
            kv_input("访问令牌", "QDRANT_API_KEY", is_password=True)

            def save_all():
                for k, v in config_values.items():
                    save_config(k, v)
                ui.notify("AI 引擎配置已重载")

            ui.button("保存配置", on_click=save_all).classes("save-btn bg-indigo-600 text-white mt-10")

    def render_kb_dify():
        with ui.column().classes("w-full gap-2"):
            ui.label("Dify 参考库").classes("section-title")
            ui.label("上传 YAML 文件供 AI 参考。").classes("section-desc")
            directory = "docs/references"
            os.makedirs(directory, exist_ok=True)

            def get_data():
                files = sorted([f for f in os.listdir(directory) if f.lower().endswith((".yml", ".yaml"))])
                rows = []
                for i, f in enumerate(files):
                    try:
                        size = f"{os.path.getsize(os.path.join(directory, f)) / 1024:.1f} KB"
                    except:
                        size = "0 KB"
                    rows.append({"index": i + 1, "name": f, "size": size, "id": f})
                return rows

            with ui.row().classes("w-full items-center justify-between mb-8"):
                search = ui.input(placeholder="搜索...").props("rounded outlined dense").classes("w-64 bg-white")
                ui.button("添加参考", icon="add", on_click=lambda: up_dlg.open()).props(
                    "unelevated color=indigo-600 rounded"
                )

            table = ui.table(
                columns=[
                    {"name": "index", "label": "", "field": "index", "align": "left"},
                    {"name": "name", "label": "文件名", "field": "name", "align": "left", "sortable": True},
                    {"name": "size", "label": "大小", "field": "size", "align": "center"},
                    {"name": "actions", "label": "操作", "field": "id", "align": "right"},
                ],
                rows=get_data(),
            ).classes("w-full nicegui-table")
            table.bind_filter_from(search, "value")

            table.add_slot(
                "body-cell-index", '<q-td :props="props"><div class="index-badge">{{props.value}}</div></q-td>'
            )
            table.add_slot(
                "body-cell-actions",
                """
                <q-td :props="props" class="text-right">
                    <q-btn flat round dense icon="edit_note" color="teal" @click="() => $parent.$emit('edit', props.value)" />
                    <q-btn flat round dense icon="delete" color="red-2" @click="() => $parent.$emit('delete', props.value)" />
                </q-td>
            """,
            )

            async def edit_fn(file_id):
                path = os.path.join(directory, file_id)
                with open(path, encoding="utf-8") as f:
                    content = f.read()

                with ui.dialog() as dlg, ui.card().classes("p-0 w-[1000px] max-w-[95vw] overflow-hidden rounded-3xl"):
                    with ui.column().classes("w-full h-[80vh] gap-0"):
                        # Header
                        with ui.row().classes(
                            "w-full p-6 items-center justify-between bg-slate-50/80 backdrop-blur border-b"
                        ):
                            with ui.row().classes("items-center gap-3"):
                                ui.icon("edit_note", color="teal-500", size="28px")
                                ui.label(f"编辑文件: {file_id}").classes("text-lg font-bold text-slate-800")
                            ui.button(icon="close", on_click=dlg.close).props("flat round dense color=slate-400")

                        # Body - Code Editor
                        ed = (
                            ui.textarea(value=content)
                            .classes("w-full flex-grow full-height-editor font-mono text-sm")
                            .props("borderless autogrow=false")
                        )
                        ed.style('font-family: "JetBrains Mono", monospace; background: #ffffff; color: #334155;')

                        # Footer
                        with ui.row().classes("w-full p-6 justify-end bg-white border-t gap-3"):
                            ui.button("取消", on_click=dlg.close).props("flat color=slate-400")

                            def do_save():
                                with open(path, "w", encoding="utf-8") as f:
                                    f.write(ed.value)
                                ui.notify("文件内容已同步更新", type="positive", icon="done_all")
                                dlg.close()

                            ui.button("保存更改", on_click=do_save, icon="save").props(
                                "unelevated color=teal-500 rounded"
                            ).classes("px-8 h-12 font-bold")
                dlg.open()

            def del_fn(file_id):
                os.remove(os.path.join(directory, file_id))
                table.rows = get_data()
                ui.notify("已删除")

            table.on("edit", lambda e: edit_fn(e.args))
            table.on("delete", lambda e: del_fn(e.args))

            with ui.dialog() as up_dlg, ui.card().classes("p-6"):

                def handle_up(e: events.UploadEventArguments):
                    with open(os.path.join(directory, e.file.name), "wb") as f:
                        f.write(e.file.read())
                    table.rows = get_data()
                    ui.notify(f"已添加: {e.file.name}")
                    up_dlg.close()

                ui.upload(on_upload=handle_up, auto_upload=True).props("accept=.yml,.yaml flat rounded")

    def render_kb_classify():
        with ui.column().classes("w-full"):
            ui.label("分类参考").classes("section-title")
            render_file_manager("docs/classify_refs", [".txt", ".json"])

    def render_kb_rag():
        with ui.column().classes("w-full"):
            ui.label("业务 RAG").classes("section-title")
            render_file_manager("docs/rag_docs", [".pdf", ".docx", ".txt"])

    def render_file_manager(directory, extensions):
        os.makedirs(directory, exist_ok=True)

        def get_files():
            return [f for f in os.listdir(directory) if f.lower().endswith(tuple(extensions))]

        container = ui.column().classes("w-full mt-8")

        def refresh():
            container.clear()
            for f in get_files():
                with container:
                    with ui.row().classes("w-full items-center justify-between p-4 bg-white/40 rounded-2xl mb-2"):
                        ui.label(f).classes("text-sm font-bold")

                        def d_del(n=f):
                            os.remove(os.path.join(directory, n))
                            refresh()
                            ui.notify("已移除")

                        ui.button(icon="delete", on_click=d_del).props("flat round color=red-3")

        def handle_up(e: events.UploadEventArguments):
            with open(os.path.join(directory, e.file.name), "wb") as f:
                f.write(e.file.read())
            refresh()
            ui.notify("上传成功")

        ui.upload(on_upload=handle_up, auto_upload=True).props("flat bordered rounded").classes("w-full")
        refresh()

    with ui.column().classes("w-full h-screen items-center justify-center p-6"):
        with ui.row().classes("settings-container w-full no-wrap gap-0"):
            with ui.column().classes("settings-nav w-84 p-10 flex-shrink-0"):
                with ui.row().classes("items-center gap-4 mb-16 px-2"):
                    ui.button(icon="arrow_back", on_click=lambda: ui.navigate.to("/")).props(
                        "flat round color=slate-400 size=lg"
                    )
                    ui.label("设置").classes("text-3xl font-black text-slate-800")

                def n_btn(l, i, t):
                    btn = ui.row().classes(
                        f"nav-item w-full items-center gap-4 {'nav-active' if t == 'general' else ''}"
                    )
                    with btn:
                        ui.icon(i, size="24px")
                        ui.label(l)
                    btn.on("click", lambda: set_tab(t))
                    nav_buttons[t] = btn

                n_btn("通用配置", "tune", "general")
                n_btn("AI 引擎内核", "shutter_speed", "llm")
                ui.label("知识图谱").classes("text-[11px] font-black text-slate-400 mt-12 mb-6 ml-6 uppercase")
                n_btn("Dify 参考库", "auto_awesome_mosaic", "kb_dify")
                n_btn("分类知识库", "account_tree", "kb_classify")
                n_btn("业务 RAG", "menu_book", "kb_rag")
            with ui.column().classes("flex-grow h-full content-area-scroll bg-transparent"):
                content_area = ui.column().classes("content-card w-full")
                with content_area:
                    render_general_settings()
