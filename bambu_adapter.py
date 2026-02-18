"""
Bambu Connect 适配器

用于与 Bambu Lab 3D 打印机（特别是 A1 mini）集成
支持通过 Bambu Connect 发送打印任务
"""

import os
import sys
import json
import subprocess
import tempfile
import zipfile
from pathlib import Path
from typing import Optional, Dict, Any
import shutil


class PrinterConfig:
    """打印机配置"""

    # 支持的打印机型号及其配置
    PRINTER_MODELS = {
        'A1MINI': {
            'name': 'Bambu Lab A1 mini',
            'volume': {'x': 180, 'y': 180, 'z': 180},  # A1 mini 是 180mm
            'nozzle_diameter': 0.4,
            'filament_diameter': 1.75,
            'default_layer_height': 0.2,
        },
        'A1': {
            'name': 'Bambu Lab A1',
            'volume': {'x': 256, 'y': 256, 'z': 256},
            'nozzle_diameter': 0.4,
            'filament_diameter': 1.75,
            'default_layer_height': 0.2,
        },
        'P1P': {
            'name': 'Bambu Lab P1P',
            'volume': {'x': 256, 'y': 256, 'z': 256},
            'nozzle_diameter': 0.4,
            'filament_diameter': 1.75,
            'default_layer_height': 0.2,
        },
        'P1S': {
            'name': 'Bambu Lab P1S',
            'volume': {'x': 256, 'y': 256, 'z': 256},
            'nozzle_diameter': 0.4,
            'filament_diameter': 1.75,
            'default_layer_height': 0.2,
        },
        'X1C': {
            'name': 'Bambu Lab X1 Carbon',
            'volume': {'x': 256, 'y': 256, 'z': 256},
            'nozzle_diameter': 0.4,
            'filament_diameter': 1.75,
            'default_layer_height': 0.2,
        },
    }

    @classmethod
    def get_model_config(cls, model: str) -> Dict[str, Any]:
        """获取打印机型号配置"""
        model_upper = model.upper()
        return cls.PRINTER_MODELS.get(model_upper, cls.PRINTER_MODELS['A1MINI'])


