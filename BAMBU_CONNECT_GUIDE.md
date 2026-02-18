# Bambu Connect 集成指南

**智能写字机项目** - 将 Bambu Lab 3D 打印机改装为自动写字设备

本项目通过控制打印机的 X/Y/Z 轴运动，用笔代替喷嘴进行书写，实现真正的"书法"而非 3D 打印。

## 系统说明

### 工作原理

```
文字输入 → 字体渲染 → 骨架化提取 → 笔画路径 → Gcode生成 → 打印机运动 → 笔迹书写
```

- **X/Y 轴**: 控制笔在纸上的移动位置
- **Z 轴**: 控制抬笔（不书写）/ 下笔（书写）
- **原 Z 轴温度控制**: 在写字机模式下禁用（无需加热）

### 硬件改装要求

将 3D 打印机改装为写字机需要：

1. **笔架装置**: 替换喷嘴，固定笔
2. **笔的压力调节**: 确保 Z=0 时笔尖刚好接触纸面
3. **纸张固定**: 在热床上固定纸张（美纹纸胶带或夹具）
4. **工作区限制**: A1 mini 提供 256×256mm 的书写区域

## 功能特性

- ✅ 支持 Bambu Lab A1 mini、A1、P1P、X1C 等型号
- ✅ 自动生成符合 Bambu Lab 标准的写字 Gcode
- ✅ 一键发送到 Bambu Connect
- ✅ 支持中英文书写（含手写体风格）
- ✅ ArUco 视觉校准功能
- ✅ 自动查词和抄写功能

## 支持的打印机型号

| 型号 | 名称 | 打印体积 |
|------|------|----------|
| A1MINI | Bambu Lab A1 mini | 256×256×256 mm |
| A1 | Bambu Lab A1 | 256×256×256 mm |
| P1P | Bambu Lab P1P | 256×256×256 mm |
| X1C | Bambu Lab X1 Carbon | 256×256×256 mm |

## 前置要求

### 1. 安装 Bambu Connect

