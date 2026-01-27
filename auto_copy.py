"""
自动抄写模块 - 识别横线本并自动抄写文字

功能：
1. 输入横线本图片，进行图像矫正
2. 识别横线及可写区域
3. 对要抄写的文字进行排版
4. 生成书写Gcode
"""

import cv2
import numpy as np
from pathlib import Path
from typing import List, Tuple, Optional
from dataclasses import dataclass
import re

try:
    import torch
    from paddleocr import PaddleOCR
    PADDLEOCR_AVAILABLE = True
except ImportError:
    PADDLEOCR_AVAILABLE = False
    print("警告: PaddleOCR未安装")

from calibration import Calibrator, ImageUnwarp
from writer import WriterMachine


@dataclass
class Line:
    """横线"""
    x1: float
    y1: float
    x2: float
    y2: float
    thickness: float = 1.0


@dataclass
class WriteArea:
    """可写区域（两横线之间）"""
    top_line: Line
    bottom_line: Line
    y_start: float  # 起始Y坐标
    y_end: float  # 结束Y坐标
    x_start: float  # 起始X坐标
    x_end: float  # 结束X坐标


@dataclass
class TextLayout:
    """文字布局"""
    text: str
    x: float  # X坐标（毫米）
    y: float  # Y坐标（毫米）
    font_size: float  # 字体大小


class LineDetector:
    """横线检测器"""

    def __init__(self, min_line_length: float = 100, max_line_gap: float = 10):
        """
        初始化横线检测器

        Args:
            min_line_length: 最小线段长度（像素）
            max_line_gap: 最大线段间隙（像素）
        """
        self.min_line_length = min_line_length
        self.max_line_gap = max_line_gap

    def detect_lines(self, image: np.ndarray) -> List[Line]:
        """
        检测图像中的横线

        Args:
            image: 输入图像

        Returns:
            横线列表
        """
        # 转换为灰度图
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        # 二值化
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # 使用霍夫变换检测直线
        lines = cv2.HoughLinesP(
            binary,
            rho=1,
            theta=np.pi / 180,
            threshold=50,
            minLineLength=self.min_line_length,
            maxLineGap=self.max_line_gap
        )

        if lines is None:
            print("未检测到横线")
            return []

        # 过滤出接近水平的线（角度在±10度以内）
        detected_lines = []
        for line in lines:
            x1, y1, x2, y2 = line[0]

            # 计算角度
            angle = np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi

            # 只保留接近水平的线
            if abs(angle) < 10:
                detected_lines.append(Line(
                    x1=float(x1),
                    y1=float(y1),
                    x2=float(x2),
                    y2=float(y2)
                ))

        print(f"✓ 检测到 {len(detected_lines)} 条横线")
        return detected_lines

    def merge_lines(self, lines: List[Line], y_threshold: float = 5.0) -> List[Line]:
        """
        合并相近的横线

        Args:
            lines: 横线列表
            y_threshold: Y坐标阈值（像素）

        Returns:
            合并后的横线列表
        """
        if not lines:
            return []

        # 按Y坐标排序
        sorted_lines = sorted(lines, key=lambda l: l.y1)

        # 合并
        merged = []
        current_line = sorted_lines[0]

        for line in sorted_lines[1:]:
            # 如果Y坐标相近，合并
            if abs(line.y1 - current_line.y1) < y_threshold:
                # 扩展X范围
                current_line.x1 = min(current_line.x1, line.x1)
                current_line.x2 = max(current_line.x2, line.x2)
            else:
                # 否则，添加当前线并开始新线
                merged.append(current_line)
                current_line = line

        merged.append(current_line)

        print(f"✓ 合并后剩余 {len(merged)} 条横线")
        return merged


