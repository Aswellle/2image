"""
config/i18n.py — 国际化字符串注册表
支持: zh-CN (简体中文), en (English)

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
        "en":    "✨ Text-to-Image Tool v10",
    },
    "app_input_label": {
        "zh-CN": "📝 输入描述（支持中文，自动翻译）",
        "en":    "📝 Enter description (Chinese supported, auto-translate)",
    },

    # ── 菜单 ────────────────────────────────────────────────
    "menu_file": {
        "zh-CN": "📁  文件",
        "en":    "📁  File",
    },
    "menu_tools": {
        "zh-CN": "🛠  工具",
        "en":    "🛠  Tools",
    },
    "menu_history": {
        "zh-CN": "📜  历史",
        "en":    "📜  History",
    },
    "menu_help": {
        "zh-CN": "💡  帮助",
        "en":    "💡  Help",
    },
    "menu_settings": {
        "zh-CN": "⚙  设置",
        "en":    "⚙  Settings",
    },
    "menu_data": {
        "zh-CN": "📊  数据",
        "en":    "📊  Data",
    },

    # ── 按钮 ────────────────────────────────────────────────
    "btn_generate": {
        "zh-CN": "🎨 生成",
        "en":    "🎨 Generate",
    },
    "btn_generating": {
        "zh-CN": "⏳ 生成中…",
        "en":    "⏳ Generating…",
    },
    "btn_add_queue": {
        "zh-CN": "➕ 加入队列 (Ctrl+Q)",
        "en":    "➕ Add to Queue (Ctrl+Q)",
    },
    "btn_phrase_lib": {
        "zh-CN": "📚 词库  (Ctrl+B)",
        "en":    "📚 Phrase Library (Ctrl+B)",
    },
    "btn_prompt_wizard": {
        "zh-CN": "✨ 提示词助手",
        "en":    "✨ Prompt Wizard",
    },
    "btn_variant_gen": {
        "zh-CN": "🎲 变体生成",
        "en":    "🎲 Generate Variants",
    },
    "btn_paid_config": {
        "zh-CN": "💎 付费配置",
        "en":    "💎 Paid API Keys",
    },
    "btn_free_config": {
        "zh-CN": "🆓 免费配置",
        "en":    "🆓 Free API Keys",
    },
    "btn_save": {
        "zh-CN": "💾 保存",
        "en":    "💾 Save",
    },
    "btn_export": {
        "zh-CN": "📤 导出",
        "en":    "📤 Export",
    },
    "btn_reset": {
        "zh-CN": "🔄 重置",
        "en":    "🔄 Reset",
    },
    "btn_clear_log": {
        "zh-CN": "清空 (Ctrl+L)",
        "en":    "Clear (Ctrl+L)",
    },
    "btn_show_more": {
        "zh-CN": "显示更多…（共 {count} 条）",
        "en":    "Show more… ({count} total)",
    },
    "btn_keep": {
        "zh-CN": "✅ 保留",
        "en":    "✅ Keep",
    },
    "btn_discard": {
        "zh-CN": "✕ 丢弃",
        "en":    "✕ Discard",
    },
    "btn_compare": {
        "zh-CN": "🔄 对比",
        "en":    "🔄 Compare",
    },
    "btn_save_image": {
        "zh-CN": "💾 保存图片",
        "en":    "💾 Save Image",
    },
    "btn_open_viewer": {
        "zh-CN": "🔍 独立查看器",
        "en":    "🔍 Open Viewer",
    },
    "btn_close": {
        "zh-CN": "关闭",
        "en":    "Close",
    },
    "btn_cancel": {
        "zh-CN": "取消",
        "en":    "Cancel",
    },
    "btn_confirm": {
        "zh-CN": "确认",
        "en":    "Confirm",
    },
    "btn_skip": {
        "zh-CN": "跳过（稍后在「⚙ 设置」中配置）",
        "en":    "Skip (configure later in Settings)",
    },
    "btn_save_and_start": {
        "zh-CN": "✅  保存并开始使用",
        "en":    "✅  Save & Start",
    },
    "btn_save_config": {
        "zh-CN": "✅  保存配置",
        "en":    "✅  Save Config",
    },
    "btn_clear_history": {
        "zh-CN": "🗑 清空历史",
        "en":    "🗑 Clear History",
    },
    "btn_delete": {
        "zh-CN": "🗑 删除",
        "en":    "🗑 Delete",
    },
    "btn_rename": {
        "zh-CN": "✏ 命名",
        "en":    "✏ Rename",
    },
    "btn_favorite": {
        "zh-CN": "⭐ 收藏",
        "en":    "⭐ Favorite",
    },
    "btn_tag": {
        "zh-CN": "🏷 标签",
        "en":    "🏷 Tag",
    },
    "btn_show_all": {
        "zh-CN": "全部",
        "en":    "All",
    },
    "btn_favorites_only": {
        "zh-CN": "⭐ 收藏",
        "en":    "⭐ Favorites",
    },
    "menu_open_viewer": {
        "zh-CN": "🔍  打开独立查看器…",
        "en":    "🔍  Open Viewer…",
    },
    "menu_save_as": {
        "zh-CN": "💾  当前图片另存为…",
        "en":    "💾  Save Current Image As…",
    },
    "menu_export": {
        "zh-CN": "📦  导出历史记录…",
        "en":    "📦  Export History…",
    },
    "menu_clear_log": {
        "zh-CN": "🧹  清空调试日志",
        "en":    "🧹  Clear Debug Log",
    },
    "menu_api": {
        "zh-CN": "接口配置",
        "en":    "Providers",
    },
    "menu_free_config": {
        "zh-CN": "🆓  免费接口配置…",
        "en":    "🆓  Free Provider Setup…",
    },
    "menu_paid_config": {
        "zh-CN": "💎  付费接口配置…",
        "en":    "💎  Paid Provider Setup…",
    },
    "menu_free_links": {
        "zh-CN": "🌐  免费接口注册链接",
        "en":    "🌐  Free Provider Sign-up Links",
    },
    "menu_paid_links": {
        "zh-CN": "🌐  付费接口注册链接",
        "en":    "🌐  Paid Provider Sign-up Links",
    },
    "menu_switch_variants": {
        "zh-CN": "🧩  切换到变体生成",
        "en":    "🧩  Go to Variants",
    },
    "menu_switch_queue": {
        "zh-CN": "📋  切换到生成队列…",
        "en":    "📋  Go to Queue…",
    },
    "settings_language": {
        "zh-CN": "界面语言",
        "en":    "Interface Language",
    },
    "settings_lang_restart": {
        "zh-CN": "🌐 语言设置已保存，重启应用后生效",
        "en":    "🌐 Language saved — restart the app to apply",
    },
    "settings_default_size": {
        "zh-CN": "默认生成尺寸",
        "en":    "Default Image Size",
    },
    "settings_startup": {
        "zh-CN": "启动行为",
        "en":    "Startup",
    },
    "settings_show_wizard": {
        "zh-CN": "启动时显示免费接口配置向导",
        "en":    "Show free provider wizard on startup",
    },
    "settings_saved": {
        "zh-CN": "✅ 已保存！",
        "en":    "✅ Saved!",
    },
    "settings_prefs_title": {
        "zh-CN": "应用偏好设置",
        "en":    "Preferences",
    },
    "settings_shortcuts_title": {
        "zh-CN": "快捷键说明",
        "en":    "Keyboard Shortcuts",
    },
    "filter_viewing": {
        "zh-CN": "正在查看：{filters}",
        "en":    "Viewing: {filters}",
    },
    "btn_clear_filter": {
        "zh-CN": "清除筛选",
        "en":    "Clear filters",
    },
    "ctx_show_in_folder": {
        "zh-CN": "📁  在文件夹中显示",
        "en":    "📁  Show in Folder",
    },
    "prompt_more_controls": {
        "zh-CN": "更多精细控制（细节/构图/光影/镜头/画质）",
        "en":    "More fine controls (detail/composition/lighting/camera/quality)",
    },

    # ── 标签页 ──────────────────────────────────────────────
    "tab_preview": {
        "zh-CN": "  🖼 预览  ",
        "en":    "  🖼 Preview  ",
    },
    "tab_variants": {
        "zh-CN": "  🎲 变体  ",
        "en":    "  🎲 Variants  ",
    },
    "tab_queue": {
        "zh-CN": "  📋 队列  ",
        "en":    "  📋 Queue  ",
    },
    "tab_debug_log": {
        "zh-CN": "  📋 调试日志  Ctrl+L=清空  ",
        "en":    "  📋 Debug Log  Ctrl+L=Clear  ",
    },

    # ── 标签 — 尺寸/接口 —──────────────────────────────────
    "lbl_size": {
        "zh-CN": "尺寸:",
        "en":    "Size:",
    },
    "lbl_provider": {
        "zh-CN": "接口:",
        "en":    "Provider:",
    },
    "lbl_variant_count": {
        "zh-CN": "变体张数:",
        "en":    "Variants:",
    },
    "lbl_chars": {
        "zh-CN": "{n} 字符",
        "en":    "{n} chars",
    },

    # ── 状态消息 ────────────────────────────────────────────
    "status_ready": {
        "zh-CN": "就绪  [ Ctrl+Enter=生成  Ctrl+B=词库  Ctrl+O=查看器 ]",
        "en":    "Ready  [ Ctrl+Enter=Generate  Ctrl+B=Phrases  Ctrl+O=Viewer ]",
    },
    "status_translating": {
        "zh-CN": "🌐 翻译中…",
        "en":    "🌐 Translating…",
    },
    "status_generating": {
        "zh-CN": "⏳ AI 绘图中，请稍候…",
        "en":    "⏳ AI is drawing, please wait…",
    },
    "status_success": {
        "zh-CN": "✅ 成功！来自: {prov}",
        "en":    "✅ Success! From: {prov}",
    },
    "status_failed": {
        "zh-CN": "❌ 生成失败，查看「调试日志」",
        "en":    "❌ Generation failed, check Debug Log",
    },
    "status_exporting": {
        "zh-CN": "📦 正在导出…",
        "en":    "📦 Exporting…",
    },
    "status_export_done": {
        "zh-CN": "✅ 导出完成",
        "en":    "✅ Export complete",
    },
    "status_no_records": {
        "zh-CN": "暂无记录",
        "en":    "No records",
    },
    "status_history_entry": {
        "zh-CN": "📖 {ts} · {prov}",
        "en":    "📖 {ts} · {prov}",
    },
    "status_batch_start": {
        "zh-CN": "🎲 开始生成 {n} 张变体…",
        "en":    "🎲 Generating {n} variants…",
    },
    "status_prompt_too_long": {
        "zh-CN": "提示词过长（{cur}/{max} 字符），请精简",
        "en":    "Prompt too long ({cur}/{max} chars), please shorten",
    },

    # ── 对话框消息 ──────────────────────────────────────────
    "dlg_confirm_delete": {
        "zh-CN": "确定删除此记录？图片文件也将被删除。",
        "en":    "Delete this record? The image file will also be deleted.",
    },
    "dlg_confirm_clear": {
        "zh-CN": "确定清空全部历史记录？此操作不可撤销。",
        "en":    "Clear all history? This cannot be undone.",
    },
    "dlg_select_export_dir": {
        "zh-CN": "选择导出目录",
        "en":    "Select export directory",
    },
    "dlg_api_key_required": {
        "zh-CN": "需要配置 API Key！\n请在「🆓 免费接口配置」或「💎 付费接口配置」中填写。",
        "en":    "API Key required!\nPlease configure in Free API Keys or Paid API Keys.",
    },
    "dlg_tip": {
        "zh-CN": "提示",
        "en":    "Notice",
    },
    "dlg_empty_prompt": {
        "zh-CN": "请先输入描述文字！",
        "en":    "Please enter a description first!",
    },
    "dlg_pick_specific_provider": {
        "zh-CN": "请选择一个具体接口，而非分隔线。",
        "en":    "Please pick a concrete provider, not a separator.",
    },
    "dlg_suggest_free_key_title": {
        "zh-CN": "建议配置",
        "en":    "Suggestion",
    },
    "dlg_suggest_free_key_body": {
        "zh-CN": "尚未配置任何免费 API Key。\n建议配置「硅基流动」。\n是否现在配置？",
        "en":    "No free API key configured yet.\nSiliconFlow is recommended.\nConfigure now?",
    },
    "dlg_budget_exhausted_title": {
        "zh-CN": "付费预算已用尽",
        "en":    "Daily budget exhausted",
    },
    "dlg_budget_exhausted_body": {
        "zh-CN": "今日付费估算消耗已达 ${spent}（上限 ${limit}）。\n如需继续使用 {provider}，请调高「paid_daily_budget_usd」设置。",
        "en":    "Today's estimated paid spend has reached ${spent} (limit ${limit}).\nTo keep using {provider}, raise the \"paid_daily_budget_usd\" setting.",
    },
    "dlg_need_config_title": {
        "zh-CN": "需要配置",
        "en":    "Configuration needed",
    },
    "dlg_need_key_body": {
        "zh-CN": "使用 {provider} 需要填写 API Key。\n是否现在配置？",
        "en":    "Using {provider} requires an API key.\nConfigure now?",
    },
    "dlg_need_keys_body": {
        "zh-CN": "使用 {provider} 需要填写全部凭证（{keys}）。\n是否现在配置？",
        "en":    "Using {provider} requires all of these credentials ({keys}).\nConfigure now?",
    },
    "dlg_batch_no_img2img": {
        "zh-CN": "批量生成暂不支持图生图模式\n请切换到「📝 文生图」后再批量生成",
        "en":    "Batch generation does not support img2img mode.\nSwitch to text-to-image first.",
    },
    "dlg_err_key_title": {
        "zh-CN": "需要配置 API Key",
        "en":    "API key configuration needed",
    },
    "dlg_err_key_body": {
        "zh-CN": "{err}\n\n点击「🆓 免费配置」配置硅基流动 API Key。",
        "en":    "{err}\n\nClick \"🆓 Free Config\" to set up a SiliconFlow API key.",
    },
    "dlg_need_generate_first": {
        "zh-CN": "请先生成或选择一张图片",
        "en":    "Generate or select an image first",
    },
    "dlg_export_done": {
        "zh-CN": "完成",
        "en":    "Done",
    },
    "dlg_export_done_body": {
        "zh-CN": "已导出 {n} 条\n至：{out}",
        "en":    "Exported {n} items\nTo: {out}",
    },
    "dlg_confirm_rename": {
        "zh-CN": "确认",
        "en":    "Confirm",
    },
    "dlg_confirm_rename_body": {
        "zh-CN": "重命名为：「{name}」？",
        "en":    "Rename to \"{name}\"?",
    },
    "dlg_unfavorite_body": {
        "zh-CN": "从喜爱列表移除？\n\n「{name}」",
        "en":    "Remove from favorites?\n\n\"{name}\"",
    },
    "dlg_favorite_body": {
        "zh-CN": "收藏到喜爱列表？\n\n「{name}」",
        "en":    "Add to favorites?\n\n\"{name}\"",
    },
    "dlg_confirm_clear_n_body": {
        "zh-CN": "清空全部 {n} 条记录？\n（不删除磁盘图片文件）",
        "en":    "Clear all {n} records?\n(Disk image files are kept)",
    },
    "dlg_queue_empty_prompt": {
        "zh-CN": "请先在主输入框填写提示词",
        "en":    "Enter a prompt in the main input box first",
    },
    "dlg_compare_empty": {
        "zh-CN": "暂无历史图片可用于对比",
        "en":    "No history images available for comparison",
    },

    # ── 搜索 / 筛选 ─────────────────────────────────────────
    "search_placeholder": {
        "zh-CN": "🔍 搜索提示词或名称…",
        "en":    "🔍 Search prompts or names…",
    },

    # ── 预览占位 ────────────────────────────────────────────
    "preview_placeholder": {
        "zh-CN": "生成图片后在此处显示缩略预览\n\n点击「🔍 独立查看器」或双击预览图\n可在独立窗口中自由缩放、拖拽、裁剪图片",
        "en":    "Thumbnail preview appears here after generation\n\nClick 'Open Viewer' or double-click preview\nto zoom, pan, and crop in a separate window",
    },
    "preview_error": {
        "zh-CN": "❌  生成失败\n\n请查看「调试日志」",
        "en":    "❌  Generation Failed\n\nCheck Debug Log",
    },

    # ── 快捷键提示 ──────────────────────────────────────────
    "shortcut_hint": {
        "zh-CN": " Ctrl+Enter=生成  Ctrl+B=词库  Ctrl+P=助手",
        "en":    " Ctrl+Enter=Generate  Ctrl+B=Phrases  Ctrl+P=Wizard",
    },

    # ── 错误映射 ────────────────────────────────────────────
    "err_rate_limit": {
        "zh-CN": "请求太频繁，请等待 30 秒后重试",
        "en":    "Too many requests. Please wait 30 seconds.",
    },
    "err_api_key": {
        "zh-CN": "API Key 无效或已过期，请在设置中检查",
        "en":    "Invalid or expired API Key. Check settings.",
    },
    "err_balance": {
        "zh-CN": "API 账户余额不足，请充值",
        "en":    "Insufficient API account balance.",
    },
    "err_timeout": {
        "zh-CN": "网络连接超时，请检查网络或稍后重试",
        "en":    "Connection timed out. Check network and retry.",
    },
    "err_connection": {
        "zh-CN": "网络连接失败，请检查网络设置",
        "en":    "Network connection failed. Check network settings.",
    },
    "err_all_failed": {
        "zh-CN": "所有接口均失败",
        "en":    "All providers failed",
    },

    # ── Provider 状态 ───────────────────────────────────────
    "provider_auto": {
        "zh-CN": "自动（按优先级）",
        "en":    "Auto (by priority)",
    },
    "provider_free_section": {
        "zh-CN": "─── 免费接口 ───",
        "en":    "─── Free ───",
    },
    "provider_paid_section": {
        "zh-CN": "─── 💎 付费接口 ───",
        "en":    "─── 💎 Paid ───",
    },
    "status_free_count": {
        "zh-CN": "🆓 免费接口 {n}/{total}",
        "en":    "🆓 Free APIs {n}/{total}",
    },
    "status_paid_count": {
        "zh-CN": "💎 付费接口 {n}/{total}",
        "en":    "💎 Paid APIs {n}/{total}",
    },

    # ── 批量面板 ────────────────────────────────────────────
    "batch_loading": {
        "zh-CN": "⏳ 生成中…",
        "en":    "⏳ Generating…",
    },
    "batch_error": {
        "zh-CN": "❌ 失败",
        "en":    "❌ Failed",
    },
    "batch_keep_all": {
        "zh-CN": "全部保留",
        "en":    "Keep All",
    },
    "batch_discard_all": {
        "zh-CN": "全部丢弃",
        "en":    "Discard All",
    },

    # ── 队列面板 ────────────────────────────────────────────
    "queue_waiting": {
        "zh-CN": "⏳ 等待中",
        "en":    "⏳ Waiting",
    },
    "queue_running": {
        "zh-CN": "🔄 生成中",
        "en":    "🔄 Running",
    },
    "queue_done": {
        "zh-CN": "✅ 完成",
        "en":    "✅ Done",
    },
    "queue_failed": {
        "zh-CN": "❌ 失败",
        "en":    "❌ Failed",
    },
    "queue_cancelled": {
        "zh-CN": "⊘ 已取消",
        "en":    "⊘ Cancelled",
    },
    "queue_btn_pause": {
        "zh-CN": "⏸ 暂停",
        "en":    "⏸ Pause",
    },
    "queue_btn_resume": {
        "zh-CN": "▶ 继续",
        "en":    "▶ Resume",
    },
    "queue_btn_start": {
        "zh-CN": "▶ 开始生成",
        "en":    "▶ Start",
    },
    "queue_btn_clear_done": {
        "zh-CN": "🗑 清除已完成",
        "en":    "🗑 Clear Done",
    },

    # ── 图片查看器 ──────────────────────────────────────────
    "viewer_title": {
        "zh-CN": "图片查看器",
        "en":    "Image Viewer",
    },
    "viewer_fit": {
        "zh-CN": "适应窗口",
        "en":    "Fit",
    },
    "viewer_100": {
        "zh-CN": "100%",
        "en":    "100%",
    },
    "viewer_zoom_in": {
        "zh-CN": "放大",
        "en":    "Zoom In",
    },
    "viewer_zoom_out": {
        "zh-CN": "缩小",
        "en":    "Zoom Out",
    },
    "viewer_rotate_left": {
        "zh-CN": "↺ 左转",
        "en":    "↺ Rotate L",
    },
    "viewer_rotate_right": {
        "zh-CN": "↻ 右转",
        "en":    "↻ Rotate R",
    },
    "viewer_crop": {
        "zh-CN": "✂ 裁剪",
        "en":    "✂ Crop",
    },
    "viewer_save": {
        "zh-CN": "💾 保存",
        "en":    "💾 Save",
    },

    # ── 提示词向导 ──────────────────────────────────────────
    "wizard_title": {
        "zh-CN": "✨ AI 提示词助手",
        "en":    "✨ AI Prompt Wizard",
    },
    "wizard_param_tab": {
        "zh-CN": "🎯 参数",
        "en":    "🎯 Parameters",
    },
    "wizard_template_tab": {
        "zh-CN": "📋 模板",
        "en":    "📋 Templates",
    },
    "wizard_generate_btn": {
        "zh-CN": "🤖 AI 生成",
        "en":    "🤖 AI Generate",
    },
    "wizard_use_btn": {
        "zh-CN": "✅ 使用此提示词",
        "en":    "✅ Use This Prompt",
    },

    # ── Wizard 配置窗口 ─────────────────────────────────────
    "wizard_free_title": {
        "zh-CN": "🆓 免费接口配置",
        "en":    "🆓 Free API Configuration",
    },
    "wizard_paid_title": {
        "zh-CN": "💎  付费接口配置",
        "en":    "💎  Paid API Configuration",
    },
    "wizard_paid_subtitle": {
        "zh-CN": "按需使用 · 按量计费 · 专业级画质",
        "en":    "On-demand · Pay-per-use · Professional quality",
    },

    # ── 词库面板 ────────────────────────────────────────────
    "phrase_title": {
        "zh-CN": "📚 提示词片段库",
        "en":    "📚 Phrase Snippet Library",
    },

    # ── 日志 ────────────────────────────────────────────────
    "log_translate_ok": {
        "zh-CN": "翻译成功: {text}",
        "en":    "Translation OK: {text}",
    },
    "log_translate_fail": {
        "zh-CN": "翻译失败（使用原文）: {err}",
        "en":    "Translation failed (using original): {err}",
    },
    "log_prompt_truncated": {
        "zh-CN": "提示词过长，已截断至 {max} 字符",
        "en":    "Prompt truncated to {max} chars",
    },

    # ── 统计标签 ────────────────────────────────────────────
    "stat_total": {
        "zh-CN": "总计: {n}",
        "en":    "Total: {n}",
    },
    "stat_today": {
        "zh-CN": "今日: {n}",
        "en":    "Today: {n}",
    },
    "stat_week": {
        "zh-CN": "本周: {n}",
        "en":    "This week: {n}",
    },
    # ── 生成状态可视化 ──────────────────────────────────────
    "state_queued": {
        "zh-CN": "排队中",
        "en":    "Queued",
    },
    "state_translating": {
        "zh-CN": "翻译提示词…",
        "en":    "Translating prompt…",
    },
    "state_routing": {
        "zh-CN": "选择服务商…",
        "en":    "Selecting provider…",
    },
    "state_submitting": {
        "zh-CN": "提交中…",
        "en":    "Submitting…",
    },
    "state_polling": {
        "zh-CN": "等待生成…",
        "en":    "Waiting for result…",
    },
    "state_downloading": {
        "zh-CN": "下载图片…",
        "en":    "Downloading image…",
    },
    "state_validating": {
        "zh-CN": "校验图片…",
        "en":    "Validating image…",
    },
    "state_persisting": {
        "zh-CN": "保存中…",
        "en":    "Saving…",
    },
    "state_succeeded": {
        "zh-CN": "生成完成",
        "en":    "Generation complete",
    },
    "state_failed": {
        "zh-CN": "生成失败",
        "en":    "Generation failed",
    },
    "state_cancelled": {
        "zh-CN": "已取消",
        "en":    "Cancelled",
    },
    "state_deadline_exceeded": {
        "zh-CN": "超时",
        "en":    "Deadline exceeded",
    },
    # ── 组件库通用文案 ──────────────────────────────────────
    "btn_copy_path": {
        "zh-CN": "📋 复制路径",
        "en":    "📋 Copy path",
    },
    "btn_view_result": {
        "zh-CN": "🔍 查看结果",
        "en":    "🔍 View result",
    },
    "btn_stop": {
        "zh-CN": "⏹ 停止",
        "en":    "⏹ Stop",
    },
    "btn_refresh": {
        "zh-CN": "🔄 刷新数据",
        "en":    "🔄 Refresh",
    },
    "empty_no_items": {
        "zh-CN": "暂无项目",
        "en":    "No items",
    },
}






#  查询函数
# ══════════════════════════════════════════════════════════════

_current_lang = "zh-CN"


def set_language(lang: str) -> None:
    """切换当前语言。zh-TW 旧配置自动回落为简体中文。"""
    global _current_lang
    if lang == "zh-TW":
        lang = "zh-CN"
    if lang in ("zh-CN", "en"):
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
