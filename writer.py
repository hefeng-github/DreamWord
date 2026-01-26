"""
写字模块 - 用于生成和控制写字机

功能：
1. 渲染文字（中文使用Handright，英文使用指定字体）
2. 将文字位图转化为骨架图
3. 将骨架图转化为笔画图
4. 将笔画图转化为Gcode
5. 通过串口控制写字机（FluidNC固件）
"""

import cv2
import numpy as np
from pathlib import Path
from typing import List, Tuple, Optional
from dataclasses import dataclass
from PIL import Image, ImageDraw, ImageFont
import re


@dataclass
class GcodePoint:
    """Gcode点"""
    x: float
    y: float
    z: float = 0.0
    is_move: bool = False  # 是否为移动命令（不绘制）


@dataclass
class Stroke:
    """笔画（一系列连续的点）"""
    points: List[GcodePoint]
    is_write: bool = True  # 是否为书写笔画（True）或移动笔画（False）


class TextRenderer:
    """文本渲染器"""

    def __init__(
        self,
        chinese_font_path: Optional[str] = None,
        english_font_path: Optional[str] = None
    ):
        """
        初始化文本渲染器

        Args:
            chinese_font_path: 中文字体路径（方正粗活意简体）
            english_font_path: 英文字体路径（Noto Sans Math）
        """
        # 默认字体路径
        project_root = Path(__file__).parent

        if chinese_font_path is None:
            chinese_font_path = str(project_root / "Fonts" / "FZZJ-DLHTJW.TTF")

        if english_font_path is None:
            english_font_path = str(project_root / "Fonts" / "NotoSansMath-Regular.ttf")

        self.chinese_font_path = chinese_font_path
        self.english_font_path = english_font_path

        # 验证字体文件
        if not Path(chinese_font_path).exists():
            print(f"警告: 中文字体不存在: {chinese_font_path}")

        if not Path(english_font_path).exists():
            print(f"警告: 英文字体不存在: {english_font_path}")

    def render_text(
        self,
        text: str,
        font_size: int = 40,
        image_width: int = 800,
        image_height: int = 400
    ) -> np.ndarray:
        """
        渲染文本为图像

        Args:
            text: 要渲染的文本
            font_size: 字体大小
            image_width: 图像宽度
            image_height: 图像高度

        Returns:
            渲染后的图像（灰度图）
        """
        # 区分中英文
        has_chinese = self._has_chinese(text)

        # 选择字体
        if has_chinese:
            font_path = self.chinese_font_path
        else:
            font_path = self.english_font_path

        # 创建PIL图像
        image = Image.new('L', (image_width, image_height), color=255)
        draw = ImageDraw.Draw(image)

        # 加载字体
        try:
            font = ImageFont.truetype(font_path, font_size)
        except Exception as e:
            print(f"警告: 无法加载字体 {font_path}: {e}")
            font = ImageFont.load_default()

        # 计算文本大小
        try:
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
        except Exception:
            # 旧版本PIL
            text_width, text_height = draw.textsize(text, font=font)

        # 居中显示
        x = (image_width - text_width) // 2
        y = (image_height - text_height) // 2

        # 绘制文本
        draw.text((x, y), text, font=font, fill=0)

        # 转换为OpenCV格式
        opencv_image = np.array(image)

        return opencv_image

    def render_text_with_handright(
        self,
        text: str,
        background_color: Tuple[int, int, int] = (255, 255, 255),
        text_color: Tuple[int, int, int] = (0, 0, 0)
    ) -> np.ndarray:
        """
        使用Handright渲染手写体中文

        Args:
            text: 要渲染的文本
            background_color: 背景颜色
            text_color: 文字颜色

        Returns:
            渲染后的图像
        """
        try:
            from handright import Template, handwrite

            # 创建模板
            template = Template(
                background=background_color,
                font=self.chinese_font_path,
                font_size=100,
                line_spacing=150,
                word_spacing=30,
                padding=50
            )

            # 渲染手写体
            images = handwrite(text, template)

            if images:
                # 转换第一张图像为OpenCV格式
                pil_image = images[0]
                opencv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
                return opencv_image
            else:
                print("警告: Handright渲染失败，使用普通渲染")
                return self.render_text(text)

        except ImportError:
            print("警告: Handright未安装，使用普通渲染")
            return self.render_text(text)
        except Exception as e:
            print(f"警告: Handright渲染失败: {e}，使用普通渲染")
            return self.render_text(text)

    def _has_chinese(self, text: str) -> bool:
        """检查文本是否包含中文字符"""
        return bool(re.search(r'[\u4e00-\u9fff]', text))


