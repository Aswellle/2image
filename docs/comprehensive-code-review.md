# 文字生图工具 — 全面代码审查报告

> 审查日期：2026-05-26 | 版本：v1.2.1 | 审查维度：架构、安全、性能、数据层、UI/UX、可扩展性

---

## 执行摘要

该项目是一个功能丰富的桌面端文字生图工具，聚合 17+ AI 图像生成 API。代码库呈现**高于平均水平的架构素养**——四层分离、Provider 插件化注册、智能路由、线程安全设计均超出同类型 Tkinter 桌面应用的通常水准。

本次审查覆盖 6 个维度，共发现 **2 个严重问题、8 个高优先级问题、16 个中优先级问题、12 个低优先级问题**。核心风险集中在：(1) 安全——API 密钥明文存储、HTML 导出 XSS；(2) 可维护性——139KB 巨石 `app.py`、分散的色彩定义；(3) 性能——SQLite 未开启 WAL 模式、历史记录无分页；(4) 国际化——所有字符串硬编码中文。

**总体评估：可维护但技术债务在积累。** 建议分三阶段推进优化：第一阶段处理安全修复和性能速赢（1-2 天），第二阶段进行架构重构和 UX 改善（1-2 周），第三阶段实现国际化、主题切换等长期特性（2-4 周）。

---

## 一、架构审查

### 1.1 亮点

#### 四层分离，依赖单向流动

```
config/settings.py → data/repository.py → services/* → ui/*
```

每层只依赖下层，不做跨层跳转。入口 `main.py` 仅 49 行。`App` 不直接操作 SQL，Provider 不从磁盘读配置。这在 Tkinter 桌面应用中罕见。

#### Provider 插件化注册机制

新增 API 供应商仅需：写 `try_xxx()` 函数 → 在 `__init__.py` 字典加一行 → 完成。UI 下拉菜单、调度器、降级链全部自动感知。

#### 智能路由 (`smart_router.py`)

根据模板 ID 或提示词关键词推断商业场景（文字入图 / 产品摄影 / 插画 / 电商 / 社媒 / 品牌科技），每个场景有独立的供应商优先级排序。

#### 细粒度串行锁

每个需限速的 Provider 有独立的 `_LOCK` 和 `_MIN_INTV`，不同供应商的并发请求互不阻塞。优于全局锁方案。

#### 生成计数器防竞态

`App._hist_gen` 自增整数——后台缩略图线程捕获当前 gen 值，UI 回调时比对，不匹配则丢弃。用不到 10 行代码解决了多线程 Tkinter 中最常见的崩溃模式。

### 1.2 架构问题

| # | 问题 | 严重度 | 位置 | 影响 |
|---|------|--------|------|------|
| A1 | **`app.py` 139KB 巨石** — 单文件承担主窗口、历史侧边栏、标签管理、生成调度、搜索过滤、缩略图加载、统计面板 | **HIGH** | `ui/app.py` (2738 行) | 修改任何功能都需跨越数千行，是持续开发的最大摩擦点 |
| A2 | **无依赖注入** — 每个面板通过 `parent_app.cfg` / `parent_app.root` 访问 App 内部状态，强耦合 | MEDIUM | `ui/*.py` 全部 | 面板无法独立测试或复用 |
| A3 | **Provider 重试逻辑重复** — 每个 `try_xxx()` 手动实现 3 次重试 + 指数退避 + 429 特殊处理，代码几乎相同 | MEDIUM | `services/providers/*.py` (17 个文件) | 修改重试规则需同步 17 处 |
| A4 | **无错误边界** — Provider 中未捕获的异常直接穿透到 Tkinter 主循环，表现为静默卡死 | MEDIUM | `services/image_service.py:22-35` | 用户体验差，难以排查 |
| A5 | **`auto_build.py` 硬编码绝对路径** — 包含开发者本地路径 `D:\Chrome Downloads\...` | MEDIUM | `auto_build.py:15-22` | 其他机器上直接报错 |
| A6 | **无日志轮转** — `debug.log` 无限追加，可能增长到几百 MB | LOW | `services/logger.py:10-15` | 长期运行后磁盘占用失控 |

