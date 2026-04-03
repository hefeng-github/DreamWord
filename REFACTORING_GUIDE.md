# 智能写字机系统 - 重构指南

## 概述

本次重构旨在将原有单体代码重构为模块化、可维护的包结构。

## 新的项目结构

```
workspace/
├── src/                          # 重构后的源代码包
│   ├── __init__.py              # 包初始化，导出核心数据结构
│   ├── core/                    # 核心模块
│   │   └── __init__.py          # 数据类和配置定义
│   ├── modules/                 # 功能模块
│   │   ├── __init__.py
│   │   └── calibration.py       # 校准模块（重构版）
│   ├── utils/                   # 工具函数
│   │   ├── __init__.py
│   │   ├── helpers.py           # 通用工具函数
│   │   └── logger.py            # 日志工具
│   ├── config/                  # 配置管理
│   │   ├── __init__.py
│   │   └── settings.py          # 配置类
│   └── api/                     # API 路由
│       ├── __init__.py
│       └── routes.py            # Flask 路由定义
│
├── app.py                        # Web 应用入口（待更新）
├── main.py                       # 命令行入口（待更新）
├── calibration.py                # 原校准模块（保留向后兼容）
├── writer.py                     # 原写字模块（保留向后兼容）
├── word_lookup.py                # 原单词查询模块（保留向后兼容）
├── auto_lookup.py                # 原自动查词模块（保留向后兼容）
├── auto_copy.py                  # 原自动抄写模块（保留向后兼容）
│
├── templates/                    # HTML 模板
├── static/                       # 静态资源
├── Fonts/                        # 字体文件
├── databases/                    # 数据库文件
│
└── REFACTORING_GUIDE.md         # 本文档
```

## 重构进度

### 已完成 ✅

1. **核心数据结构** (`src/core/__init__.py`)
   - GcodePoint: Gcode 点数据结构
   - Stroke: 笔画数据结构
   - WordEntry: 单词条目
   - LookupResult: 查词结果
   - OCRResult: OCR 识别结果
   - Line, WriteArea, TextLayout: 几何和布局数据结构
   - Annotation, WordPosition: 标注和位置数据结构
   - PrinterModel: 打印机型号枚举
   - SystemConfig: 系统配置常量

2. **配置管理** (`src/config/`)
   - Settings: 配置数据类
   - 支持环境变量覆盖
   - 提供默认配置

3. **工具函数** (`src/utils/`)
   - helpers.py: 目录创建、JSON 读写、Base64 转换等
   - logger.py: 统一的日志记录器

4. **API 路由** (`src/api/`)
   - routes.py: Flask 蓝图定义
   - 健康检查端点
   - 配置查询端点
   - 文件下载/预览端点

5. **校准模块** (`src/modules/calibration.py`)
   - ArUcoMarkerGenerator: ArUco 标记生成
   - ImageUnwarp: 图像矫正
   - Calibrator: 校准器

6. **写字模块** (`src/modules/writer.py`)
   - TextRenderer: 文本渲染
   - Skeletonizer: 骨架化
   - GcodeGenerator: Gcode 生成
   - WriterMachine: 写字机控制
   - MachineController: 串口控制器

7. **单词查询模块** (`src/modules/word_lookup.py`)
   - MDXParser: MDX 格式解析（已完成）
   - WordLookup: 单词查询服务（已完成）
     - 智能语义匹配
     - 词形还原和变体识别
     - 语境消歧功能
     - 多种相似度计算
     - 向量缓存机制

8. **自动查词模块** (`src/modules/auto_lookup.py`) ✅
   - KnownWordsDatabase: 已知单词数据库
   - TextExtractor: 文本提取（OCR）
   - PositionCalculator: 位置计算
   - AutoLookup: 自动查词主类

9. **自动抄写模块** (`src/modules/auto_copy.py`) ✅
   - LineDetector: 横线检测
   - WriteAreaExtractor: 可写区域提取
   - TextLayoutEngine: 文本布局引擎
   - AutoCopy: 自动抄写主类

### 待完成 🔄

1. **更新应用入口**
   - 更新 app.py 使用新的包结构
   - 更新 main.py 使用新的包结构

2. **添加单元测试**
   - 核心数据结构测试
   - 各功能模块测试
   - 集成测试

3. **完善文档**
   - API 文档
   - 使用示例
   - 部署指南

## 迁移步骤

### 步骤 1: 安装新依赖

```bash
pip install -r requirements.txt
```

### 步骤 2: 测试新模块

```bash
# 测试核心模块导入
python -c "from src.core import SystemConfig; print(SystemConfig.get_defaults())"

# 测试配置加载
python -c "from src.config import get_settings; print(get_settings().to_dict())"

# 测试工具函数
python -c "from src.utils import ensure_directory; ensure_directory('test_dir')"
```

### 步骤 3: 逐步替换旧模块

1. 首先替换校准模块
2. 然后替换写字模块
3. 最后替换业务逻辑模块

### 步骤 4: 更新入口文件

修改 `app.py` 和 `main.py` 使用新的导入路径：

```python
# 旧方式
from calibration import Calibrator, ArUcoMarkerGenerator

# 新方式
from src.modules.calibration import Calibrator, ArUcoMarkerGenerator
```

## 向后兼容性

在重构完成前，原有的模块文件保持不变，确保现有功能继续可用。

## 优势

1. **模块化**: 清晰的模块划分，便于理解和维护
2. **可测试性**: 每个模块可以独立测试
3. **可扩展性**: 易于添加新功能
4. **类型安全**: 使用类型注解，提高代码质量
5. **配置管理**: 统一的配置管理，支持环境变量

## 下一步计划

1. 完成剩余模块的重构
2. 添加单元测试
3. 更新文档
4. 优化性能

## 贡献指南

欢迎提交 Issue 和 Pull Request 来帮助改进项目！
