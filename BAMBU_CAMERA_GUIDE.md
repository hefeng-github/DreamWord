# Bambu 打印机摄像头功能使用指南

## 功能概述

智能写字机系统现已集成 Bambu Lab 打印机摄像头功能，可以直接使用打印机的内置摄像头进行拍照，用于：
- **📚 自动查词** - 拍摄试卷图片进行单词识别和注释
- **📝 自动抄写** - 拍摄横线本图片进行智能排版
- **📐 校准** - 拍摄 ArUco 标记进行写字机校准

## 支持的打印机型号

- ✅ **A1 mini** - 使用 JPEG 帧流
- ✅ **A1** - 使用 JPEG 帧流
- ✅ **P1P/P1S** - 使用 JPEG 帧流
- ✅ **X1 Carbon** - 使用 RTSP 流

## 安装步骤

### 1. 安装依赖库

```bash
pip install bambu-lab-cloud-api
```

### 2. 启动 Web 服务器

```bash
python app.py
```

### 3. 访问 Web 界面

在浏览器中打开：`http://127.0.0.1:5000`

## 配置打印机

### 获取打印机 IP 地址

1. 确保打印机连接到网络（LAN 模式或云端模式）
2. 在打印机屏幕上进入：`设置` → `网络`
3. 记下打印机的 IP 地址（例如：`192.168.1.100`）

### 获取访问码（Access Code）

1. 在打印机上进入：`设置` → `网络`
2. 找到"访问码"选项
3. 记下访问码（这是8位数字）

### 在系统中添加打印机配置

1. 在任意需要拍照的功能页面（自动查词、自动抄写、校准）
2. 点击 **"🖨️ 使用打印机摄像头"** 按钮
3. 在弹出的对话框中点击 **"➕ 添加配置"**
4. 填写配置信息：
   - **配置名称**：例如"我的A1mini"（方便识别）
   - **打印机IP地址**：例如 `192.168.1.100`
   - **访问码**：从打印机设置中获取的8位数字
   - **打印机型号**：选择对应的型号
5. 点击 **"💾 保存配置"**
6. 可选：点击 **"🧪 测试连接"** 验证配置是否正确

## 使用方法

### 场景 1：自动查词中使用打印机摄像头

1. 切换到 **"📚 自动查词"** 标签页
2. 点击 **"🖨️ 使用打印机摄像头"** 按钮
3. 选择已配置的打印机
4. 点击 **"📸 拍照"**
5. 系统会自动捕获打印机摄像头的画面
6. 继续后续的查词流程

### 场景 2：自动抄写中使用打印机摄像头

1. 切换到 **"📝 自动抄写"** 标签页
2. 点击 **"🖨️ 使用打印机摄像头"** 按钮
3. 选择已配置的打印机
4. 点击 **"📸 拍照"**
5. 系统会自动捕获打印机摄像头的画面
6. 继续后续的抄写流程

### 场景 3：校准中使用打印机摄像头

1. 切换到 **"📐 校准"** 标签页
2. 完成标记位置设置和绘制
3. 点击 **"🖨️ 使用打印机摄像头"** 按钮
4. 选择已配置的打印机
5. 点击 **"📸 拍照"**
6. 系统会自动捕获打印机摄像头的画面
7. 继续后续的校准流程

## API 参考

### 检查摄像头功能是否可用

```http
GET /api/bambu/camera/available
```

**响应：**
```json
{
  "success": true,
  "available": true,
  "message": "摄像头功能可用"
}
```

### 获取所有摄像头配置

```http
GET /api/bambu/camera/configs
```

**响应：**
```json
{
  "success": true,
  "configs": {
    "我的A1mini": {
      "ip": "192.168.1.100",
      "model": "A1MINI",
      "stream_type": "jpeg"
    }
  }
}
```

### 添加摄像头配置

```http
POST /api/bambu/camera/add-config
Content-Type: application/json

{
  "name": "我的打印机",
  "printer_ip": "192.168.1.100",
  "access_code": "12345678",
  "printer_model": "A1MINI"
}
```

### 拍照

```http
POST /api/bambu/camera/capture
Content-Type: application/json

{
  "config_name": "我的A1mini"
}
```

**响应：**
```json
{
  "success": true,
  "filename": "bambu_camera_abc123.jpg",
  "preview_url": "/api/preview/bambu_camera_abc123.jpg",
  "message": "拍照成功"
}
```