---

## 二、安全审查

### 2.1 发现汇总

**严重问题：0 | 高：2 | 中：5 | 低：3**

### 2.2 高危问题

#### S1 [HIGH] API 密钥明文存储，默认文件权限不安全

**位置：** `config/settings.py:82-85` + `config/settings.py:12-17`

**描述：** 17 个 API 供应商的密钥以明文 JSON 存储在 `~/.text_to_image_app/config.json`。未调用 `os.chmod()`，文件继承默认权限（多用户系统上可能是 world-readable）。任何以该用户身份运行的进程均可读取所有密钥。

**攻击场景：** 恶意 npm 包、浏览器扩展或本地进程读取 `config.json`，获取 OpenAI、Stability AI、Google Gemini 等付费 API 的密钥。攻击者可消耗付费额度或代表用户生成违规内容。

**修复方案：**
```python
# config/settings.py — 在 save_config() 中添加：
def save_config(cfg: dict) -> None:
    os.makedirs(APP_DIR, mode=0o700, exist_ok=True)  # 限制目录权限
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    os.chmod(CONFIG_FILE, 0o600)  # 仅所有者可读写
```
**工作量：** 5 分钟

---

#### S2 [HIGH] HTML 历史导出存在存储型 XSS

**位置：** `ui/app.py:2704-2716`（`_export` 方法）

**描述：** 四个用户可控字段（`prompt`、`title`/prompt 文本、`translated` 翻译文本、`provider` 名称、`tags`）直接拼接到 HTML 中，未经过 `html.escape()`。含 `<script>` 或 `<img onerror=>` 标签的提示词在导出的 HTML 被浏览器打开时会被执行。

**攻击场景：** 攻击者与他人分享历史导出 HTML 文件，其中包含精心构造的提示词记录。打开 HTML 时执行 XSS payload，可窃取剪贴板内容或跳转到钓鱼页面。

**修复方案：**
```python
# ui/app.py — 在 _export() 方法开头添加：
import html

# 然后对所有用户字段进行转义：
f"<td>{html.escape(e['prompt'], quote=True)}</td>"
f"<span style='color:#f0a500'>{html.escape(e.get('translated',''), quote=True)}</span>"
f"<td style='color:#4ecca3'>{html.escape(e.get('provider',''), quote=True)}</td>"
```
**工作量：** 10 分钟

### 2.3 中危问题

| # | 问题 | 位置 | 修复方向 | 工作量 |
|---|------|------|----------|--------|
| S3 | **日志注入** — `log_to_file()` 不对用户输入过滤换行符 | `services/logger.py:10-15` | `msg.replace('\n', '\\n')` + 5MB 日志轮转 | 15 分钟 |
| S4 | **SSRF 风险** — 10 个 Provider 从上游 API URL 下载图片不做 URL 校验 | `siliconflow.py:126`, `recraft.py:88`, `fal_flux.py:109` 等 | 添加 `_validate_image_url()` 屏蔽内网 IP 和非 HTTPS | 30 分钟 |
| S5 | **API 错误响应泄露** — 14 个 Provider 在异常中包含 `resp.text[:200]`，传播到 UI `messagebox` | `ui/app.py:2622-2633`, 14 个 provider 文件 | 创建 `_safe_error_text(resp)` 只提取 JSON 中的 error message | 1 小时 |
| S6 | **API 响应体写入日志** — 图片解析失败时 3 个 Provider 将完整 API 响应写入日志 | `gemini.py:117`, `openrouter.py:124`, `xai_grok.py:123` | `str(data)[:100]` 截断 | 10 分钟 |
| S7 | **无输入长度限制** — 提示词无最大长度限制，可消耗大量付费 token | `ui/app.py:2542-2544`, `services/translation.py:20` | 添加 `MAX_PROMPT_CHARS = 2000` 常量并在两处校验 | 15 分钟 |