class Skeletonizer:
    """骨架化器 - 将文字位图转化为骨架"""

    def __init__(self):
        """初始化骨架化器"""
        pass

    def skeletonize(self, image: np.ndarray) -> np.ndarray:
        """
        骨架化图像

        Args:
            image: 输入图像（二值图，白色背景，黑色文字）

        Returns:
            骨架化后的图像
        """
        # 确保是二值图
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        # 二值化（确保背景是白色255，文字是黑色0）
        _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)

        # 形态学操作去除噪声
        kernel = np.ones((2, 2), np.uint8)
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)

        # 使用Zhang-Suen骨架化算法
        skeleton = cv2.ximgproc.thinning(binary, thinningType=cv2.ximgproc.THINNING_ZHANGSUEN)

        # 转换回原来的格式（白色背景，黑色骨架）
        skeleton = cv2.bitwise_not(skeleton)

        return skeleton

    def extract_strokes(self, skeleton: np.ndarray) -> List[List[Tuple[int, int]]]:
        """
        从骨架图中提取笔画

        Args:
            skeleton: 骨架化图像

        Returns:
            笔画列表，每个笔画是一系列点
        """
        # 确保是二值图
        if len(skeleton.shape) == 3:
            gray = cv2.cvtColor(skeleton, cv2.COLOR_BGR2GRAY)
        else:
            gray = skeleton.copy()

        # 二值化
        _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)

        # 查找轮廓
        contours, _ = cv2.findContours(binary, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)

        strokes = []
        for contour in contours:
            # 将轮廓转换为点列表
            points = [(int(pt[0][0]), int(pt[0][1])) for pt in contour]
            if len(points) > 1:
                strokes.append(points)

        return strokes


class GcodeGenerator:
    """Gcode生成器 - 将笔画转化为Gcode命令"""

    def __init__(
        self,
        work_area_width: float = 217.0,
        work_area_height: float = 299.0,
        z_up: float = 5.0,
        z_down: float = 0.0,
        feed_rate: float = 3000.0
    ):
        """
        初始化Gcode生成器

        Args:
            work_area_width: 工作区宽度（毫米）
            work_area_height: 工作区高度（毫米）
            z_up: 抬笔高度（毫米）
            z_down: 下笔高度（毫米）
            feed_rate: 进给速度（毫米/分钟）
        """
        self.work_area_width = work_area_width
        self.work_area_height = work_area_height
        self.z_up = z_up
        self.z_down = z_down
        self.feed_rate = feed_rate

        # Gcode命令列表
        self.gcode_lines: List[str] = []

    def generate_gcode(
        self,
        strokes: List[Stroke],
        image_width: int,
        image_height: int,
        margin_x: float = 10.0,
        margin_y: float = 10.0
    ) -> str:
        """
        生成Gcode

        Args:
            strokes: 笔画列表
            image_width: 图像宽度（像素）
            image_height: 图像高度（像素）
            margin_x: X方向边距（毫米）
            margin_y: Y方向边距（毫米）

        Returns:
            Gcode字符串
        """
        self.gcode_lines = []

        # 添加头部
        self._add_header()

        # 计算可写区域
        write_width = self.work_area_width - 2 * margin_x
        write_height = self.work_area_height - 2 * margin_y

        # 处理每个笔画
        for stroke in strokes:
            if not stroke.points:
                continue

            # 移动到笔画起点（抬笔）
            first_point = stroke.points[0]
            phys_x = margin_x + (first_point.x / image_width) * write_width
            phys_y = margin_y + (first_point.y / image_height) * write_height

            # Y轴翻转（图像坐标系与物理坐标系不同）
            phys_y = self.work_area_height - phys_y

            self._add_move(phys_x, phys_y)

            # 如果是书写笔画，下笔并绘制
            if stroke.is_write:
                self._add_pen_down()

                for point in stroke.points[1:]:
                    phys_x = margin_x + (point.x / image_width) * write_width
                    phys_y = margin_y + (point.y / image_height) * write_height
                    phys_y = self.work_area_height - phys_y

                    self._add_draw(phys_x, phys_y)

                # 绘制完笔画，抬笔
                self._add_pen_up()

        # 添加尾部
        self._add_footer()

        return '\n'.join(self.gcode_lines)

    def _add_header(self):
        """添加Gcode头部"""
        self.gcode_lines.append("; Auto-generated Gcode")
        self.gcode_lines.append("G21 ; Set units to millimeters")
        self.gcode_lines.append("G90 ; Use absolute coordinates")
        self.gcode_lines.append(f"G1 Z{self.z_up} F{self.feed_rate} ; Lift pen")
        self.gcode_lines.append("")

    def _add_footer(self):
        """添加Gcode尾部"""
        self.gcode_lines.append("")
        self.gcode_lines.append(f"G1 Z{self.z_up} ; Lift pen")
        self.gcode_lines.append("G0 X0 Y0 ; Return to origin")
        self.gcode_lines.append("M2 ; End of program")

    def _add_move(self, x: float, y: float):
        """添加移动命令"""
        self.gcode_lines.append(f"G0 X{x:.3f} Y{y:.3f}")

    def _add_draw(self, x: float, y: float):
        """添加绘制命令"""
        self.gcode_lines.append(f"G1 X{x:.3f} Y{y:.3f} F{self.feed_rate}")

    def _add_pen_up(self):
        """添加抬笔命令"""
        self.gcode_lines.append(f"G1 Z{self.z_up} F{self.feed_rate}")

    def _add_pen_down(self):
        """添加下笔命令"""
        self.gcode_lines.append(f"G1 Z{self.z_down} F{self.feed_rate}")

    def save_gcode(self, gcode: str, file_path: str):
        """
        保存Gcode到文件

        Args:
            gcode: Gcode字符串
            file_path: 保存路径
        """
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(gcode)
        print(f"✓ Gcode已保存到: {file_path}")


