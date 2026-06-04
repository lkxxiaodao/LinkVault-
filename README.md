<div align="center">

# 🔗 LinkVault

**桌面书签管理工具 — 高效收藏、组织、回顾你的网址**

</div>

---

## 📖 简介

LinkVault 是一款基于 **Python + PySide6 (Qt6)** 开发的 Windows 桌面书签管理工具。它帮你摆脱浏览器自带书签管理器的局限，提供更强大的组织、搜索和回顾能力。

无论你是收藏了大量网页需要分类整理，还是希望定时打开某些网站，或是想随机「邂逅」被遗忘的收藏，LinkVault 都能满足你。

---

## ✨ 功能特性

### 📑 书签管理
- **完整的 CRUD**：添加、编辑、删除书签，支持标题、网址、备注、标签
- **批量操作**：批量移动、批量打标签、批量设置默认浏览器、批量删除
- **点击统计**：自动记录每个书签的打开次数和最近打开时间
- **多种排序**：按标题、最常打开、最近打开排序

### 📂 文件夹组织
- **树形结构**：多层级文件夹，无限嵌套
- **灵活管理**：新建、重命名、删除文件夹（删除文件夹不影响书签）
- **快捷筛选**：点击文件夹自动筛选其中书签

### 🏷️ 标签系统
- 书签支持多个标签，用逗号分隔
- 标签按钮快速筛选，点击即用

### 🔍 快速搜索
- **全局热键搜索**：`Ctrl+Shift+L` 唤起快速搜索弹窗（可自定义）
- 实时搜索标题、网址、备注、标签

### ⚡ 快速捕获
- **全局热键捕获**：`Ctrl+Shift+N` 唤出快速添加弹窗（可自定义）
- 自动从剪贴板提取网址，一键保存

### ⏰ 定时任务
- 设置定时打开书签计划
- 支持重复模式：仅一次、每天、工作日、每周、双周、每月、自定义
- 到点自动弹出 Windows Toast 通知

### 🎲 随机漫步
- 创建书签池，将书签加入池中
- 点击「漫步」随机打开池中一个书签
- 帮你发现被遗忘的收藏

### 📊 习惯分析
- 分析书签打开记录
- 发现周期性打开习惯
- 智能建议创建定时任务

### 🗑️ 回收站
- 软删除机制，删除的书签移入回收站
- 可恢复或彻底删除

### 🔒 备份与恢复
- **加密备份**：AES-256-GCM 加密导出 `.linkvault` 格式
- **按需筛选**：导出时可按文件夹或标签筛选内容
- **HTML 导出**：导出标准 HTML 书签文件，可在浏览器中导入

### 🎨 界面主题
- 9 种 Material Design 主题（亮色/暗色）
- 随你喜好自由切换

### 🖥️ 系统集成
- **系统托盘**：最小化到托盘，后台常驻运行
- **开机自启**：支持 Windows 开机自启动
- **多浏览器支持**：Chrome、Edge、Firefox、QQ 浏览器、360 浏览器、Brave、Opera 等

---

## 🚀 快速开始

### 从源码运行

```bash
# 克隆仓库、
git clone https://gitcode.com/lkx040527/LinkVault.git

# 进入源码目录
cd linkvault

# 安装依赖
pip install -r requirements.txt

# 运行
python main.py
```

### 依赖清单

```
PySide6>=6.5.0
qt_material>=2.14
schedule>=1.2.0
win11toast>=0.4.0
cryptography>=41.0.0
```

---

## 🏗️ 项目架构

```
linkvault/
├── app_qt.py              # 应用入口：Qt 应用、系统托盘、全局热键、定时引擎
├── main.py                # 启动脚本
├── requirements.txt       # 依赖清单
├── app_qt.spec            # PyInstaller 打包配置
├── installer.iss          # Inno Setup 安装包脚本
│
├── core/                  # 业务逻辑层
│   ├── bookmark_manager.py   # 书签管理
│   ├── folder_manager.py     # 文件夹管理
│   ├── config_manager.py     # 配置管理
│   ├── schedule_engine.py    # 定时任务引擎
│   ├── random_walker.py      # 随机漫步
│   ├── habit_analyzer.py     # 习惯分析
│   └── url_extractor.py      # URL 提取
│
├── data/                  # 数据访问层 (Repository 模式)
│   ├── database.py           # SQLite 数据库初始化与迁移
│   ├── bookmark_repo.py      # 书签数据访问
│   ├── folder_repo.py        # 文件夹数据访问
│   ├── history_repo.py       # 打开历史数据访问
│   ├── pool_repo.py          # 随机池数据访问
│   └── schedule_repo.py      # 定时任务数据访问
│
├── infra/                 # 基础设施层
│   ├── config.py             # 全局配置常量
│   ├── browser_launcher.py   # 浏览器启动器（多浏览器检测）
│   ├── global_hotkey.py      # 全局热键（Win32 API）
│   ├── backup.py             # 备份与恢复
│   ├── encryption.py         # AES-256-GCM 加解密
│   ├── notifier.py           # Windows Toast 通知
│   └── auto_start.py         # 开机自启动
│
├── ui_qt/                 # 视图层 (PySide6)
│   ├── main_window.py        # 主窗口
│   ├── folder_tree.py        # 文件夹树控件
│   ├── bookmark_list.py      # 书签列表控件
│   ├── search_bar.py         # 搜索栏
│   ├── random_walk_bar.py    # 随机漫步栏
│   ├── habit_card.py         # 习惯建议卡片
│   └── dialogs/
│       ├── quick_search_dialog.py   # 快速搜索弹窗
│       ├── quick_capture_dialog.py  # 快速捕获弹窗
│       └── settings_dialog.py       # 设置弹窗
│
├── assets/                # 资源文件
│   ├── icon.ico               # 应用图标
│   └── default_bookmark.png   # 默认书签图标
│
└── tests/                 # 测试
    ├── core/                  # 核心业务测试
    ├── data/                  # 数据层测试
    └── infra/                 # 基础设施测试
```

### 架构分层

```
┌─────────────────────────────────────────┐
│              UI (ui_qt/)                │  ← PySide6 控件
├─────────────────────────────────────────┤
│           Core (core/)                  │  ← 业务逻辑
├─────────────────────────────────────────┤
│           Data (data/)                  │  ← Repository 模式
├─────────────────────────────────────────┤
│         Infra (infra/)                  │  ← 系统接口、加密、通知
└─────────────────────────────────────────┘
```

---

## 🖼️ 界面预览

| 功能 | 说明 |
|------|------|
| **主窗口** | 左侧文件夹树 + 右侧书签列表 + 顶部搜索栏 + 底部随机漫步栏 |
| **快速搜索** | Ctrl+Shift+L 唤出，在全屏弹窗中搜索书签 |
| **快速捕获** | Ctrl+Shift+N 唤出，从剪贴板提取网址快速保存 |
| **定时任务** | 标签页管理定时打开计划 |
| **随机池** | 标签页管理书签池 |
| **设置** | 热键配置、主题切换、开机自启、备份管理 |

---

## 🙏 致谢

- [PySide6](https://wiki.qt.io/Qt_for_Python) — Qt6 的 Python 绑定
- [qt_material](https://github.com/UN-GCPDS/qt-material) — Material Design 主题
- [schedule](https://github.com/dbader/schedule) — Python 定时任务库
- [win11toast](https://github.com/o7-Fire/win11toast) — Windows Toast 通知
- [cryptography](https://github.com/pyca/cryptography) — Python 加密库