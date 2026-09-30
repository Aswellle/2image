"""
tools/fetch_fonts.py — 构建期字体获取（SUP-001 长期方案）
─────────────────────────────────────────────────────────
把发布所需的字体在**构建时**下载（锁定版本 tag + SHA256 校验）到
assets/fonts/，由 main.spec 打进安装包 —— 彻底消除运行时字体下载。

幂等：目标文件已存在且哈希匹配时直接跳过。
下载失败只告警不报错（构建继续；fonts.py 运行时回退系统字体）。
"""
import argparse
import hashlib
import os
import sys
import urllib.request

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_FONTS = os.path.join(PROJECT_ROOT, "assets", "fonts")

# 与 config/fonts.py._DL 保持一致（单一事实来源：构建期校验两者）
FONTS = [
    {
        "file":     "JetBrainsMono-Regular.ttf",
        "sha256":   "a0bf60ef0f83c5ed4d7a75d45838548b1f6873372dfac88f71804491898d138f",
        "url":      "https://cdn.jsdelivr.net/gh/JetBrains/JetBrainsMono@v2.304/fonts/ttf/JetBrainsMono-Regular.ttf",
    },
    # 许可文件（OFL 要求再分发时附带）；纯文本，不做哈希钉死
    {
        "file":     "OFL.txt",
        "sha256":   None,
        "url":      "https://cdn.jsdelivr.net/gh/JetBrains/JetBrainsMono@v2.304/OFL.txt",
    },
]


def _verify(path: str, expected: str | None) -> bool:
    if expected is None:
        return True
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest() == expected


def fetch(entry: dict, retries: int = 3) -> bool:
    dest = os.path.join(ASSETS_FONTS, entry["file"])
    if os.path.exists(dest) and _verify(dest, entry["sha256"]):
        print(f"[fonts] {entry['file']} 已存在且校验通过，跳过")
        return True
    os.makedirs(ASSETS_FONTS, exist_ok=True)
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(entry["url"],
                                         headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                data = r.read()
            tmp = dest + ".tmp"
            with open(tmp, "wb") as f:
                f.write(data)
            if not _verify(tmp, entry["sha256"]):
                os.remove(tmp)
                print(f"[fonts] {entry['file']} SHA256 不匹配，已丢弃", file=sys.stderr)
                return False
            os.replace(tmp, dest)
            print(f"[fonts] {entry['file']} 已获取（{len(data)//1024} KB，校验通过）")
            return True
        except Exception as exc:
            print(f"[fonts] 尝试 {attempt}/{retries} 失败: {exc}", file=sys.stderr)
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true",
                        help="任一字体获取失败即返回非零（CI 构建建议开启）")
    args = parser.parse_args()

    ok = True
    for entry in FONTS:
        if not fetch(entry):
            ok = False
    return 0 if (ok or not args.strict) else 1


if __name__ == "__main__":
    raise SystemExit(main())
