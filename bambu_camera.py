"""
Bambu 打印机摄像头模块

用于捕获 Bambu Lab 3D 打印机的摄像头画面
支持 A1/P1 系列（JPEG帧流）和 X1 系列（RTSP流）

使用 bambu-lab-cloud-api: https://github.com/coelacant1/Bambu-Lab-Cloud-API
"""

import os
import base64
import yaml
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List
import io


class BambuCameraConfig:
    """Bambu 摄像头配置"""

    def __init__(
        self,
        printer_ip: str,
        access_code: str,
        printer_model: str = 'A1MINI',
        work_area: Optional[Dict[str, float]] = None
    ):
        """
        初始化摄像头配置

        Args:
            printer_ip: 打印机 IP 地址（例如: 192.168.1.100）
            access_code: 打印机访问码（在打印机设置中查看）
            printer_model: 打印机型号（A1MINI, A1, P1P, X1C）
            work_area: 工作区域（行程）配置 {'x': 256, 'y': 256, 'z': 256}
        """
        self.printer_ip = printer_ip
        self.access_code = access_code
        self.printer_model = printer_model.upper()

        # 根据型号确定流类型
        if self.printer_model in ['A1MINI', 'A1', 'P1P', 'P1S']:
            self.stream_type = 'jpeg'
        elif self.printer_model in ['X1C', 'X1']:
            self.stream_type = 'rtsp'
        else:
            # 默认使用 JPEG
            self.stream_type = 'jpeg'

        # 设置工作区域
        if work_area:
            self.work_area = work_area
        else:
            # 使用默认工作区域
            self.work_area = self._get_default_work_area()

    def _get_default_work_area(self) -> Dict[str, float]:
        """获取打印机型号的默认工作区域"""
        default_areas = {
            'A1MINI': {'x': 180, 'y': 180, 'z': 180},  # A1 mini 是 180mm
            'A1': {'x': 256, 'y': 256, 'z': 256},
            'P1P': {'x': 256, 'y': 256, 'z': 256},
            'P1S': {'x': 256, 'y': 256, 'z': 256},
            'X1C': {'x': 256, 'y': 256, 'z': 256},
        }
        return default_areas.get(self.printer_model, {'x': 180, 'y': 180, 'z': 180})

    def get_work_area(self) -> Dict[str, float]:
        """获取工作区域配置"""
        return self.work_area

    def validate(self) -> Tuple[bool, str]:
        """
        验证配置是否有效

        Returns:
            (是否有效, 错误信息)
        """
        if not self.printer_ip:
            return False, "打印机 IP 地址不能为空"

        if not self.access_code:
            return False, "访问码不能为空"

        # 简单的 IP 地址格式验证
        parts = self.printer_ip.split('.')
        if len(parts) != 4:
            return False, "IP 地址格式不正确"

        try:
            for part in parts:
                num = int(part)
                if num < 0 or num > 255:
                    return False, "IP 地址格式不正确"
        except ValueError:
            return False, "IP 地址格式不正确"

        return True, ""


class BambuCamera:
    """Bambu 打印机摄像头"""

    def __init__(self, config: BambuCameraConfig):
        """
        初始化摄像头

        Args:
            config: 摄像头配置
        """
        self.config = config
        self._stream = None
        self._available = False

        # 检查依赖是否可用
        try:
            from bambulab import JPEGFrameStream, RTSPStream
            self._available = True
        except ImportError:
            self._available = False
            print("[警告] bambu-lab-cloud-api 未安装，摄像头功能不可用")
            print("请运行: pip install bambu-lab-cloud-api")

    @property
    def available(self) -> bool:
        """检查摄像头是否可用"""
        return self._available

    def connect(self) -> Tuple[bool, str]:
        """
        连接到打印机摄像头

        Returns:
            (是否成功, 消息)
        """
        if not self._available:
            return False, "bambu-lab-cloud-api 未安装"

        # 验证配置
        valid, error = self.config.validate()
        if not valid:
            return False, error

        try:
            from bambulab import JPEGFrameStream, RTSPStream

            # 根据流类型创建相应的流对象
            if self.config.stream_type == 'jpeg':
                self._stream = JPEGFrameStream(
                    self.config.printer_ip,
                    self.config.access_code
                )
            else:  # rtsp
                self._stream = RTSPStream(
                    self.config.printer_ip,
                    self.config.access_code
                )

            return True, "连接成功"

        except Exception as e:
            return False, f"连接失败: {str(e)}"

    def capture_frame(self) -> Tuple[bool, Optional[bytes], str]:
        """
        捕获一帧图像

        Returns:
            (是否成功, 图像数据(JPEG格式), 消息)
        """
        if not self._available:
            return False, None, "bambu-lab-cloud-api 未安装"

        if not self._stream:
            success, message = self.connect()
            if not success:
                return False, None, message

        try:
            # 获取一帧
            frame_data = self._stream.get_frame()

            if frame_data:
                return True, frame_data, "捕获成功"
            else:
                return False, None, "未能获取图像数据"

        except Exception as e:
            return False, None, f"捕获失败: {str(e)}"

    def capture_and_save(
        self,
        output_path: str
    ) -> Tuple[bool, str]:
        """
        捕获图像并保存到文件

        Args:
            output_path: 输出文件路径

        Returns:
            (是否成功, 消息)
        """
        success, frame_data, message = self.capture_frame()

        if success and frame_data:
            try:
                # 确保目录存在
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)

                # 保存图像
                with open(output_path, 'wb') as f:
                    f.write(frame_data)

                return True, f"已保存到: {output_path}"

            except Exception as e:
                return False, f"保存失败: {str(e)}"
        else:
            return False, message

    def capture_to_base64(self) -> Tuple[bool, Optional[str], str]:
        """
        捕获图像并返回 base64 编码

        Returns:
            (是否成功, base64字符串, 消息)
        """
        success, frame_data, message = self.capture_frame()

        if success and frame_data:
            try:
                # 转换为 base64
                base64_str = base64.b64encode(frame_data).decode('utf-8')
                return True, base64_str, "转换成功"
            except Exception as e:
                return False, None, f"转换失败: {str(e)}"
        else:
            return False, None, message

    def disconnect(self):
        """断开连接"""
        if self._stream:
            try:
                # 对于有上下文管理器的流，关闭它
                if hasattr(self._stream, 'close'):
                    self._stream.close()
            except Exception:
                pass
            finally:
                self._stream = None