class WriteAreaExtractor:
    """可写区域提取器"""

    def __init__(self, min_area_height: float = 20, min_area_width: float = 50):
        """
        初始化可写区域提取器

        Args:
            min_area_height: 最小区域高度（像素）
            min_area_width: 最小区域宽度（像素）
        """
        self.min_area_height = min_area_height
        self.min_area_width = min_area_width

    def extract_areas(self, lines: List[Line], image_width: int) -> List[WriteArea]:
        """
        从横线中提取可写区域

        Args:
            lines: 横线列表（按Y坐标排序）
            image_width: 图像宽度

        Returns:
            可写区域列表
        """
        if len(lines) < 2:
            print("横线数量不足，无法提取可写区域")
            return []

        areas = []

        # 提取相邻横线之间的区域
        for i in range(len(lines) - 1):
            top_line = lines[i]
            bottom_line = lines[i + 1]

            # 计算Y坐标
            y_start = top_line.y1
            y_end = bottom_line.y1

            # 检查高度
            height = y_end - y_start
            if height < self.min_area_height:
                continue

            # 计算X坐标（取两条线的交集）
            x_start = max(top_line.x1, bottom_line.x1)
            x_end = min(top_line.x2, bottom_line.x2)

            # 检查宽度
            width = x_end - x_start
            if width < self.min_area_width:
                continue

            # 边界检查
            x_start = max(0, x_start)
            x_end = min(image_width, x_end)

            areas.append(WriteArea(
                top_line=top_line,
                bottom_line=bottom_line,
                y_start=y_start,
                y_end=y_end,
                x_start=x_start,
                x_end=x_end
            ))

        print(f"✓ 提取了 {len(areas)} 个可写区域")
        return areas


class TextLayoutEngine:
    """文字排版引擎"""

    def __init__(
        self,
        char_width_ratio: float = 0.6,
        line_height_ratio: float = 0.8,
        margin: float = 5.0
    ):
        """
        初始化文字排版引擎

        Args:
            char_width_ratio: 字符宽度比例（相对于区域高度）
            line_height_ratio: 行高比例（相对于区域高度）
            margin: 边距（像素）
        """
        self.char_width_ratio = char_width_ratio
        self.line_height_ratio = line_height_ratio
        self.margin = margin

    def layout_text(
        self,
        text: str,
        areas: List[WriteArea],
        calibrator: Calibrator
    ) -> List[TextLayout]:
        """
        对文字进行排版

        Args:
            text: 要抄写的文字
            areas: 可写区域列表
            calibrator: 校准器

        Returns:
            文字布局列表
        """
        layouts = []

        # 分词（按空格和标点）
        words = self._split_text(text)

        current_word_index = 0
        current_x = 0

        for area in areas:
            if current_word_index >= len(words):
                break

            # 计算区域参数
            area_height = area.y_end - area.y_start
            area_width = area.x_end - area.x_start

            # 计算字体大小（基于区域高度）
            font_size = area_height * self.line_height_ratio

            # 计算字符宽度
            char_width = font_size * self.char_width_ratio

            # 起始X坐标
            current_x = area.x_start + self.margin

            # 计算可容纳的字符数
            max_chars = int((area_width - 2 * self.margin) / char_width)

            # 放置字符
            for _ in range(max_chars):
                if current_word_index >= len(words):
                    break

                word = words[current_word_index]

                # 计算物理坐标
                img_x = current_x
                img_y = area.y_start + area_height / 2

                try:
                    phys_x, phys_y = calibrator.image_to_physical((img_x, img_y))
                except Exception:
                    # 如果校准失败，使用图像坐标
                    phys_x, phys_y = img_x, img_y

                # 添加布局
                layouts.append(TextLayout(
                    text=word,
                    x=phys_x,
                    y=phys_y,
                    font_size=font_size
                ))

                # 更新位置
                current_x += char_width * len(word)
                current_word_index += 1

        # 如果还有剩余文字，添加到最后一行
        if current_word_index < len(words):
            remaining_text = ''.join(words[current_word_index:])
            print(f"警告: 文字未完全放置，剩余 {len(remaining_text)} 个字符")

        print(f"✓ 排版完成，共 {len(layouts)} 个字符")
        return layouts

    def _split_text(self, text: str) -> List[str]:
        """
        分割文本

        Args:
            text: 输入文本

        Returns:
            字符/单词列表
        """
        # 检查是否包含中文
        has_chinese = bool(re.search(r'[\u4e00-\u9fff]', text))

        if has_chinese:
            # 中文按字符分割
            return list(text.replace(' ', ''))
        else:
            # 英文按单词分割
            words = re.findall(r'\w+|\s+', text)
            # 过滤空格
            return [w for w in words if not w.isspace()]