class WriterMachine:
    """写字机控制器 - 整合所有功能"""

    def __init__(
        self,
        chinese_font_path: Optional[str] = None,
        english_font_path: Optional[str] = None,
        work_area_width: float = 217.0,
        work_area_height: float = 299.0
    ):
        """
        初始化写字机控制器

        Args:
            chinese_font_path: 中文字体路径
            english_font_path: 英文字体路径
            work_area_width: 工作区宽度（毫米）
            work_area_height: 工作区高度（毫米）
        """
        self.renderer = TextRenderer(chinese_font_path, english_font_path)
        self.skeletonizer = Skeletonizer()
        self.gcode_generator = GcodeGenerator(work_area_width, work_area_height)

        self.work_area_width = work_area_width
        self.work_area_height = work_area_height

    def write_text(
        self,
        text: str,
        use_handright: bool = False,
        save_gcode_path: Optional[str] = None,
        save_image_path: Optional[str] = None
    ) -> str:
        """
        将文字转换为Gcode

        Args:
            text: 要书写的文字
            use_handright: 是否使用Handright渲染手写体
            save_gcode_path: Gcode保存路径（可选）
            save_image_path: 渲染图像保存路径（可选）

        Returns:
            Gcode字符串
        """
        print(f"正在渲染文字: {text}")

        # 1. 渲染文字
        if use_handright and self._has_chinese(text):
            rendered_image = self.renderer.render_text_with_handright(text)
        else:
            rendered_image = self.renderer.render_text(text)

        # 保存渲染图像
        if save_image_path:
            cv2.imwrite(save_image_path, rendered_image)
            print(f"✓ 渲染图像已保存到: {save_image_path}")

        # 2. 骨架化
        print("正在进行骨架化...")
        skeleton = self.skeletonizer.skeletonize(rendered_image)

        # 3. 提取笔画
        print("正在提取笔画...")
        stroke_points = self.skeletonizer.extract_strokes(skeleton)

        # 转换为Stroke对象
        strokes = []
        for points in stroke_points:
            gcode_points = [
                GcodePoint(x=float(p[0]), y=float(p[1]), is_move=False)
                for p in points
            ]
            strokes.append(Stroke(points=gcode_points, is_write=True))

        print(f"✓ 提取了 {len(strokes)} 个笔画")

        # 4. 生成Gcode
        print("正在生成Gcode...")
        image_height, image_width = rendered_image.shape[:2]

        gcode = self.gcode_generator.generate_gcode(
            strokes=strokes,
            image_width=image_width,
            image_height=image_height
        )

        # 保存Gcode
        if save_gcode_path:
            self.gcode_generator.save_gcode(gcode, save_gcode_path)

        return gcode

    def _has_chinese(self, text: str) -> bool:
        """检查文本是否包含中文字符"""
        return bool(re.search(r'[\u4e00-\u9fff]', text))