class BambuCameraManager:
    """Bambu 摄像头管理器

    管理多个摄像头配置，提供便捷的接口
    """

    # 配置文件路径
    CONFIG_FILE = Path(__file__).parent / 'bambu_config.yaml'

    def __init__(self, auto_load: bool = True):
        """初始化管理器

        Args:
            auto_load: 是否自动加载配置文件
        """
        self._configs: Dict[str, BambuCameraConfig] = {}
        self._cameras: Dict[str, BambuCamera] = {}
        self._default_printer: Optional[str] = None

        if auto_load:
            self.load_from_yaml()

    def add_config(
        self,
        name: str,
        printer_ip: str,
        access_code: str,
        printer_model: str = 'A1MINI',
        auto_save: bool = True
    ) -> Tuple[bool, str]:
        """
        添加摄像头配置

        Args:
            name: 配置名称（例如: "我的A1mini"）
            printer_ip: 打印机 IP 地址
            access_code: 访问码
            printer_model: 打印机型号
            auto_save: 是否自动保存到配置文件

        Returns:
            (是否成功, 消息)
        """
        config = BambuCameraConfig(
            printer_ip=printer_ip,
            access_code=access_code,
            printer_model=printer_model
        )

        valid, error = config.validate()
        if not valid:
            return False, error

        self._configs[name] = config

        # 自动保存配置
        if auto_save:
            self.save_to_yaml()

        # 如果是第一个配置，自动设为默认
        if len(self._configs) == 1 and self._default_printer is None:
            self._default_printer = name
            if auto_save:
                self.save_to_yaml()

        return True, f"配置 '{name}' 已添加"

    def get_camera(self, name: str) -> Optional[BambuCamera]:
        """
        获取指定名称的摄像头

        Args:
            name: 配置名称

        Returns:
            BambuCamera 实例，如果不存在则返回 None
        """
        if name not in self._configs:
            return None

        if name not in self._cameras:
            # 创建新的摄像头实例
            self._cameras[name] = BambuCamera(self._configs[name])

        return self._cameras[name]

    def list_configs(self) -> Dict[str, Dict[str, str]]:
        """
        列出所有配置

        Returns:
            配置字典 {name: {ip, model}}
        """
        return {
            name: {
                'ip': config.printer_ip,
                'model': config.printer_model,
                'stream_type': config.stream_type
            }
            for name, config in self._configs.items()
        }

    def remove_config(self, name: str) -> Tuple[bool, str]:
        """
        移除配置

        Args:
            name: 配置名称

        Returns:
            (是否成功, 消息)
        """
        if name in self._configs:
            # 断开摄像头连接
            if name in self._cameras:
                self._cameras[name].disconnect()
                del self._cameras[name]

            del self._configs[name]

            # 如果是默认打印机，清除默认设置
            if self._default_printer == name:
                self._default_printer = None

            # 自动保存
            self.save_to_yaml()

            return True, f"配置 '{name}' 已移除"
        else:
            return False, f"配置 '{name}' 不存在"

    def load_from_yaml(self, config_path: Optional[str] = None) -> Tuple[bool, str]:
        """
        从 YAML 文件加载配置

        Args:
            config_path: 配置文件路径（可选，默认使用 bambu_config.yaml）

        Returns:
            (是否成功, 消息)
        """
        if config_path is None:
            config_path = self.CONFIG_FILE

        config_file = Path(config_path)

        # 如果配置文件不存在，创建默认配置
        if not config_file.exists():
            print(f"[INFO] 配置文件不存在，创建默认配置: {config_file}")
            self.save_to_yaml(config_path)
            return True, "已创建默认配置文件"

        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)

            if not data or 'printers' not in data:
                print("[WARN] 配置文件为空或格式不正确")
                return True, "配置文件为空"

            # 加载打印机配置
            for printer_data in data.get('printers', []):
                try:
                    success, message = self.add_config(
                        name=printer_data['name'],
                        printer_ip=printer_data['ip'],
                        access_code=printer_data['access_code'],
                        printer_model=printer_data.get('model', 'A1MINI'),
                        auto_save=False  # 避免循环保存
                    )
                    if success:
                        print(f"[OK] 已加载配置: {printer_data['name']}")
                    else:
                        print(f"[ERROR] 加载配置失败: {printer_data['name']} - {message}")
                except Exception as e:
                    print(f"[ERROR] 解析配置失败: {printer_data.get('name', 'Unknown')} - {e}")

            # 加载默认打印机
            default_printer = data.get('default_printer')
            if default_printer and default_printer in self._configs:
                self._default_printer = default_printer
                print(f"[OK] 默认打印机: {default_printer}")

            loaded_count = len(self._configs)
            return True, f"已加载 {loaded_count} 个配置"

        except yaml.YAMLError as e:
            print(f"[ERROR] YAML 解析失败: {e}")
            return False, f"YAML 格式错误: {e}"
        except Exception as e:
            print(f"[ERROR] 加载配置失败: {e}")
            return False, f"加载失败: {e}"

    def save_to_yaml(self, config_path: Optional[str] = None) -> Tuple[bool, str]:
        """
        保存配置到 YAML 文件

        Args:
            config_path: 配置文件路径（可选，默认使用 bambu_config.yaml）

        Returns:
            (是否成功, 消息)
        """
        if config_path is None:
            config_path = self.CONFIG_FILE

        config_file = Path(config_path)

        try:
            # 构建配置数据
            data = {
                'version': '1.0',
                'default_printer': self._default_printer,
                'printers': []
            }

            # 添加打印机配置
            for name, config in self._configs.items():
                printer_data = {
                    'name': name,
                    'ip': config.printer_ip,
                    'access_code': config.access_code,
                    'model': config.printer_model
                }
                data['printers'].append(printer_data)

            # 确保目录存在
            config_file.parent.mkdir(parents=True, exist_ok=True)

            # 写入文件
            with open(config_file, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

            return True, f"配置已保存到: {config_file}"

        except Exception as e:
            print(f"[ERROR] 保存配置失败: {e}")
            return False, f"保存失败: {e}"

    def get_default_printer(self) -> Optional[str]:
        """获取默认打印机名称"""
        return self._default_printer

    def set_default_printer(self, name: str) -> Tuple[bool, str]:
        """
        设置默认打印机

        Args:
            name: 打印机配置名称

        Returns:
            (是否成功, 消息)
        """
        if name not in self._configs:
            return False, f"配置 '{name}' 不存在"

        self._default_printer = name
        self.save_to_yaml()
        return True, f"默认打印机已设置为: {name}"


# 全局管理器实例
_camera_manager = None


def get_camera_manager() -> BambuCameraManager:
    """获取全局摄像头管理器"""
    global _camera_manager
    if _camera_manager is None:
        _camera_manager = BambuCameraManager()
    return _camera_manager


def main():
    """测试函数"""
    print("=" * 70)
    print("Bambu 摄像头模块测试")
    print("=" * 70)

    # 检查依赖
    try:
        from bambulab import JPEGFrameStream, RTSPStream
        print("[OK] bambu-lab-cloud-api 已安装\n")
    except ImportError:
        print("[警告] bambu-lab-cloud-api 未安装")
        print("请运行: pip install bambu-lab-cloud-api\n")
        return

    print("使用示例:")
    print("""
from bambu_camera import BambuCamera, BambuCameraConfig

# 1. 创建配置
config = BambuCameraConfig(
    printer_ip="192.168.1.100",
    access_code="your_access_code",
    printer_model="A1MINI"
)

# 2. 创建摄像头实例
camera = BambuCamera(config)

# 3. 捕获并保存
success, message = camera.capture_and_save("photo.jpg")
if success:
    print(f"[OK] {message}")
else:
    print(f"[ERROR] {message}")

# 4. 捕获并获取 base64
success, base64_data, message = camera.capture_to_base64()
if success:
    print(f"[OK] Base64 长度: {len(base64_data)}")
    """)

    print("\n或使用管理器:")
    print("""
from bambu_camera import get_camera_manager

# 获取管理器
manager = get_camera_manager()

# 添加配置
manager.add_config(
    name="我的打印机",
    printer_ip="192.168.1.100",
    access_code="your_access_code",
    printer_model="A1MINI"
)

# 获取摄像头并拍照
camera = manager.get_camera("我的打印机")
if camera:
    success, message = camera.capture_and_save("photo.jpg")
    """)

    print("\n" + "=" * 70)


if __name__ == '__main__':
    main()
