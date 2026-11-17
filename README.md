# GitHub 资源雷达 · Signal

> 捕捉 GitHub 上的每一次星标跃迁。
>
> 一个把「星标飙升榜、本周流行、星标最高榜、最新资源」与五个精选分类装进同一块工作台式大屏的单页数据面板。数据每日自动刷新，悬停即见成长轨迹，点开即读完整简介。

[![在线体验](https://img.shields.io/badge/在线体验-GitHub%20Pages-4fd8d2?style=flat-square)](https://davin-96.github.io/github-radar-signal/)
[![离线版](https://img.shields.io/badge/离线版-双击即用-6fb3ff?style=flat-square)](https://github.com/Davin-96/github-radar-signal/releases/latest)

---

## 预览

**亮色 · 星标飙升榜**

![亮色主题首屏](preview/v4-light.png)

**暗色 · 同一数据，另一套主题**

![暗色主题首屏](preview/v4-dark.png)

**悬停仓库名 · 就近弹出星标走势**

![悬停星标走势](preview/v4-hover.png)

**点击卡片 · 完整简介 + 星标走势大图**

![项目详情弹窗](preview/v4-modal.png)

---

## 这是什么

一个**零依赖的单文件数据面板**。`index.html` 一个文件包含全部 HTML / CSS / JS 与数据快照——不需要服务器、不需要构建、不需要联网，双击就能看。

打开后左侧是榜单与分类导航，右侧是大屏仓库列表：

- **四个榜单**：⚡ 星标飙升榜（今日 `period_stars`）、🔥 本周流行、🏆 星标最高榜、🆕 最新资源
- **五个精选分类**：文章/教程、AI/机器学习、开发工具、人生哲理、财经金融
- **中文简介**：每条仓库附中文一句解读，中英双语可切换
- **星标走势**：鼠标悬停仓库名，就近浮出 mini 走势图；点击卡片展开大图 + 完整简介 + 语言/标签

顶部四个数字随数据更新：收录仓库、累计星标、今日星标飙升、精选分类数。

---

## 快速开始

### 方式一 · 在线版（推荐）

打开 <https://davin-96.github.io/github-radar-signal/>。

部署在 HTTPS 站点时，页面会**自动从 GitHub Search API 拉取实时数据**刷新榜单与分类（约每 3 小时一次，也可点右上角「刷新」手动触发）。拉取失败时自动回退到内嵌快照，不影响浏览。

### 方式二 · 离线版

从 [Releases](https://github.com/Davin-96/github-radar-signal/releases/latest) 下载 `GitHub-Radar-Signal-v1.0.0.zip`：

1. 解压到任意目录
2. 双击 `index.html`，浏览器直接打开

无需联网、无需服务器。离线状态使用**内嵌数据快照**（快照时间显示在顶部状态栏），榜单与分类完整可浏览。

> 星标走势图来自 star-history.com 公共服务，需联网加载；离线或加载失败时，「新标签打开」仍可跳转 GitHub 查看项目。

---

## 操作速查

| 操作 | 效果 |
|---|---|
| 左侧点榜单 / 分类 | 切换右侧大屏列表 |
| 鼠标悬停仓库名 | 就近弹出星标走势 mini 图 |
| 点击仓库卡片 | 打开详情弹窗：完整简介 + 走势大图 |
| 右上角「🌐 中文 / English」 | 中英双语切换（记忆到 localStorage） |
| 右上角「🌙 暗色 / ☀️ 亮色」 | 明暗主题切换（记忆到 localStorage） |
| 右上角「刷新」 | 手动从 GitHub 实时刷新（在线版有效） |
| 顶部状态标签 | `本地快照` / `实时` / 降级提示 |

---

## 数据来源与口径

- **榜单与分类**：内嵌快照取自 GitHub Trending 与 GitHub Search API（`stars:>10000`、`created:>14d stars:>50`、各 topic 检索），快照时间写在数据里并显示在页面顶部
- **实时刷新**：仅 HTTPS 在线站点触发，直接请求 `api.github.com/search/repositories`； GitHub 未认证接口有频率限制，触发限额时自动回退快照
- **星标走势图**：来自 [star-history.com](https://star-history.com/) 公共服务，按仓库全名在线加载 SVG
- **今日星标飙升**（`period_stars`）：来自 Trending 日榜口径，非精确 24h 增量，仅供相对比较
- 本项目为开源项目情报的**聚合展示**，星标数为抓取时点的近似值，不构成任何排名或推荐意见

---

## 目录结构（仓库精简版）

```
.
├─ index.html              成品：全部 HTML/CSS/JS + 数据快照，单文件自包含
├─ README.md               本文件
├─ preview/                定稿预览图（v4）
│  ├─ v4-light.png
│  ├─ v4-dark.png
│  ├─ v4-hover.png
│  └─ v4-modal.png
└─ .nojekyll              告知 GitHub Pages 跳过 Jekyll 构建
```

构建脚本（`build/`）与原始数据（`assets/`）不随仓库发布，成品已完全内嵌。

---

## 下载

- **在线版**：<https://davin-96.github.io/github-radar-signal/>
- **离线包**：[Releases · v1.0.0](https://github.com/Davin-96/github-radar-signal/releases/tag/v1.0.0) → `GitHub-Radar-Signal-v1.0.0.zip`

---

## License

MIT
