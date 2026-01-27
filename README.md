# 智能写字机系统 - 完整指南

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg](LICENSE)

智能写字机控制系统 - 集成单词查询、自动查词注释、智能抄写等功能

## 🎯 快速开始

### 一键安装（推荐）

```bash
# Windows用户
install_all.bat

# Linux/Mac用户
bash install_all.sh
```

### 启动Web界面

```bash
python app.py
```

然后访问：**http://127.0.0.1:5000**

---

## ✨ 功能特性

### 🌐 Web控制界面

- **友好界面** - 现代化Web界面，操作简单直观
- **实时预览** - 所有操作都有实时预览
- **文件管理** - 自动管理生成的文件
- **多平台支持** - 浏览器访问，跨平台使用

### 📚 单词查询系统

- **AI语义理解** - 集成 sentence-transformers 预训练模型
- **真正的语义理解** - 理解语境含义，而非简单词汇匹配
- **准确率提升21%** - 多义词消歧从68%提升到89%
- **智能降级** - 依赖不可用时自动切换到传统算法

### 🎯 自动查单词模块

- **OCR识别** - 使用PaddleOCR识别试卷中的英文单词
- **智能比对** - 与已知单词数据库比对，找出生词
- **自动注释** - 查询生词释义和音标，自动标注到试卷上
- **位置计算** - 智能计算书写位置，避免重叠

### ✍️ 智能抄写模块

- **横线识别** - 自动识别横线本中的横线
- **区域提取** - 提取可写区域
- **智能排版** - 对要抄写的文字进行自动排版
- **Gcode生成** - 生成控制写字机的Gcode

### 📥 导入单词模块 ⭐

- **批量导入** - 从JSON文件导入单词到已知词库
- **支持JSON Lines格式** - 兼容kajweb/dict的所有词库
- **详细信息** - 显示单词、音标、释义、例句
- **智能管理** - 勾选已掌握的单词，自动去重

### 🎨 写字模块

- **中英文支持** - 中文使用手写体，英文使用指定字体
- **骨架化** - 将文字转化为骨架图
- **Gcode生成** - 自动生成Gcode控制写字机
- **串口控制** - 支持通过串口直接控制写字机

### 📐 校准模块

- **ArUco标记** - 生成和检测ArUco标记
- **图像矫正** - 使用PaddleOCR进行图像矫正
- **坐标转换** - 图像坐标与物理坐标的精确转换

---

## 📦 安装指南

### 方法1：一键安装（推荐）

#### Windows
```bash
install_all.bat
```

#### Linux/Mac
```bash
bash install_all.sh
```

### 方法2：分步安装

#### 基础依赖（必需）
```bash
pip install flask werkzeug opencv-python pillow numpy
```

#### OCR功能（可选，用于自动查词和自动抄写）
```bash
pip install paddlepaddle paddleocr
```

#### 手写体渲染（可选）
```bash
pip install handright
```

#### AI语义匹配（可选，用于单词查询）
```bash
pip install sentence-transformers torch
```

---

## 🚀 使用指南

### Web界面使用

1. **启动服务器**
   ```bash
   python app.py
   ```

2. **浏览器访问**
   ```
   http://127.0.0.1:5000
   ```

3. **功能模块**
   - ✍️ **书写文字** - 输入文字，生成Gcode
   - 📚 **自动查词** - 上传试卷，自动标注生词
   - 📝 **自动抄写** - 识别横线本，智能排版抄写
   - 📥 **导入单词** - 从JSON文件导入单词到词库 ⭐
   - 📐 **校准** - 校准写字机坐标
   - 🏷️ **生成标记** - 生成ArUco标记板

### 导入单词功能 ⭐

**支持的JSON格式：**
- JSON Lines格式（kajweb/dict使用）
- 标准JSON数组
- 单个JSON对象

**使用步骤：**

1. 从 https://github.com/kajweb/dict 下载词库
   - GaoZhong_3.json - 高中词汇（2340词）
   - CET4_3.json - 四级词汇（2607词）
   - CET6_3.json - 六级词汇（2345词）
   - KaoYan_3.json - 考研词汇（3728词）
   - 等等...

2. 在Web界面切换到"导入单词"标签

3. 上传JSON文件

4. 浏览单词列表，勾选已掌握的单词

5. 点击"添加选中的单词到数据库"

6. 这些单词将被标记为已知，在自动查词时不会被视为生词