class AutoCopy:
    """自动抄写器 - 整合所有功能"""

    def __init__(
        self,
        work_area_width: float = 217.0,
        work_area_height: float = 299.0
    ):
        """
        初始化自动抄写器

        Args:
            work_area_width: 工作区宽度（毫米）
            work_area_height: 工作区高度（毫米）
        """
        self.line_detector = LineDetector()
        self.area_extractor = WriteAreaExtractor()
        self.layout_engine = TextLayoutEngine()
        self.writer = WriterMachine(work_area_width=work_area_width, work_area_height=work_area_height)
        self.calibrator = Calibrator()
        self.unwarper = ImageUnwarp()

    def copy_text(
        self,
        notebook_image_path: str,
        text: str,
        calibration_path: Optional[str] = None,
        save_gcode_path: Optional[str] = None,
        save_layout_image: Optional[str] = None
    ) -> bool:
        """
        自动抄写文字

        Args:
            notebook_image_path: 横线本图片路径
            text: 要抄写的文字
            calibration_path: 校准数据路径
            save_gcode_path: Gcode保存路径
            save_layout_image: 布局图像保存路径

        Returns:
            是否成功
        """
        # 1. 加载校准数据
        if calibration_path:
            self.calibrator.load_calibration(calibration_path)
        else:
            print("警告: 未提供校准数据，将使用图像坐标")
            self.calibrator.transformation_matrix = np.eye(3)

        # 2. 读取图像
        image = cv2.imread(notebook_image_path)
        if image is None:
            print(f"错误: 无法读取图像 {notebook_image_path}")
            return False

        image_height, image_width = image.shape[:2]

        # 3. 图像矫正
        print("\n正在矫正图像...")
        unwarp_image = self.unwarper.unwarp_image(image)

        # 4. 检测横线
        print("\n正在检测横线...")
        lines = self.line_detector.detect_lines(unwarp_image)

        if not lines:
            print("未检测到横线，无法继续")
            return False

        # 5. 合并横线
        print("\n正在合并横线...")
        merged_lines = self.line_detector.merge_lines(lines)

        # 6. 提取可写区域
        print("\n正在提取可写区域...")
        areas = self.area_extractor.extract_areas(merged_lines, image_width)

        if not areas:
            print("未找到可写区域")
            return False

        print(f"✓ 找到 {len(areas)} 个可写区域")

        # 7. 排版文字
        print("\n正在排版文字...")
        layouts = self.layout_engine.layout_text(text, areas, self.calibrator)

        if not layouts:
            print("排版失败")
            return False

        # 8. 绘制布局预览
        if save_layout_image:
            self._draw_layout(image, layouts, save_layout_image)

        # 9. 生成书写Gcode
        if save_gcode_path:
            print("\n正在生成书写Gcode...")
            self._generate_writing_gcode(layouts, save_gcode_path)

        return True

    def _draw_layout(
        self,
        image: np.ndarray,
        layouts: List[TextLayout],
        save_path: str
    ):
        """
        绘制布局预览

        Args:
            image: 图像
            layouts: 布局列表
            save_path: 保存路径
        """
        preview = image.copy()

        for layout in layouts:
            # 尝试将物理坐标转换回图像坐标
            try:
                img_x, img_y = self.calibrator.physical_to_image((layout.x, layout.y))
            except Exception:
                img_x, img_y = layout.x, layout.y

            # 绘制文字
            cv2.putText(
                preview,
                layout.text,
                (int(img_x), int(img_y)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 255, 0),
                1
            )

        cv2.imwrite(save_path, preview)
        print(f"✓ 布局预览已保存到: {save_path}")

    def _generate_writing_gcode(self, layouts: List[TextLayout], save_path: str):
        """
        生成书写Gcode

        Args:
            layouts: 布局列表
            save_path: 保存路径
        """
        # 合并所有文字
        combined_text = ''.join([layout.text for layout in layouts])

        # 使用写字模块生成Gcode
        gcode = self.writer.write_text(
            text=combined_text,
            use_handright=False,
            save_gcode_path=save_path
        )

        print(f"✓ Gcode已保存到: {save_path}")


def main():
    """测试函数"""
    print("=" * 70)
    print("自动抄写模块测试")
    print("=" * 70)

    # 创建自动抄写器
    auto_copy = AutoCopy()

    print("\n使用示例:")
    print("""
    auto_copy = AutoCopy()

    # 自动抄写
    auto_copy.copy_text(
        notebook_image_path="notebook.jpg",
        text="Hello World 你好世界",
        calibration_path="calibration.pkl",
        save_gcode_path="copy.gcode",
        save_layout_image="copy_layout.jpg"
    )

    # 这将:
    # 1. 识别横线本中的横线
    # 2. 提取可写区域
    # 3. 对文字进行排版
    # 4. 生成书写Gcode
    # 5. 保存布局预览图
    """)

    print("\n" + "=" * 70)


if __name__ == '__main__':
    main()