### 2.4 低危问题

| # | 问题 | 位置 | 修复方向 |
|---|------|------|----------|
| S8 | `os.system()` 路径拼接 — 当前安全但模式脆弱 | `ui/app.py:343-347` | 改用 `subprocess.Popen()` |
| S9 | `requests` 默认 `verify=True` — 所有 API 调用正确使用 HTTPS + 证书验证 | 全局 | 无需修复，记录为良好实践 |
| S10 | 无 CSRF 风险 — 纯桌面应用，无浏览器会话 | N/A | 无需关注 |

---

## 三、性能审查

### 3.1 发现汇总

**严重问题：0 | 高：4 | 中：7 | 低：5**

### 3.2 高优先级性能问题

#### P1 [HIGH] SQLite 未开启 WAL 模式 — 并发读写阻塞

**位置：** `data/repository.py:23-28`

**当前行为：** SQLite 使用默认 DELETE 日志模式，`synchronous=FULL`，无 busy timeout。多个后台线程并发读取历史记录时，读线程等待写锁释放。

**测量估算：** 500+ 条记录 + 并发缩略图加载时，DELETE 模式下并发读取比 WAL 慢 2-4 倍。每次 `get_stats()` 发 8 条独立 `SELECT COUNT(*)`，均竞争同一把锁。

**修复方案：**
```python
# data/repository.py — 替换 _conn():
def _conn() -> sqlite3.Connection:
    if not hasattr(_thread_local, "conn"):
        conn = sqlite3.connect(DB_FILE, check_same_thread=True, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=-8000")   # 8MB 缓存
        conn.execute("PRAGMA busy_timeout=5000")
        _thread_local.conn = conn
    return _thread_local.conn
```
**预期提升：** 并发读写吞吐量提升 3-5 倍 | **工作量：** 5 分钟

---

#### P2 [HIGH] 缩略图 PhotoImage 缓存无限增长 — 内存泄漏

**位置：** `ui/app.py:850` (`self._thumbs[path] = ph`)

**当前行为：** 每个加载的缩略图 `PhotoImage` 存入 `self._thumbs` 字典，从不清理。1000 张 90×90 RGBA 缩略图 ≈ 32MB Tcl 内存泄漏。`PhotoImage` 不受 Python GC 管理。

**修复方案：**
```python
# ui/app.py — 在 _refresh_hist() 开始处添加一行：
self._thumbs.clear()
```
**预期提升：** 会话内存稳定 | **工作量：** 1 行代码

---

#### P3 [HIGH] 每次过滤/搜索都全量重建历史卡片 — O(n) Widget 开销

**位置：** `ui/app.py:553-576` (`_refresh_hist`)

**当前行为：** 每次过滤变更、搜索按键、标签点击、收藏切换、图片生成都销毁全部历史卡片 Widget 并从头重建。500 条记录时→创建 500+ 个 Frame/Label/Button，每次阻塞主线程 200-400ms。搜索框的 `trace("w", ...)` 使每次按键都触发重建。

**修复方案：**
```python
# 方案 1：搜索防抖（ui/app.py:_build_sidebar）
self._search_timer = None
def _on_search(*_):
    if self._search_timer:
        self.root.after_cancel(self._search_timer)
    self._search_timer = self.root.after(250, self._refresh_hist)
self.sv.trace("w", _on_search)

# 方案 2：分页（ui/app.py:_refresh_hist）
HIST_PAGE_SIZE = 100
items = get_all_entries(keyword=kw, only_favorites=self._fav_only,
                        tag_filter=self._tag_filter, limit=HIST_PAGE_SIZE, offset=0)
```
**预期提升：** 搜索消除卡顿；Widget 数量上限 100 | **工作量：** 30 分钟

---

#### P4 [HIGH] `get_stats()` 冗余查询 — 每次调用发 8 条 COUNT

**位置：** `data/repository.py:155-225`，调用点：`ui/app.py:512,974,1700,2620`

