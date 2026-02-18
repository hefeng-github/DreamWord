# Bambu 打印机摄像头 - YAML 配置持久化功能

## 更新日期
2026-02-18

## 新增功能

### 1. YAML 配置文件持久化
- **配置文件**: `bambu_config.yaml`
- **自动保存**: 添加/删除/修改配置时自动保存
- **自动加载**: 应用启动时自动加载配置
- **格式标准**: 使用 YAML 格式，易于编辑和备份

### 2. 默认打印机设置
- 可以设置某个配置为默认打印机
- 默认打印机会显示 ✓ 默认 标记
- 新添加的第一个配置自动设为默认

### 3. 增强的 Web 界面
- **默认标记**: 配置列表中显示默认打印机徽章
- **设为默认按钮**: 每个配置都有"设为默认"按钮
- **删除按钮**: 每个配置都有删除按钮
- **视觉优化**: 橙色渐变主题，操作按钮悬停效果

---

## 配置文件格式

```yaml
# Bambu 打印机摄像头配置文件
version: '1.0'
default_printer: 我的A1mini  # 默认打印机名称

printers:
  - name: 我的A1mini         # 配置名称
    ip: 192.168.1.100        # 打印机 IP 地址
    access_code: '12345678'  # 访问码（8位数字）
    model: A1MINI            # 打印机型号

  - name: 工作室P1P
    ip: 192.168.1.101
    access_code: '87654321'
    model: P1P
```

---

## API 端点

### 新增端点
- `GET /api/bambu/camera/configs` - 获取所有配置（包含默认打印机信息）
- `POST /api/bambu/camera/set-default` - 设置默认打印机

### 已有端点
- `GET /api/bambu/camera/available` - 检查功能可用性
- `POST /api/bambu/camera/add-config` - 添加配置
- `POST /api/bambu/camera/remove-config` - 删除配置
- `POST /api/bambu/camera/capture` - 拍照
- `POST /api/bambu/camera/test-connection` - 测试连接

---

## 使用方法

### 方法 1: 通过 Web 界面

1. **启动应用**
   ```bash
   python app.py
   ```

2. **访问配置界面**
   - 进入查词/抄写/校准页面
   - 点击 "🖨️ 使用打印机摄像头"

3. **添加配置**
   - 点击 "➕ 添加配置"
   - 填写打印机信息
   - 点击 "💾 保存配置"
   - 配置自动保存到 `bambu_config.yaml`

4. **设置默认打印机**
   - 在配置列表中找到目标打印机
   - 点击 "设为默认" 按钮
   - 默认标记自动显示

5. **删除配置**
   - 在配置列表中点击 "🗑️ 删除" 按钮
   - 确认删除

### 方法 2: 直接编辑配置文件

编辑 `bambu_config.yaml` 文件，重启应用后自动加载。

```yaml
version: '1.0'
default_printer: 客厅A1mini

printers:
  - name: 客厅A1mini
    ip: 192.168.1.100
    access_code: '12345678'
    model: A1MINI
```

### 方法 3: 通过代码

```python
from bambu_camera import get_camera_manager

# 获取管理器（自动加载配置）
manager = get_camera_manager()

# 添加配置（自动保存）
manager.add_config(
    name="我的打印机",
    printer_ip="192.168.1.100",
    access_code="12345678",
    printer_model="A1MINI"
)

# 设置默认打印机（自动保存）
manager.set_default_printer("我的打印机")

# 列出所有配置
configs = manager.list_configs()
print(configs)

# 获取默认打印机
default = manager.get_default_printer()
print(f"默认打印机: {default}")

# 删除配置（自动保存）
manager.remove_config("我的打印机")
```

---

## 功能特点

### ✅ 已实现
- 配置持久化（YAML 格式）
- 应用启动时自动加载配置
- 添加/删除配置时自动保存
- 默认打印机设置
- Web 界面完整支持
- 配置文件手动编辑支持
- 默认打印机视觉标记
- 一键设为默认/删除

### 🔧 配置文件管理
- **位置**: 项目根目录下的 `bambu_config.yaml`
- **备份**: 可以直接复制文件进行备份
- **迁移**: 将配置文件复制到其他项目即可使用
- **版本控制**: 可以纳入 Git 管理（注意访问码安全）

---

## 界面预览

### 配置列表
```
┌─────────────────────────────────────┐
│ 选择打印机              [➕ 添加配置] │
├─────────────────────────────────────┤
│ 我的A1mini           [✓ 默认]        │
│ IP: 192.168.1.100                    │
│ 型号: A1MINI  行程: 180×180×180mm    │
│ [设为默认] [🗑️ 删除]                 │
├─────────────────────────────────────┤
│ 工作室P1P                            │
│ IP: 192.168.1.101                    │
│ 型号: P1P  行程: 256×256×256mm       │
│ [设为默认] [🗑️ 删除]                 │
└─────────────────────────────────────┘
```

---

## 支持的打印机型号

| 型号 | 工作区域 | 流类型 |
|------|----------|--------|
| A1 mini | 180×180×180mm | JPEG |
| A1 | 256×256×256mm | JPEG |
| P1P | 256×256×256mm | JPEG |
| P1S | 256×256×256mm | JPEG |
| X1 Carbon | 256×256×256mm | RTSP |

---

## 常见问题

### Q: 配置文件丢失了怎么办？
A: 重新添加配置即可，或者从备份文件恢复。

### Q: 如何修改已有配置？
A: 目前需要删除后重新添加，或者直接编辑 YAML 文件。

### Q: 默认打印机有什么作用？
A: 未来可以在拍照时自动使用默认打印机，无需每次选择。

### Q: 配置文件可以加密吗？
A: 目前访问码是明文存储的，建议不要将配置文件上传到公开位置。

---

## 文件清单

### 新增文件
- `bambu_config.yaml` - 配置文件（自动生成）
- `YAML_CONFIG_FEATURE.md` - 本文档

### 修改文件
- `bambu_camera.py` - 添加 YAML 持久化功能
- `app.py` - 添加 `/api/bambu/camera/set-default` 端点
- `static/js/app.js` - 添加默认打印机管理功能
- `static/css/style.css` - 添加操作按钮和徽章样式

---

## 总结

✅ **配置持久化**: YAML 格式，自动保存/加载
✅ **默认打印机**: 快速切换常用打印机
✅ **Web 界面**: 完整的配置管理 UI
✅ **易于使用**: 一键操作，直观清晰
✅ **可扩展性**: 支持手动编辑和代码管理

**配置文件示例**:
```yaml
version: '1.0'
default_printer: 我的A1mini
printers:
  - name: 我的A1mini
    ip: 192.168.1.100
    access_code: '12345678'
    model: A1MINI
```

---

**更新日志**:
- v1.1 (2026-02-18): 新增 YAML 配置持久化和默认打印机功能
- v1.0 (2026-02-17): 初始版本，基本的摄像头拍照功能