请访问 [Bambu Connect 官方文档](https://wiki.bambulab.com/zh/software/bambu-connect) 下载并安装：

- **Windows**: Windows 10 或更高版本（x86_64）
- **macOS**: macOS 13 或更高版本（arm64 & x86_64）
- **Linux**: 开发中

### 2. 打印机设置（写字机模式）

#### 方式一：使用 Bambu Connect（推荐）

1. **硬件改装**: 完成打印机笔架安装
2. **网络连接**: 将打印机连接到网络（LAN 模式）
3. **软件配置**: 在 Bambu Connect 中登录账户
4. **设备发现**: Bambu Connect 会自动发现同一网络下的打印机

#### 方式二：使用开发者模式

1. 进入打印机设置 → 开发者选项
2. 启用"开发者模式"
3. 打印机将在 LAN 模式下工作，无需授权验证

**注意**:
- 开发者模式下打印机无法连接到 Bambu 云端，仅限局域网使用
- 写字机不需要加热功能，所有温度参数仅为兼容 Bambu Connect 格式

## 使用方法

### 方法一：通过 Web 界面

1. 启动 Web 服务器：
   ```bash
   python app.py
   ```

2. 访问 `http://127.0.0.1:5000`

3. 在"书写文字"功能中：
   - 输入要书写的文字
   - 选择打印机型号（默认为 A1 mini）
   - 调整打印参数（可选）
   - 点击"生成并发送"

4. Bambu Connect 将自动打开并加载文件

5. 在 Bambu Connect 中：
   - 确认打印预览
   - 选择目标打印机
   - 点击"开始打印"

### 方法二：通过 Python API

```python
from bambu_adapter import BambuPrinterAdapter
from writer import WriterMachine

# 1. 生成 Gcode
writer = WriterMachine(printer_model='A1MINI')
gcode = writer.write_text(
    text="你好世界",
    use_handright=True,
    save_gcode_path="output.gcode"
)

# 2. 发送到 Bambu Connect
adapter = BambuPrinterAdapter(printer_model='A1MINI')
adapter.prepare_and_send(
    gcode_path="output.gcode",
    model_name="我的书法作品"
)
```

### 方法三：通过命令行

```bash
# 测试 Bambu Connect 连接
python bambu_adapter.py
```

## API 文档

### 获取支持的打印机型号

**请求**:
```
GET /api/printer/models
```

**响应**:
```json
{
  "success": true,
  "models": [
    {
      "id": "A1MINI",
      "name": "Bambu Lab A1 mini",
      "volume": {"x": 256, "y": 256, "z": 256}
    }
  ]
}
```

### 发送到 Bambu Connect

**请求**:
```
POST /api/bambu/send
Content-Type: application/json

{
  "gcode_file": "write_abc123.gcode",
  "model_name": "书法作品",
  "printer_model": "A1MINI"
}
```

**响应**:
```json
{
  "success": true,
  "message": "已发送到 Bambu Connect"
}
```

### 检查 Bambu Connect 状态

**请求**:
```
GET /api/bambu/check
```

**响应**:
```json
{
  "success": true,
  "available": true,
  "message": "Bambu Connect 已安装"
}
```

## 参数说明

### 写字参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `printer_model` | string | "A1MINI" | 打印机型号 |
| `z_up` | float | 5.0 | 抬笔高度（毫米）|
| `z_down` | float | 0.0 | 下笔位置（毫米）|
| `feed_rate` | float | 3000.0 | 移动速度（毫米/分钟）|

**注意**: 温度参数（nozzle_temp, bed_temp）仅用于兼容 Bambu Connect 文件格式，实际写字过程中不会加热。

### 推荐参数设置

#### 日常书写
```
z_up: 5.0 mm（抬笔高度）
z_down: 0.0 mm（下笔接触纸面）
feed_rate: 3000 mm/min（移动速度）
```

#### 精细书写（更慢，更稳定）
```
z_up: 3.0 mm（抬笔高度）
z_down: 0.0 mm
feed_rate: 1500 mm/min（降低速度）
```

#### 快速书写
```
z_up: 5.0 mm
z_down: 0.0 mm
feed_rate: 5000 mm/min（提高速度）
```

## 工作原理

### 1. Gcode 生成

系统将文字转换为笔画路径，生成符合 Bambu Lab 标准的 Gcode：

- 添加打印机特定头部信息
- 设置温度和移动参数
- 优化抬笔/下笔动作
- 添加结束指令（归零、关闭加热等）

### 2. 3MF 转换

生成的 Gcode 会转换为 3MF 格式（3D Manufacturing Format）：

```
Gcode → 3MF 容器 → Bambu Connect
```

3MF 文件结构：
```
file.3mf
├── [Content_Types].xml
├── _rels/.rels
└── 3D/
    ├── model/
    │   ├── 3dmodel.model
    │   └── _rels/
    │       └── 3dmodel.model.rels
```

### 3. URL Scheme 调用

通过 URL Scheme 启动 Bambu Connect：

```
bambu-connect://import-file?path=%2Fpath%2Fto%2Ffile.3mf&name=Job&version=1.0.0
```

参数说明：
- `path`: 文件绝对路径（URL 编码）
- `name`: 任务名称（URL 编码）
- `version`: 固定为 "1.0.0"

## 故障排除

### 问题：Bambu Connect 未启动

**解决方案**：
1. 检查 Bambu Connect 是否已安装
2. 检查 URL Scheme 是否正确注册
3. 尝试手动打开 Bambu Connect

### 问题：文件格式错误

**解决方案**：
1. 确保 Gcode 符合 Bambu Lab 标准
2. 检查 3MF 文件结构是否完整
3. 查看错误日志获取详细信息

### 问题：打印机未连接

**解决方案**：
1. 确保打印机与电脑在同一网络
2. 在 Bambu Connect 中手动添加打印机
3. 检查打印机是否启用了 LAN 模式

### 问题：书写质量不佳

**解决方案**：
1. **调整 Z 轴下笔位置**: 确保 z_down=0 时笔尖刚好接触纸面
2. **调整抬笔高度**: 如果笔迹有拖尾，增加 z_up 值
3. **优化移动速度**: 降低 feed_rate 提高稳定性
4. **检查笔架**: 确保笔固定稳固，无晃动
5. **纸张选择**: 使用光滑的纸张减少摩擦
6. **字体渲染**: 启用 Handright 手写体风格获得更自然的笔迹

## 参考资源

- [Bambu Connect 官方文档](https://wiki.bambulab.com/zh/software/bambu-connect)
- [Bambu Lab 第三方集成指南](https://wiki.bambulab.com/en/software/third-party-integration)
- [A1 mini 产品页面](https://bambulab.com/products/a1-mini)

## 技术支持

如有问题，请：
1. 查看本文档的"故障排除"部分
2. 检查控制台输出的错误信息
3. 在项目 GitHub 提交 Issue

---

**注意**: 本功能需要 Bambu Lab 打印机和相关软件。请确保遵守 Bambu Lab 的使用条款和版权声明。