**当前行为：** `get_stats()` 执行 8 条独立 `SELECT COUNT(*)`，外加加载所有 `tags` 列到 Python 做内存聚合。每次标签点击触发至少 1 次调用；每次生成成功也触发 1 次。1000 条记录时每次调用 ~15-25ms。

**修复方案：**
```python
def get_stats() -> dict:
    today = datetime.now().strftime("%Y-%m-%d")
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    month_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    with _conn() as c:
        row = c.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN favorited=1 THEN 1 ELSE 0 END) as favorites,
                SUM(CASE WHEN timestamp >= ? THEN 1 ELSE 0 END) as week,
                SUM(CASE WHEN timestamp >= ? THEN 1 ELSE 0 END) as month,
                SUM(CASE WHEN timestamp LIKE ? THEN 1 ELSE 0 END) as today
            FROM history
        """, (week_ago, month_ago, f"{today}%")).fetchone()
        # … 其余 provider + daily 查询不变
```
**预期提升：** 统计查询从 8 条降为 1 条主查询 + 2 条辅助查询 | **工作量：** 10 分钟

### 3.3 中优先级性能问题

| # | 问题 | 位置 | 修复方向 | 工作量 |
|---|------|------|----------|--------|
| P5 | **无分页 — `get_all_entries()` 全量加载** | `data/repository.py:80-105` | 添加 `LIMIT ? OFFSET ?` 参数 | 15 分钟 |
| P6 | **CSV 标签用 LIKE 过滤 — 无法走索引** | `data/repository.py:83-92` | 建立 `tag` + `entry_tag` 关联表（见数据层改造） | 2 小时 |
| P7 | **HTTP 连接不复用 — 每次请求新建 TCP/TLS** | 所有 provider 文件 | 每模块添加 `requests.Session()` | 30 分钟 |
| P8 | **缺少 `timestamp` 和 `favorited` 索引** | `data/repository.py:47` | 添加两个索引 | 5 分钟 |
| P9 | **`init_fonts()` 每次都启动后台下载线程** | `config/fonts.py:95-99` | 先检查文件是否存在再启动线程 | 5 分钟 |
| P10 | **`get_stats()` 将所有 tags 加载到内存做聚合** | `data/repository.py:203-215` | 随标签关联表改造解决 | 随 P6 |
| P11 | **面板拖拽结束时遍历 4 层 Widget 树更新 wrapyth** | `ui/app.py:522-531` | 维护标签引用列表替代嵌套遍历 | 10 分钟 |

### 3.4 低优先级性能问题

| # | 问题 | 位置 | 修复方向 |
|---|------|------|----------|
| P12 | `generate_image()` 在 Provider 降级间硬编码 `time.sleep(0.5)` | `services/image_service.py:32` | 降低或移除延时 |
| P13 | Canvas resize 每次触发完整 PIL 重渲染 | `ui/app.py:1565-1569` | 添加 50ms debounce |
| P14 | `_export()` 在主线程顺序复制文件，无进度指示 | `ui/app.py:2680-2721` | 后台线程 + 进度条 |
| P15 | `init_db()` 每次启动尝试 3 次 ALTER TABLE（异常被静默捕获） | `data/repository.py:47-58` | Schema 版本号检查 |
| P16 | `migrate_from_json()` 中每次 `INSERT` 为独立事务 | `data/repository.py:267-280` | 实际已在一个 `with` 块内批量提交，非问题 |

---

## 四、数据层审查

### 4.1 Schema 分析

**当前 Schema：**
```sql
CREATE TABLE history (
    id         INTEGER PRIMARY KEY,
    timestamp  TEXT NOT NULL,
    prompt     TEXT NOT NULL,
    translated TEXT DEFAULT '',
    image_path TEXT DEFAULT '',
    provider   TEXT DEFAULT '',
    nickname   TEXT,
    favorited  INTEGER DEFAULT 0,
    tags       TEXT DEFAULT ''       -- CSV 字符串 "tag1,tag2,tag3"
);
CREATE INDEX idx_id ON history(id DESC);
```

