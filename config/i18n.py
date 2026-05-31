"""
config/i18n.py — 国际化字符串注册表
支持: zh-CN (简体中文), zh-TW (繁體中文), en (English)

用法:
    from config.i18n import _
    label.config(text=_("btn_generate"))
"""

# ══════════════════════════════════════════════════════════════
#  字符串注册表
# ══════════════════════════════════════════════════════════════

STRINGS = {
    # ── 应用主窗口 ──────────────────────────────────────────
    "app_title": {
        "zh-CN": "✨ 文字生图工具 v10",
        "zh-TW": "✨ 文字生圖工具 v10",
        "en":    "✨ Text-to-Image Tool v10",
    },
    "app_input_label": {
        "zh-CN": "📝 输入描述（支持中文，自动翻译）",
        "zh-TW": "📝 輸入描述（支援中文，自動翻譯）",
        "en":    "📝 Enter description (Chinese supported, auto-translate)",
    },

    # ── 菜单 ────────────────────────────────────────────────
    "menu_file": {
        "zh-CN": "📁  文件",
        "zh-TW": "📁  檔案",
        "en":    "📁  File",
    },
    "menu_tools": {
        "zh-CN": "🛠  工具",
        "zh-TW": "🛠  工具",
        "en":    "🛠  Tools",
    },
    "menu_history": {
        "zh-CN": "📜  历史",
        "zh-TW": "📜  歷史",
        "en":    "📜  History",
    },
    "menu_help": {
        "zh-CN": "💡  帮助",
        "zh-TW": "💡  幫助",
        "en":    "💡  Help",
    },
    "menu_settings": {
        "zh-CN": "⚙  设置",
        "zh-TW": "⚙  設定",
        "en":    "⚙  Settings",
    },
    "menu_data": {
        "zh-CN": "📊  数据",
        "zh-TW": "📊  資料",
        "en":    "📊  Data",
    },

    # ── 按钮 ────────────────────────────────────────────────
    "btn_generate": {
        "zh-CN": "🎨 生成",
        "zh-TW": "🎨 生成",
        "en":    "🎨 Generate",
    },
    "btn_generating": {
        "zh-CN": "⏳ 生成中…",
        "zh-TW": "⏳ 生成中…",
        "en":    "⏳ Generating…",
    },
    "btn_add_queue": {
        "zh-CN": "➕ 加入队列 (Ctrl+Q)",
        "zh-TW": "➕ 加入佇列 (Ctrl+Q)",
        "en":    "➕ Add to Queue (Ctrl+Q)",
    },
    "btn_phrase_lib": {
        "zh-CN": "📚 词库  (Ctrl+B)",
        "zh-TW": "📚 詞庫  (Ctrl+B)",
        "en":    "📚 Phrase Library (Ctrl+B)",
    },
    "btn_prompt_wizard": {
        "zh-CN": "✨ 提示词助手",
        "zh-TW": "✨ 提示詞助手",
        "en":    "✨ Prompt Wizard",
    },
    "btn_variant_gen": {
        "zh-CN": "🎲 变体生成",
        "zh-TW": "🎲 變體生成",
        "en":    "🎲 Generate Variants",
    },
    "btn_paid_config": {
        "zh-CN": "💎 付费配置",
        "zh-TW": "💎 付費配置",
        "en":    "💎 Paid API Keys",
    },
    "btn_free_config": {
        "zh-CN": "🆓 免费配置",
        "zh-TW": "🆓 免費配置",
        "en":    "🆓 Free API Keys",
    },
    "btn_save": {
        "zh-CN": "💾 保存",
        "zh-TW": "💾 儲存",
        "en":    "💾 Save",
    },
    "btn_export": {
        "zh-CN": "📤 导出",
        "zh-TW": "📤 匯出",
        "en":    "📤 Export",
    },
    "btn_reset": {
        "zh-CN": "🔄 重置",
        "zh-TW": "🔄 重置",
        "en":    "🔄 Reset",
    },
    "btn_clear_log": {
        "zh-CN": "清空 (Ctrl+L)",
        "zh-TW": "清空 (Ctrl+L)",
        "en":    "Clear (Ctrl+L)",
    },
    "btn_show_more": {
        "zh-CN": "显示更多…（共 {count} 条）",
        "zh-TW": "顯示更多…（共 {count} 條）",
        "en":    "Show more… ({count} total)",
    },
    "btn_keep": {
        "zh-CN": "✅ 保留",
        "zh-TW": "✅ 保留",
        "en":    "✅ Keep",
    },
    "btn_discard": {
        "zh-CN": "✕ 丢弃",
        "zh-TW": "✕ 丟棄",
        "en":    "✕ Discard",
    },
    "btn_compare": {
        "zh-CN": "🔄 对比",
        "zh-TW": "🔄 對比",
        "en":    "🔄 Compare",
    },
    "btn_save_image": {
        "zh-CN": "💾 保存图片",
        "zh-TW": "💾 儲存圖片",
        "en":    "💾 Save Image",
    },
    "btn_open_viewer": {
        "zh-CN": "🔍 独立查看器",
        "zh-TW": "🔍 獨立檢視器",
        "en":    "🔍 Open Viewer",
    },
    "btn_close": {
        "zh-CN": "关闭",
        "zh-TW": "關閉",
        "en":    "Close",
    },
    "btn_cancel": {
        "zh-CN": "取消",
        "zh-TW": "取消",
        "en":    "Cancel",
    },
    "btn_confirm": {
        "zh-CN": "确认",
        "zh-TW": "確認",
        "en":    "Confirm",
    },
    "btn_skip": {
        "zh-CN": "跳过（稍后在「⚙ 设置」中配置）",
        "zh-TW": "跳過（稍後在「⚙ 設定」中配置）",
        "en":    "Skip (configure later in Settings)",
    },
    "btn_save_and_start": {
        "zh-CN": "✅  保存并开始使用",
        "zh-TW": "✅  儲存並開始使用",
        "en":    "✅  Save & Start",
    },
    "btn_save_config": {
        "zh-CN": "✅  保存配置",
        "zh-TW": "✅  儲存配置",
        "en":    "✅  Save Config",
    },
    "btn_clear_history": {
        "zh-CN": "🗑 清空历史",
        "zh-TW": "🗑 清空歷史",
        "en":    "🗑 Clear History",
    },
    "btn_delete": {
        "zh-CN": "🗑 删除",
        "zh-TW": "🗑 刪除",
        "en":    "🗑 Delete",
    },
    "btn_rename": {
        "zh-CN": "✏ 命名",
        "zh-TW": "✏ 命名",
        "en":    "✏ Rename",
    },
    "btn_favorite": {
        "zh-CN": "⭐ 收藏",
        "zh-TW": "⭐ 收藏",
        "en":    "⭐ Favorite",
    },
    "btn_tag": {
        "zh-CN": "🏷 标签",
        "zh-TW": "🏷 標籤",
        "en":    "🏷 Tag",
    },
    "btn_show_all": {
        "zh-CN": "全部",
        "zh-TW": "全部",
        "en":    "All",
    },
    "btn_favorites_only": {
        "zh-CN": "⭐ 收藏",
        "zh-TW": "⭐ 收藏",
        "en":    "⭐ Favorites",
    },

    # ── 标签页 ──────────────────────────────────────────────
    "tab_preview": {
        "zh-CN": "  🖼 预览  ",
        "zh-TW": "  🖼 預覽  ",
        "en":    "  🖼 Preview  ",
    },
    "tab_variants": {
        "zh-CN": "  🎲 变体  ",
        "zh-TW": "  🎲 變體  ",
        "en":    "  🎲 Variants  ",
    },
    "tab_queue": {
        "zh-CN": "  📋 队列  ",
        "zh-TW": "  📋 佇列  ",
        "en":    "  📋 Queue  ",
    },
    "tab_debug_log": {
        "zh-CN": "  📋 调试日志  Ctrl+L=清空  ",
        "zh-TW": "  📋 偵錯日誌  Ctrl+L=清空  ",
        "en":    "  📋 Debug Log  Ctrl+L=Clear  ",
    },

    # ── 标签 — 尺寸/接口 —──────────────────────────────────
    "lbl_size": {
        "zh-CN": "尺寸:",
        "zh-TW": "尺寸:",
        "en":    "Size:",
    },
    "lbl_provider": {
        "zh-CN": "接口:",
        "zh-TW": "接口:",
        "en":    "Provider:",
    },
    "lbl_variant_count": {
        "zh-CN": "变体张数:",
        "zh-TW": "變體張數:",
        "en":    "Variants:",
    },
    "lbl_chars": {
        "zh-CN": "{n} 字符",
        "zh-TW": "{n} 字元",
        "en":    "{n} chars",
    },

    # ── 状态消息 ────────────────────────────────────────────
    "status_ready": {
        "zh-CN": "就绪  [ Ctrl+Enter=生成  Ctrl+B=词库  Ctrl+O=查看器 ]",
        "zh-TW": "就緒  [ Ctrl+Enter=生成  Ctrl+B=詞庫  Ctrl+O=檢視器 ]",
        "en":    "Ready  [ Ctrl+Enter=Generate  Ctrl+B=Phrases  Ctrl+O=Viewer ]",
    },
    "status_translating": {
        "zh-CN": "🌐 翻译中…",
        "zh-TW": "🌐 翻譯中…",
        "en":    "🌐 Translating…",
    },
    "status_generating": {
        "zh-CN": "⏳ AI 绘图中，请稍候…",
        "zh-TW": "⏳ AI 繪圖中，請稍候…",
        "en":    "⏳ AI is drawing, please wait…",
    },
    "status_success": {
        "zh-CN": "✅ 成功！来自: {prov}",
        "zh-TW": "✅ 成功！來自: {prov}",
        "en":    "✅ Success! From: {prov}",
    },
    "status_failed": {
        "zh-CN": "❌ 生成失败，查看「调试日志」",
        "zh-TW": "❌ 生成失敗，檢視「偵錯日誌」",
        "en":    "❌ Generation failed, check Debug Log",
    },
    "status_exporting": {
        "zh-CN": "📦 正在导出…",
        "zh-TW": "📦 正在匯出…",
        "en":    "📦 Exporting…",
    },
    "status_export_done": {
        "zh-CN": "✅ 导出完成",
        "zh-TW": "✅ 匯出完成",
        "en":    "✅ Export complete",
    },
    "status_no_records": {
        "zh-CN": "暂无记录",
        "zh-TW": "暫無記錄",
        "en":    "No records",
    },
    "status_history_entry": {
        "zh-CN": "📖 {ts} · {prov}",
        "zh-TW": "📖 {ts} · {prov}",
        "en":    "📖 {ts} · {prov}",
    },
    "status_batch_start": {
        "zh-CN": "🎲 开始生成 {n} 张变体…",
        "zh-TW": "🎲 開始生成 {n} 張變體…",
        "en":    "🎲 Generating {n} variants…",
    },
    "status_prompt_too_long": {
        "zh-CN": "提示词过长（{cur}/{max} 字符），请精简",
        "zh-TW": "提示詞過長（{cur}/{max} 字元），請精簡",
        "en":    "Prompt too long ({cur}/{max} chars), please shorten",
    },

    # ── 对话框消息 ──────────────────────────────────────────
    "dlg_confirm_delete": {
        "zh-CN": "确定删除此记录？图片文件也将被删除。",
        "zh-TW": "確定刪除此記錄？圖片檔案也將被刪除。",
        "en":    "Delete this record? The image file will also be deleted.",
    },
    "dlg_confirm_clear": {
        "zh-CN": "确定清空全部历史记录？此操作不可撤销。",
        "zh-TW": "確定清空全部歷史記錄？此操作不可撤銷。",
        "en":    "Clear all history? This cannot be undone.",
    },
    "dlg_select_export_dir": {
        "zh-CN": "选择导出目录",
        "zh-TW": "選擇匯出目錄",
        "en":    "Select export directory",
    },
    "dlg_api_key_required": {
        "zh-CN": "需要配置 API Key！\n请在「🆓 免费接口配置」或「💎 付费接口配置」中填写。",
        "zh-TW": "需要配置 API Key！\n請在「🆓 免費接口配置」或「💎 付費接口配置」中填寫。",
        "en":    "API Key required!\nPlease configure in Free API Keys or Paid API Keys.",
    },

    # ── 搜索 / 筛选 ─────────────────────────────────────────
    "search_placeholder": {
        "zh-CN": "🔍 搜索提示词或名称…",
        "zh-TW": "🔍 搜尋提示詞或名稱…",
        "en":    "🔍 Search prompts or names…",
    },

    # ── 预览占位 ────────────────────────────────────────────
    "preview_placeholder": {
        "zh-CN": "生成图片后在此处显示缩略预览\n\n点击「🔍 独立查看器」或双击预览图\n可在独立窗口中自由缩放、拖拽、裁剪图片",
        "zh-TW": "生成圖片後在此處顯示縮略預覽\n\n點擊「🔍 獨立檢視器」或雙擊預覽圖\n可在獨立視窗中自由縮放、拖曳、裁剪圖片",
        "en":    "Thumbnail preview appears here after generation\n\nClick 'Open Viewer' or double-click preview\nto zoom, pan, and crop in a separate window",
    },
    "preview_error": {
        "zh-CN": "❌  生成失败\n\n请查看「调试日志」",
        "zh-TW": "❌  生成失敗\n\n請檢視「偵錯日誌」",
        "en":    "❌  Generation Failed\n\nCheck Debug Log",
    },

    # ── 快捷键提示 ──────────────────────────────────────────
    "shortcut_hint": {
        "zh-CN": " Ctrl+Enter=生成  Ctrl+B=词库  Ctrl+P=助手",
        "zh-TW": " Ctrl+Enter=生成  Ctrl+B=詞庫  Ctrl+P=助手",
        "en":    " Ctrl+Enter=Generate  Ctrl+B=Phrases  Ctrl+P=Wizard",
    },

    # ── 错误映射 ────────────────────────────────────────────
    "err_rate_limit": {
        "zh-CN": "请求太频繁，请等待 30 秒后重试",
        "zh-TW": "請求太頻繁，請等待 30 秒後重試",
        "en":    "Too many requests. Please wait 30 seconds.",
    },
    "err_api_key": {
        "zh-CN": "API Key 无效或已过期，请在设置中检查",
        "zh-TW": "API Key 無效或已過期，請在設定中檢查",
        "en":    "Invalid or expired API Key. Check settings.",
    },
    "err_balance": {
        "zh-CN": "API 账户余额不足，请充值",
        "zh-TW": "API 帳戶餘額不足，請儲值",
        "en":    "Insufficient API account balance.",
    },
    "err_timeout": {
        "zh-CN": "网络连接超时，请检查网络或稍后重试",
        "zh-TW": "網路連線逾時，請檢查網路或稍後重試",
        "en":    "Connection timed out. Check network and retry.",
    },
    "err_connection": {
        "zh-CN": "网络连接失败，请检查网络设置",
        "zh-TW": "網路連線失敗，請檢查網路設定",
        "en":    "Network connection failed. Check network settings.",
    },
    "err_all_failed": {
        "zh-CN": "所有接口均失败",
        "zh-TW": "所有接口均失敗",
        "en":    "All providers failed",
    },

    # ── Provider 状态 ───────────────────────────────────────
    "provider_auto": {
        "zh-CN": "自动（按优先级）",
        "zh-TW": "自動（按優先級）",
        "en":    "Auto (by priority)",
    },
    "provider_free_section": {
        "zh-CN": "─── 免费接口 ───",
        "zh-TW": "─── 免費接口 ───",
        "en":    "─── Free ───",
    },
    "provider_paid_section": {
        "zh-CN": "─── 💎 付费接口 ───",
        "zh-TW": "─── 💎 付費接口 ───",
        "en":    "─── 💎 Paid ───",
    },
    "status_free_count": {
        "zh-CN": "🆓 免费接口 {n}/{total}",
        "zh-TW": "🆓 免費接口 {n}/{total}",
        "en":    "🆓 Free APIs {n}/{total}",
    },
    "status_paid_count": {
        "zh-CN": "💎 付费接口 {n}/{total}",
        "zh-TW": "💎 付費接口 {n}/{total}",
        "en":    "💎 Paid APIs {n}/{total}",
    },

    # ── 批量面板 ────────────────────────────────────────────
    "batch_loading": {
        "zh-CN": "⏳ 生成中…",
        "zh-TW": "⏳ 生成中…",
        "en":    "⏳ Generating…",
    },
    "batch_error": {
        "zh-CN": "❌ 失败",
        "zh-TW": "❌ 失敗",
        "en":    "❌ Failed",
    },
    "batch_keep_all": {
        "zh-CN": "全部保留",
        "zh-TW": "全部保留",
        "en":    "Keep All",
    },
    "batch_discard_all": {
        "zh-CN": "全部丢弃",
        "zh-TW": "全部丟棄",
        "en":    "Discard All",
    },

    # ── 队列面板 ────────────────────────────────────────────
    "queue_waiting": {
        "zh-CN": "⏳ 等待中",
        "zh-TW": "⏳ 等待中",
        "en":    "⏳ Waiting",
    },
    "queue_running": {
        "zh-CN": "🔄 生成中",
        "zh-TW": "🔄 生成中",
        "en":    "🔄 Running",
    },
    "queue_done": {
        "zh-CN": "✅ 完成",
        "zh-TW": "✅ 完成",
        "en":    "✅ Done",
    },
    "queue_failed": {
        "zh-CN": "❌ 失败",
        "zh-TW": "❌ 失敗",
        "en":    "❌ Failed",
    },
    "queue_cancelled": {
        "zh-CN": "⊘ 已取消",
        "zh-TW": "⊘ 已取消",
        "en":    "⊘ Cancelled",
    },
    "queue_btn_pause": {
        "zh-CN": "⏸ 暂停",
        "zh-TW": "⏸ 暫停",
        "en":    "⏸ Pause",
    },
    "queue_btn_resume": {
        "zh-CN": "▶ 继续",
        "zh-TW": "▶ 繼續",
        "en":    "▶ Resume",
    },
    "queue_btn_start": {
        "zh-CN": "▶ 开始生成",
        "zh-TW": "▶ 開始生成",
        "en":    "▶ Start",
    },
    "queue_btn_clear_done": {
        "zh-CN": "🗑 清除已完成",
        "zh-TW": "🗑 清除已完成",
        "en":    "🗑 Clear Done",
    },

    # ── 图片查看器 ──────────────────────────────────────────
    "viewer_title": {
        "zh-CN": "图片查看器",
        "zh-TW": "圖片檢視器",
        "en":    "Image Viewer",
    },
    "viewer_fit": {
        "zh-CN": "适应窗口",
        "zh-TW": "適應視窗",
        "en":    "Fit",
    },
    "viewer_100": {
        "zh-CN": "100%",
        "zh-TW": "100%",
        "en":    "100%",
    },
    "viewer_zoom_in": {
        "zh-CN": "放大",
        "zh-TW": "放大",
        "en":    "Zoom In",
    },
    "viewer_zoom_out": {
        "zh-CN": "缩小",
        "zh-TW": "縮小",
        "en":    "Zoom Out",
    },
    "viewer_rotate_left": {
        "zh-CN": "↺ 左转",
        "zh-TW": "↺ 左轉",
        "en":    "↺ Rotate L",
    },
    "viewer_rotate_right": {
        "zh-CN": "↻ 右转",
        "zh-TW": "↻ 右轉",
        "en":    "↻ Rotate R",
    },
    "viewer_crop": {
        "zh-CN": "✂ 裁剪",
        "zh-TW": "✂ 裁剪",
        "en":    "✂ Crop",
    },
    "viewer_save": {
        "zh-CN": "💾 保存",
        "zh-TW": "💾 儲存",
        "en":    "💾 Save",
    },

    # ── 提示词向导 ──────────────────────────────────────────
    "wizard_title": {
        "zh-CN": "✨ AI 提示词助手",
        "zh-TW": "✨ AI 提示詞助手",
        "en":    "✨ AI Prompt Wizard",
    },
    "wizard_param_tab": {
        "zh-CN": "🎯 参数",
        "zh-TW": "🎯 參數",
        "en":    "🎯 Parameters",
    },
    "wizard_template_tab": {
        "zh-CN": "📋 模板",
        "zh-TW": "📋 模板",
        "en":    "📋 Templates",
    },
    "wizard_generate_btn": {
        "zh-CN": "🤖 AI 生成",
        "zh-TW": "🤖 AI 生成",
        "en":    "🤖 AI Generate",
    },
    "wizard_use_btn": {
        "zh-CN": "✅ 使用此提示词",
        "zh-TW": "✅ 使用此提示詞",
        "en":    "✅ Use This Prompt",
    },

    # ── Wizard 配置窗口 ─────────────────────────────────────
    "wizard_free_title": {
        "zh-CN": "🆓 免费接口配置",
        "zh-TW": "🆓 免費接口配置",
        "en":    "🆓 Free API Configuration",
    },
    "wizard_paid_title": {
        "zh-CN": "💎  付费接口配置",
        "zh-TW": "💎  付費接口配置",
        "en":    "💎  Paid API Configuration",
    },
    "wizard_paid_subtitle": {
        "zh-CN": "按需使用 · 按量计费 · 专业级画质",
        "zh-TW": "按需使用 · 按量計費 · 專業級畫質",
        "en":    "On-demand · Pay-per-use · Professional quality",
    },

    # ── 词库面板 ────────────────────────────────────────────
    "phrase_title": {
        "zh-CN": "📚 提示词片段库",
        "zh-TW": "📚 提示詞片段庫",
        "en":    "📚 Phrase Snippet Library",
    },

    # ── 日志 ────────────────────────────────────────────────
    "log_translate_ok": {
        "zh-CN": "翻译成功: {text}",
        "zh-TW": "翻譯成功: {text}",
        "en":    "Translation OK: {text}",
    },
    "log_translate_fail": {
        "zh-CN": "翻译失败（使用原文）: {err}",
        "zh-TW": "翻譯失敗（使用原文）: {err}",
        "en":    "Translation failed (using original): {err}",
    },
    "log_prompt_truncated": {
        "zh-CN": "提示词过长，已截断至 {max} 字符",
        "zh-TW": "提示詞過長，已截斷至 {max} 字元",
        "en":    "Prompt truncated to {max} chars",
    },

    # ── 统计标签 ────────────────────────────────────────────
    "stat_total": {
        "zh-CN": "总计: {n}",
        "zh-TW": "總計: {n}",
        "en":    "Total: {n}",
    },
    "stat_today": {
        "zh-CN": "今日: {n}",
        "zh-TW": "今日: {n}",
        "en":    "Today: {n}",
    },
    "stat_week": {
        "zh-CN": "本周: {n}",
        "zh-TW": "本週: {n}",
        "en":    "This week: {n}",
    },
}


# ══════════════════════════════════════════════════════════════
#  查询函数
# ══════════════════════════════════════════════════════════════

_current_lang = "zh-CN"


def set_language(lang: str) -> None:
    """切换当前语言。"""
    global _current_lang
    if lang in ("zh-CN", "zh-TW", "en"):
        _current_lang = lang


def get_language() -> str:
    """获取当前语言代码。"""
    return _current_lang


def init_language(cfg: dict) -> None:
    """从配置初始化语言设置。"""
    lang = cfg.get("language", "zh-CN")
    set_language(lang)


def _(key: str, **kwargs) -> str:
    """
    获取当前语言的字符串。

    用法:
        _("btn_generate")              → "🎨 生成"
        _("status_success", prov="X")  → "✅ 成功！来自: X"
        _("lbl_chars", n=42)           → "42 字符"
    """
    entry = STRINGS.get(key)
    if entry is None:
        return f"??{key}??"
    text = entry.get(_current_lang) or entry.get("zh-CN", key)
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, ValueError):
            pass
    return text
