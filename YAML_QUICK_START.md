# YAML 配置功能 - 快速开始

## 新功能概览

从 **v1.1** 版本开始，Bambu 打印机摄像头功能支持 **YAML 配置文件持久化**：

### 主要改进
- ✅ 配置自动保存到 `bambu_config.yaml` 文件
- ✅ 应用启动时自动加载配置
- ✅ 支持设置默认打印机
- ✅ Web 界面完整支持

---

## 配置文件示例

**文件位置**: 项目根目录下的 `bambu_config.yaml`

```yaml
version: '1.0'
default_printer: 我的A1mini

printers:
  - name: 我的A1mini
    ip: 192.168.1.100
    access_code: '12345678'
    model: A1MINI

  - name: 工作室P1P
    ip: 192.168.1.101
    access_code: '87654321'
    model: P1P
```

---

## 使用方法

### 1️⃣ 启动应用

```bash
python app.py
```

应用启动时会自动：
- 加载 `bambu_config.yaml` 配置
- 初始化摄像头管理器
- 显示默认打印机

### 2️⃣ 通过 Web 界面管理配置

1. 访问 `http://127.0.0.1:5000`
2. 进入查词/抄写/校准页面
3. 点击 **"🖨️ 使用打印机摄像头"**
4. 在配置对话框中：
   - 查看已有配置
   - 添加新配置
   - 设置默认打印机
   - 删除配置

### 3️⃣ 直接编辑配置文件（可选）

直接编辑 `bambu_config.yaml` 文件，重启应用后生效。

---

## Web 界面功能

### 配置列表
- 显示所有已配置的打印机
- 默认打印机有 **✓ 默认** 标记
- 显示 IP、型号、工作区域等信息

### 操作按钮
- **设为默认**: 将某个配置设为默认打印机
- **🗑️ 删除**: 删除配置

### 添加配置
- 点击 "➕ 添加配置"
- 填写配置信息：
  - 配置名称
  - IP 地址
  - 访问码
  - 打印机型号
- 点击 "💾 保存配置"

---

## 代码使用

```python
from bambu_camera import get_camera_manager

# 获取管理器（自动加载配置）
manager = get_camera_manager()

# 添加配置（自动保存到 YAML）
manager.add_config(
    name="我的打印机",
    printer_ip="192.168.1.100",
    access_code="12345678",
    printer_model="A1MINI"
)

# 设置默认打印机
manager.set_default_printer("我的打印机")

# 查看所有配置
configs = manager.list_configs()
for name, info in configs.items():
    print(f"{name}: {info['ip']}")

# 获取默认打印机
default = manager.get_default_printer()
print(f"默认: {default}")
```

---

## 配置文件管理

### 备份配置
直接复制 `bambu_config.yaml` 文件到安全位置。

### 迁移配置
将配置文件复制到其他项目根目录即可。

### 重置配置
删除 `bambu_config.yaml` 文件，重启应用会创建新的默认配置文件。

---

## 支持的打印机型号

| 型号 | 工作区域 | 标记 |
|------|----------|------|
| A1 mini | 180×180×180mm | 自动 |
| A1 | 256×256×256mm | 自动 |
| P1P | 256×256×256mm | 自动 |
| P1S | 256×256×256mm | 自动 |
| X1 Carbon | 256×256×256mm | 自动 |

应用会根据型号自动选择：
- **JPEG 帧流**: A1/P1 系列
- **RTSP 流**: X1 系列

---

## 常见问题

### Q: 配置文件在哪里？
A: 在项目根目录下，文件名为 `bambu_config.yaml`

### Q: 如何修改已有配置？
A: 可以删除后重新添加，或者直接编辑 YAML 文件

### Q: 默认打印机有什么用？
A: 未来可以在拍照时自动使用默认打印机

### Q: 配置会丢失吗？
A: 不会，配置持久化保存在 YAML 文件中

### Q: 可以有多个打印机配置吗？
A: 可以，支持无限数量的打印机配置

---

## 版本历史

- **v1.1** (2026-02-18)
  - 新增 YAML 配置持久化
  - 新增默认打印机功能
  - Web 界面完整支持

- **v1.0** (2026-02-17)
  - 初始版本
  - 基本的摄像头拍照功能

---

## 相关文件

- `bambu_camera.py` - 摄像头核心模块
- `bambu_config.yaml` - 配置文件（自动生成）
- `app.py` - Web 应用
- `static/js/app.js` - 前端逻辑
- `static/css/style.css` - 界面样式

---

**提示**: 配置文件中的访问码是敏感信息，请注意不要上传到公开仓库！
