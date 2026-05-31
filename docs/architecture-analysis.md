# 文字生图工具 — 架构分析报告

> 分析日期：2026-05-25 | 版本：v1.2.1

---

## 一、亮点与特色

### 系统架构

#### 1. 四层分离，依赖单向流动

```
config/settings.py → data/repository.py → services/* → ui/*
```

每层只依赖下层，不做跨层跳转。`App` 不直接碰 SQL，Provider 不读磁盘配置，入口 `main.py` 只有 49 行。这在 Tkinter 桌面应用中罕见——大多数此类项目会把 SQL、HTTP、UI 全揉在一个 3000 行的文件里。

#### 2. Provider 插件化注册机制

新增 API 供应商只需三步：

1. 写一个遵循统一签名的 `try_xxx()` 函数
2. 在 `services/providers/__init__.py` 的字典里加一行
3. 完成

UI 下拉菜单、调度器、降级链全部自动感知。真正的开闭原则——对扩展开放，对修改封闭。

#### 3. 智能路由（`smart_router.py`）

不是简单的优先级列表。根据模板 ID 或提示词关键词推断场景（文字入图 / 产品摄影 / 插画 / 电商 / 社媒 / 品牌科技），每个场景有独立的供应商优先级排序。例如检测到 "logo"、"海报" 等关键词 → 路由到支持文字渲染的 Ideogram/Recraft，而不是通用模型。这在同类工具中几乎没有。

#### 4. 串行锁的细粒度设计

每个需要限速的 Provider 有自己的 `_LOCK` 和 `_MIN_INTV`，调用不同供应商的并发请求不互相阻塞。对比全局锁方案，这在不增加复杂度的前提下最大化吞吐。

#### 5. 生成计数器防止竞态条件

`App._hist_gen` 自增整数——后台缩略图线程在生成时捕获当前 gen 值，UI 回调时比对。不匹配则丢弃结果。用不到 10 行代码解决了多线程 Tkinter 中最常见的一类崩溃（`widget no longer exists` / `invalid command name`）。

---

### 数据操作

#### 1. JSON → SQLite 静默迁移

`migrate_from_json()` 在 `init_db()` 时自动检测旧版 `history.json`，`INSERT OR IGNORE` 导入后重命名为 `.migrated`。用户无感知，零数据丢失。

#### 2. 线程本地连接

`_conn()` 用 `threading.local()` 给每个线程分配独立 `sqlite3.Connection` + `check_same_thread=False`。没有连接池依赖，没有跨线程争用，简单有效。

#### 3. 标签系统使用逗号分隔字符串

不是规范化设计（没有关联表），但对于桌面端 SQLite + 几千条记录的场景，`tags TEXT DEFAULT ''` + `LIKE '%,tag,%'` 匹配比 JOIN 三张表更简单、更快、更容易调试。务实的反范式化选择。

#### 4. 统计接口完整

`get_stats()` 返回 `{total, favorites, today, week, month, providers[], daily[], top_tags[]}`，附加热力图 (`get_year_heatmap()`) 和年度统计 (`get_year_stats()`)。给 UI 统计面板提供了充足的数据支撑。

---

### UI/UX

#### 1. 历史卡片悬停工具提示有淡入动画

`_Tooltip` 类：450ms 延迟 → 60fps opacity 渐变。不是功能性的，但说明开发者在细节上花了心思。

#### 2. 图片查看器的缩放缓存

`ImageViewerWindow` 用 `OrderedDict(max=3)` 缓存最近 3 个缩放级别，后台渲染线程 + Queue 提交。在大图（4K+）上的缩放体验不会每次都重新采样。

#### 3. 批量变体的交错延迟

`BatchPanel.run()` 对 6 个并发线程各加 `sleep(cell_idx * 2.0s)` 错开请求。对比同时发出 6 个请求 → 429 限流 → 全部失败，这个简单策略大幅提高变体成功率。

#### 4. 配置向导按免费/付费分拆

新用户只需过 `wizard_free.py`（9 个免费接口），不会被 OpenAI / Stability 的付费 Key 输入框吓退。降低激活门槛的设计。

---

## 二、可改善之处

### 系统架构

| 问题 | 影响 | 建议 |
|---|---|---|
| **`app.py` 139KB 巨石** | 单个文件承担主窗口、历史侧边栏、标签管理、生成调度、搜索过滤、缩略图加载、统计面板。修改任何功能都要跨越数千行。 | 拆分为 `app.py`（窗口骨架 + 生命周期）、`sidebar.py`（历史面板）、`main_content.py`（Notebook + 生成区）。`App` 退化为协调器。 |
| **无依赖注入，全局 `parent_app` 传递** | 每个面板通过 `parent_app.cfg` / `parent_app.root` 访问 App 内部状态。面板和 App 强耦合，无法独立测试或复用。 | 引入简单的 protocol：`class AppProtocol(Protocol): cfg: dict; root: tk.Tk; def refresh_hist(self): ...`。面板构造函数接收 `app: AppProtocol` 而非 `App` 实例。 |
| **Provider 重试逻辑重复** | 每个 `try_xxx()` 手动实现 3 次重试 + 指数退避 + 429 特殊处理，代码几乎相同（~20 行），容易遗漏。 | 抽取装饰器 `@with_retries(max_retries=3)` 或上下文管理器 `with rate_limited(lock, min_interval=2.0):` |
| **无错误边界 / 全局异常处理** | Provider 中任何未捕获异常会直接穿透到 Tkinter 主循环，表现为静默卡死或奇怪的 TclError。 | 在 `image_service.generate_image()` 加 `except Exception` 兜底，或给 daemon 线程注册 `threading.excepthook`。 |
| **`auto_build.py` 和 `main.spec` 硬编码绝对路径** | 包含开发者本地路径 `D:\Chrome Downloads\...`，其他机器上直接报错。 | 改用 `os.path.dirname(__file__)` 相对路径，或通过 CLI 参数传入。 |
| **无日志轮转** | `debug.log` 无限追加，运行几个月后可能是几百 MB。 | 加 `RotatingFileHandler` 或按日期切分。 |
| **`smart_router.py` 关键词规则是扁平列表** | 76+ 关键词线性扫描，匹配第一个即返回。规则间的优先级和冲突没有形式化。 | 规则增多后可考虑权重打分而非 first-match，或在规则注释中显式标注优先级依据。 |

