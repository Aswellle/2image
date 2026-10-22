# assets/

本目录只存放随仓库分发的静态资源。`main.spec` 只打包 `assets/fonts/`
与根目录的 `ICON_256x256.ico`，其余文件不进入构建产物。

| 文件 | 用途 | 是否被引用 |
|---|---|---|
| `logo.png` | 两份 README 头部的项目图标（200px 显示） | 是 — `README.md` / `README.en.md` |
| `banner.png` | `logo.png` 的原始未裁剪源图（1672×941） | 否 — 保留作重新导出 logo 的素材 |
| `fonts/` | 打包进安装包的开源字体 | 是 — `main.spec` datas、`config/fonts.py` |

`banner.png` 在代码与文档里没有任何运行时引用，**不是死资源**：当前的
`logo.png` 就是由它缩放并做透明圆角得到的（见 commit `51e8a84`）。删除会
失去重新导出 logo 的唯一无损素材，因此保留在仓库中。新增资源时请在本表
登记用途与引用位置，避免后续审查重复误判。