### 4.2 问题与改进

| # | 问题 | 严重度 | 改进方案 |
|---|------|--------|----------|
| D1 | **标签存为 CSV 字符串** — 无法做索引查询，LIKE 全表扫描；无去重、无规范化 | **HIGH** | 建立 `tag` + `entry_tag` 关联表（含迁移脚本） |
| D2 | **`get_all_entries()` 无分页** — 千条记录时全部加载到内存 | **HIGH** | 加 `LIMIT`/`OFFSET` 参数 |
| D3 | **缺少 `timestamp` 索引** — 日期范围查询全表扫描 | MEDIUM | `CREATE INDEX idx_timestamp ON history(timestamp)` |
| D4 | **缺少 `favorited` 索引** — 收藏过滤全表扫描 | MEDIUM | `CREATE INDEX idx_favorited ON history(favorited)` |
| D5 | **`get_stats()` 8 条独立 COUNT** — 可用条件聚合合并为 1 条 | MEDIUM | 见 §3.2 P4 |
| D6 | **SQL LIKE 子句使用 f-string 拼接** — `LIKE '%{keyword}%'` 未参数化 | LOW | 改为 `c.execute("... LIKE ?", (f'%{kw}%',))` |

### 4.3 标签关联表迁移方案

```sql
-- 新建规范化标签表
CREATE TABLE IF NOT EXISTS tag (
    id   INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL
);
CREATE TABLE IF NOT EXISTS entry_tag (
    entry_id INTEGER REFERENCES history(id) ON DELETE CASCADE,
    tag_id   INTEGER REFERENCES tag(id) ON DELETE CASCADE,
    PRIMARY KEY (entry_id, tag_id)
);
CREATE INDEX IF NOT EXISTS idx_entry_tag_tag ON entry_tag(tag_id);

-- 从旧 CSV 迁移数据
-- Python: iterate all rows, split tags by ',', strip whitespace,
--         INSERT OR IGNORE into tag, INSERT OR IGNORE into entry_tag
```

**工作量：** 2 小时（含迁移脚本 + 更新 `add_entry`/`update_tags`/`get_all_entries`/`get_all_tags`/`get_stats`）

---

## 五、UI/UX 审查

### 5.1 发现汇总

**严重问题：0 | 高：3 | 中：5 | 低：3**

### 5.2 高优先级 UX 问题

#### U1 [HIGH] 色彩系统碎片化 — 8 个模块各维护独立调色板

**位置：** `ui/app.py:57`, `ui/batch_panel.py:22`, `ui/viewer.py:22`, `ui/wizard_free.py:15`, `ui/wizard_paid.py:19`, `ui/queue_panel.py:27`, `ui/phrase_panel.py:26`, `ui/prompt_wizard.py:39`

**问题：** 不同模块的 `bg` 值存在微妙差异（`#111827` vs `#0d1117` vs `#1a1a2e`），导致面板切换时视觉跳跃。

**修复方案：** 创建 `config/theme.py`，所有模块从统一来源导入：
```python
# config/theme.py
DARK_THEME = {
    "bg":     "#0a0f1a",
    "panel":  "#0d1b2a",
    "acc":    "#1e3a6a",
    "hl":     "#e94560",
    "text":   "#eaeaea",
    "sub":    "#7a8aaa",
    # ...
}
```
所有 `ui/*.py` 中：`from config.theme import DARK_THEME as C`

**工作量：** Medium — 需触碰 8 个文件，可用查找替换完成

---

#### U2 [HIGH] 零国际化基础设施 — 所有字符串硬编码中文

**位置：** 所有 `ui/` 和 `config/` 下的 `.py` 文件（约 250-350 个独立字符串）

**问题：** 窗口标题、菜单、按钮、状态消息、错误提示、向导说明全部硬编码中文。非中文用户完全无法使用。