### 数据操作

| 问题 | 影响 | 建议 |
|---|---|---|
| **`get_all_entries()` 无分页** | 历史记录上千条时一次性加载全部到 UI，内存和 Tkinter Canvas 创建开销线性增长。 | 加 `LIMIT ? OFFSET ?` 参数，UI 侧加"加载更多"或虚拟滚动（Canvas 可见区域外的卡片不创建 widget）。 |
| **标签是裸字符串，无约束** | `tags` 字段存逗号分隔字符串，无去重、无规范化（"风景" vs " 风景" vs "风景 "），搜索时容易漏。 | 在 `update_tags()` 中 strip + 去重 + sort 后再写入。纯应用层约束，不需要改 schema。 |
| **SQL 拼接 LIKE 子句未参数化** | `get_all_entries()` 用 f-string 拼接 `LIKE '%{keyword}%'`。如果 UI 端已做好输入清理则风险可控，但习惯上应参数化。 | `cursor.execute("... WHERE prompt LIKE ?", (f'%{keyword}%',))` |
| **`migrate_from_json()` 无事务包裹** | 迁移过程中如果 crash，可能部分导入。 | 包裹 `BEGIN/COMMIT` 事务。 |
| **无数据导出功能** | 用户无法导出历史记录或图片集合。 | 加 JSON 导出、按标签批量导出图片。 |

### UI/UX

| 问题 | 影响 | 建议 |
|---|---|---|
| **每个模块重复定义 `COLORS` 字典** | `app.py`、`batch_panel.py`、`viewer.py`、`wizard_free.py` 等各有一份相同的暗色主题色彩定义。改一个颜色要改 8 个文件。 | 抽取 `ui/theme.py`，所有模块 `from ui.theme import C`。 |
| **`app.py` 中 `place()` 布局硬编码像素** | `_L.place(x=0, y=0, width=320)` — 侧边栏固定 320px。在小屏（1366x768）上占比过大。 | 改用百分比宽度或 `PanedWindow`，或至少将侧边栏宽度写入配置可调。 |
| **`main.spec` 中 `console=True`** | 打包后的 `.exe` 启动时会弹一个黑色控制台窗口在 GUI 后面，用户体验很差。 | 改 `console=False`，将 `print()` 改为日志写文件。 |
| **生成过程中 UI 无进度预估** | 只能看到"正在生成..."，不知道当前在尝试第几个 Provider、还要多久。 | 在 `status_cb` 中传结构化数据 `{"step": 3, "total": 9, "provider": "SiliconFlow"}`，UI 渲染进度条 + 当前供应商名。 |
| **错误信息直接显示 API 原始报错** | 用户看到 `HTTP 429: rate limit exceeded for key sk-or-v1-...`，不知道这意味着什么，也不知道该等多久。 | 错误映射：`429` → "请求太频繁，请等待 30 秒后重试"；`401` → "API Key 无效，请在设置中检查"。 |
| **无暗色 / 亮色主题切换** | 只有一套暗色主题硬编码。 | 按上面的 `theme.py` 抽取后，加 `light` / `dark` 两套配色，支持切换。 |
| **无键盘快捷键** | 生成、保存、打开查看器全依赖鼠标点击。 | `Ctrl+Enter` 生成，`Ctrl+S` 保存当前图，`Ctrl+F` 聚焦搜索框。 |
| **批量变体无"全保留 / 全丢弃"** | 6 个变体需要逐个点保留/丢弃。 | 加"全部保留"和"全部丢弃"按钮。 |
| **图片查看器无 EXIF / 元数据显示** | 无法查看生成参数（prompt, seed, provider, 尺寸）。 | 保存时将元数据嵌入 PNG tEXt chunk 或 sidecar JSON，查看器读取显示。 |

---

## 三、优先级建议

| 优先级 | 任务 | 理由 |
|---|---|---|
| **P0** | 拆分 `app.py`（139KB → 3~4 个模块） | 当前所有改动都要在这个文件里找位置，已是持续开发的最大摩擦点。 |
| **P1** | 抽取 `ui/theme.py` 统一配色 | 改一个颜色要改 8 个文件，改动小、范围可控、立即减少维护负担。 |
| **P1** | Provider 重试逻辑去重 | 17 个 Provider 各抄一遍相同的重试代码，每次修改规则都要同步 17 处。 |
| **P2** | `get_all_entries()` 加分页 | 历史记录过千后启动变慢、内存上升，数据量只会增加。 |
| **P2** | `main.spec` 改 `console=False` | 一行改动，消除打包版的黑窗口。 |
| **P2** | 错误信息中文化映射 | 显著提升普通用户体验，工作量可控。 |
| **P3** | 日志轮转 | 防止长期运行后磁盘占用失控。 |
| **P3** | 键盘快捷键 | 提升高频操作用户效率。 |
| **P3** | 主题切换 | 功能完整性的加分项。 |