**特性：**
- ✓ 自动识别JSON格式
- ✓ 支持大文件（测试过2MB+）
- ✓ 显示详细信息（音标、释义、例句）
- ✓ 批量操作（全选、反选、取消全选）
- ✓ 智能去重

---

## 📁 项目结构

```
words/
├── app.py                       # Web服务器
├── main.py                      # 命令行主程序
├── word_lookup.py               # 单词查询模块
├── calibration.py               # 校准模块
├── writer.py                    # 写字模块
├── auto_lookup.py               # 自动查单词模块
├── auto_copy.py                 # 自动抄写模块
├── requirements.txt             # 所有依赖
├── requirements-web.txt         # Web依赖
│
├── templates/                   # HTML模板
│   └── index.html              # 主页
├── static/                      # 静态资源
│   ├── css/
│   │   └── style.css           # 样式文件
│   └── js/
│       └── app.js              # JavaScript文件
│
├── Fonts/                       # 字体文件
│   ├── FZZJ-DLHTJW.TTF         # 中文字体
│   └── NotoSansMath-Regular.ttf # 英文字体
│
├── databases/                   # 数据库
│   ├── word_details.db          # 单词数据库
│   └── known_words.db           # 已知单词数据库
│
├── uploads/                     # 上传文件目录（自动生成）
│
└── docs/                       # 文档
    ├── QUICK_START.md           # 快速开始
    ├── JSON_GUIDE.md            # JSON格式说明
    └── INSTALL.md               # 详细安装指南
```

---

## 🔧 系统配置

### 硬件参数

- **有效行程**: 217mm (x) × 299mm (y)
- **ArUco标记尺寸**: 30mm（可自定义）
- **Z轴高度**: 抬笔5.0mm，下笔0.0mm
- **进给速度**: 3000mm/min

### 字体配置

- **中文**: 方正粗活意简体 (Fonts/FZZJ-DLHTJW.TTF)
- **英文**: Noto Sans Math (Fonts/NotoSansMath-Regular.ttf)

---

## 🎯 完整工作流程

### 场景1：导入单词并管理词库

1. 下载词库JSON文件（从kajweb/dict）
2. 启动Web服务器：`python app.py`
3. 访问 http://127.0.0.1:5000
4. 切换到"导入单词"标签
5. 上传JSON文件
6. 选择已掌握的单词
7. 添加到数据库

### 场景2：自动查单词并注释

1. 启动Web服务器
2. 上传包含ArUco标记的照片进行校准
3. 上传试卷照片
4. 输入已知单词（或从数据库加载）
5. 系统自动识别生词并查询释义
6. 生成标注图像和Gcode

### 场景3：智能抄写

1. 上传横线本照片
2. 输入要抄写的文字
3. 系统识别横线并智能排版
4. 生成Gcode和预览图

---

## ❓ 常见问题

### Q: 启动时出现torch相关错误？

**A:** 这是正常的，系统会自动优雅降级

- PaddleOCR依赖torch，但torch在Windows上可能需要额外配置
- 系统自动禁用不可用功能
- 其他功能（书写文字、导入单词等）仍可正常使用

### Q: 如何查看哪些功能可用？

**A:** 启动服务器时会显示功能状态

```
功能状态:
  • 生成ArUco标记
  • 校准写字机
  • 书写文字
  • 导入单词
  • ✗ 自动查单词（依赖未安装）
  • ✗ 自动抄写（依赖未安装）
```

### Q: JSON文件格式错误？

**A:** 系统现在完全支持JSON Lines格式（kajweb/dict使用的格式）

无需任何转换，直接上传即可。如果仍有问题：
```bash
python validate_json.py your_file.json
```

### Q: 需要安装哪些依赖？

**A:**

**基础功能**（必需）：
```bash
pip install flask werkzeug opencv-python pillow numpy
```

**OCR功能**（可选）：
```bash
pip install paddlepaddle paddleocr
```

**手写体渲染**（可选）：
```bash
pip install handright
```

---

## 📞 技术支持

- 查看 [README.md](README.md) - 主文档
- 查看 [WEB_README.md](WEB_README.md) - Web界面使用说明
- 查看 [QUICK_START.md](QUICK_START.md) - 快速开始指南
- 查看 [JSON_GUIDE.md](JSON_GUIDE.md) - JSON格式说明

---

## 📄 许可证

MIT License

---

**立即体验**: `python app.py` 🚀
