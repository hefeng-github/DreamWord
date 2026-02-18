"""
Bambu 打印机摄像头模块

用于捕获 Bambu Lab 3D 打印机的摄像头画面
支持 A1/P1 系列（JPEG帧流）和 X1 系列（RTSP流）

使用 bambu-lab-cloud-api: https://github.com/coelacant1/Bambu-Lab-Cloud-API
"""

import os
import base64
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
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

    def __init__(self):
        """初始化管理器"""
        self._configs: Dict[str, BambuCameraConfig] = {}
        self._cameras: Dict[str, BambuCamera] = {}

    def add_config(
        self,
        name: str,
        printer_ip: str,
        access_code: str,
        printer_model: str = 'A1MINI'
    ) -> Tuple[bool, str]:
        """
        添加摄像头配置

        Args:
            name: 配置名称（例如: "我的A1mini"）
            printer_ip: 打印机 IP 地址
            access_code: 访问码
            printer_model: 打印机型号

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
            return True, f"配置 '{name}' 已移除"
        else:
            return False, f"配置 '{name}' 不存在"


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
