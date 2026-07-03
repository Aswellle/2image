# ✨ 文字生图工具 v10 — 重构版

## 项目结构

```
text_to_image/
├── main.py                        # 程序入口（DPI初始化 → DB初始化 → 启动UI）
│
├── config/                        # ① 配置层（Configuration Layer）
│   ├── __init__.py
│   └── settings.py                # 路径常量、DEFAULT_CONFIG、load/save config
│
├── data/                          # ② 数据层（Data Layer）
│   ├── __init__.py
│   └── repository.py              # SQLite CRUD（替代原 history.json）
│                                  # 提供 add_entry / get_all / delete / clear
│
├── services/                      # ③ 服务层（Service Layer）
│   ├── __init__.py
│   ├── logger.py                  # 日志工具（写文件 + UI回调组合）
│   ├── translation.py             # 中→英翻译（has_chinese / translate_zh_to_en）
│   ├── image_service.py           # 生成调度器 + 图片落盘（generate_image / save_image_file）
│   └── providers/                 # 各接口实现（每个接口独立一文件）
│       ├── __init__.py            # 注册表（FREE_PROVIDERS / PAID_PROVIDERS / ALL_PROVIDERS）
│       ├── siliconflow.py         # 硅基流动
│       ├── huggingface.py         # HuggingFace
│       ├── stablehorde.py         # StableHorde
│       ├── openai_dalle.py        # OpenAI DALL-E 3
│       ├── stability_ai.py        # Stability AI
│       └── replicate_flux.py      # Replicate FLUX
│
└── ui/                            # ④ 表现层（Presentation Layer）
    ├── __init__.py
    ├── app.py                     # 主窗口（App类，调度各层，不含业务实现）
    ├── viewer.py                  # 独立图片查看器（ImageViewerWindow）
    ├── wizard_free.py             # 免费接口配置向导（ConfigWizard）
    └── wizard_paid.py             # 付费接口配置向导（PaidWizard）
```

---

## 架构原则

### 高内聚

| 模块 | 职责（且仅此职责）|
|------|-----------------|
| `config/settings.py` | 路径常量、默认配置、读写 JSON |
| `data/repository.py` | 历史记录的增删查，操作 SQLite |
| `services/logger.py` | 日志写文件 + 回调组合 |
| `services/translation.py` | 中文检测 + 翻译 API |
| `services/image_service.py` | 调度接口、保存图片文件 |
| `services/providers/*.py` | 各接口 HTTP 请求（每文件仅负责一个接口）|
| `ui/app.py` | 主窗口布局、用户交互响应 |
| `ui/viewer.py` | 图片查看、缩放、裁剪 |
| `ui/wizard_*.py` | API Key 配置表单 |

### 低耦合

- **UI ↔ 服务层**：UI 通过函数调用（`generate_image`、`add_entry`）解耦，不直接操作网络或数据库
- **服务层 ↔ Provider**：通过统一签名 `fn(prompt, w, h, seed, cfg, log)` 注册，新增接口只需在 `providers/__init__.py` 中注册一行，其余代码零改动
- **日志回调**：通过 `log_cb` 参数注入，Provider 代码不依赖 UI，可独立测试
- **配置传递**：各层通过 `cfg: dict` 参数传递，不引用全局变量

### 数据层升级：JSON → SQLite

原版将历史记录存为 `history.json`，每次读写均全量加载/保存，记录多时性能下降。
重构后改用 **SQLite**（内置于 Python，无需额外安装）：

- 支持按关键词索引查询（`LIKE`）
- 单条增删，无需全量读写
- `migrate_from_json()` 函数在首次启动时自动将旧 JSON 数据导入，向后兼容

---

## 运行方式

```bash
# 安装依赖
pip install pillow requests

# 启动程序
cd text_to_image
python main.py
```

## 打包为 Windows 安装程序

本工程提供一个简单的脚本用于生成 Inno Setup 安装包（.exe）。该脚本位于 `tools/build_inno_installer.py`，使用一个模板 `installer/template.iss`，并调用 Inno Setup 命令行编译器 `ISCC`。

示例使用：

```bash
python tools/build_inno_installer.py --app-name "MyApp" --version 1.0.0 --src-dir . --out-dir dist --iscc-path ISCC
```

说明：
- `--iscc-path`：如果 `ISCC` 已添加到系统 PATH，则直接传 `ISCC`；否则传 `C:\Program Files (x86)\Inno Setup 6\ISCC.exe` 的完整路径。
- 生成的临时 `.iss` 文件会被写入临时目录，`ISCC` 将在其默认输出目录中生成安装程序，或按 `.iss` 中的 `OutputBaseFilename` 指定的位置。
 - `--icon-path`：可选，指定要包含为应用图标的 `.ico` 文件路径（默认查找 `<src-dir>/ICON_256x256.ico`）。构建器会把该图标作为安装包窗口图标并复制到程序目录，快捷方式会使用它。


## 扩展新接口（示例）

1. 新建 `services/providers/my_provider.py`，实现 `try_my_provider(prompt, w, h, seed, cfg, log)` 函数
2. 在 `services/providers/__init__.py` 中添加：
   ```python
   from services.providers.my_provider import try_my_provider

   FREE_PROVIDERS["我的接口"] = try_my_provider   # 或加入 PAID_PROVIDERS
   ```
3. 完成，UI 下拉菜单和调度器自动包含新接口

> ⚠️ API 密钥请通过应用内「⚙ 设置 → 免费配置 / 付费配置」向导填写，切勿硬编码在代码或文档中。
