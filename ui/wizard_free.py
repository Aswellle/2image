"""
ui/wizard_free.py — 新手引导：配置免费 Provider
首次启动时弹出，引导用户配置免费 Key。
"""
import os, sys, webbrowser
import tkinter as tk
from tkinter import messagebox

BG   = "#1e1e2e"
FG   = "#cdd6f4"
ACCENT = "#cba6f7"
GREEN = "#a6e3a1"
YELLOW = "#f9e2af"

# 已知稳定的免费接口
TIER0_NO_KEY = [
    ("Pollinations.AI", "无需 Key，0 成本， 支持 img2img（需网络）", "https://image.pollinations.ai/"),
]
TIER1_FREE = [
    ("Google Gemini 2.5 Flash", "免费 500次/天，中文友好，无需翻墙",
     "https://aistudio.google.com/apikey"),
    ("Cloudflare AI", "免费 1万次/天，SDXL 模型，全球 CDN",
     "https://dash.cloudflare.com"),
    ("ModelsLab", "免费 100次/天，支持 img2img",
     "https://modelslab.com/"),
    ("Segmind", "注册送 $5，支持 img2img",
     "https://segmind.com/"),
    ("Ideogram V2", "注册送 100 次，文字生成图像天花板",
     "https://ideogram.ai/api"),
    ("Recraft V3", "50 次/小时免费，支持矢量/真实风格",
     "https://recraft.ai/"),
]


def launch_wizard() -> None:
    root = tk.Tk()
    root.configure(bg=BG)
    root.title("2image — 新手引导 ✨")
    root.geometry("680x580")
    root.resizable(False, False)

    canvas = tk.Canvas(root, bg=BG, highlightthickness=0)
    scroll = tk.Scrollbar(root, orient="vertical", command=canvas.yview)
    frame  = tk.Frame(canvas, bg=BG)

    canvas.pack(side="left", fill="both", expand=True)
    scroll.pack(side="right", fill="y")
    canvas.configure(yscrollcommand=scroll.set)
    canvas.create_window((0, 0), window=frame, anchor="nw")

    def on_configure(e):
        canvas.configure(scrollregion=canvas.bbox("all"))
    frame.bind("<Configure>", on_configure)

    # 标题
    tk.Label(frame, text="🎉 欢迎使用 2image！",
             bg=BG, fg=ACCENT, font=("Segoe UI", 16, "bold")).pack(pady=(16, 4))
    tk.Label(frame, text="以下 Provider 可免费使用，配置越多越不容易失败：",
             bg=BG, fg=FG, font=("Segoe UI", 10)).pack(pady=(0, 12))

    # TIER0: 无需 Key
    tk.Label(frame, text="🟢 无需 Key（直接可用）",
             bg=BG, fg=GREEN, font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=20)
    for name, desc, url in TIER0_NO_KEY:
        row = tk.Frame(frame, bg=BG)
        row.pack(fill="x", padx=24, pady=2)
        tk.Label(row, text=f"✅ {name}", bg=BG, fg=FG,
                 font=("Segoe UI", 10, "bold")).pack(side="left")
        tk.Label(row, text=desc, bg=BG, fg=YELLOW,
                 font=("Segoe UI", 9)).pack(side="left", padx=8)

    # TIER1: 免费 Key
    tk.Label(frame, text="🟡 需要免费 API Key（点击链接获取）",
             bg=BG, fg=YELLOW, font=("Segoe UI", 11, "bold")).pack(
                 anchor="w", padx=20, pady=(16, 4))

    for name, desc, url in TIER1_FREE:
        row = tk.Frame(frame, bg=BG)
        row.pack(fill="x", padx=24, pady=3)
        left = tk.Frame(row, bg=BG)
        left.pack(side="left")
        tk.Label(left, text=f"🔑 {name}", bg=BG, fg=FG,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w")
        tk.Label(left, text=desc, bg=BG, fg="#a6adc8",
                 font=("Segoe UI", 9)).pack(anchor="w")
        tk.Button(row, text="获取 Key →",
                  bg=ACCENT, fg="#1e1e2e", relief="flat",
                  font=("Segoe UI", 9, "bold"),
                  command=lambda u=url: webbrowser.open(u)).pack(side="right")

    # 提示
    tk.Label(frame, text="💡 获取 Key 后，在「设置」标签页填入即可。",
             bg=BG, fg="#89b4fa", font=("Segoe UI", 10)).pack(pady=(16, 4))
    tk.Label(frame, text="配置越多 → 失败自动切换 → 成功率越高",
             bg=BG, fg="#89b4fa", font=("Segoe UI", 9)).pack()

    # 按钮
    btn = tk.Button(frame, text="开始使用 2image →",
                    bg=ACCENT, fg="#1e1e2e",
                    font=("Segoe UI", 12, "bold"),
                    relief="flat", padx=24, pady=8,
                    command=root.destroy)
    btn.pack(pady=20)

    root.mainloop()
