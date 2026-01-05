# 系统设置页面的专用样式
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
    .full-height-editor { height: 100% !important; display: flex !important; flex-direction: column !important; }
    .full-height-editor .q-field__control, .full-height-editor .q-field__control-container, .full-height-editor .q-field__native { height: 100% !important; padding: 32px !important; }
</style>
"""
