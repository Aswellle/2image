"""
config/fonts.py — 字体管理器

加载开源字体并注册到当前进程，提供全局字体配置字典 F。
• 主字体：MiSans Medium（小米开源，OFL 授权）→ 微软雅黑（系统兜底）
• 等宽字体：JetBrains Mono（OFL 授权）→ Consolas（系统兜底）

字体文件缓存在 ~/.text_to_image_app/fonts/。
下载源：jsDelivr CDN（国内可正常访问）。
字体仅注册到当前进程，不修改系统字体配置。
"""
import os
import sys
import ctypes
import threading
import urllib.request

from config.settings import APP_DIR

_FONTS_DIR = os.path.join(APP_DIR, "fonts")
os.makedirs(_FONTS_DIR, exist_ok=True)

# ── 下载源配置 ────────────────────────────────────────────────
_DL = [
    {
        "file":   "MiSans-Medium.ttf",
        "family": "MiSans",
        "role":   "sans",
        "urls": [
            "https://cdn.jsdelivr.net/gh/xiaomi/MiSans@main/MiSans/MiSans-Medium.ttf",
            "https://raw.githubusercontent.com/xiaomi/MiSans/main/MiSans/MiSans-Medium.ttf",
        ],
    },
    {
        "file":   "JetBrainsMono-Regular.ttf",
        "family": "JetBrains Mono",
        "role":   "mono",
        "urls": [
            "https://cdn.jsdelivr.net/gh/JetBrains/JetBrainsMono@v2.304/fonts/ttf/JetBrainsMono-Regular.ttf",
        ],
    },
]

_SYS_SANS = "Microsoft YaHei"
_SYS_MONO = "Consolas"

# 全局字体字典，init_fonts() 调用后填充
F: dict = {}


def _download(url: str, dest: str) -> bool:
    """从 URL 下载字体到 dest，失败返回 False。"""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=12) as r:
            data = r.read()
        if len(data) < 30_000:
            return False
        with open(dest, "wb") as _fh:
            _fh.write(data)
        return True
    except Exception:
        return False


def _register_win(path: str) -> bool:
    """Windows：将字体注册到当前进程（FR_PRIVATE，不污染系统）。"""
    try:
        FR_PRIVATE = 0x10
        return ctypes.windll.gdi32.AddFontResourceExW(path, FR_PRIVATE, 0) > 0
    except Exception:
        return False


def _bg_download():
    """后台静默下载缺失字体文件，下次启动时生效。"""
    for entry in _DL:
        local = os.path.join(_FONTS_DIR, entry["file"])
        if os.path.exists(local):
            continue
        for url in entry["urls"]:
            if _download(url, local):
                break


def init_fonts():
    """
    同步初始化：加载已缓存字体（快速），后台下载缺失字体（次次启动生效）。
    必须在 tk.Tk() 创建前调用，否则自定义字体无法被 Tkinter 识别。
    """
    sans = _SYS_SANS
    mono = _SYS_MONO

    if sys.platform == "win32":
        for entry in _DL:
            local = os.path.join(_FONTS_DIR, entry["file"])
            if os.path.exists(local) and _register_win(local):
                if entry["role"] == "sans":
                    sans = entry["family"]
                elif entry["role"] == "mono":
                    mono = entry["family"]

        threading.Thread(target=_bg_download, daemon=True).start()

    # ── 字体规格字典 ──────────────────────────────────────────
    F.update({
        # 标题层级
        "title":      (sans, 15, "bold"),   # 窗口/模块主标题
        "h1":         (sans, 13, "bold"),   # 区域大标题
        "h2":         (sans, 12, "bold"),   # 区域小标题
        "label":      (sans, 12),           # 较大标签
        "label_lg":   (sans, 13),           # 大标签

        # 正文层级
        "btn":        (sans, 11, "bold"),   # 主要按钮（粗体 11）
        "input":      (sans, 11),           # 输入框 / 文本区
        "body":       (sans, 10),           # 普通标签 / 说明文字
        "body_b":     (sans, 10, "bold"),   # 强调正文
        "body_i":     (sans, 10, "italic"), # 斜体正文
        "small":      (sans, 9),            # 辅助说明
        "small_b":    (sans, 9, "bold"),    # 加粗辅助说明
        "small_i":    (sans, 9, "italic"),  # 斜体辅助说明
        "tiny":       (sans, 8),            # 极小文字
        "tiny_b":     (sans, 8, "bold"),    # 加粗极小文字

        # 大尺寸展示（统计数字、大标题等）
        "disp":       (sans, 14, "bold"),
        "disp_lg":    (sans, 18),
        "display":    (sans, 24),
        "display_b":  (sans, 28, "bold"),

        # 等宽字体
        "mono_tiny":  (mono, 8),
        "mono_tiny_b":(mono, 8, "bold"),
        "mono_sm":    (mono, 9),
        "mono_sm_b":  (mono, 9, "bold"),
        "mono":       (mono, 10),
        "badge":      (mono, 10, "bold"),   # 状态标签
        "mono_lg":    (mono, 11, "bold"),

        # 字体名称字符串（供动态字重场景使用）
        "_sans":      sans,
        "_mono":      mono,
    })