class MachineController:
    """机器控制器 - 通过串口控制写字机"""

    def __init__(self, port: str = 'COM3', baudrate: int = 115200):
        """
        初始化机器控制器

        Args:
            port: 串口
            baudrate: 波特率
        """
        self.port = port
        self.baudrate = baudrate
        self.serial_connection = None

    def connect(self) -> bool:
        """
        连接到写字机

        Returns:
            是否成功连接
        """
        try:
            import serial
            self.serial_connection = serial.Serial(self.port, self.baudrate, timeout=5)
            print(f"✓ 已连接到 {self.port}")
            return True
        except ImportError:
            print("错误: pyserial未安装")
            print("安装命令: pip install pyserial")
            return False
        except Exception as e:
            print(f"连接失败: {e}")
            return False

    def disconnect(self):
        """断开连接"""
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.close()
            print("✓ 已断开连接")

    def send_gcode(self, gcode: str, line_delay: float = 0.1) -> bool:
        """
        发送Gcode到写字机

        Args:
            gcode: Gcode字符串
            line_delay: 每行之间的延迟（秒）

        Returns:
            是否成功发送
        """
        if not self.serial_connection or not self.serial_connection.is_open:
            print("错误: 未连接到写字机")
            return False

        try:
            lines = gcode.split('\n')

            for i, line in enumerate(lines):
                # 跳过空行和注释
                line = line.strip()
                if not line or line.startswith(';'):
                    continue

                # 发送命令
                self.serial_connection.write((line + '\n').encode('utf-8'))

                # 显示进度
                if (i + 1) % 10 == 0:
                    print(f"已发送 {i + 1}/{len(lines)} 行...")

                # 延迟
                import time
                time.sleep(line_delay)

            print(f"✓ 已发送 {len(lines)} 行Gcode命令")
            return True

        except Exception as e:
            print(f"发送Gcode失败: {e}")
            return False

    def __enter__(self):
        """上下文管理器入口"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        self.disconnect()


def main():
    """测试函数"""
    print("=" * 70)
    print("写字模块测试")
    print("=" * 70)

    # 创建写字机控制器
    writer = WriterMachine()

    # 测试写字
    text = "Hello World"
    print(f"\n1. 测试写字: {text}")

    gcode = writer.write_text(
        text=text,
        use_handright=False,
        save_gcode_path="test.gcode",
        save_image_path="test_rendered.png"
    )

    print("\n✓ 测试完成")
    print("\n生成的文件：")
    print("- test.gcode: Gcode文件")
    print("- test_rendered.png: 渲染图像")

    # 测试中文
    text_cn = "你好世界"
    print(f"\n2. 测试中文: {text_cn}")

    gcode_cn = writer.write_text(
        text=text_cn,
        use_handright=True,
        save_gcode_path="test_cn.gcode",
        save_image_path="test_cn_rendered.png"
    )

    print("\n✓ 测试完成")
    print("\n生成的文件：")
    print("- test_cn.gcode: Gcode文件")
    print("- test_cn_rendered.png: 渲染图像")

    print("\n使用说明：")
    print("1. 将Gcode文件发送到写字机控制器（如FluidNC）")
    print("2. 使用串口或网络连接到写字机")
    print("3. 示例代码：")
    print("""
    # 方法1: 保存Gcode文件后手动发送
    writer.write_text("Hello", save_gcode_path="output.gcode")

    # 方法2: 通过串口直接控制
    controller = MachineController(port='COM3')
    if controller.connect():
        gcode = writer.write_text("Hello")
        controller.send_gcode(gcode)
        controller.disconnect()
    """)

    print("\n" + "=" * 70)


if __name__ == '__main__':
    main()
