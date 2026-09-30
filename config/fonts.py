"""
config/fonts.py — 字体管理器

加载开源字体并注册到当前进程，提供全局字体配置字典 F。
• 等宽字体：JetBrains Mono（OFL 授权，锁定 v2.304 + SHA256 校验）→ Consolas（系统兜底）
• 主字体：微软雅黑（系统兜底）

字体文件缓存在 ~/2image/fonts/。
下载源：jsDelivr CDN（锁定具体版本 tag，非浮动分支）。
安全（SUP-001）：下载后校验 SHA256 + 尺寸上下界，不匹配即丢弃，
绝不注册来源不可信的字体文件。字体下载失败不影响任何核心功能。
（未来可将字体文件直接打进安装包，彻底消除运行时下载。）
"""
import hashlib
import os
import sys
import ctypes
import threading
import urllib.request

from config.settings import APP_DIR

_FONTS_DIR = os.path.join(APP_DIR, "fonts")
os.makedirs(_FONTS_DIR, exist_ok=True)

# ── 下载源配置（SUP-001：pinned URL + SHA256 + 尺寸上下界）─────
# 注意：原 MiSans 源（github.com/xiaomi/MiSans@main）已失效
# （仓库 404，2026-09 验证），浮动 main 分支不可复现，故移除；
# 主字体回退到系统微软雅黑。
_DL = [
    {
        "file":      "JetBrainsMono-Regular.ttf",
        "family":    "JetBrains Mono",
        "role":      "mono",
        "sha256":    "a0bf60ef0f83c5ed4d7a75d45838548b1f6873372dfac88f71804491898d138f",
        "min_bytes": 100_000,   # 合理字体文件下界
        "max_bytes": 20_000_000,
        "urls": [
            "https://cdn.jsdelivr.net/gh/JetBrains/JetBrainsMono@v2.304/fonts/ttf/JetBrainsMono-Regular.ttf",
        ],
    },
]

_SYS_SANS = "Microsoft YaHei"
_SYS_MONO = "Consolas"

# ── 打包内字体（SUP-001 长期方案）──────────────────────────────
# PyInstaller: datas ('assets/fonts/*' → 'fonts') → sys._MEIPASS/fonts
# 开发运行：仓库 assets/fonts/（构建期由 tools/fetch_fonts.py 填充）
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_BUNDLED_DIRS = [
    os.path.join(getattr(sys, "_MEIPASS", ""), "fonts"),
    os.path.join(_PROJECT_ROOT, "assets", "fonts"),
]


def _bundled_font_path(filename: str) -> str:
    """返回打包内字体路径；不存在返回空串。"""
    for d in _BUNDLED_DIRS:
        p = os.path.join(d, filename)
        if filename and os.path.isfile(p):
            return p
    return ""


# 全局字体字典，init_fonts() 调用后填充
F: dict = {}


def _verify(data: bytes, entry: dict) -> bool:
    """SHA256 + 尺寸上下界校验；条目缺字段时仅做尺寸检查。"""
    n = len(data)
    if n < entry.get("min_bytes", 30_000):
        return False
    if n > entry.get("max_bytes", 50_000_000):
        return False
    expected = entry.get("sha256")
    if expected:
        actual = hashlib.sha256(data).hexdigest()
        if actual != expected:
            import logging
            logging.getLogger(__name__).warning(
                "字体 SHA256 不匹配，拒绝落盘: %s (got %s…)",
                entry.get("file", "?"), actual[:16])
            return False
    return True


def _download(url: str, dest: str, entry: dict) -> bool:
    """从 URL 下载字体到 dest（校验通过才落盘），失败返回 False。"""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=12) as r:
            data = r.read()
        if not _verify(data, entry):
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
            if _download(url, local, entry):
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
            # 解析顺序：用户缓存 → 打包内资源（随安装包分发，无网络依赖）
            local = os.path.join(_FONTS_DIR, entry["file"])
            path = local if os.path.exists(local) else _bundled_font_path(entry["file"])
            if path and _register_win(path):
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