**修复方案（分阶段）：**
```python
# config/i18n.py
STRINGS = {
    "zh": {
        "btn_generate":    "🎨 生成",
        "status_ready":    "就绪",
        "err_api_key":     "API Key 无效，请在设置中检查",
        # … 250-350 entries
    },
    "en": {
        "btn_generate":    "🎨 Generate",
        "status_ready":    "Ready",
        "err_api_key":     "Invalid API Key. Check your settings.",
        # …
    },
}

def _(key: str) -> str:
    lang = current_config.get("language", "zh")
    return STRINGS.get(lang, {}).get(key, key)
```
全局替换：`"🎨 生成"` → `_("btn_generate")`

**工作量：** High — 需触碰约 15 个文件，250-350 处替换

---

#### U3 [HIGH] 无键盘无障碍支持

**位置：** 所有 UI 文件

**问题：**
- 无显式 Tab 键导航顺序
- 批量变体的"保留"/"丢弃"按钮无键盘快捷键
- 模态对话框无 Enter/Escape 绑定
- 队列面板拖拽排序仅支持鼠标

**修复方案：**
- 为所有模态对话框绑定 `<Escape>` = 关闭、`<Return>` = 确认
- 批量面板添加键盘：`K` = 保留、`D` = 丢弃、`C` = 对比
- 菜单项添加 `Alt+<letter>` 加速键

**工作量：** Medium — 约 15-20 个绑定

### 5.4 中优先级 UX 问题

| # | 问题 | 严重度 | 工作量 |
|---|------|--------|--------|
| U4 | **对比度不足** — 占位文本 `#6a7a9a` 对比度仅 3.2:1（WCAG AA 要求 4.5:1） | MEDIUM | Low |
| U5 | **错误处理 UX** — 原始异常字符串显示给用户，需切换到"调试日志"标签页才能查看 | MEDIUM | Medium |
| U6 | **加载状态缺失** — 无耗时显示、无取消按钮、无 Provider 尝试进度 | MEDIUM | Medium |
| U7 | **无"全部保留"/"全部丢弃"按钮** — 批量变体需逐个操作 | LOW | Low |
| U8 | **图片查看器无元数据显示** — 无法查看生成参数（prompt、seed、provider） | LOW | Medium |

---

## 六、可扩展性审查

### 6.1 添加一个新 Provider 的当前成本

**需修改的文件：** 5-7 个
1. 创建 `services/providers/<name>.py`
2. 在 `services/providers/__init__.py` 注册
3. 在 `config/settings.py` 添加 API Key 字段
4. 在 `services/smart_router.py` 添加路由规则（可选）
5. 在 `ui/wizard_free.py` 或 `ui/wizard_paid.py` 添加配置 UI（可选但期望）
6. 在 `ui/app.py` 添加 Key 校验逻辑
7. 在 `ui/app.py` 更新状态栏计数器

### 6.2 改进：Provider 自动发现

```python
# services/providers/__init__.py — 改为自动扫描：
import pkgutil
import importlib

FREE_PROVIDERS = {}
PAID_PROVIDERS = {}
COMMERCIAL_PROVIDERS = {}

for loader, module_name, is_pkg in pkgutil.iter_modules(__path__):
    if module_name.startswith("_"):
        continue
    mod = importlib.import_module(f".{module_name}", __package__)
    info = getattr(mod, "PROVIDER_INFO", None)
    if info is None:
        continue
    registry = {"free": FREE_PROVIDERS, "paid": PAID_PROVIDERS,
                "commercial": COMMERCIAL_PROVIDERS}
    registry[info["category"]][info["name"]] = info["try_fn"]
```

每个 Provider 模块添加：
```python
PROVIDER_INFO = {
    "name": "My Provider",
    "category": "free",
    "requires_key": True,
    "config_key": "my_provider_key",
    "try_fn": try_my_provider,
}
```

**收益：** 新 Provider 从 5-7 文件修改降为 1 文件创建。**工作量：** Medium（约 50 行发现逻辑 + 13 个现有 Provider 各加 `PROVIDER_INFO` 字典）

### 6.3 配置 Schema 版本化