### 测试连接

```http
POST /api/bambu/camera/test-connection
Content-Type: application/json

{
  "printer_ip": "192.168.1.100",
  "access_code": "12345678",
  "printer_model": "A1MINI"
}
```

## Python API 使用

### 基本使用

```python
from bambu_camera import BambuCamera, BambuCameraConfig

# 1. 创建配置
config = BambuCameraConfig(
    printer_ip="192.168.1.100",
    access_code="12345678",
    printer_model="A1MINI"
)

# 2. 创建摄像头实例
camera = BambuCamera(config)

# 3. 连接到打印机
success, message = camera.connect()
if success:
    print(f"连接成功: {message}")
else:
    print(f"连接失败: {message}")

# 4. 捕获图像并保存
success, message = camera.capture_and_save("photo.jpg")
if success:
    print(f"拍照成功: {message}")
else:
    print(f"拍照失败: {message}")
```

### 使用管理器（推荐）

```python
from bambu_camera import get_camera_manager

# 1. 获取管理器
manager = get_camera_manager()

# 2. 添加配置
manager.add_config(
    name="我的打印机",
    printer_ip="192.168.1.100",
    access_code="12345678",
    printer_model="A1MINI"
)

# 3. 获取摄像头
camera = manager.get_camera("我的打印机")

# 4. 拍照
success, message = camera.capture_and_save("output.jpg")
```

### 获取 Base64 编码的图像

```python
from bambu_camera import BambuCamera, BambuCameraConfig

config = BambuCameraConfig(
    printer_ip="192.168.1.100",
    access_code="12345678",
    printer_model="A1MINI"
)

camera = BambuCamera(config)

# 捕获并获取 base64
success, base64_data, message = camera.capture_to_base64()
if success:
    print(f"Base64 长度: {len(base64_data)}")
    # 可以直接在 HTML 中使用
    # <img src="data:image/jpeg;base64,{base64_data}">
```

## 故障排除

### 问题：无法连接到打印机

**可能原因：**
1. 打印机未连接到网络
2. IP 地址错误
3. 访问码错误
4. 防火墙阻止连接

**解决方案：**
1. 检查打印机是否在同一网络
2. 在打印机设置中确认 IP 地址
3. 重新获取访问码
4. 临时关闭防火墙测试

### 问题：拍照失败

**可能原因：**
1. 打印机型号选择错误（A1/P1 应使用 JPEG，X1 应使用 RTSP）
2. 访问码已更改
3. 打印机正在执行其他任务

**解决方案：**
1. 确认打印机型号选择正确
2. 重新获取访问码并更新配置
3. 等待打印机空闲后重试

### 问题：依赖库安装失败

**解决方案：**
```bash
# 使用国内镜像加速
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple bambu-lab-cloud-api
```

## 技术细节

### 工作原理

1. **配置管理**：使用 `BambuCameraConfig` 存储打印机连接信息
2. **连接建立**：根据打印机型号自动选择正确的流类型（JPEG 或 RTSP）
3. **图像捕获**：使用 `bambu-lab-cloud-api` 库获取摄像头画面
4. **文件保存**：将捕获的图像保存到服务器 `uploads/` 目录
5. **前端展示**：通过 HTTP 接口返回预览 URL

### 支持的流类型

| 打印机系列 | 流类型 | 说明 |
|-----------|--------|------|
| A1 mini / A1 | JPEG 帧流 | 逐帧获取 JPEG 图像 |
| P1P / P1S | JPEG 帧流 | 逐帧获取 JPEG 图像 |
| X1 Carbon | RTSP 流 | 使用 RTSP 协议获取视频流 |

### 安全说明

- ⚠️ 访问码是敏感信息，请妥善保管
- ⚠️ 打印机应仅在可信网络中使用
- ⚠️ 建议在局域网环境使用，避免暴露到公网

## 参考资料

- [Bambu Lab Cloud API GitHub](https://github.com/coelacant1/Bambu-Lab-Cloud-API)
- [Bambu Connect 官方文档](https://wiki.bambulab.com/zh/software/bambu-connect)
- [项目主文档](README.md)

## 更新日志

### v1.0.0 (2025-02-17)

- ✅ 初始版本
- ✅ 支持 A1/A1 mini/P1P/P1S/X1C 系列打印机
- ✅ Web 界面配置和拍照功能
- ✅ Python API 支持
- ✅ 自动流类型检测