class GcodeTo3MFConverter:
    """Gcode 转 3MF 转换器

    3MF 是 Bambu Lab 打印机使用的格式
    """

    def __init__(self, printer_model: str = 'A1MINI'):
        """
        初始化转换器

        Args:
            printer_model: 打印机型号
        """
        self.printer_model = printer_model
        self.printer_config = PrinterConfig.get_model_config(printer_model)

    def gcode_to_3mf(
        self,
        gcode_path: str,
        output_3mf_path: Optional[str] = None,
        model_name: str = "Writing Job"
    ) -> str:
        """
        将 Gcode 文件转换为 3MF 格式

        Args:
            gcode_path: Gcode 文件路径
            output_3mf_path: 输出 3MF 文件路径（可选）
            model_name: 模型名称

        Returns:
            输出的 3MF 文件路径
        """
        # 读取 Gcode
        with open(gcode_path, 'r', encoding='utf-8') as f:
            gcode_content = f.read()

        # 如果未指定输出路径，使用与输入相同的名称
        if output_3mf_path is None:
            output_3mf_path = str(Path(gcode_path).with_suffix('.3mf'))

        # 创建临时目录
        with tempfile.TemporaryDirectory() as temp_dir:
            # 3MF 文件结构
            # 创建必要的目录和文件
            model_dir = Path(temp_dir) / '3D' / 'model'
            model_dir.mkdir(parents=True)

            # 创建 .rels 文件
            rels_dir = Path(temp_dir) / '_rels'
            rels_dir.mkdir()

            # 创建 .rels 文件
            rels_content = '''<?xml version="1.0" encoding="utf-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel" />
</Relationships>'''
            with open(rels_dir / '.rels', 'w', encoding='utf-8') as f:
                f.write(rels_content)

            # 创建 Content_Types 文件
            content_types = '''<?xml version="1.0" encoding="utf-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
    <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml" />
    <Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml" />
</Types>'''
            with open(Path(temp_dir) / '[Content_Types].xml', 'w', encoding='utf-8') as f:
                f.write(content_types)

            # 创建 3dmodel.model 文件
            model_content = self._create_model_content(gcode_content, model_name)
            with open(model_dir / '3dmodel.model', 'w', encoding='utf-8') as f:
                f.write(model_content)

            # 创建 .rels 文件（用于模型）
            model_rels_dir = model_dir / '_rels'
            model_rels_dir.mkdir()

            model_rels_content = '''<?xml version="1.0" encoding="utf-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
</Relationships>'''
            with open(model_rels_dir / '3dmodel.model.rels', 'w', encoding='utf-8') as f:
                f.write(model_rels_content)

            # 创建 ZIP 文件（3MF 本质上是 ZIP）
            with zipfile.ZipFile(output_3mf_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        file_path = Path(root) / file
                        arcname = file_path.relative_to(temp_dir)
                        zf.write(file_path, arcname)

        print(f"[OK] 3MF 文件已生成: {output_3mf_path}")
        return output_3mf_path

    def _create_model_content(self, gcode_content: str, model_name: str) -> str:
        """创建 model 文件内容"""
        # 简化版本的 3MF model 文件
        # 实际使用中可能需要更复杂的结构
        volume = self.printer_config['volume']

        model_content = f'''<?xml version="1.0" encoding="utf-8"?>
<model unit="millimeter" xml:lang="en-US" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">
  <metadata>
    <name>{model_name}</name>
    <description>Generated by Intelligent Writing Machine</description>
    <printer>{self.printer_config['name']}</printer>
  </metadata>
  <resources>
    <object id="1" type="model">
      <mesh>
        <vertices>
        </vertices>
        <triangles>
        </triangles>
      </mesh>
    </object>
  </resources>
  <build>
    <item objectid="1" transform="scale 1 1 1">
    </item>
  </build>
</model>'''

        return model_content

    def create_bambu_gcode(
        self,
        original_gcode: str,
        layer_height: float = 0.2,
        nozzle_temp: int = 220,
        bed_temp: int = 60
    ) -> str:
        """
        创建符合 Bambu Lab 格式的 Gcode

        Args:
            original_gcode: 原始 Gcode
            layer_height: 层高
            nozzle_temp: 喷嘴温度
            bed_temp: 热床温度

        Returns:
            处理后的 Gcode
        """
        lines = original_gcode.split('\n')
        bambu_gcode_lines = []

        # 添加 Bambu Lab 特定的头部信息
        header = f""";
; Bambu Lab G-code file
; Printer: {self.printer_config['name']}
; Layer height: {layer_height} mm
; Nozzle temperature: {nozzle_temp} °C
; Bed temperature: {bed_temp} °C
;
; Generated by Intelligent Writing Machine
;

G21 ; Set units to millimeters
G90 ; Use absolute coordinates
M82 ; Use absolute distances for extrusion
M104 S{nozzle_temp} ; Set nozzle temperature
M140 S{bed_temp} ; Set bed temperature
M190 S{bed_temp} ; Wait for bed temperature
M109 S{nozzle_temp} ; Wait for nozzle temperature

; Home axes
G28
G1 Z5 F3000 ; Lift pen

; Begin writing
"""
        bambu_gcode_lines.append(header)

        # 添加原始 Gcode 内容
        in_gcode_section = False
        for line in lines:
            line_stripped = line.strip()

            # 跳过原始头部
            if not in_gcode_section:
                if line_stripped.startswith('G21') or line_stripped.startswith('G90'):
                    in_gcode_section = True
                    continue

            # 跳过尾部
            if line_stripped.startswith('M2') or line_stripped.startswith('M30'):
                continue

            if in_gcode_section:
                bambu_gcode_lines.append(line)

        # 添加尾部
        footer = f"""
; End of writing job
G1 Z5 F3000 ; Lift pen
G28 X Y ; Home X and Y
M104 S0 ; Turn off nozzle
M140 S0 ; Turn off bed
G28 X Y ; Home X and Y again
M84 ; Disable motors
M2 ; End of program
"""
        bambu_gcode_lines.append(footer)

        return '\n'.join(bambu_gcode_lines)


class BambuConnectLauncher:
    """Bambu Connect 启动器

    通过 URL Scheme 启动 Bambu Connect 并导入文件
    """

    def __init__(self):
        """初始化启动器"""
        self.url_scheme = "bambu-connect://import-file"

    def launch_with_file(
        self,
        file_path: str,
        file_name: Optional[str] = None,
        version: str = "1.0.0"
    ) -> bool:
        """
        启动 Bambu Connect 并导入文件

        Args:
            file_path: 文件路径（3MF 或 Gcode）
            file_name: 文件名称（可选）
            version: 版本号

        Returns:
            是否成功启动
        """
        from urllib.parse import quote

        # 获取文件名
        if file_name is None:
            file_name = Path(file_path).stem

        # 构建参数
        params = {
            'path': file_path,
            'name': file_name,
            'version': version
        }

        # 编码参数
        encoded_params = '&'.join([
            f"{key}={quote(str(value), safe='')}"
            for key, value in params.items()
        ])

        # 构建 URL
        url = f"{self.url_scheme}?{encoded_params}"

        print(f"启动 Bambu Connect: {url}")

        try:
            # 根据操作系统启动
            if os.name == 'nt':  # Windows
                os.startfile(url)
            elif os.name == 'posix':
                if sys.platform == 'darwin':  # macOS
                    subprocess.run(['open', url], check=True)
                else:  # Linux
                    subprocess.run(['xdg-open', url], check=True)

            print("[OK] Bambu Connect 已启动")
            return True

        except Exception as e:
            print(f"[ERROR] 启动 Bambu Connect 失败: {e}")
            return False

    def is_available(self) -> bool:
        """
        检查 Bambu Connect 是否可用

        Returns:
            是否可用
        """
        # 在 Windows 上检查注册表
        if os.name == 'nt':
            try:
                import winreg
                # 尝试打开 Bambu Connect 的注册表项
                key = winreg.OpenKey(
                    winreg.HKEY_CLASSES_ROOT,
                    'bambu-connect'
                )
                winreg.CloseKey(key)
                return True
            except Exception:
                return False

        # 在其他系统上，尝试检查是否安装
        # 这里可以扩展检查逻辑
        return False


class BambuPrinterAdapter:
    """Bambu 打印机适配器

    整合所有功能的统一接口
    """

    def __init__(
        self,
        printer_model: str = 'A1MINI',
        auto_launch: bool = True
    ):
        """
        初始化适配器

        Args:
            printer_model: 打印机型号
            auto_launch: 是否自动启动 Bambu Connect
        """
        self.printer_model = printer_model
        self.auto_launch = auto_launch

        self.converter = GcodeTo3MFConverter(printer_model)
        self.launcher = BambuConnectLauncher()

    def prepare_and_send(
        self,
        gcode_path: str,
        model_name: str = "Writing Job",
        launch_connect: bool = None
    ) -> bool:
        """
        准备并发送打印任务到 Bambu Connect

        Args:
            gcode_path: Gcode 文件路径
            model_name: 模型名称
            launch_connect: 是否启动 Bambu Connect（None 表示使用初始化时的设置）

        Returns:
            是否成功
        """
        print("=" * 70)
        print(f"Bambu 打印机适配器 - {self.printer_model}")
        print("=" * 70)

        # 1. 转换为 3MF 格式
        print("\n1. 转换 Gcode 为 3MF 格式...")
        try:
            three_mf_path = self.converter.gcode_to_3mf(
                gcode_path=gcode_path,
                model_name=model_name
            )
        except Exception as e:
            print(f"[ERROR] 3MF 转换失败: {e}")
            return False

        # 2. 启动 Bambu Connect
        if launch_connect is None:
            launch_connect = self.auto_launch

        if launch_connect:
            print("\n2. 启动 Bambu Connect...")

            # 检查 Bambu Connect 是否可用
            if not self.launcher.is_available():
                print("[ERROR] Bambu Connect 未安装或未配置")
                print("\n请访问以下地址安装 Bambu Connect:")
                print("https://wiki.bambulab.com/zh/software/bambu-connect")
                return False

            # 启动 Bambu Connect
            if not self.launcher.launch_with_file(
                file_path=os.path.abspath(three_mf_path),
                file_name=model_name
            ):
                return False

        print("\n[OK] 准备完成！")
        print(f"\n生成的文件:")
        print(f"- 3MF: {three_mf_path}")
        print(f"- Gcode: {gcode_path}")

        print("\n使用说明:")
        print("1. Bambu Connect 将自动打开并加载文件")
        print("2. 确保打印机已连接（LAN 模式或云端模式）")
        print("3. 在 Bambu Connect 中选择目标打印机")
        print("4. 点击开始打印")

        print("\n" + "=" * 70)

        return True

    def get_printer_info(self) -> Dict[str, Any]:
        """
        获取打印机信息

        Returns:
            打印机配置信息
        """
        return self.converter.printer_config


def main():
    """测试函数"""
    print("=" * 70)
    print("Bambu Connect 适配器测试")
    print("=" * 70)

    # 创建适配器
    adapter = BambuPrinterAdapter(printer_model='A1MINI')

    # 显示打印机信息
    print("\n打印机信息:")
    info = adapter.get_printer_info()
    for key, value in info.items():
        print(f"  {key}: {value}")

    # 检查 Bambu Connect 是否可用
    print("\n检查 Bambu Connect...")
    if adapter.launcher.is_available():
        print("[OK] Bambu Connect 已安装")
    else:
        print("[WARN] Bambu Connect 未安装")
        print("\n请访问以下地址安装:")
        print("https://wiki.bambulab.com/zh/software/bambu-connect")

    print("\n使用示例:")
    print("""
from bambu_adapter import BambuPrinterAdapter

# 创建适配器
adapter = BambuPrinterAdapter(printer_model='A1MINI')

# 准备并发送打印任务
adapter.prepare_and_send(
    gcode_path='output.gcode',
    model_name='我的书法作品'
)
""")

    print("\n" + "=" * 70)


if __name__ == '__main__':
    import sys
    main()
