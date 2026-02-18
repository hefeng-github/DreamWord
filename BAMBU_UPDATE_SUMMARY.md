# Bambu Connect 集成更新总结

## 已完成的工作

### 1. 新建文件

#### [bambu_adapter.py](bambu_adapter.py)
**Bambu Connect 适配器模块**

- `PrinterConfig`: 打印机配置类，支持 A1 mini、A1、P1P、X1C 等型号
- `GcodeTo3MFConverter`: Gcode 转 3MF 格式转换器
- `BambuConnectLauncher`: Bambu Connect 启动器（通过 URL Scheme）
- `BambuPrinterAdapter`: 统一适配器接口

#### [test_bambu_integration.py](test_bambu_integration.py)
**集成测试脚本**

包含 5 个测试用例：
- 写字机基本功能测试
- 中文书写测试
- 打印机配置测试
- Bambu Connect 适配器测试
- 完整工作流程测试

#### [BAMBU_CONNECT_GUIDE.md](BAMBU_CONNECT_GUIDE.md)
**完整使用指南**

包含：
- 功能特性说明
- 支持的打印机型号
- 前置要求和安装步骤
- 使用方法（Web 界面、Python API、命令行）
- API 文档
- 参数说明
- 故障排除

### 2. 更新的文件

#### [writer.py](writer.py)
**写字机核心模块**

主要更新：
- ✅ 默认工作区尺寸更新为 256×256mm（适配 A1 mini）
- ✅ 添加打印机型号参数（printer_model）
- ✅ 添加层高、喷嘴温度、热床温度参数
- ✅ Gcode 头部信息优化，符合 Bambu Lab 标准
- ✅ Gcode 尾部添加归零和关闭加热指令

#### [calibration.py](calibration.py)
**校准模块**

- ✅ 默认工作区更新为 256×256mm

#### [app.py](app.py)
**Web 应用**

新增 API 端点：
- ✅ `GET /api/printer/models` - 获取支持的打印机型号列表
- ✅ `GET /api/printer/info/<model>` - 获取指定打印机详细信息
- ✅ `POST /api/bambu/send` - 发送到 Bambu Connect
- ✅ `GET /api/bambu/check` - 检查 Bambu Connect 状态

更新 API 端点：
- ✅ `POST /api/write` - 添加打印机型号和温度参数支持

### 3. 测试结果

```
总计: 5 通过, 0 失败

[OK] 通过 - 写字机基本功能
[OK] 通过 - 中文书写
[OK] 通过 - 打印机配置
[OK] 通过 - Bambu Connect 适配器
[OK] 通过 - 完整工作流程
```

## 支持的打印机型号

| 型号代码 | 名称 | 工作区体积 |
|---------|------|-----------|
| A1MINI | Bambu Lab A1 mini | 256×256×256 mm |
| A1 | Bambu Lab A1 | 256×256×256 mm |
| P1P | Bambu Lab P1P | 256×256×256 mm |
| X1C | Bambu Lab X1 Carbon | 256×256×256 mm |

## 使用方法

### 快速开始

1. **启动 Web 界面**：
   ```bash
   python app.py
   ```

2. **访问控制台**：
   ```
   http://127.0.0.1:5000
   ```

3. **生成并发送**：
   - 输入文字
   - 选择打印机型号（默认 A1 mini）
   - 点击"生成并发送到 Bambu Connect"

### Python API 使用

```python
from writer import WriterMachine
from bambu_adapter import BambuPrinterAdapter

# 1. 生成 Gcode
writer = WriterMachine(printer_model='A1MINI')
writer.write_text(
    text="你好世界",
    save_gcode_path="output.gcode"
)

# 2. 发送到 Bambu Connect
adapter = BambuPrinterAdapter(printer_model='A1MINI')
adapter.prepare_and_send(
    gcode_path="output.gcode",
    model_name="我的书法作品"
)
```

## 技术特性

### 写字机工作原理

```
文字输入 → 字体渲染 → 骨架化提取 → 笔画路径生成 → Gcode生成 → 打印机运动 → 笔迹书写
```

- **X/Y 轴**: 控制笔在纸上的移动位置
- **Z 轴**: 控制抬笔（不书写）/ 下笔（书写）
- **温度控制**: 仅用于兼容 Bambu Connect 格式（写字机不加热）

### Bambu Connect 集成

- ✅ 自动生成符合 Bambu Lab 标准的 Gcode
- ✅ Gcode 转 3MF 格式
- ✅ 通过 URL Scheme 启动 Bambu Connect
- ✅ 支持检查 Bambu Connect 安装状态

URL Scheme 格式：
```
bambu-connect://import-file?path=%2Fpath%2Fto%2Ffile.3mf&name=Job&version=1.0.0
```

## 前置要求

### 软件要求

