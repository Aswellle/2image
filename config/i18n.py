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
        "en": "✨ Text-to-Image Tool v10",
    },
    "app_input_label": {
        "zh-CN": "📝 输入描述（支持中文，自动翻译）",
        "en": "📝 Enter description (Chinese supported, auto-translate)",
    },
    # ── 菜单 ────────────────────────────────────────────────
    "menu_file": {
        "zh-CN": "📁  文件",
        "en": "📁  File",
    },
    "menu_tools": {
        "zh-CN": "🛠  工具",
        "en": "🛠  Tools",
    },
    "menu_history": {
        "zh-CN": "📜  历史",
        "en": "📜  History",
    },
    "menu_help": {
        "zh-CN": "💡  帮助",
        "en": "💡  Help",
    },
    "menu_settings": {
        "zh-CN": "⚙  设置",
        "en": "⚙  Settings",
    },
    "menu_data": {
        "zh-CN": "📊  数据",
        "en": "📊  Data",
    },
    # ── 按钮 ────────────────────────────────────────────────
    "btn_generate": {
        "zh-CN": "🎨 生成",
        "en": "🎨 Generate",
    },
    "btn_generating": {
        "zh-CN": "⏳ 生成中…",
        "en": "⏳ Generating…",
    },
    "btn_add_queue": {
        "zh-CN": "➕ 加入队列",
        "en": "➕ Add to Queue",
    },
    "btn_phrase_lib": {
        "zh-CN": "📚 词库",
        "en": "📚 Phrase Library",
    },
    "btn_prompt_wizard": {
        "zh-CN": "✨ 提示词助手",
        "en": "✨ Prompt Wizard",
    },
    "btn_variant_gen": {
        "zh-CN": "🎲 变体生成",
        "en": "🎲 Generate Variants",
    },
    "btn_paid_config": {
        "zh-CN": "💎 付费配置",
        "en": "💎 Paid API Keys",
    },
    "btn_free_config": {
        "zh-CN": "🆓 免费配置",
        "en": "🆓 Free API Keys",
    },
    "btn_save": {
        "zh-CN": "💾 保存",
        "en": "💾 Save",
    },
    "btn_export": {
        "zh-CN": "📤 导出",
        "en": "📤 Export",
    },
    "btn_reset": {
        "zh-CN": "🔄 重置",
        "en": "🔄 Reset",
    },
    "btn_clear_log": {
        "zh-CN": "清空",
        "en": "Clear",
    },
    "btn_show_more": {
        "zh-CN": "显示更多…（共 {count} 条）",
        "en": "Show more… ({count} total)",
    },
    "btn_keep": {
        "zh-CN": "✅ 保留",
        "en": "✅ Keep",
    },
    "btn_discard": {
        "zh-CN": "✕ 丢弃",
        "en": "✕ Discard",
    },
    "btn_compare": {
        "zh-CN": "🔄 对比",
        "en": "🔄 Compare",
    },
    "btn_save_image": {
        "zh-CN": "💾 保存图片",
        "en": "💾 Save Image",
    },
    "btn_open_viewer": {
        "zh-CN": "🔍 独立查看器",
        "en": "🔍 Open Viewer",
    },
    "btn_close": {
        "zh-CN": "关闭",
        "en": "Close",
    },
    "btn_cancel": {
        "zh-CN": "取消",
        "en": "Cancel",
    },
    "btn_confirm": {
        "zh-CN": "确认",
        "en": "Confirm",
    },
    "btn_skip": {
        "zh-CN": "跳过（稍后在「⚙ 设置」中配置）",
        "en": "Skip (configure later in Settings)",
    },
    "btn_save_and_start": {
        "zh-CN": "✅  保存并开始使用",
        "en": "✅  Save & Start",
    },
    "btn_save_config": {
        "zh-CN": "✅  保存配置",
        "en": "✅  Save Config",
    },
    "btn_clear_history": {
        "zh-CN": "🗑 清空历史",
        "en": "🗑 Clear History",
    },
    "btn_delete": {
        "zh-CN": "🗑 删除",
        "en": "🗑 Delete",
    },
    "btn_rename": {
        "zh-CN": "✏ 命名",
        "en": "✏ Rename",
    },
    "btn_favorite": {
        "zh-CN": "⭐ 收藏",
        "en": "⭐ Favorite",
    },
    "btn_tag": {
        "zh-CN": "🏷 标签",
        "en": "🏷 Tag",
    },
    "btn_show_all": {
        "zh-CN": "全部",
        "en": "All",
    },
    "btn_favorites_only": {
        "zh-CN": "⭐ 收藏",
        "en": "⭐ Favorites",
    },
    "menu_open_viewer": {
        "zh-CN": "🔍  打开独立查看器…",
        "en": "🔍  Open Viewer…",
    },
    "menu_save_as": {
        "zh-CN": "💾  当前图片另存为…",
        "en": "💾  Save Current Image As…",
    },
    "menu_export": {
        "zh-CN": "📦  导出历史记录…",
        "en": "📦  Export History…",
    },
    "menu_clear_log": {
        "zh-CN": "🧹  清空调试日志",
        "en": "🧹  Clear Debug Log",
    },
    "menu_api": {
        "zh-CN": "接口配置",
        "en": "Providers",
    },
    "menu_free_config": {
        "zh-CN": "🆓  免费接口配置…",
        "en": "🆓  Free Provider Setup…",
    },
    "menu_paid_config": {
        "zh-CN": "💎  付费接口配置…",
        "en": "💎  Paid Provider Setup…",
    },
    "menu_free_links": {
        "zh-CN": "🌐  免费接口注册链接",
        "en": "🌐  Free Provider Sign-up Links",
    },
    "menu_paid_links": {
        "zh-CN": "🌐  付费接口注册链接",
        "en": "🌐  Paid Provider Sign-up Links",
    },
    "menu_switch_variants": {
        "zh-CN": "🧩  切换到变体生成",
        "en": "🧩  Go to Variants",
    },
    "menu_switch_queue": {
        "zh-CN": "📋  切换到生成队列…",
        "en": "📋  Go to Queue…",
    },
    "settings_language": {
        "zh-CN": "界面语言",
        "en": "Interface Language",
    },
    "settings_lang_restart": {
        "zh-CN": "🌐 语言设置已保存，重启应用后生效",
        "en": "🌐 Language saved — restart the app to apply",
    },
    "settings_default_size": {
        "zh-CN": "默认生成尺寸",
        "en": "Default Image Size",
    },
    "settings_startup": {
        "zh-CN": "启动行为",
        "en": "Startup",
    },
    "settings_show_wizard": {
        "zh-CN": "启动时显示免费接口配置向导",
        "en": "Show free provider wizard on startup",
    },
    "settings_saved": {
        "zh-CN": "✅ 已保存！",
        "en": "✅ Saved!",
    },
    "settings_prefs_title": {
        "zh-CN": "应用偏好设置",
        "en": "Preferences",
    },
    "settings_shortcuts_title": {
        "zh-CN": "快捷键说明",
        "en": "Keyboard Shortcuts",
    },
    "filter_viewing": {
        "zh-CN": "正在查看：{filters}",
        "en": "Viewing: {filters}",
    },
    "btn_clear_filter": {
        "zh-CN": "清除筛选",
        "en": "Clear filters",
    },
    "ctx_show_in_folder": {
        "zh-CN": "📁  在文件夹中显示",
        "en": "📁  Show in Folder",
    },
    "prompt_more_controls": {
        "zh-CN": "更多精细控制（细节/构图/光影/镜头/画质）",
        "en": "More fine controls (detail/composition/lighting/camera/quality)",
    },
    # ── 标签页 ──────────────────────────────────────────────
    "tab_preview": {
        "zh-CN": "  🖼 预览  ",
        "en": "  🖼 Preview  ",
    },
    "tab_variants": {
        "zh-CN": "  🎲 变体  ",
        "en": "  🎲 Variants  ",
    },
    "tab_queue": {
        "zh-CN": "  📋 队列  ",
        "en": "  📋 Queue  ",
    },
    "tab_debug_log": {
        "zh-CN": "  📋 调试日志  ",
        "en": "  📋 Debug Log  ",
    },
    # ── 标签 — 尺寸/接口 —──────────────────────────────────
    "lbl_size": {
        "zh-CN": "尺寸:",
        "en": "Size:",
    },
    "lbl_provider": {
        "zh-CN": "接口:",
        "en": "Provider:",
    },
    "lbl_variant_count": {
        "zh-CN": "变体张数:",
        "en": "Variants:",
    },
    "lbl_chars": {
        "zh-CN": "{n} 字符",
        "en": "{n} chars",
    },
    # ── 状态消息 ────────────────────────────────────────────
    "status_ready": {
        "zh-CN": "就绪",
        "en": "Ready",
    },
    "status_translating": {
        "zh-CN": "🌐 翻译中…",
        "en": "🌐 Translating…",
    },
    "status_generating": {
        "zh-CN": "⏳ AI 绘图中，请稍候…",
        "en": "⏳ AI is drawing, please wait…",
    },
    "status_success": {
        "zh-CN": "✅ 成功！来自: {prov}",
        "en": "✅ Success! From: {prov}",
    },
    "status_failed": {
        "zh-CN": "❌ 生成失败，查看「调试日志」",
        "en": "❌ Generation failed, check Debug Log",
    },
    "status_exporting": {
        "zh-CN": "📦 正在导出…",
        "en": "📦 Exporting…",
    },
    "status_export_done": {
        "zh-CN": "✅ 导出完成",
        "en": "✅ Export complete",
    },
    "status_no_records": {
        "zh-CN": "暂无记录",
        "en": "No records",
    },
    "status_history_entry": {
        "zh-CN": "📖 {ts} · {prov}",
        "en": "📖 {ts} · {prov}",
    },
    "status_batch_start": {
        "zh-CN": "🎲 开始生成 {n} 张变体…",
        "en": "🎲 Generating {n} variants…",
    },
    "status_prompt_too_long": {
        "zh-CN": "提示词过长（{cur}/{max} 字符），请精简",
        "en": "Prompt too long ({cur}/{max} chars), please shorten",
    },
    # ── 对话框消息 ──────────────────────────────────────────
    "dlg_confirm_delete": {
        "zh-CN": "确定删除此记录？图片文件也将被删除。",
        "en": "Delete this record? The image file will also be deleted.",
    },
    "dlg_confirm_clear": {
        "zh-CN": "确定清空全部历史记录？此操作不可撤销。",
        "en": "Clear all history? This cannot be undone.",
    },
    "dlg_select_export_dir": {
        "zh-CN": "选择导出目录",
        "en": "Select export directory",
    },
    "dlg_api_key_required": {
        "zh-CN": "需要配置 API Key！\n请在「🆓 免费接口配置」或「💎 付费接口配置」中填写。",
        "en": "API Key required!\nPlease configure in Free API Keys or Paid API Keys.",
    },
    "dlg_tip": {
        "zh-CN": "提示",
        "en": "Notice",
    },
    "dlg_empty_prompt": {
        "zh-CN": "请先输入描述文字！",
        "en": "Please enter a description first!",
    },
    "dlg_pick_specific_provider": {
        "zh-CN": "请选择一个具体接口，而非分隔线。",
        "en": "Please pick a concrete provider, not a separator.",
    },
    "dlg_suggest_free_key_title": {
        "zh-CN": "建议配置",
        "en": "Suggestion",
    },
    "dlg_suggest_free_key_body": {
        "zh-CN": "尚未配置任何免费 API Key。\n建议配置「硅基流动」。\n是否现在配置？",
        "en": "No free API key configured yet.\nSiliconFlow is recommended.\nConfigure now?",
    },
    "dlg_budget_exhausted_title": {
        "zh-CN": "付费预算已用尽",
        "en": "Daily budget exhausted",
    },
    "dlg_budget_exhausted_body": {
        "zh-CN": "今日付费估算消耗已达 ${spent}（上限 ${limit}）。\n如需继续使用 {provider}，请调高「paid_daily_budget_usd」设置。",
        "en": 'Today\'s estimated paid spend has reached ${spent} (limit ${limit}).\nTo keep using {provider}, raise the "paid_daily_budget_usd" setting.',
    },
    "dlg_need_config_title": {
        "zh-CN": "需要配置",
        "en": "Configuration needed",
    },
    "dlg_need_key_body": {
        "zh-CN": "使用 {provider} 需要填写 API Key。\n是否现在配置？",
        "en": "Using {provider} requires an API key.\nConfigure now?",
    },
    "dlg_need_keys_body": {
        "zh-CN": "使用 {provider} 需要填写全部凭证（{keys}）。\n是否现在配置？",
        "en": "Using {provider} requires all of these credentials ({keys}).\nConfigure now?",
    },
    "dlg_batch_no_img2img": {
        "zh-CN": "批量生成暂不支持图生图模式\n请切换到「📝 文生图」后再批量生成",
        "en": "Batch generation does not support img2img mode.\nSwitch to text-to-image first.",
    },
    "dlg_err_key_title": {
        "zh-CN": "需要配置 API Key",
        "en": "API key configuration needed",
    },
    "dlg_err_key_body": {
        "zh-CN": "{err}\n\n点击「🆓 免费配置」配置硅基流动 API Key。",
        "en": '{err}\n\nClick "🆓 Free Config" to set up a SiliconFlow API key.',
    },
    "dlg_need_generate_first": {
        "zh-CN": "请先生成或选择一张图片",
        "en": "Generate or select an image first",
    },
    "dlg_export_done": {
        "zh-CN": "完成",
        "en": "Done",
    },
    "dlg_export_done_body": {
        "zh-CN": "已导出 {n} 条\n至：{out}",
        "en": "Exported {n} items\nTo: {out}",
    },
    "dlg_confirm_rename": {
        "zh-CN": "确认",
        "en": "Confirm",
    },
    "dlg_confirm_rename_body": {
        "zh-CN": "重命名为：「{name}」？",
        "en": 'Rename to "{name}"?',
    },
    "dlg_unfavorite_body": {
        "zh-CN": "从喜爱列表移除？\n\n「{name}」",
        "en": 'Remove from favorites?\n\n"{name}"',
    },
    "dlg_favorite_body": {
        "zh-CN": "收藏到喜爱列表？\n\n「{name}」",
        "en": 'Add to favorites?\n\n"{name}"',
    },
    "dlg_confirm_clear_n_body": {
        "zh-CN": "清空全部 {n} 条记录？\n（不删除磁盘图片文件）",
        "en": "Clear all {n} records?\n(Disk image files are kept)",
    },
    "dlg_queue_empty_prompt": {
        "zh-CN": "请先在主输入框填写提示词",
        "en": "Enter a prompt in the main input box first",
    },
    "settings_update_on_start": {
        "zh-CN": "启动时自动检查更新（仅提示，不自动下载）",
        "en": "Check for updates on startup (notify only, never auto-download)",
    },
    "menu_check_update": {
        "zh-CN": "🔄  检查更新…",
        "en": "🔄  Check for Updates…",
    },
    "menu_about": {
        "zh-CN": "ℹ  关于 2image…",
        "en": "ℹ  About 2image…",
    },
    "about_title": {
        "zh-CN": "关于 2image",
        "en": "About 2image",
    },
    "about_repo_hint": {
        "zh-CN": "开源仓库：github.com/Aswellle/2image（发行版由 GitHub Releases 托管）",
        "en": "Source: github.com/Aswellle/2image (releases hosted on GitHub Releases)",
    },
    "about_version_label": {
        "zh-CN": "当前版本",
        "en": "Current version",
    },
    "about_check_update": {
        "zh-CN": "🔄 检查更新",
        "en": "🔄 Check for Updates",
    },
    "about_checking": {
        "zh-CN": "正在检查更新…",
        "en": "Checking for updates…",
    },
    "about_up_to_date": {
        "zh-CN": "已是最新版本（v{version}）",
        "en": "Up to date (v{version})",
    },
    "about_no_releases": {
        "zh-CN": "仓库暂无正式发行版",
        "en": "No stable release published yet",
    },
    "about_new_found": {
        "zh-CN": "发现新版本 {tag}（当前 v{current}）",
        "en": "New version {tag} available (current v{current})",
    },
    "about_released_at": {
        "zh-CN": "发布于 {date}",
        "en": "Published {date}",
    },
    "about_check_failed": {
        "zh-CN": "检查更新失败：{err}",
        "en": "Check for updates failed: {err}",
    },
    "about_download_install": {
        "zh-CN": "⬇ 下载并安装",
        "en": "⬇ Download && Install",
    },
    "about_downloading": {
        "zh-CN": "下载中 {tag}：{pct}%（{done} / {total} MB · {speed} MB/s）",
        "en": "Downloading {tag}: {pct}% ({done} / {total} MB · {speed} MB/s)",
    },
    "about_downloading_nolen": {
        "zh-CN": "下载中（已接收 {done} MB）",
        "en": "Downloading ({done} MB received)",
    },
    "about_verifying": {
        "zh-CN": "校验 SHA256 中…",
        "en": "Verifying SHA256…",
    },
    "about_ready": {
        "zh-CN": "下载完成，SHA256 校验通过：\n{path}",
        "en": "Downloaded and verified: \n{path}",
    },
    "about_confirm_install_body": {
        "zh-CN": "更新包已准备完成并通过校验。\n\n安装更新需要关闭 2image：正在生成的任务应先完成或取消。\n独立更新器将退出本应用、原位升级到新版本，并自动重启新版；\n若安装失败会自动恢复旧版本。\n\n现在安装吗？",
        "en": "The update package is downloaded and verified.\n\nInstalling requires closing 2image; running generation tasks should finish or be cancelled first.\nThe independent updater will exit this app, upgrade in place and start the new build automatically;\nif installation fails the previous version is restored.\n\nInstall now?",
    },
    "about_installing": {
        "zh-CN": "独立更新器已启动，应用即将退出并安装新版本…",
        "en": "Updater started; exiting the app to install the new version…",
    },
    "about_install_failed": {
        "zh-CN": "更新失败",
        "en": "Update failed",
    },
    "about_download_cancelled": {
        "zh-CN": "已取消下载",
        "en": "Download cancelled",
    },
    "about_cancel_download": {
        "zh-CN": "取消下载",
        "en": "Cancel download",
    },
    "about_open_releases": {
        "zh-CN": "🌐 打开发布页",
        "en": "🌐 Open Releases Page",
    },
    "about_dev_hint": {
        "zh-CN": "开发环境不支持应用内安装，将打开发布页供手动下载。",
        "en": "In-app install is disabled in dev environment; opening the releases page instead.",
    },
    "about_asset_missing": {
        "zh-CN": "该发行版未附带所需的安装资产，请前往发布页下载。",
        "en": "This release has no required asset; please download from the releases page.",
    },
    "about_portable_flow": {
        "zh-CN": "检测到便携版运行：将下载新便携版，下载完成后请退出应用并用其替换当前 exe。",
        "en": "Running as portable: the new portable exe will be downloaded; exit the app and replace the current one with it.",
    },
    "about_portable_hint": {
        "zh-CN": "新便携版已下载并通过校验：\n{path}\n请退出应用后，用它替换当前 exe 即可完成更新。",
        "en": "New portable build downloaded and verified: \n{path}\nExit the app and replace your current exe with it to finish the update.",
    },
    "update_toast_found": {
        "zh-CN": "发现新版本 {tag}！可在 设置 → 关于 2image 中下载安装",
        "en": "New version {tag} available! See Settings → About 2image to install",
    },
    "about_check_failed_hint": {
        "zh-CN": "可能原因：网络连接失败 / GitHub 暂时不可访问 / 更新清单无效",
        "en": "Possible causes: network failure / GitHub temporarily unreachable / invalid update manifest",
    },
    "about_size_line": {
        "zh-CN": "安装包：Windows x64 · 约 {size} MB",
        "en": "Installer: Windows x64 · ~{size} MB",
    },
    "about_view_notes": {
        "zh-CN": "📄 查看更新内容",
        "en": "📄 View Release Notes",
    },
    "about_install_ready": {
        "zh-CN": "⬇ 安装并重启",
        "en": "⬇ Install && Restart",
    },
    "about_tasks_running_title": {
        "zh-CN": "当前有任务运行",
        "en": "A task is still running",
    },
    "about_tasks_running_body": {
        "zh-CN": "检测到正在进行的生成任务或队列任务，安装更新会退出应用并中断任务。\n\n[是] 仍要退出并更新\n[否] 等待任务完成后自行重试\n[取消] 暂不更新",
        "en": "A generation or queue task is running; installing exits the app and interrupts it.\n\n[Yes] exit and install anyway\n[No] wait for the task to finish, retry later\n[Cancel] do not update now",
    },
    "about_tasks_wait_hint": {
        "zh-CN": "已保留更新包，可稍后在此窗口继续安装。",
        "en": "The update package is kept; you can install it later from this window.",
    },
    "about_portable_ready_body": {
        "zh-CN": "更新包已下载并通过校验：\n{path}\n\n是否立即运行安装包安装正式版？（选「否」将打开发布页）",
        "en": 'The installer is downloaded and verified:\n{path}\n\nRun it now to install the full version? ("No" opens the releases page)',
    },
    "about_portable_launched": {
        "zh-CN": "已启动安装程序，请按向导完成新版安装。",
        "en": "Installer launched; follow its wizard to install the new version.",
    },
    "about_updater_missing": {
        "zh-CN": "未找到独立更新器（2image_updater.exe），将直接静默运行安装程序（无校验回滚保护）。",
        "en": "The independent updater (2image_updater.exe) was not found; falling back to a direct silent install (without verify/rollback protection).",
    },
    "upd_err_network": {
        "zh-CN": "网络连接失败",
        "en": "Network request failed",
    },
    "upd_err_http": {
        "zh-CN": "服务器返回错误",
        "en": "Server returned an error",
    },
    "upd_err_manifest": {
        "zh-CN": "更新清单无效",
        "en": "Invalid update manifest",
    },
    "upd_err_version": {
        "zh-CN": "版本号无效",
        "en": "Invalid version number",
    },
    "upd_err_size": {
        "zh-CN": "下载文件大小与清单不符",
        "en": "Downloaded size does not match the manifest",
    },
    "upd_err_hash": {
        "zh-CN": "SHA-256 校验失败，已删除下载文件",
        "en": "SHA-256 verification failed; the download was deleted",
    },
    "upd_err_launch": {
        "zh-CN": "无法启动安装程序",
        "en": "Could not launch the installer",
    },
    "upd_err_install": {
        "zh-CN": "安装程序执行失败",
        "en": "The installer did not finish successfully",
    },
    "upd_err_cancel": {
        "zh-CN": "已取消",
        "en": "Cancelled",
    },
    "upd_err_unknown": {
        "zh-CN": "未知错误",
        "en": "Unknown error",
    },
    "dlg_compare_empty": {
        "zh-CN": "暂无历史图片可用于对比",
        "en": "No history images available for comparison",
    },
    # ── 搜索 / 筛选 ─────────────────────────────────────────
    "search_placeholder": {
        "zh-CN": "🔍 搜索提示词或名称…",
        "en": "🔍 Search prompts or names…",
    },
    # ── 预览占位 ────────────────────────────────────────────
    "preview_placeholder": {
        "zh-CN": "生成图片后在此处显示缩略预览\n\n点击「🔍 独立查看器」或双击预览图\n可在独立窗口中自由缩放、拖拽、裁剪图片",
        "en": "Thumbnail preview appears here after generation\n\nClick 'Open Viewer' or double-click preview\nto zoom, pan, and crop in a separate window",
    },
    "preview_placeholder_detailed": {
        "zh-CN": "生成图片后在此处显示缩略预览\n\n双击预览图 → 独立查看器\n点击「⚖ 选取对比图」→ 并排对比",
        "en": "Thumbnail preview appears here after generation\n\nDouble-click preview → Viewer\nClick 'Pick Compare Image' → Side-by-side compare",
    },
    "preview_error": {
        "zh-CN": "❌  生成失败\n\n请查看「调试日志」",
        "en": "❌  Generation Failed\n\nCheck Debug Log",
    },
    # ── 快捷键提示 ──────────────────────────────────────────
    # 只保留 Ctrl+Enter：它在输入框内触发，且没有对应的菜单项可承载说明。
    # 其余快捷键统一由菜单栏右侧的 accelerator 文本说明。
    "shortcut_hint": {
        "zh-CN": "Ctrl+Enter 生成",
        "en": "Ctrl+Enter to generate",
    },
    # ── 错误映射 ────────────────────────────────────────────
    "err_rate_limit": {
        "zh-CN": "请求太频繁，请等待 30 秒后重试",
        "en": "Too many requests. Please wait 30 seconds.",
    },
    "err_api_key": {
        "zh-CN": "API Key 无效或已过期，请在设置中检查",
        "en": "Invalid or expired API Key. Check settings.",
    },
    "err_balance": {
        "zh-CN": "API 账户余额不足，请充值",
        "en": "Insufficient API account balance.",
    },
    "err_timeout": {
        "zh-CN": "网络连接超时，请检查网络或稍后重试",
        "en": "Connection timed out. Check network and retry.",
    },
    "err_connection": {
        "zh-CN": "网络连接失败，请检查网络设置",
        "en": "Network connection failed. Check network settings.",
    },
    "err_all_failed": {
        "zh-CN": "所有接口均失败",
        "en": "All providers failed",
    },
    # ── Provider 状态 ───────────────────────────────────────
    "provider_auto": {
        "zh-CN": "自动（按优先级）",
        "en": "Auto (by priority)",
    },
    "provider_free_section": {
        "zh-CN": "─── 免费接口 ───",
        "en": "─── Free ───",
    },
    "provider_paid_section": {
        "zh-CN": "─── 💎 付费接口 ───",
        "en": "─── 💎 Paid ───",
    },
    "status_free_count": {
        "zh-CN": "🆓 免费接口 {n}/{total}",
        "en": "🆓 Free APIs {n}/{total}",
    },
    "status_paid_count": {
        "zh-CN": "💎 付费接口 {n}/{total}",
        "en": "💎 Paid APIs {n}/{total}",
    },
    # ── 批量面板 ────────────────────────────────────────────
    "batch_loading": {
        "zh-CN": "⏳ 生成中…",
        "en": "⏳ Generating…",
    },
    "batch_error": {
        "zh-CN": "❌ 失败",
        "en": "❌ Failed",
    },
    "batch_keep_all": {
        "zh-CN": "全部保留",
        "en": "Keep All",
    },
    "batch_discard_all": {
        "zh-CN": "全部丢弃",
        "en": "Discard All",
    },
    # ── 队列面板 ────────────────────────────────────────────
    "queue_waiting": {
        "zh-CN": "⏳ 等待中",
        "en": "⏳ Waiting",
    },
    "queue_running": {
        "zh-CN": "🔄 生成中",
        "en": "🔄 Running",
    },
    "queue_done": {
        "zh-CN": "✅ 完成",
        "en": "✅ Done",
    },
    "queue_failed": {
        "zh-CN": "❌ 失败",
        "en": "❌ Failed",
    },
    "queue_cancelled": {
        "zh-CN": "⊘ 已取消",
        "en": "⊘ Cancelled",
    },
    "queue_btn_pause": {
        "zh-CN": "⏸ 暂停",
        "en": "⏸ Pause",
    },
    "queue_btn_resume": {
        "zh-CN": "▶ 继续",
        "en": "▶ Resume",
    },
    "queue_btn_start": {
        "zh-CN": "▶ 开始生成",
        "en": "▶ Start",
    },
    "queue_btn_clear_done": {
        "zh-CN": "🗑 清除已完成",
        "en": "🗑 Clear Done",
    },
    # ── 图片查看器 ──────────────────────────────────────────
    "viewer_title": {
        "zh-CN": "图片查看器",
        "en": "Image Viewer",
    },
    "viewer_fit": {
        "zh-CN": "适应窗口",
        "en": "Fit",
    },
    "viewer_100": {
        "zh-CN": "100%",
        "en": "100%",
    },
    "viewer_zoom_in": {
        "zh-CN": "放大",
        "en": "Zoom In",
    },
    "viewer_zoom_out": {
        "zh-CN": "缩小",
        "en": "Zoom Out",
    },
    "viewer_rotate_left": {
        "zh-CN": "↺ 左转",
        "en": "↺ Rotate L",
    },
    "viewer_rotate_right": {
        "zh-CN": "↻ 右转",
        "en": "↻ Rotate R",
    },
    "viewer_crop": {
        "zh-CN": "✂ 裁剪",
        "en": "✂ Crop",
    },
    "viewer_save": {
        "zh-CN": "💾 保存",
        "en": "💾 Save",
    },
    "viewer_save_as": {
        "zh-CN": "📁 另存为",
        "en": "📁 Save As",
    },
    # ── 提示词向导 ──────────────────────────────────────────
    "wizard_title": {
        "zh-CN": "✨ AI 提示词助手",
        "en": "✨ AI Prompt Wizard",
    },
    "wizard_param_tab": {
        "zh-CN": "🎯 参数",
        "en": "🎯 Parameters",
    },
    "wizard_template_tab": {
        "zh-CN": "📋 模板",
        "en": "📋 Templates",
    },
    "wizard_generate_btn": {
        "zh-CN": "🤖 AI 生成",
        "en": "🤖 AI Generate",
    },
    "wizard_use_btn": {
        "zh-CN": "✅ 使用此提示词",
        "en": "✅ Use This Prompt",
    },
    # ── Wizard 配置窗口 ─────────────────────────────────────
    "wizard_free_title": {
        "zh-CN": "🆓 免费接口配置",
        "en": "🆓 Free API Configuration",
    },
    "wizard_paid_title": {
        "zh-CN": "💎  付费接口配置",
        "en": "💎  Paid API Configuration",
    },
    "wizard_paid_subtitle": {
        "zh-CN": "按需使用 · 按量计费 · 专业级画质",
        "en": "On-demand · Pay-per-use · Professional quality",
    },
    # ── 词库面板 ────────────────────────────────────────────
    "phrase_title": {
        "zh-CN": "📚 提示词片段库",
        "en": "📚 Phrase Snippet Library",
    },
    # ── 日志 ────────────────────────────────────────────────
    "log_translate_ok": {
        "zh-CN": "翻译成功: {text}",
        "en": "Translation OK: {text}",
    },
    "log_translate_fail": {
        "zh-CN": "翻译失败（使用原文）: {err}",
        "en": "Translation failed (using original): {err}",
    },
    "log_prompt_truncated": {
        "zh-CN": "提示词过长，已截断至 {max} 字符",
        "en": "Prompt truncated to {max} chars",
    },
    # ── 统计标签 ────────────────────────────────────────────
    "stat_total": {
        "zh-CN": "总计: {n}",
        "en": "Total: {n}",
    },
    "stat_today": {
        "zh-CN": "今日: {n}",
        "en": "Today: {n}",
    },
    "stat_week": {
        "zh-CN": "本周: {n}",
        "en": "This week: {n}",
    },
    # ── 生成状态可视化 ──────────────────────────────────────
    "state_queued": {
        "zh-CN": "排队中",
        "en": "Queued",
    },
    "state_translating": {
        "zh-CN": "翻译提示词…",
        "en": "Translating prompt…",
    },
    "state_routing": {
        "zh-CN": "选择服务商…",
        "en": "Selecting provider…",
    },
    "state_submitting": {
        "zh-CN": "提交中…",
        "en": "Submitting…",
    },
    "state_polling": {
        "zh-CN": "等待生成…",
        "en": "Waiting for result…",
    },
    "state_downloading": {
        "zh-CN": "下载图片…",
        "en": "Downloading image…",
    },
    "state_validating": {
        "zh-CN": "校验图片…",
        "en": "Validating image…",
    },
    "state_persisting": {
        "zh-CN": "保存中…",
        "en": "Saving…",
    },
    "state_succeeded": {
        "zh-CN": "生成完成",
        "en": "Generation complete",
    },
    "state_failed": {
        "zh-CN": "生成失败",
        "en": "Generation failed",
    },
    "state_cancelled": {
        "zh-CN": "已取消",
        "en": "Cancelled",
    },
    "state_deadline_exceeded": {
        "zh-CN": "超时",
        "en": "Deadline exceeded",
    },
    # ── 组件库通用文案 ──────────────────────────────────────
    "btn_copy_path": {
        "zh-CN": "📋 复制路径",
        "en": "📋 Copy path",
    },
    "btn_view_result": {
        "zh-CN": "🔍 查看结果",
        "en": "🔍 View result",
    },
    "btn_stop": {
        "zh-CN": "⏹ 停止",
        "en": "⏹ Stop",
    },
    "btn_refresh": {
        "zh-CN": "🔄 刷新数据",
        "en": "🔄 Refresh",
    },
    # ── 快捷键对话框 ────────────────────────────────────────
    "shortcut_generate": {
        "zh-CN": "生成 / 重新生成",
        "en": "Generate / Regenerate",
    },
    "shortcut_wizard": {
        "zh-CN": "AI 提示词助手",
        "en": "AI Prompt Wizard",
    },
    "shortcut_phrase": {
        "zh-CN": "📚 提示词片段库",
        "en": "📚 Phrase Library",
    },
    "shortcut_save_as": {
        "zh-CN": "另存为",
        "en": "Save As",
    },
    "shortcut_export_history": {
        "zh-CN": "导出历史记录",
        "en": "Export History",
    },
    "shortcut_open_viewer": {
        "zh-CN": "打开独立查看器",
        "en": "Open Viewer",
    },
    "shortcut_clear_log": {
        "zh-CN": "清空调试日志",
        "en": "Clear Debug Log",
    },
    # ── API 注册链接 ────────────────────────────────────────
    "link_siliconflow": {
        "zh-CN": "★ 硅基流动（推荐，免费赠额）",
        "en": "★ SiliconFlow (recommended, free credits)",
    },
    "link_gemini": {
        "zh-CN": "Google Gemini（500次/天）",
        "en": "Google Gemini (500/day)",
    },
    "link_cloudflare": {
        "zh-CN": "Cloudflare AI（1万次/天）",
        "en": "Cloudflare AI (10k/day)",
    },
    "link_openrouter": {
        "zh-CN": "OpenRouter（部分模型免费）",
        "en": "OpenRouter (some models free)",
    },
    "link_modelslab": {
        "zh-CN": "ModelsLab（100次/天）",
        "en": "ModelsLab (100/day)",
    },
    "link_segmind": {
        "zh-CN": "Segmind（注册送 $5）",
        "en": "Segmind (free $5)",
    },
    "link_huggingface": {
        "zh-CN": "HuggingFace Token",
        "en": "HuggingFace Token",
    },
    "link_xai": {
        "zh-CN": "xAI Grok（注册送 $25）",
        "en": "xAI Grok (free $25)",
    },
    # ── 数据菜单 ────────────────────────────────────────────
    "menu_stats": {
        "zh-CN": "📊 统计看板…",
        "en": "📊 Statistics Dashboard…",
    },
    "menu_open_data_dir": {
        "zh-CN": "📁 打开数据文件夹",
        "en": "📁 Open Data Folder",
    },
    "menu_open_log": {
        "zh-CN": "📄 打开调试日志",
        "en": "📄 Open Debug Log",
    },
    # ── 模型显示名称 ────────────────────────────────────────
    "model_gpt_image_1": {
        "zh-CN": "GPT-Image 1 (旧版)",
        "en": "GPT-Image 1 (Legacy)",
    },
    "model_gpt_image_25_flare": {
        "zh-CN": "GPT-Image 2.5 Flare (快速)",
        "en": "GPT-Image 2.5 Flare (Fast)",
    },
    "model_gpt_image_25_sunburst": {
        "zh-CN": "GPT-Image 2.5 Sunburst (最强)",
        "en": "GPT-Image 2.5 Sunburst (Best)",
    },
    "model_gemini_nb_v1": {
        "zh-CN": "Nano Banana v1 (即将下线)",
        "en": "Nano Banana v1 (Deprecated)",
    },
    "model_ark_seedream_30": {
        "zh-CN": "豆包 Seedream 3.0 (文生图)",
        "en": "Doubao Seedream 3.0 (Text-to-Image)",
    },
    "model_ark_seedream_40": {
        "zh-CN": "豆包 Seedream 4.0 (文生图, 最新)",
        "en": "Doubao Seedream 4.0 (Text-to-Image, Latest)",
    },
    "model_ark_seedit_30": {
        "zh-CN": "豆包 SeedEdit 3.0 (图生图)",
        "en": "Doubao SeedEdit 3.0 (Image-to-Image)",
    },
    "variant_kept": {
        "zh-CN": "✅ 已保留变体到历史记录",
        "en": "✅ Variant saved to history",
    },
    "err_balance_word": {
        "zh-CN": "额度",
        "en": "quota",
    },
    "export_choose_dir": {
        "zh-CN": "选择导出位置",
        "en": "Select export location",
    },
    "export_no_image": {
        "zh-CN": "无图",
        "en": "No image",
    },
    "export_html_title": {
        "zh-CN": "AI生图记录",
        "en": "AI Image Records",
    },
    "export_html_heading": {
        "zh-CN": "✨ AI 文字生图记录本",
        "en": "✨ AI Text-to-Image Records",
    },
    "export_html_count": {
        "zh-CN": " 条",
        "en": " items",
    },
    "export_html_col_time": {
        "zh-CN": "时间",
        "en": "Time",
    },
    "export_html_col_prompt": {
        "zh-CN": "提示词",
        "en": "Prompt",
    },
    "export_html_col_provider": {
        "zh-CN": "接口",
        "en": "Provider",
    },
    "export_html_col_favorite": {
        "zh-CN": "收藏",
        "en": "Favorite",
    },
    "export_html_col_image": {
        "zh-CN": "图片",
        "en": "Image",
    },
    "export_html_filename": {
        "zh-CN": "记录本.html",
        "en": "records.html",
    },
    "dlg_no_image_body": {
        "zh-CN": "暂无图片",
        "en": "No image available",
    },
    "filetype_all": {
        "zh-CN": "所有文件",
        "en": "All Files",
    },
    "dlg_saved_body": {
        "zh-CN": "已保存：",
        "en": "Saved: ",
    },
    "path_copied": {
        "zh-CN": "📋 路径已复制",
        "en": "📋 Path copied",
    },
    # ── Viewer 信息栏标签 ────────────────────────────────────
    "lbl_size_kb": {
        "zh-CN": "大小:",
        "en": "Size:",
    },
    "lbl_zoom": {
        "zh-CN": "缩放:",
        "en": "Zoom:",
    },
    "lbl_file": {
        "zh-CN": "文件:",
        "en": "File:",
    },
    "viewer_shortcuts_hint": {
        "zh-CN": "滚轮缩放  拖拽平移  +/- 键  Esc 退出裁剪",
        "en": "Wheel: zoom  Drag: pan  +/- keys  Esc: cancel crop",
    },
    "viewer_no_metadata": {
        "zh-CN": "无元数据",
        "en": "No metadata",
    },
    "viewer_please_load": {
        "zh-CN": "请先加载图片",
        "en": "Please load an image first",
    },
    "viewer_no_image": {
        "zh-CN": "暂无图片",
        "en": "No image",
    },
    "viewer_cancel_crop": {
        "zh-CN": "✂ 取消裁剪",
        "en": "✂ Cancel crop",
    },
    "viewer_crop_mode_tip": {
        "zh-CN": "裁剪模式：拖拽鼠标选区，Esc 取消",
        "en": "Crop mode: drag to select, Esc to cancel",
    },
    "viewer_crop_title": {
        "zh-CN": "裁剪",
        "en": "Crop",
    },
    "viewer_crop_too_small": {
        "zh-CN": "选区太小，请重新选择",
        "en": "Selection too small, please reselect",
    },
    "viewer_crop_preview_title": {
        "zh-CN": "裁剪预览",
        "en": "Crop Preview",
    },
    "viewer_crop_saved_overwrite": {
        "zh-CN": "✂ 裁剪完成，原图已覆盖保存",
        "en": "✂ Crop done, original file overwritten",
    },
    "viewer_crop_saved_no_modify": {
        "zh-CN": "✂ 裁剪完成（原图未修改）",
        "en": "✂ Crop done (original file unchanged)",
    },
    "viewer_apply_crop": {
        "zh-CN": "✅ 应用裁剪",
        "en": "✅ Apply Crop",
    },
    "viewer_save_new_file": {
        "zh-CN": "📁 另存为新文件…",
        "en": "📁 Save as new file…",
    },
    "viewer_overwrite_original": {
        "zh-CN": "同时覆盖保存原图文件（此操作不可撤销）",
        "en": "Also overwrite original file (cannot be undone)",
    },
    "viewer_preview_only": {
        "zh-CN": "仅在查看器中显示裁剪结果（不修改原图文件）",
        "en": "Only show crop result in viewer (do not modify original file)",
    },
    "viewer_crop_dimensions": {
        "zh-CN": "裁剪后尺寸：{w} × {h} px",
        "en": "Cropped size: {w} × {h} px",
    },
    "viewer_crop_save_as_title": {
        "zh-CN": "裁剪另存为",
        "en": "Save Crop As",
    },
    "viewer_saved_as": {
        "zh-CN": "另存: {name}",
        "en": "Saved as: {name}",
    },
    "viewer_save_success": {
        "zh-CN": "保存成功",
        "en": "Save successful",
    },
    "viewer_saved_to": {
        "zh-CN": "已保存至：\n{path}",
        "en": "Saved to:\n{path}",
    },
    "viewer_saved": {
        "zh-CN": "💾 已保存: {name}",
        "en": "💾 Saved: {name}",
    },
    "viewer_path_copied": {
        "zh-CN": "📋 路径已复制",
        "en": "📋 Path copied",
    },
    "filetype_all": {
        "zh-CN": "所有文件",
        "en": "All files",
    },
    # ── 强度滑块锚点标签 ────────────────────────────────────
    "strength_fine_tune": {
        "zh-CN": "微调",
        "en": "Fine-tune",
    },
    "strength_blend": {
        "zh-CN": "融合",
        "en": "Blend",
    },
    "strength_reconstruct": {
        "zh-CN": "重构",
        "en": "Reconstruct",
    },
    # ── 主内容区按钮 ────────────────────────────────────────
    "btn_copy_prompt": {
        "zh-CN": "📋 复制提示词",
        "en": "📋 Copy prompt",
    },
    "mode_t2i": {
        "zh-CN": "📝 文生图",
        "en": "📝 Text-to-Image",
    },
    "mode_i2i": {
        "zh-CN": "🖼 图生图",
        "en": "🖼 Image-to-Image",
    },
    "btn_regenerate": {
        "zh-CN": "🔄 重新生成",
        "en": "🔄 Regenerate",
    },
    "btn_pick_compare": {
        "zh-CN": "⚖ 选取对比图",
        "en": "⚖ Pick Compare Image",
    },
    "btn_clear_compare": {
        "zh-CN": "✕ 清空对比",
        "en": "✕ Clear Compare",
    },
    "preview_dblclick_hint": {
        "zh-CN": "双击预览图 → 独立查看器",
        "en": "Double-click preview → Viewer",
    },
    "compare_current": {
        "zh-CN": "当前图",
        "en": "Current",
    },
    "compare_image": {
        "zh-CN": "对比图",
        "en": "Compare",
    },
    "compare_pick_hint": {
        "zh-CN": "选取对比图后显示",
        "en": "Select a compare image",
    },
    "compare_pick_title": {
        "zh-CN": "⚖  选取对比图（从历史记录）",
        "en": "⚖  Pick Compare Image (from history)",
    },
    "compare_recent_count": {
        "zh-CN": "最近 {n} 张 · 滚轮滑动",
        "en": "Recent {n} · Scroll",
    },
    "btn_pick_this": {
        "zh-CN": "✅ 选取此图",
        "en": "✅ Pick This",
    },
    "compare_pick_file_title": {
        "zh-CN": "选取对比图片",
        "en": "Pick Compare Image",
    },
    "filetype_images": {
        "zh-CN": "图片",
        "en": "Images",
    },
    "copied_feedback": {
        "zh-CN": "✓ 已复制",
        "en": "✓ Copied",
    },
    # ── 图生图参考图侧栏 ────────────────────────────────────
    "i2i_ref_title": {
        "zh-CN": "🖼 图生图参考图",
        "en": "🖼 Image-to-Image Reference",
    },
    "btn_upload_ref": {
        "zh-CN": "上传参考图",
        "en": "Upload Reference",
    },
    "btn_clear": {
        "zh-CN": "✕ 清除",
        "en": "✕ Clear",
    },
    "lbl_strength": {
        "zh-CN": "变化强度",
        "en": "Strength",
    },
    "strength_description": {
        "zh-CN": "变化强度仅适用于 Stability AI：0.1–0.3 尽量保留原图；0.4–0.6 平衡改动；0.7–0.9 按提示词重绘更多。\n其他接口会使用参考图，但不读取此数值。",
        "en": "Strength only applies to Stability AI: 0.1–0.3 preserves original; 0.4–0.6 balanced; 0.7–0.9 more redraw.\nOther providers use the reference image but ignore this value.",
    },
    "i2i_no_providers": {
        "zh-CN": "⚠ 暂无可用图生图接口，请先配置密钥",
        "en": "⚠ No image-to-image providers available, please configure keys first",
    },
    "i2i_available_providers": {
        "zh-CN": "✓ 可用接口 ({n})",
        "en": "✓ Available ({n})",
    },
    "i2i_not_supported": {
        "zh-CN": "（图生图暂不支持）",
        "en": "(not supported for i2i)",
    },
    "ref_upload_hint": {
        "zh-CN": "点击上传参考图",
        "en": "Click to upload reference",
    },
    "ref_pick_title": {
        "zh-CN": "选取参考图（图生图）",
        "en": "Pick Reference Image (i2i)",
    },
    "btn_change_ref": {
        "zh-CN": "更换参考图",
        "en": "Change Reference",
    },
    "ref_read_failed": {
        "zh-CN": "读取失败",
        "en": "Read failed",
    },
    # ── 批量面板标题/按钮 ──────────────────────────────────
    "batch_panel_title": {
        "zh-CN": "🎲  批量变体面板",
        "en": "🎲  Batch Variants Panel",
    },
    "batch_btn_compare": {
        "zh-CN": "⚖ 查看对比",
        "en": "⚖ Compare",
    },
    "batch_cmp_title": {
        "zh-CN": "⚖  图片对比模式",
        "en": "⚖  Image Compare Mode",
    },
    "batch_btn_back": {
        "zh-CN": "← 返回网格",
        "en": "← Back to Grid",
    },
    "batch_btn_swap": {
        "zh-CN": "🔄 交换 A/B",
        "en": "🔄 Swap A/B",
    },
    "batch_cmp_label_a": {
        "zh-CN": "← A  原图",
        "en": "← A  Original",
    },
    "batch_cmp_label_b": {
        "zh-CN": "B →  对比图",
        "en": "B →  Variant",
    },
    "batch_status_waiting": {
        "zh-CN": "等待…",
        "en": "Waiting…",
    },
    "batch_status_generating": {
        "zh-CN": "生成中",
        "en": "Generating",
    },
    "batch_status_cancelled": {
        "zh-CN": "⏹ 已取消",
        "en": "⏹ Cancelled",
    },
    "batch_progress_generating": {
        "zh-CN": "{done} / {total}  生成中…",
        "en": "{done} / {total}  Generating…",
    },
    "batch_progress_cancelling": {
        "zh-CN": "⏹ 停止中…",
        "en": "⏹ Cancelling…",
    },
    "batch_progress_partial": {
        "zh-CN": "⚠ {ok} 张成功 / {fail} 张失败  · 请检查状态",
        "en": "⚠ {ok} succeeded / {fail} failed  · Check status",
    },
    "batch_progress_done": {
        "zh-CN": "✅ 全部 {n} 张生成完成  · 请选择保留或丢弃",
        "en": "✅ All {n} generated  · Keep or discard",
    },
    "dlg_batch_cmp_select": {
        "zh-CN": "请先在两张图上点击「⚖ 对比」按钮分别标记 A 和 B",
        "en": "Click the ⚖ Compare button on two images to mark A and B first",
    },
    # ── 队列面板标题/按钮 ──────────────────────────────────
    "queue_panel_title": {
        "zh-CN": "📋  顺序生成队列",
        "en": "📋  Sequential Generation Queue",
    },
    "queue_empty_progress": {
        "zh-CN": "队列为空 · 在主输入框写好提示词后点「➕ 加入队列」",
        "en": "Queue is empty · Write a prompt and click ➕ Add to Queue",
    },
    "queue_empty_hint": {
        "zh-CN": "📋  队列为空\n\n在主输入框填好提示词，点击「➕ 加入队列」\n连续添加多个不同提示词后，点「▶ 开始」\n程序会按顺序自动逐一生成，无需手动等待",
        "en": "📋  Queue is empty\n\nWrite a prompt and click ➕ Add to Queue\nAdd multiple prompts, then click ▶ Start\nImages are generated sequentially",
    },
    "queue_added": {
        "zh-CN": "已加入：{prompt}…",
        "en": "Added: {prompt}…",
    },
    "dlg_queue_no_img2img": {
        "zh-CN": "顺序生成队列暂不支持图生图模式\n请切换到「📝 文生图」后再加入队列",
        "en": "Sequential queue does not support img2img mode.\nSwitch to text-to-image first.",
    },
    "dlg_queue_no_waiting": {
        "zh-CN": "队列中没有等待中的任务\n请先点「➕ 加入队列」添加提示词",
        "en": "No waiting tasks in queue.\nClick ➕ Add to Queue to add a prompt.",
    },
    "queue_btn_running": {
        "zh-CN": "▶ 运行中…",
        "en": "▶ Running…",
    },
    "queue_paused": {
        "zh-CN": "⏸ 已暂停 — 当前任务完成后停止",
        "en": "⏸ Paused — Stop after current task completes",
    },
    "queue_resumed": {
        "zh-CN": "▶ 已继续运行…",
        "en": "▶ Resumed…",
    },
    "queue_stopping": {
        "zh-CN": "⏹ 停止中 — 正在打断当前任务…",
        "en": "⏹ Stopping — Interrupting current task…",
    },
    "queue_progress_running": {
        "zh-CN": "🔄  [{done}/{total}]  {prompt}…",
        "en": "🔄  [{done}/{total}]  {prompt}…",
    },
    "queue_status_done_one": {
        "zh-CN": "✅ 队列完成一张  {provider}",
        "en": "✅ Queue completed 1 image  {provider}",
    },
    "queue_stopped": {
        "zh-CN": "⏹ 已停止  ·  本轮完成 {done} 张  ·  还有 {waiting} 个等待中（可再次点「▶ 开始」）",
        "en": "⏹ Stopped  ·  {done} completed this round  ·  {waiting} waiting (click ▶ Start to resume)",
    },
    "queue_all_done": {
        "zh-CN": "🎉 全部完成！  共生成 {n} 张图片",
        "en": "🎉 All done!  {n} images generated",
    },
    "queue_count_total": {
        "zh-CN": "共 {n}",
        "en": "Total {n}",
    },
    # ── 侧栏 & 片段库 ──────────────────────────────────────
    "tip_set_as_right_compare": {
        "zh-CN": "设为右侧对比图",
        "en": "Set as right compare image",
    },
    "status_copied_prompt": {
        "zh-CN": "📋 提示词已复制",
        "en": "📋 Prompt copied",
    },
    "toast_added_to_queue": {
        "zh-CN": "📋 已加入队列",
        "en": "📋 Added to queue",
    },
    "ctx_open_in_viewer": {
        "zh-CN": "🔍  在查看器中打开",
        "en": "🔍  Open in Viewer",
    },
    "ctx_regen": {
        "zh-CN": "🔁  一键重新生成",
        "en": "🔁  Quick Regenerate",
    },
    "ctx_copy_prompt": {
        "zh-CN": "📋  复制提示词",
        "en": "📋  Copy Prompt",
    },
    "ctx_copy_path": {
        "zh-CN": "📁  复制图片路径",
        "en": "📁  Copy Image Path",
    },
    "ctx_add_to_queue": {
        "zh-CN": "➕  加入生成队列",
        "en": "➕  Add to Queue",
    },
    "ctx_delete_entry": {
        "zh-CN": "🗑  删除此记录",
        "en": "🗑  Delete This Entry",
    },
    "dlg_edit_tag_title": {
        "zh-CN": "🏷 编辑标签 — {name}",
        "en": "🏷 Edit Tags — {name}",
    },
    "lbl_edit_tag": {
        "zh-CN": "🏷  编辑标签",
        "en": "🏷  Edit Tags",
    },
    "dlg_edit_tag_entry": {
        "zh-CN": "「{name}」",
        "en": "「{name}」",
    },
    "lbl_current_tags": {
        "zh-CN": "当前标签（点击移除）",
        "en": "Current Tags (click to remove)",
    },
    "lbl_select_from_history": {
        "zh-CN": "从历史标签选择",
        "en": "Select from History Tags",
    },
    "lbl_no_history_tags": {
        "zh-CN": "（无历史标签）",
        "en": "(No history tags)",
    },
    "lbl_new_tag": {
        "zh-CN": "新建标签",
        "en": "New Tag",
    },
    "lbl_char_count": {
        "zh-CN": "{cur}/{max} 字",
        "en": "{cur}/{max} chars",
    },
    "lbl_cleared": {
        "zh-CN": "(清除)",
        "en": "(Cleared)",
    },
    "tip_remove_from_favorites": {
        "zh-CN": "取消收藏",
        "en": "Remove from Favorites",
    },
    "tip_add_to_favorites": {
        "zh-CN": "添加到收藏",
        "en": "Add to Favorites",
    },
    "empty_no_favorites": {
        "zh-CN": "暂无收藏",
        "en": "No Favorites",
    },
    "empty_no_tag_results": {
        "zh-CN": "🏷 无「{tag}」标签",
        "en": "🏷 No 「{tag}」 tag",
    },
    "empty_no_match": {
        "zh-CN": "无匹配",
        "en": "No Match",
    },
    "phrase_hint": {
        "zh-CN": "点击词条追加到输入框  ·  🖱 悬停词条查看中文说明",
        "en": "Click phrase to append to input  ·  🖱 Hover to view Chinese description",
    },
    "btn_clear_search": {
        "zh-CN": "✕ 清空搜索",
        "en": "✕ Clear Search",
    },
    "lbl_category": {
        "zh-CN": "分类",
        "en": "Category",
    },
    "lbl_new_phrase": {
        "zh-CN": "➕ 新建词条：",
        "en": "➕ New Phrase:",
    },
    "btn_add_to_category": {
        "zh-CN": "添加到当前分类",
        "en": "Add to Current Category",
    },
    "lbl_count_items": {
        "zh-CN": "  {n} 条",
        "en": "  {n} items",
    },
    "empty_no_phrases": {
        "zh-CN": "（暂无词条）",
        "en": "(No phrases)",
    },
    "empty_no_match_results": {
        "zh-CN": "（无匹配结果）",
        "en": "(No matching results)",
    },
    "dlg_delete_phrase_title": {
        "zh-CN": "删除词条",
        "en": "Delete Phrase",
    },
    "dlg_delete_phrase_body": {
        "zh-CN": "删除「{name}」？",
        "en": 'Delete "{name}"?',
    },
    "desc_custom_phrase": {
        "zh-CN": "🔧 自定义词条\n\n点击「➕」将此词条追加到主输入框末尾，\n与其他词条用逗号自动分隔。",
        "en": '🔧 Custom Phrase\n\nClick "➕" to append this phrase to the end of the main input box,\nautomatically separated by commas with other phrases.',
    },
    "phrase_footer": {
        "zh-CN": "共 {n} 条词条  ·  点击词条追加到输入框  ·  🖱 悬停查看中文说明",
        "en": "{n} phrases total  ·  Click phrase to append to input  ·  🖱 Hover to view Chinese description",
    },
    "dlg_enter_phrase": {
        "zh-CN": "请输入词条内容",
        "en": "Please enter phrase content",
    },
    "dlg_select_category": {
        "zh-CN": "请先选择分类",
        "en": "Please select a category first",
    },
    # ── LLM 提示词向导 (wizard_llm.py) ──────────────────────
    "wizard_llm_title": {
        "zh-CN": "🤖 AI 提示词助手 · 模型密钥配置",
        "en": "🤖 AI Prompt Wizard · Model Key Setup",
    },
    "wizard_llm_btn_save_close": {
        "zh-CN": "💾  保存并关闭",
        "en": "💾  Save & Close",
    },
    "wizard_llm_btn_later": {
        "zh-CN": "稍后配置",
        "en": "Configure Later",
    },
    "wizard_llm_header_title": {
        "zh-CN": "🤖  AI 提示词助手 · 模型密钥配置",
        "en": "🤖  AI Prompt Wizard · Model Key Setup",
    },
    "wizard_llm_header_subtitle": {
        "zh-CN": "配置后即可使用 AI 自动生成高质量生图提示词",
        "en": "Configure to auto-generate high-quality prompts with AI",
    },
    "wizard_llm_preset_section_title": {
        "zh-CN": "提示词模型预设",
        "en": "Prompt Model Preset",
    },
    "wizard_llm_preset_section_sub": {
        "zh-CN": "选择质量优先或速度优先的调用路径",
        "en": "Choose quality-first or speed-first route",
    },
    "wizard_llm_preset_header": {
        "zh-CN": "单选模型预设",
        "en": "Select Model Preset",
    },
    "wizard_llm_preset_hint": {
        "zh-CN": "请选择 1 个模型作为 AI 提示词助手的调用路径",
        "en": "Select 1 model as the AI prompt wizard route",
    },
    "wizard_llm_current_badge": {
        "zh-CN": "◉ 当前使用",
        "en": "◉ Active",
    },
    "wizard_llm_preset_auto_title": {
        "zh-CN": "硅基流动自动（推荐）",
        "en": "SiliconFlow Auto (Recommended)",
    },
    "wizard_llm_preset_auto_desc": {
        "zh-CN": "按 DeepSeek V3 → Qwen → GLM 自动降级；复用 sf_key，适合免费/稳妥使用",
        "en": "Auto-fallback DeepSeek V3 → Qwen → GLM; reuses sf_key, free & reliable",
    },
    "wizard_llm_click_select": {
        "zh-CN": "点击选择",
        "en": "Click to Select",
    },
    "wizard_llm_selected": {
        "zh-CN": "✓ 已选择",
        "en": "✓ Selected",
    },
    "wizard_llm_deepseek_key_label": {
        "zh-CN": "DeepSeek 官方 API Key（Pro / Flash 预设专用）:",
        "en": "DeepSeek Official API Key (Pro / Flash preset only):",
    },
    "wizard_llm_deepseek_platform_btn": {
        "zh-CN": "🌐 DeepSeek 官方平台",
        "en": "🌐 DeepSeek Official Platform",
    },
    "wizard_llm_deepseek_hint": {
        "zh-CN": "提示：Pro / Flash 使用 DeepSeek 官方 API（api.deepseek.com），不能复用硅基流动 sf_key；未填 Key 时请选回「硅基流动自动」。",
        "en": "Note: Pro / Flash use DeepSeek official API (api.deepseek.com), cannot reuse SiliconFlow sf_key; select 'SiliconFlow Auto' if no key filled.",
    },
    "wizard_llm_sf_section_title": {
        "zh-CN": "硅基流动 SiliconFlow",
        "en": "SiliconFlow",
    },
    "wizard_llm_sf_section_sub": {
        "zh-CN": "⭐ 强烈推荐 · DeepSeek V3 · 免费额度 · 国内访问快",
        "en": "⭐ Recommended · DeepSeek V3 · Free credits · Fast in China",
    },
    "wizard_llm_sf_info_1": {
        "zh-CN": "• 注册即送免费 Token，DeepSeek V3-0324 / Qwen2.5-72B 等顶级模型均可调用",
        "en": "• Free credits on signup; DeepSeek V3-0324 / Qwen2.5-72B and more available",
    },
    "wizard_llm_sf_info_2": {
        "zh-CN": "• 同一个 sf_key 同时用于生图和提示词生成，已在「免费配置」中填写则此处自动预填",
        "en": "• Same sf_key used for image & prompt generation; auto-filled if set in Free Config",
    },
    "wizard_llm_sf_info_3": {
        "zh-CN": "• 提示词生成约消耗 200~400 token/次，免费额度通常够用数百次",
        "en": "• ~200-400 tokens per prompt; free credits usually cover hundreds of uses",
    },
    "wizard_llm_model_priority_label": {
        "zh-CN": "  模型调用优先级（自动降级，无需手动选择）",
        "en": "  Model priority (auto-fallback, no manual selection)",
    },
    "wizard_llm_sf_key_label": {
        "zh-CN": "硅基流动 API Key（sf_key）:",
        "en": "SiliconFlow API Key (sf_key):",
    },
    "wizard_llm_sf_register_btn": {
        "zh-CN": "🌐 注册硅基流动（免费）",
        "en": "🌐 Sign up SiliconFlow (Free)",
    },
    "wizard_llm_sf_get_key_btn": {
        "zh-CN": "🔑 获取 API Key",
        "en": "🔑 Get API Key",
    },
    "wizard_llm_sf_steps": {
        "zh-CN": "📋 步骤：注册/登录 → 控制台 → API 密钥 → 新建密钥 → 复制（格式：sk-xxxxx）",
        "en": "📋 Steps: Sign up → Console → API Keys → Create → Copy (format: sk-xxxxx)",
    },
    "wizard_llm_hf_section_title": {
        "zh-CN": "HuggingFace",
        "en": "HuggingFace",
    },
    "wizard_llm_hf_section_sub": {
        "zh-CN": "🆓 完全免费 · 速度较慢 · 硅基流动不可用时自动切换",
        "en": "🆓 Completely free · Slower · Auto-fallback when SiliconFlow unavailable",
    },
    "wizard_llm_hf_info_1": {
        "zh-CN": "• 免费推理 API，Mixtral-8x7B / Zephyr-7b 两个模型按顺序自动尝试",
        "en": "• Free inference API; Mixtral-8x7B / Zephyr-7b tried in order",
    },
    "wizard_llm_hf_info_2": {
        "zh-CN": "• 生成质量低于硅基流动，且有并发限制（免费队列可能需等待 20~60 秒）",
        "en": "• Lower quality than SiliconFlow; concurrency limits (free queue may wait 20-60s)",
    },
    "wizard_llm_hf_info_3": {
        "zh-CN": "• 建议：已配置 sf_key 的情况下，hf_token 作为备用即可；也可只填 sf_key",
        "en": "• Tip: If sf_key is set, hf_token is just a backup; sf_key alone is fine",
    },
    "wizard_llm_hf_key_label": {
        "zh-CN": "HuggingFace Token（hf_token）:",
        "en": "HuggingFace Token (hf_token):",
    },
    "wizard_llm_hf_register_btn": {
        "zh-CN": "🌐 注册 HuggingFace（免费）",
        "en": "🌐 Sign up HuggingFace (Free)",
    },
    "wizard_llm_hf_get_token_btn": {
        "zh-CN": "🔑 获取 Access Token",
        "en": "🔑 Get Access Token",
    },
    "wizard_llm_hf_steps": {
        "zh-CN": "📋 步骤：注册/登录 → Settings → Access Tokens → New token → 复制（格式：hf_xxxxx）",
        "en": "📋 Steps: Sign up → Settings → Access Tokens → New token → Copy (format: hf_xxxxx)",
    },
    "wizard_llm_privacy_1": {
        "zh-CN": "• 密钥仅保存在本机 ~/2image/config.json，不上传至任何服务器",
        "en": "• Keys stored only locally in ~/2image/config.json, never uploaded",
    },
    "wizard_llm_privacy_2": {
        "zh-CN": "• 开发版本的 .gitignore 已排除 config.json，密钥不会随代码提交到仓库",
        "en": "• .gitignore excludes config.json; keys never committed to repo",
    },
    "wizard_llm_privacy_3": {
        "zh-CN": "• 提示词生成请求直接从你的电脑发往 SiliconFlow / HuggingFace，不经过中间服务器",
        "en": "• Prompt requests go directly from your PC to SiliconFlow / HuggingFace",
    },
    "wizard_llm_status_deepseek_ready": {
        "zh-CN": "✅  检测到 DeepSeek 官方 Key，{label} 预设可立即使用",
        "en": "✅  DeepSeek official key detected, {label} preset ready to use",
    },
    "wizard_llm_status_sf_ready": {
        "zh-CN": "✅  检测到已配置硅基流动 Key，AI 提示词助手可立即使用",
        "en": "✅  SiliconFlow key detected, AI Prompt Wizard ready to use",
    },
    "wizard_llm_status_deepseek_select": {
        "zh-CN": "✅  检测到 DeepSeek 官方 Key；请选择 DeepSeek Pro 或 Flash 预设后使用",
        "en": "✅  DeepSeek key detected; select DeepSeek Pro or Flash preset to use",
    },
    "wizard_llm_status_hf_only": {
        "zh-CN": "⚠️  仅配置了 HuggingFace Token（兜底通道），建议同时配置硅基流动或 DeepSeek",
        "en": "⚠️  Only HuggingFace Token configured (fallback); consider adding SiliconFlow or DeepSeek",
    },
    "wizard_llm_status_none": {
        "zh-CN": "❌  尚未配置任何推理模型密钥，AI 提示词助手暂时无法使用，请至少配置一项",
        "en": "❌  No inference model key configured; AI Prompt Wizard unavailable. Please configure at least one.",
    },
    "wizard_llm_warn_deepseek_needed": {
        "zh-CN": "⚠️  Pro / Flash 预设需要填写 DeepSeek 官方 API Key",
        "en": "⚠️  Pro / Flash preset requires DeepSeek official API Key",
    },
    "wizard_llm_warn_auto_need_key": {
        "zh-CN": "⚠️  自动预设请至少填写硅基流动或 HuggingFace Key",
        "en": "⚠️  Auto preset requires at least SiliconFlow or HuggingFace key",
    },
    # ── 付费接口向导 (wizard_paid.py) ──────────────────────
    "wizard_paid_title": {
        "zh-CN": "💎 付费接口配置",
        "en": "💎 Paid API Config",
    },
    "wizard_paid_header_title": {
        "zh-CN": "💎 付费接口配置",
        "en": "💎 Paid API Config",
    },
    "wizard_paid_header_subtitle": {
        "zh-CN": "GPT-Image / 豆包 / Stability / Replicate",
        "en": "GPT-Image / Doubao / Stability / Replicate",
    },
    "wizard_paid_btn_save": {
        "zh-CN": "💾 保存配置",
        "en": "💾 Save Config",
    },
    "wizard_paid_openai_section_title": {
        "zh-CN": "OpenAI GPT-Image",
        "en": "OpenAI GPT-Image",
    },
    "wizard_paid_openai_section_sub": {
        "zh-CN": "支持文生图+图生图  |  6 种模型可选  |  按量计费",
        "en": "Text-to-image + Image-to-image  |  6 models  |  Pay-as-you-go",
    },
    "wizard_paid_openai_info_1": {
        "zh-CN": "• 模型族：GPT-Image 1 (旧版) / 1.5 / 2 / 2.5 Flare (快速) / 2.5 Sunburst (最强)",
        "en": "• Model family: GPT-Image 1 (legacy) / 1.5 / 2 / 2.5 Flare (fast) / 2.5 Sunburst (best)",
    },
    "wizard_paid_openai_info_2": {
        "zh-CN": "• GPT-Image 2+ 支持任意分辨率（16 的倍数，长边 ≤3840）",
        "en": "• GPT-Image 2+ supports any resolution (multiple of 16, long edge ≤3840)",
    },
    "wizard_paid_openai_info_3": {
        "zh-CN": "• quality=auto/low/medium/high  |  支持图生图",
        "en": "• quality=auto/low/medium/high  |  Image-to-image supported",
    },
    "wizard_paid_openai_info_4": {
        "zh-CN": "• 首次使用可能需要在 OpenAI 后台完成 Organization Verification",
        "en": "• First use may require Organization Verification in OpenAI dashboard",
    },
    "wizard_paid_openai_info_5": {
        "zh-CN": "• 需要信用卡绑定，按用量计费（最低充值 $5）",
        "en": "• Credit card required, pay-as-you-go (min top-up $5)",
    },
    "wizard_paid_openai_key_label": {
        "zh-CN": "OpenAI API Key:",
        "en": "OpenAI API Key:",
    },
    "wizard_paid_model_label": {
        "zh-CN": "模型:",
        "en": "Model:",
    },
    "wizard_paid_quality_label": {
        "zh-CN": "画质:",
        "en": "Quality:",
    },
    "wizard_paid_openai_register_btn": {
        "zh-CN": "🌐 OpenAI 注册 / 充值",
        "en": "🌐 OpenAI Sign up / Top-up",
    },
    "wizard_paid_openai_key_btn": {
        "zh-CN": "🔑 生成 API Key",
        "en": "🔑 Generate API Key",
    },
    "wizard_paid_stability_section_title": {
        "zh-CN": "Stability AI  (Stable Image)",
        "en": "Stability AI  (Stable Image)",
    },
    "wizard_paid_stability_section_sub": {
        "zh-CN": "Core ~¥0.02/张  |  Ultra ~¥0.06/张  |  SD3.5 ~¥0.47/张",
        "en": "Core ~¥0.02/img  |  Ultra ~¥0.06/img  |  SD3.5 ~¥0.47/img",
    },
    "wizard_paid_stability_info_1": {
        "zh-CN": "• 支持 Core / Ultra / SD3.5-Large 三档，新用户赠送 25 Credits 试用",
        "en": "• Core / Ultra / SD3.5-Large tiers; 25 free Credits for new users",
    },
    "wizard_paid_stability_info_2": {
        "zh-CN": "• Core：速度最快；Ultra：最高画质；SD3.5：文字渲染能力强",
        "en": "• Core: fastest; Ultra: best quality; SD3.5: strong text rendering",
    },
    "wizard_paid_stability_key_label": {
        "zh-CN": "Stability AI API Key:",
        "en": "Stability AI API Key:",
    },
    "wizard_paid_stability_model_label": {
        "zh-CN": "模型档位:",
        "en": "Model Tier:",
    },
    "wizard_paid_stability_model_hint": {
        "zh-CN": "  core=最快  ultra=最佳  sd3.5=文字强",
        "en": "  core=fastest  ultra=best  sd3.5=text",
    },
    "wizard_paid_stability_register_btn": {
        "zh-CN": "🌐 注册 Stability AI",
        "en": "🌐 Sign up Stability AI",
    },
    "wizard_paid_stability_key_btn": {
        "zh-CN": "🔑 获取 API Key",
        "en": "🔑 Get API Key",
    },
    "wizard_paid_replicate_section_title": {
        "zh-CN": "Replicate  (FLUX / SD3)",
        "en": "Replicate  (FLUX / SD3)",
    },
    "wizard_paid_replicate_section_sub": {
        "zh-CN": "多种 FLUX 模型可选  |  社区模型丰富  |  按量计费",
        "en": "Multiple FLUX models  |  Rich community models  |  Pay-as-you-go",
    },
    "wizard_paid_replicate_info_1": {
        "zh-CN": "• FLUX.1 系列：Pro / Dev / Schnell / Realism 多种风格",
        "en": "• FLUX.1 series: Pro / Dev / Schnell / Realism styles",
    },
    "wizard_paid_replicate_info_2": {
        "zh-CN": "• 支持图生图（FLUX.1 Kontext 系列）和 ControlNet",
        "en": "• Supports image-to-image (FLUX.1 Kontext series) and ControlNet",
    },
    "wizard_paid_replicate_info_3": {
        "zh-CN": "• $0.04~0.08/张，新用户赠送 $5 Credits",
        "en": "• $0.04~0.08/img, $5 free Credits for new users",
    },
    "wizard_paid_replicate_key_label": {
        "zh-CN": "Replicate API Token:",
        "en": "Replicate API Token:",
    },
    "wizard_paid_replicate_register_btn": {
        "zh-CN": "🌐 注册 Replicate",
        "en": "🌐 Sign up Replicate",
    },
    "wizard_paid_replicate_token_btn": {
        "zh-CN": "🔑 获取 API Token",
        "en": "🔑 Get API Token",
    },
    "wizard_paid_ark_section_title": {
        "zh-CN": "火山引擎 豆包 Seedream",
        "en": "Volcengine Doubao Seedream",
    },
    "wizard_paid_ark_section_sub": {
        "zh-CN": "Seedream 4.0 文生图 (最新最强)  |  SeedEdit 3.0 图生图  |  按量计费",
        "en": "Seedream 4.0 text-to-image (latest)  |  SeedEdit 3.0 image-to-image  |  Pay-as-you-go",
    },
    "wizard_paid_ark_info_1": {
        "zh-CN": "• Seedream 4.0：最新最强模型，支持 1024x1024 ~ 2048x2048 多种尺寸",
        "en": "• Seedream 4.0: latest & strongest, supports 1024x1024 ~ 2048x2048",
    },
    "wizard_paid_ark_info_2": {
        "zh-CN": "• Seedream 3.0：上一代模型，速度更快，成本更低",
        "en": "• Seedream 3.0: previous gen, faster & cheaper",
    },
    "wizard_paid_ark_info_3": {
        "zh-CN": "• SeedEdit 3.0：图生图专用，自动在「图生图」模式下启用",
        "en": "• SeedEdit 3.0: image-to-image only, auto-enabled in I2I mode",
    },
    "wizard_paid_ark_info_4": {
        "zh-CN": "• guidance_scale 建议 2.0~3.0，支持 watermark 开关",
        "en": "• guidance_scale recommended 2.0~3.0, watermark toggle supported",
    },
    "wizard_paid_ark_info_5": {
        "zh-CN": "• 新用户赠送试用额度，按生成张数计费",
        "en": "• Free trial credits for new users, billed per image",
    },
    "wizard_paid_ark_key_label": {
        "zh-CN": "火山引擎 API Key:",
        "en": "Volcengine API Key:",
    },
    "wizard_paid_ark_model_hint": {
        "zh-CN": "  图生图自动用 SeedEdit",
        "en": "  Image-to-image auto-uses SeedEdit",
    },
    "wizard_paid_ark_register_btn": {
        "zh-CN": "🌐 注册火山引擎",
        "en": "🌐 Sign up Volcengine",
    },
    "wizard_paid_ark_key_btn": {
        "zh-CN": "🔑 获取 API Key",
        "en": "🔑 Get API Key",
    },
    "wizard_paid_bfl_section_title": {
        "zh-CN": "Black Forest Labs (FLUX 官方)",
        "en": "Black Forest Labs (FLUX Official)",
    },
    "wizard_paid_bfl_section_sub": {
        "zh-CN": "FLUX.2 Pro / Flex  |  最高写实质量  |  按量计费",
        "en": "FLUX.2 Pro / Flex  |  Best photorealism  |  Pay-as-you-go",
    },
    "wizard_paid_bfl_info_1": {
        "zh-CN": "• FLUX.2 Pro：官方最强模型，支持 2K 分辨率",
        "en": "• FLUX.2 Pro: official best model, supports 2K resolution",
    },
    "wizard_paid_bfl_info_2": {
        "zh-CN": "• FLUX.2 Flex：灵活风格，适合创意设计",
        "en": "• FLUX.2 Flex: flexible style, ideal for creative design",
    },
    "wizard_paid_bfl_info_3": {
        "zh-CN": "• FLUX Kontext Pro：图生图专用（自动在图生图模式启用）",
        "en": "• FLUX Kontext Pro: image-to-image only (auto-enabled in I2I mode)",
    },
    "wizard_paid_bfl_key_label": {
        "zh-CN": "BFL API Key:",
        "en": "BFL API Key:",
    },
    "wizard_paid_bfl_register_btn": {
        "zh-CN": "🌐 注册 BFL",
        "en": "🌐 Sign up BFL",
    },
    "wizard_paid_bfl_key_btn": {
        "zh-CN": "🔑 获取 API Key",
        "en": "🔑 Get API Key",
    },
    # ── 提示词向导 Pro 版 ────────────────────────────────────
    "wizard_pro_suffix": {
        "zh-CN": "专业版",
        "en": "Pro",
    },
    "wizard_subtitle": {
        "zh-CN": "参数模式精细调控 · 模板模式一键出图",
        "en": "Parameter mode fine-tuning · Template mode one-click generation",
    },
    "wizard_badge_idle": {
        "zh-CN": "● 空闲",
        "en": "● Idle",
    },
    "wizard_badge_previewing": {
        "zh-CN": "◐ 预览中",
        "en": "◐ Previewing",
    },
    "wizard_badge_pending_fill": {
        "zh-CN": "● 待填充",
        "en": "● Pending Fill",
    },
    "wizard_random_all": {
        "zh-CN": "🎲 随机全部维度",
        "en": "🎲 Random All Dimensions",
    },
    "wizard_apply_template_btn": {
        "zh-CN": "📋  应用模板",
        "en": "📋  Apply Template",
    },
    "wizard_label_keyword_required": {
        "zh-CN": "🎯  主题关键词（必填）",
        "en": "🎯  Topic Keywords (Required)",
    },
    "wizard_example_keywords": {
        "zh-CN": "  示例：东亚少女  海边咖啡馆  黄昏  白色长裙",
        "en": "  Example: East Asian girl, seaside café, dusk, white dress",
    },
    "wizard_label_dimensions": {
        "zh-CN": "🎛  可选维度参数",
        "en": "🎛  Optional Dimension Parameters",
    },
    "wizard_label_style": {
        "zh-CN": "🎨 风格",
        "en": "🎨 Style",
    },
    "wizard_guide_style": {
        "zh-CN": "填写绘画风格，如：水墨画风、复古漫画、科幻写实",
        "en": "Enter painting style, e.g.: ink wash, retro comic, sci-fi realism",
    },
    "wizard_label_mood": {
        "zh-CN": "🌙 氛围",
        "en": "🌙 Mood",
    },
    "wizard_guide_mood": {
        "zh-CN": "填写情绪基调，如：压抑沉重、喜庆热闹、梦幻迷离",
        "en": "Enter emotional tone, e.g.: oppressive, festive, dreamy",
    },
    "wizard_label_detail": {
        "zh-CN": "🔍 细节",
        "en": "🔍 Detail",
    },
    "wizard_guide_detail": {
        "zh-CN": "填写关键细节，如：雨滴挂在睫毛上、锈迹斑斑的金属板",
        "en": "Enter key details, e.g.: raindrops on eyelashes, rusty metal plate",
    },
    "wizard_label_composition": {
        "zh-CN": "📐 构图",
        "en": "📐 Composition",
    },
    "wizard_guide_composition": {
        "zh-CN": "填写画面布局，如：主体偏左 1/3、强调前景后景层次",
        "en": "Enter layout, e.g.: subject left 1/3, emphasize foreground/background",
    },
    "wizard_label_lighting": {
        "zh-CN": "💡 光影",
        "en": "💡 Lighting",
    },
    "wizard_guide_lighting": {
        "zh-CN": "填写光源，如：烛光从下方打亮脸部、雨后阳光穿破云层",
        "en": "Enter light source, e.g.: candlelight from below, sunlight through clouds",
    },
    "wizard_label_camera": {
        "zh-CN": "📷 镜头",
        "en": "📷 Camera",
    },
    "wizard_guide_camera": {
        "zh-CN": "填写镜头参数，如：400mm 望远 f/5.6、GoPro 超广角",
        "en": "Enter lens params, e.g.: 400mm telephoto f/5.6, GoPro ultra-wide",
    },
    "wizard_label_quality": {
        "zh-CN": "✨ 画质",
        "en": "✨ Quality",
    },
    "wizard_guide_quality": {
        "zh-CN": "填写画质描述，如：胶片颗粒感、印刷品半调网点",
        "en": "Enter quality description, e.g.: film grain, print halftone dots",
    },
    "wizard_label_extra": {
        "zh-CN": "📝  额外补充（可选）",
        "en": "📝  Extra Notes (Optional)",
    },
    "wizard_example_extra": {
        "zh-CN": "  💡  如：不要水印、主体面朝右边、禁止出现文字",
        "en": "  💡  E.g.: no watermark, subject facing right, no text",
    },
    "wizard_label_keyword_template": {
        "zh-CN": "🎯  主题关键词（用于填充模板）",
        "en": "🎯  Topic Keywords (for template fill)",
    },
    "wizard_example_template_keywords": {
        "zh-CN": "  💡  输入图片主题，如：咖啡美食、职场干货、旅行风景",
        "en": "  💡  Enter image topic, e.g.: coffee food, workplace tips, travel scenery",
    },
    "wizard_cat_xiaohongshu": {
        "zh-CN": "小红书",
        "en": "Xiaohongshu",
    },
    "wizard_cat_emotional": {
        "zh-CN": "情绪爆款",
        "en": "Emotional Hits",
    },
    "wizard_cat_knowledge": {
        "zh-CN": "知识干货",
        "en": "Knowledge Tips",
    },
    "wizard_cat_general": {
        "zh-CN": "通用自媒体",
        "en": "General Self-Media",
    },
    "wizard_previewing": {
        "zh-CN": "已预览：{name}",
        "en": "Previewing: {name}",
    },
    "wizard_applied": {
        "zh-CN": "已应用：{name}",
        "en": "Applied: {name}",
    },
    "wizard_label_positive_prompt": {
        "zh-CN": "📋  正面提示词（可编辑）",
        "en": "📋  Positive Prompt (Editable)",
    },
    "wizard_clear_content": {
        "zh-CN": "✕ 清除内容",
        "en": "✕ Clear Content",
    },
    "wizard_placeholder_prompt": {
        "zh-CN": "AI 生成或选中模板后\n正面提示词显示在这里…",
        "en": "After AI generation or template selection\npositive prompt will appear here…",
    },
    "wizard_smart_trim": {
        "zh-CN": "✂️ 智能压缩",
        "en": "✂️ Smart Trim",
    },
    "wizard_copy_positive": {
        "zh-CN": "📋 复制正面",
        "en": "📋 Copy Positive",
    },
    "wizard_label_session_history": {
        "zh-CN": "📖  本次会话历史",
        "en": "📖  Session History",
    },
    "wizard_warn_no_keyword": {
        "zh-CN": "请先填写主题关键词！",
        "en": "Please enter topic keywords first!",
    },
    "wizard_label_param_prefix": {
        "zh-CN": "[参数] {text}",
        "en": "[Params] {text}",
    },
    "wizard_label_template_prefix": {
        "zh-CN": "[模板] {text}",
        "en": "[Template] {text}",
    },
    "wizard_gen_success": {
        "zh-CN": "✅ 生成成功！",
        "en": "✅ Generation Successful!",
    },
    "wizard_gen_done": {
        "zh-CN": "✅ 生成完成",
        "en": "✅ Generation Complete",
    },
    "wizard_gen_failed": {
        "zh-CN": "❌ 失败",
        "en": "❌ Failed",
    },
    "wizard_cleared": {
        "zh-CN": "已清除模板内容",
        "en": "Template content cleared",
    },
    "wizard_trim_to_count": {
        "zh-CN": "✂️ 智能压缩（→ {count} 词）",
        "en": "✂️ Smart Trim (→ {count} words)",
    },
    "wizard_trim_suggest": {
        "zh-CN": "✂️ 建议压缩（→ 约72词）",
        "en": "✂️ Suggest Trim (→ ~72 words)",
    },
    "wizard_trimmed": {
        "zh-CN": "✂️ 已压缩：{before} 词 → {after} 词",
        "en": "✂️ Trimmed: {before} words → {after} words",
    },
    "wizard_generating": {
        "zh-CN": "AI 生成中{dots}",
        "en": "AI Generating{dots}",
    },
    "wizard_filled_main": {
        "zh-CN": "✅ 已填入主输入框！可切回主界面微调后生成",
        "en": "✅ Filled into main input! Switch back to main UI to fine-tune",
    },
    "wizard_copied": {
        "zh-CN": "📋 已复制！",
        "en": "📋 Copied!",
    },
    "wizard_model_configured": {
        "zh-CN": "✅ 模型已配置",
        "en": "✅ Model Configured",
    },
    "wizard_backup_only": {
        "zh-CN": "⚠️ 仅备用通道",
        "en": "⚠️ Backup Channel Only",
    },
    "wizard_configure_key": {
        "zh-CN": "🔑 配置模型密钥",
        "en": "🔑 Configure Model Key",
    },
    "wizard_custom_option": {
        "zh-CN": "自定义…",
        "en": "Custom…",
    },
    # ── 统计仪表板 ──────────────────────────────────────────
    "stats_title": {
        "zh-CN": "📊 生成统计看板",
        "en": "📊 Generation Stats Dashboard",
    },
    "stats_refresh": {
        "zh-CN": "🔄 刷新数据",
        "en": "🔄 Refresh Data",
    },
    "stats_updated_at": {
        "zh-CN": "更新于 {time}",
        "en": "Updated at {time}",
    },
    "stats_total_images": {
        "zh-CN": "总生成图片",
        "en": "Total Images",
    },
    "stats_favorites": {
        "zh-CN": "已收藏",
        "en": "Favorites",
    },
    "stats_today": {
        "zh-CN": "今日生成",
        "en": "Today",
    },
    "stats_last_7d": {
        "zh-CN": "近 7 天",
        "en": "Last 7 Days",
    },
    "stats_last_30d": {
        "zh-CN": "近 30 天",
        "en": "Last 30 Days",
    },
    "stats_heatmap_title": {
        "zh-CN": "全年生成热力图",
        "en": "Yearly Generation Heatmap",
    },
    "stats_heatmap_subtitle": {
        "zh-CN": "悬浮格子查看当日详情",
        "en": "Hover cells for daily details",
    },
    "stats_year_total": {
        "zh-CN": "{year} 年  全年生成 {count} 张",
        "en": "{year}  Year Total: {count} images",
    },
    "stats_best_month": {
        "zh-CN": "最活跃月份: {month}月 ({count}张)",
        "en": "Most active month: {month} ({count} images)",
    },
    "stats_best_day": {
        "zh-CN": "最高单日: {date} ({count}张)",
        "en": "Peak day: {date} ({count} images)",
    },
    "stats_weekday_prefix": {
        "zh-CN": "星期{day}",
        "en": "{day}",
    },
    "stats_generated_count": {
        "zh-CN": "生成: {count} 张图片",
        "en": "Generated: {count} images",
    },
    "stats_no_records": {
        "zh-CN": "暂无生成记录",
        "en": "No generation records",
    },
    "stats_less": {
        "zh-CN": "较少",
        "en": "Less",
    },
    "stats_more": {
        "zh-CN": "较多",
        "en": "More",
    },
    "stats_year": {
        "zh-CN": "年份",
        "en": "Year",
    },
    "stats_provider_dist": {
        "zh-CN": "接口使用分布",
        "en": "Provider Usage Distribution",
    },
    "stats_top_tags": {
        "zh-CN": "标签热度 Top-10",
        "en": "Tag Popularity Top-10",
    },
    "stats_no_tags": {
        "zh-CN": "暂未使用标签  —  在历史记录卡片中点击 🏷 添加",
        "en": "No tags used yet — Click 🏷 on history cards to add",
    },
    "stats_count_suffix": {
        "zh-CN": "{count} 次",
        "en": "{count} times",
    },
    "stats_count_pct": {
        "zh-CN": "{count}次  {pct}%",
        "en": "{count} times  {pct}%",
    },
    "stats_month_1": {
        "zh-CN": "1月",
        "en": "Jan",
    },
    "stats_month_2": {
        "zh-CN": "2月",
        "en": "Feb",
    },
    "stats_month_3": {
        "zh-CN": "3月",
        "en": "Mar",
    },
    "stats_month_4": {
        "zh-CN": "4月",
        "en": "Apr",
    },
    "stats_month_5": {
        "zh-CN": "5月",
        "en": "May",
    },
    "stats_month_6": {
        "zh-CN": "6月",
        "en": "Jun",
    },
    "stats_month_7": {
        "zh-CN": "7月",
        "en": "Jul",
    },
    "stats_month_8": {
        "zh-CN": "8月",
        "en": "Aug",
    },
    "stats_month_9": {
        "zh-CN": "9月",
        "en": "Sep",
    },
    "stats_month_10": {
        "zh-CN": "10月",
        "en": "Oct",
    },
    "stats_month_11": {
        "zh-CN": "11月",
        "en": "Nov",
    },
    "stats_month_12": {
        "zh-CN": "12月",
        "en": "Dec",
    },
    "stats_week_0": {
        "zh-CN": "一",
        "en": "Mon",
    },
    "stats_week_1": {
        "zh-CN": "二",
        "en": "Tue",
    },
    "stats_week_2": {
        "zh-CN": "三",
        "en": "Wed",
    },
    "stats_week_3": {
        "zh-CN": "四",
        "en": "Thu",
    },
    "stats_week_4": {
        "zh-CN": "五",
        "en": "Fri",
    },
    "stats_week_5": {
        "zh-CN": "六",
        "en": "Sat",
    },
    "stats_week_6": {
        "zh-CN": "日",
        "en": "Sun",
    },
    # ── 提示词向导预设数据 ──────────────────────────────────
    "preset_style_1": {
        "zh-CN": "写实摄影 (Photorealistic)",
        "en": "Photorealistic",
    },
    "preset_style_2": {
        "zh-CN": "电影感 (Cinematic)",
        "en": "Cinematic",
    },
    "preset_style_3": {
        "zh-CN": "动漫插画 (Anime/Illustration)",
        "en": "Anime/Illustration",
    },
    "preset_style_4": {
        "zh-CN": "油画 (Oil Painting)",
        "en": "Oil Painting",
    },
    "preset_style_5": {
        "zh-CN": "水彩 (Watercolor)",
        "en": "Watercolor",
    },
    "preset_style_6": {
        "zh-CN": "赛博朋克 (Cyberpunk)",
        "en": "Cyberpunk",
    },
    "preset_style_7": {
        "zh-CN": "奇幻艺术 (Fantasy Art)",
        "en": "Fantasy Art",
    },
    "preset_style_8": {
        "zh-CN": "极简主义 (Minimalist)",
        "en": "Minimalist",
    },
    "preset_style_9": {
        "zh-CN": "复古胶片 (Vintage Film)",
        "en": "Vintage Film",
    },
    "preset_style_10": {
        "zh-CN": "3D 渲染 (3D Render)",
        "en": "3D Render",
    },
    "preset_style_11": {
        "zh-CN": "波普艺术 (Pop Art)",
        "en": "Pop Art",
    },
    "preset_style_12": {
        "zh-CN": "黑白摄影 (Black & White)",
        "en": "Black & White",
    },
    "preset_mood_1": {
        "zh-CN": "温柔浪漫 (Romantic)",
        "en": "Romantic",
    },
    "preset_mood_2": {
        "zh-CN": "神秘深邃 (Mysterious)",
        "en": "Mysterious",
    },
    "preset_mood_3": {
        "zh-CN": "史诗壮观 (Epic)",
        "en": "Epic",
    },
    "preset_mood_4": {
        "zh-CN": "清新自然 (Fresh & Natural)",
        "en": "Fresh & Natural",
    },
    "preset_mood_5": {
        "zh-CN": "忧郁诗意 (Melancholic)",
        "en": "Melancholic",
    },
    "preset_mood_6": {
        "zh-CN": "活泼欢快 (Cheerful)",
        "en": "Cheerful",
    },
    "preset_mood_7": {
        "zh-CN": "冷峻帅气 (Cool & Calm)",
        "en": "Cool & Calm",
    },
    "preset_mood_8": {
        "zh-CN": "温暖治愈 (Warm & Healing)",
        "en": "Warm & Healing",
    },
    "preset_mood_9": {
        "zh-CN": "紧张刺激 (Intense)",
        "en": "Intense",
    },
    "preset_mood_10": {
        "zh-CN": "梦幻唯美 (Dreamy)",
        "en": "Dreamy",
    },
    "preset_mood_11": {
        "zh-CN": "孤独静谧 (Solitary)",
        "en": "Solitary",
    },
    "preset_mood_12": {
        "zh-CN": "欢庆喜悦 (Festive)",
        "en": "Festive",
    },
    "preset_detail_1": {
        "zh-CN": "柔滑细腻皮肤 (Smooth porcelain skin)",
        "en": "Smooth porcelain skin",
    },
    "preset_detail_2": {
        "zh-CN": "毛发清晰可见 (Ultra-detailed hair strands)",
        "en": "Ultra-detailed hair strands",
    },
    "preset_detail_3": {
        "zh-CN": "服装纹理细致 (Fabric texture detail)",
        "en": "Fabric texture detail",
    },
    "preset_detail_4": {
        "zh-CN": "金属反光质感 (Metallic reflective surface)",
        "en": "Metallic reflective surface",
    },
    "preset_detail_5": {
        "zh-CN": "水面涟漪细节 (Water ripple details)",
        "en": "Water ripple details",
    },
    "preset_detail_6": {
        "zh-CN": "自然植被纹理 (Organic botanical texture)",
        "en": "Organic botanical texture",
    },
    "preset_detail_7": {
        "zh-CN": "砖石建筑细节 (Stone and brick texture)",
        "en": "Stone and brick texture",
    },
    "preset_detail_8": {
        "zh-CN": "光线粒子感 (Volumetric light particles)",
        "en": "Volumetric light particles",
    },
    "preset_comp_1": {
        "zh-CN": "三分法构图 (Rule of thirds)",
        "en": "Rule of thirds",
    },
    "preset_comp_2": {
        "zh-CN": "中心构图 (Center composition)",
        "en": "Center composition",
    },
    "preset_comp_3": {
        "zh-CN": "对称构图 (Symmetrical)",
        "en": "Symmetrical",
    },
    "preset_comp_4": {
        "zh-CN": "引导线构图 (Leading lines)",
        "en": "Leading lines",
    },
    "preset_comp_5": {
        "zh-CN": "框架构图 (Frame within frame)",
        "en": "Frame within frame",
    },
    "preset_comp_6": {
        "zh-CN": "对角线构图 (Diagonal)",
        "en": "Diagonal",
    },
    "preset_comp_7": {
        "zh-CN": "黄金螺旋 (Golden spiral)",
        "en": "Golden spiral",
    },
    "preset_comp_8": {
        "zh-CN": "留白构图 (Negative space)",
        "en": "Negative space",
    },
    "preset_comp_9": {
        "zh-CN": "俯瞰鸟瞰 (Bird's eye view)",
        "en": "Bird's eye view",
    },
    "preset_comp_10": {
        "zh-CN": "低角度仰拍 (Low angle worm's eye)",
        "en": "Low angle worm's eye",
    },
    "preset_light_1": {
        "zh-CN": "黄金时刻柔光 (Golden hour soft light)",
        "en": "Golden hour soft light",
    },
    "preset_light_2": {
        "zh-CN": "蓝调时刻 (Blue hour)",
        "en": "Blue hour",
    },
    "preset_light_3": {
        "zh-CN": "霓虹灯夜景 (Neon night lighting)",
        "en": "Neon night lighting",
    },
    "preset_light_4": {
        "zh-CN": "伦勃朗光 (Rembrandt lighting)",
        "en": "Rembrandt lighting",
    },
    "preset_light_5": {
        "zh-CN": "逆光剪影 (Backlit silhouette)",
        "en": "Backlit silhouette",
    },
    "preset_light_6": {
        "zh-CN": "柔和自然光 (Soft natural window light)",
        "en": "Soft natural window light",
    },
    "preset_light_7": {
        "zh-CN": "戏剧性侧光 (Dramatic side lighting)",
        "en": "Dramatic side lighting",
    },
    "preset_light_8": {
        "zh-CN": "环境光 (Ambient environmental lighting)",
        "en": "Ambient environmental lighting",
    },
    "preset_light_9": {
        "zh-CN": "工作室三点布光 (Studio three-point lighting)",
        "en": "Studio three-point lighting",
    },
    "preset_light_10": {
        "zh-CN": "体积光丁达尔 (Volumetric Tyndall rays)",
        "en": "Volumetric Tyndall rays",
    },
    "preset_camera_1": {
        "zh-CN": "85mm 人像定焦 f/1.4 浅景深",
        "en": "85mm portrait prime f/1.4 shallow DOF",
    },
    "preset_camera_2": {
        "zh-CN": "35mm 街拍 f/2.8 自然透视",
        "en": "35mm street f/2.8 natural perspective",
    },
    "preset_camera_3": {
        "zh-CN": "50mm 标准 f/1.8 接近人眼",
        "en": "50mm standard f/1.8 near human eye",
    },
    "preset_camera_4": {
        "zh-CN": "24mm 广角 f/4 环境感强",
        "en": "24mm wide-angle f/4 strong ambient",
    },
    "preset_camera_5": {
        "zh-CN": "200mm 长焦 f/2.8 压缩背景",
        "en": "200mm telephoto f/2.8 compressed bg",
    },
    "preset_camera_6": {
        "zh-CN": "微距镜头 f/8 超近距特写",
        "en": "Macro lens f/8 extreme close-up",
    },
    "preset_camera_7": {
        "zh-CN": "鱼眼镜头 180° 夸张透视",
        "en": "Fisheye lens 180° exaggerated perspective",
    },
    "preset_camera_8": {
        "zh-CN": "移轴镜头 miniature 效果",
        "en": "Tilt-shift lens miniature effect",
    },
    "preset_quality_1": {
        "zh-CN": "8K 超高清 (8K Ultra HD)",
        "en": "8K Ultra HD",
    },
    "preset_quality_2": {
        "zh-CN": "HDR 高动态范围 (HDR)",
        "en": "HDR High Dynamic Range",
    },
    "preset_quality_3": {
        "zh-CN": "RAW 摄影质感 (RAW photography)",
        "en": "RAW photography",
    },
    "preset_quality_4": {
        "zh-CN": "杂志封面品质 (Magazine cover quality)",
        "en": "Magazine cover quality",
    },
    "preset_quality_5": {
        "zh-CN": "专业修图精修 (Professional retouched)",
        "en": "Professional retouched",
    },
    "preset_quality_6": {
        "zh-CN": "电影级色调 (Cinematic color grade)",
        "en": "Cinematic color grade",
    },
    "preset_quality_7": {
        "zh-CN": "超锐细节 (Ultra sharp details)",
        "en": "Ultra sharp details",
    },
    "preset_quality_8": {
        "zh-CN": "无噪点纯净 (Noise-free clean)",
        "en": "Noise-free clean",
    },
    "empty_no_items": {
        "zh-CN": "暂无项目",
        "en": "No items",
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