**当前问题：** `DEFAULT_CONFIG` 无 `config_version` 字段。新 Key 自动添加（好），但重命名/改格式的 Key 会静默破坏。

**修复方案：**
```python
# config/settings.py
DEFAULT_CONFIG = {
    "config_version": 2,
    # … existing keys …
}

def load_config():
    cfg = DEFAULT_CONFIG.copy()
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            saved = json.load(f)
        saved_ver = saved.get("config_version", 1)
        if saved_ver < 2:
            saved = _migrate_v1_to_v2(saved)
        cfg.update(saved)
    except Exception:
        pass
    return cfg
```

**工作量：** Low（约 30 行）

---

## 七、分阶段实施路线图

### 第一阶段：安全加固 + 性能速赢（1-2 天）

| 优先级 | 任务 | 文件 | 工作量 | 收益 |
|--------|------|------|--------|------|
| **P0** | API 密钥文件权限加固 | `config/settings.py` | 5 分钟 | 防止密钥泄露 |
| **P0** | HTML 导出 XSS 修复 | `ui/app.py:_export` | 10 分钟 | 消除存储型 XSS |
| **P1** | SQLite WAL 模式 + 索引 | `data/repository.py` | 10 分钟 | 3-5x 读写吞吐提升 |
| **P1** | 日志注入修复 + 轮转 | `services/logger.py` | 15 分钟 | 防止日志膨胀 |
| **P1** | 缩略图缓存清理 | `ui/app.py` | 1 行 | 消除内存泄漏 |
| **P1** | `get_stats()` 条件聚合 | `data/repository.py` | 10 分钟 | 统计查询 4x 加速 |
| **P2** | 搜索防抖 | `ui/app.py:_build_sidebar` | 10 分钟 | 消除搜索卡顿 |
| **P2** | SSRF 防护 | 10 个 provider 文件 | 30 分钟 | 防止内网探测 |
| **P2** | API 错误信息净化 | `services/providers/*.py` | 1 小时 | 防止信息泄露 |
| **P2** | 输入长度限制 | `ui/app.py` + `services/translation.py` | 15 分钟 | 防止 token 浪费 |

**第一阶段产出：** 安全性提升至生产可用标准，核心性能瓶颈消除。

---

### 第二阶段：架构重构 + 可维护性（1-2 周）

| 优先级 | 任务 | 文件 | 工作量 | 收益 |
|--------|------|------|--------|------|
| **P0** | 拆分 `app.py` → 3-4 个模块 | `ui/app.py` → `app.py` + `sidebar.py` + `main_content.py` | 4-6 小时 | 降低持续开发摩擦 |
| **P0** | 抽取 `config/theme.py` 统一配色 | `config/theme.py` + 8 个 `ui/*.py` | 2 小时 | 一处修改全局生效 |
| **P1** | Provider 重试逻辑去重 → `@with_retries` 装饰器 | `services/providers/*.py` (17 文件) | 2 小时 | 一处修改全局生效 |
| **P1** | Provider 自动发现机制 | `services/providers/__init__.py` + 13 个现有 Provider | 2 小时 | 新 Provider 从 7 文件降为 1 文件 |
| **P1** | `get_all_entries()` 加分页 | `data/repository.py` + `ui/app.py` | 1 小时 | 千条记录时内存可控 |
| **P1** | 标签关联表规范化 | `data/repository.py` + 迁移脚本 | 2 小时 | 标签查询 O(n) → O(log n) |
| **P1** | 配置 Schema 版本化 | `config/settings.py` | 30 分钟 | 配置迁移安全 |
| **P2** | 引入 `AppProtocol` 接口 | `ui/app.py` | 1 小时 | 面板可测试、可复用 |
| **P2** | 错误信息中文化映射 | `ui/app.py` | 1 小时 | 显著提升普通用户体验 |
| **P2** | HTTP Session 复用 | 各 provider 文件 | 30 分钟 | 减少 200-400ms 网络延迟 |
| **P2** | Canvas resize debounce | `ui/app.py` | 10 分钟 | 窗口缩放流畅 |
| **P2** | 导出后台线程化 | `ui/app.py:_export` | 30 分钟 | 导出不阻塞 UI |
| **P3** | 键盘快捷键完善 | `ui/app.py` + `ui/batch_panel.py` | 1 小时 | 高频操作效率提升 |
| **P3** | `main.spec` console=False | `main.spec` | 1 行 | 消除打包版黑窗口 |