1. **Python 依赖**（已满足）：
   - Flask
   - OpenCV
   - NumPy
   - PIL

2. **Bambu Connect**：
   - Windows: Windows 10 或更高版本
   - macOS: macOS 13 或更高版本
   - 下载地址：https://wiki.bambulab.com/zh/software/bambu-connect

### 硬件要求

1. **Bambu Lab 3D 打印机**（A1 mini 推荐）
2. **笔架改装**：将喷嘴替换为笔固定装置
3. **纸张固定**：在热床上固定纸张
4. **Z 轴校准**：确保 Z=0 时笔尖刚好接触纸面

## 打印机连接方式

### 方式一：Bambu Connect（推荐）

1. 将打印机连接到网络（LAN 模式）
2. 在 Bambu Connect 中登录 Bambu Lab 账户
3. 自动发现并连接打印机

### 方式二：开发者模式

1. 进入打印机设置 → 开发者选项
2. 启用"开发者模式"
3. 打印机在 LAN 模式下工作，无需授权验证

**注意**：开发者模式下无法连接云端，仅限局域网使用。

## 推荐参数设置

### 日常书写
```
z_up: 5.0 mm（抬笔高度）
z_down: 0.0 mm（下笔位置）
feed_rate: 3000 mm/min（移动速度）
```

### 精细书写
```
z_up: 3.0 mm
z_down: 0.0 mm
feed_rate: 1500 mm/min（降低速度）
```

### 快速书写
```
z_up: 5.0 mm
z_down: 0.0 mm
feed_rate: 5000 mm/min（提高速度）
```

## 下一步

1. ✅ 查看 [BAMBU_CONNECT_GUIDE.md](BAMBU_CONNECT_GUIDE.md) 了解完整使用指南
2. ✅ 安装 Bambu Connect
3. ✅ 完成打印机硬件改装（笔架安装）
4. ✅ 运行 `python app.py` 启动 Web 界面
5. ✅ 开始创作书法作品！

## 文件清单

### 新增文件
- `bambu_adapter.py` - Bambu Connect 适配器
- `test_bambu_integration.py` - 集成测试脚本
- `BAMBU_CONNECT_GUIDE.md` - 使用指南
- `BAMBU_UPDATE_SUMMARY.md` - 本文档

### 更新文件
- `writer.py` - 添加 A1 mini 支持
- `calibration.py` - 更新工作区尺寸
- `app.py` - 添加 Bambu Connect API

### 测试文件
- `test_hello.gcode` - "Hello" 的 Gcode
- `test_chinese.gcode` - "你好" 的 Gcode
- `workflow_test.gcode` - "智能写字机" 的 Gcode
- 对应的预览图片（.png）

## 参考资源

- [Bambu Connect 官方文档](https://wiki.bambulab.com/zh/software/bambu-connect)
- [Bambu Lab 第三方集成指南](https://wiki.bambulab.com/en/software/third-party-integration)
- [A1 mini 产品页面](https://bambulab.com/products/a1-mini)

---

**更新日期**: 2025-02-15 / 2025-02-17
**版本**: v1.0 / v1.1
**作者**: Claude Code
**项目**: 智能写字机系统

## v1.1 更新 (2025-02-17)

### 新增功能：打印机摄像头支持

#### 新建文件
- `bambu_camera.py` - Bambu 打印机摄像头模块
- `BAMBU_CAMERA_GUIDE.md` - 摄像头功能使用指南

#### 功能特性
- ✅ 支持使用打印机内置摄像头拍照
- ✅ 集成到自动查词、自动抄写、校准功能
- ✅ Web 界面配置管理
- ✅ 支持 A1/A1 mini/P1P/P1S/X1C 系列打印机
- ✅ 自动检测流类型（JPEG/RTSP）
- ✅ 连接测试功能

#### API 端点
- `GET /api/bambu/camera/available` - 检查摄像头功能可用性
- `GET /api/bambu/camera/configs` - 获取所有配置
- `POST /api/bambu/camera/add-config` - 添加配置
- `POST /api/bambu/camera/remove-config` - 删除配置
- `POST /api/bambu/camera/capture` - 拍照
- `POST /api/bambu/camera/test-connection` - 测试连接

#### 前端更新
- 在自动查词、自动抄写、校准页面添加"使用打印机摄像头"按钮
- 添加摄像头配置对话框
- 添加配置管理界面（添加、选择、删除配置）

#### 使用方法
1. 安装依赖：`pip install bambu-lab-cloud-api`
2. 在 Web 界面添加打印机配置（IP地址、访问码）
3. 点击"使用打印机摄像头"按钮
4. 选择已配置的打印机并拍照

详细使用说明请参考：[BAMBU_CAMERA_GUIDE.md](BAMBU_CAMERA_GUIDE.md)
