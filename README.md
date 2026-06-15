# DreamWord 智能写字机系统

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-GPLv3-green.svg)](LICENSE)
[![Flask](https://img.shields.io/badge/Web-Flask-black)](https://flask.palletsprojects.com/)

一套面向教学场景的智能写字机控制系统：拍照识别试卷生词并自动标注释义、识别横线本智能排版抄写、手写体文字生成 Gcode 控制写字机书写，并支持已会词库管理与 OneDrive 云端备份。

硬件基于 [CoreXY 结构写字机](https://oshwhub.com/supercaii/coerxy-jie-gou-xie-zi-ji-ji-guang-diao-ke-ji-_-wu-jie-3)，使用 FluidNC 固件。

---

## ✨ 功能特性

| 模块 | 说明 |
|------|------|
| 🌐 **Web 控制台** | 基于 Flask 的现代化界面，浏览器访问，所有操作实时预览 |
| 📐 **校准模块** | 生成/检测 ArUco 标记，PaddleOCR 图像矫正，图像↔物理坐标转换 |
| ✍️ **写字模块** | 中英文渲染（中文 Handright 手写体），文字→骨架→笔画→Gcode，串口直连 FluidNC |
| 🎯 **自动查词** | OCR 识别试卷，与已会词库比对找生词，查释义/音标后自动标注到行间，智能避让重叠 |
| 📝 **自动抄写** | 识别横线本及可写区域，对文字智能排版后生成 Gcode |
| 📚 **单词查询** | 本地词典查询，可选集成 sentence-transformers 做语义消歧（准确率 +21%），依赖缺失自动降级 |
| 📥 **词库导入** | 从 JSON / JSON Lines（兼容 [kajweb/dict](https://github.com/kajweb/dict)）批量导入并管理已会词 |
| ☁️ **OneDrive 备份** | 已会词库版本化备份到 OneDrive，支持恢复（Client ID 可在 WebUI 配置） |

---

## 🚀 快速开始

### 1. 安装依赖

**Windows（推荐，交互式选择可选组件）：**
```bat
install_all.bat
```

**手动安装：**
```bash
# 基础依赖（必需）
pip install -r requirements.txt        # 全部依赖
# 或仅 Web 核心：
pip install flask werkzeug opencv-python pillow numpy pyserial
```

> OCR（自动查词/抄写）依赖较重，`requirements.txt` 默认包含；若只需基础书写功能可按需精简，缺失依赖时系统会自动降级。

### 2. 启动 Web 界面

```bash
python app.py
```

浏览器访问 **http://127.0.0.1:5000** ，启动时会打印各模块功能状态。

### 3. 命令行使用（可选）

```bash
python main.py --help
# 例：生成 ArUco 校准标记板
python main.py calibrate -i 校准照片.jpg -o calibration.pkl
# 例：书写文字
python main.py write -t "Hello"
```

---

## 📁 项目结构

```
DreamWord/
├── app.py                       # Web 服务入口（Flask），提供全部 API 路由
├── main.py                      # 命令行入口
│
├── src/                         # 核心代码（模块化包）
│   ├── modules/
│   │   ├── calibration.py       # 校准：ArUco 标记 + 图像矫正 + 坐标转换
│   │   ├── writer.py            # 写字：渲染→骨架→笔画→Gcode + 串口控制
│   │   ├── word_lookup.py       # 单词查询（本地词典 + 可选语义匹配）
│   │   ├── auto_lookup.py       # 自动查词：OCR 找生词并标注
│   │   ├── auto_copy.py         # 自动抄写：识别横线本并排版
│   │   └── onedrive_backup.py   # OneDrive 词库备份/恢复
│   ├── api/                     # 路由蓝图（重构预留）
│   ├── config/                  # 配置
│   ├── core/                    # 公共数据结构
│   └── utils/                   # 工具函数、日志
│
├── templates/index.html         # Web 主页
├── static/
│   ├── css/style.css
│   └── js/app.js
│
├── Fonts/                       # 字体（中文/英文/音标）
├── databases/                   # 词典数据库（word_details.db，随仓库分发）
├── cloudflare-worker/           # 拍照查词的 Cloudflare Workers 边缘版（独立子项目）
│   └── README.md                # 详见其内文档
│
├── validate_json.py             # 词库 JSON 格式校验/修复工具
├── requirements.txt             # 全部依赖
├── requirements-web.txt         # 仅 Web 核心依赖（可选组件已注释）
├── install_all.bat              # Windows 交互式安装脚本
├── install_ai_semantic.bat/.sh  # 单独安装 AI 语义匹配依赖
├── start_web.bat / .sh          # 快速启动 Web 服务
└── LICENSE                      # GPLv3
```

> **运行时产物**（已加入 `.gitignore`，不会提交）：`uploads/`、`known_words.db`（个人已会词数据）、`calibration.pkl`、`__pycache__/`。

---

## 🔧 系统配置

### 硬件参数
- **有效行程**：217 mm (X) × 299 mm (Y)
- **ArUco 标记**：30 mm（可自定义）
- **Z 轴**：抬笔 5.0 mm，下笔 0.0 mm
- **进给速度**：3000 mm/min
- **固件**：FluidNC（通过串口直连发送 Gcode）

### 字体
- 中文：`Fonts/FZZJ-DLHTJW.TTF`
- 英文/音标：`Fonts/NotoSansMath-Regular.ttf`

---

## 🎯 典型工作流

### 场景 A：管理已会词库
1. 从 [kajweb/dict](https://github.com/kajweb/dict) 下载词库 JSON
2. Web 界面切到「导入单词」→ 上传 JSON → 勾选已掌握的词 → 添加到数据库
3. 可在「已会词管理」中增删，并一键备份到 OneDrive

### 场景 B：试卷自动标注生词
1. 「校准」上传带 ArUco 标记的写字机照片完成坐标校准
2. 「自动查词」上传试卷照片 → OCR 识别 → 与已会词库比对 → 生词自动查询并标注到行间
3. 生成标注预览图与书写 Gcode

### 场景 C：智能抄写
1. 「自动抄写」上传横线本照片 + 输入文字 → 自动识别横线、排版 → 生成 Gcode

### 场景 D：串口直连书写
1. 通过 Web 界面的串口面板选择端口连接写字机
2. 直接发送 Gcode 实时控制书写

---

## ❓ 常见问题

**Q：启动出现 torch / paddle 相关错误？**
A：正常现象。PaddleOCR/torch 在 Windows 上可能需额外配置，系统会自动优雅降级——查词、书写、导入单词等基础功能不受影响。

**Q：词库 JSON 格式报错？**
A：系统支持 JSON Lines（kajweb/dict 格式）与标准 JSON 数组，可直接上传。仍报错时可校验：
```bash
python validate_json.py 你的词库.json
```

**Q：哪些功能可用？**
A：启动 `app.py` 时控制台会打印功能状态清单，标记 ✗ 的表示对应可选依赖未安装。

---

## ☁️ Cloudflare Workers 版（拍照查词）

`cloudflare-worker/` 是一个独立的边缘查词服务，提供与 Python 版类似的查词预览/拍照查词 API，部署在 Cloudflare 全球网络。OCR 在前端用 Tesseract.js 完成。部署与 API 细节见 [`cloudflare-worker/README.md`](cloudflare-worker/README.md)。

---

## 📄 许可证

本项目采用 [GPLv3](LICENSE) 许可证。

---

**立即体验**：`python app.py` 🚀