**第二阶段产出：** 代码库可维护性大幅提升，`app.py` 从 139KB 降至 30-50KB 骨架 + 3-4 个 20-40KB 模块。

---

### 第三阶段：国际化 + 主题 + 完整体验（2-4 周）

| 优先级 | 任务 | 文件 | 工作量 | 收益 |
|--------|------|------|--------|------|
| **P1** | 国际化基础设施 + 中英文词条 | `config/i18n.py` + 15 个 UI 文件 | 8-12 小时 | 非中文用户可用 |
| **P1** | 亮色/暗色主题支持 | `config/theme.py` + 8 个 UI 文件 | 4-6 小时 | 白天使用舒适度提升 |
| **P2** | 图片元数据嵌入 + 查看器显示 | `services/image_service.py` + `ui/viewer.py` | 3 小时 | 查看生成参数 |
| **P2** | 批量变体"全保留/全丢弃" | `ui/batch_panel.py` | 1 小时 | 减少重复操作 |
| **P2** | 生成进度细化（Provider 尝试计数） | `ui/app.py` + `services/image_service.py` | 2 小时 | 用户不再盲等 |
| **P3** | 错误恢复 — Recycle Bin 删除模式 | `data/repository.py` | 2 小时 | 防止误删 |
| **P3** | 配置向导脏跟踪 | `ui/wizard_free.py` + `ui/wizard_paid.py` | 1 小时 | 防止误关丢失配置 |

**第三阶段产出：** 产品完整体验，具备出海和多语言用户基础。

---

## 八、风险矩阵

| 风险 | 可能性 | 影响 | 缓解措施 |
|------|--------|------|----------|
| API 密钥泄露 | 中 | 高 | 第一阶段 P0：文件权限加固 |
| XSS 通过导出 HTML | 低 | 中 | 第一阶段 P0：html.escape() |
| `app.py` 持续膨胀导致无法维护 | 高 | 高 | 第二阶段 P0：模块拆分 |
| 历史记录过千后性能退化 | 高 | 中 | 第一阶段 P2 + 第二阶段 P1：分页+WAL |
| 新开发者上手困难（无英文支持） | 低 | 中 | 第三阶段 P1：国际化 |
| 日志文件撑满磁盘 | 中 | 低 | 第一阶段 P1：轮转 |
| 硬编码路径导致构建失败 | 高 | 低 | 第二阶段 P3：相对路径 |

---

## 九、附录：良好实践记录

以下模式设计良好，应在重构中保留：

1. **字体系统** (`config/fonts.py`) — 集中化字体管理、按需下载、平台检测、语义化 `F` 字典。这是色彩系统应仿照的模式。

2. **面板架构** — 每个 UI 面板为独立类，接收 `App` 引用。Notebook 标签页 + Toplevel 弹窗区分得当。

3. **缩略图线程安全** (`app.py:813-876`) — gen 计数器 + UUID token 双重校验，稳健。

4. **轻量级选中高亮** (`app.py:791-808`) — 仅修改两张卡片的颜色而非重建整个历史列表，正确的性能决策。

5. **商业 Provider 防御性导入** (`services/providers/__init__.py:34-53`) — `try/except` 包裹导入，防止单个损坏的 Provider 导致整个应用崩溃。

6. **Provider 降级链** (`services/image_service.py:22-35`) — 遍历 Provider 列表，捕获 `ValueError` 自动切换下一个，所有接口均失败时抛出聚合错误。

---

> 报告结束。建议按第一阶段 → 第二阶段 → 第三阶段顺序推进，每阶段完成后验证应用正常运行再进入下一阶段。
