"""
自动查单词模块 - 自动识别试卷中的生词并书写释义

功能：
1. 输入试卷图片，进行图像矫正
2. 使用OCR识别文字和位置
3. 与已会单词数据库比对，找出不会的单词
4. 查询单词释义和音标
5. 计算书写位置（行间区域）
6. 自动避免重叠
7. 生成书写Gcode
"""

import cv2
import numpy as np
import sqlite3
import re
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from collections import defaultdict

try:
    import torch
    from paddleocr import PaddleOCR
    PADDLEOCR_AVAILABLE = True
except ImportError:
    PADDLEOCR_AVAILABLE = False
    print("警告: PaddleOCR未安装，OCR功能将不可用")

from word_lookup import WordLookup
from calibration import Calibrator, ImageUnwarp
from writer import WriterMachine, Stroke, GcodePoint


@dataclass
class OCRResult:
    """OCR识别结果"""
    text: str
    bbox: List[List[int]]  # [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
    confidence: float
    center: Tuple[float, float]  # 中心点坐标


@dataclass
class WordPosition:
    """单词位置信息"""
    word: str
    bbox: List[List[int]]
    center: Tuple[float, float]
    line_index: int  # 所在行


@dataclass
class Annotation:
    """标注信息"""
    text: str  # 要书写的文字（释义或音标）
    position: Tuple[float, float]  # 书写位置（物理坐标，毫米）
    is_phonetic: bool  # 是否为音标


class KnownWordsDatabase:
    """已知单词数据库"""

    def __init__(self, db_path: str = "known_words.db"):
        """
        初始化已知单词数据库

        Args:
            db_path: 数据库路径
        """
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 创建表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS known_words (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                word TEXT UNIQUE NOT NULL,
                add_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        conn.commit()
        conn.close()

    def add_word(self, word: str):
        """
        添加已知单词

        Args:
            word: 单词
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute('INSERT OR IGNORE INTO known_words (word) VALUES (?)', (word.lower(),))
            conn.commit()
        except Exception as e:
            print(f"添加单词失败: {e}")
        finally:
            conn.close()

    def is_known(self, word: str) -> bool:
        """
        检查单词是否已知

        Args:
            word: 单词

        Returns:
            是否已知
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute('SELECT 1 FROM known_words WHERE word = ?', (word.lower(),))
            result = cursor.fetchone()
            return result is not None
        except Exception as e:
            print(f"检查单词失败: {e}")
            return False
        finally:
            conn.close()

    def remove_word(self, word: str):
        """
        移除已知单词

        Args:
            word: 单词
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute('DELETE FROM known_words WHERE word = ?', (word.lower(),))
            conn.commit()
        except Exception as e:
            print(f"移除单词失败: {e}")
        finally:
            conn.close()

    def get_all_words(self) -> List[str]:
        """
        获取所有已知单词

        Returns:
            单词列表
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute('SELECT word FROM known_words')
            words = [row[0] for row in cursor.fetchall()]
            return words
        except Exception as e:
            print(f"获取单词列表失败: {e}")
            return []
        finally:
            conn.close()


class TextExtractor:
    """文本提取器 - 使用OCR"""

    def __init__(self, use_angle_cls: bool = True, lang: str = 'en'):
        """
        初始化文本提取器

        Args:
            use_angle_cls: 是否使用方向分类器
            lang: 语言（en=英文, ch=中文）
        """
        if not PADDLEOCR_AVAILABLE:
            print("错误: PaddleOCR未安装")
            self.ocr = None
            return

        try:
            print("正在初始化PaddleOCR...")
            self.ocr = PaddleOCR(
                use_angle_cls=use_angle_cls,
                lang=lang,
                show_log=False
            )
            print("✓ PaddleOCR初始化成功")
        except Exception as e:
            print(f"PaddleOCR初始化失败: {e}")
            self.ocr = None

        # 图像矫正器
        self.unwarper = ImageUnwarp()

    def extract_text(self, image: np.ndarray, unwarp: bool = True) -> List[OCRResult]:
        """
        从图像中提取文本

        Args:
            image: 输入图像
            unwarp: 是否进行图像矫正

        Returns:
            OCR结果列表
        """
        if self.ocr is None:
            print("错误: OCR未初始化")
            return []

        # 图像矫正
        if unwarp:
            image = self.unwarper.unwarp_image(image)

        try:
            # 执行OCR
            result = self.ocr.ocr(image, cls=True)

            if not result or not result[0]:
                print("未检测到文字")
                return []

            # 解析结果
            ocr_results = []
            for line in result[0]:
                bbox = line[0]  # 边界框
                text_info = line[1]  # (文本, 置信度)

                text = text_info[0]
                confidence = text_info[1]

                # 计算中心点
                points = np.array(bbox)
                center_x = float(np.mean(points[:, 0]))
                center_y = float(np.mean(points[:, 1]))

                ocr_results.append(OCRResult(
                    text=text,
                    bbox=bbox,
                    confidence=confidence,
                    center=(center_x, center_y)
                ))

            print(f"✓ 识别到 {len(ocr_results)} 个文本块")
            return ocr_results

        except Exception as e:
            print(f"OCR识别失败: {e}")
            return []

    def filter_english_words(self, ocr_results: List[OCRResult]) -> List[OCRResult]:
        """
        过滤出英文单词

        Args:
            ocr_results: OCR结果列表

        Returns:
            英文单词的OCR结果
        """
        english_words = []

        for result in ocr_results:
            # 使用正则表达式提取英文单词
            words = re.findall(r'\b[a-zA-Z]+\b', result.text)

            for word in words:
                # 过滤掉单个字母和常见词
                if len(word) > 1 and not self._is_common_word(word):
                    # 创建新的OCR结果
                    english_words.append(OCRResult(
                        text=word,
                        bbox=result.bbox,
                        confidence=result.confidence,
                        center=result.center
                    ))

        return english_words

    def _is_common_word(self, word: str) -> bool:
        """检查是否为常见词"""
        common_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to',
            'of', 'for', 'with', 'by', 'from', 'as', 'is', 'was', 'are',
            'been', 'be', 'have', 'has', 'had', 'do', 'does', 'did'
        }
        return word.lower() in common_words


class PositionCalculator:
    """位置计算器 - 计算书写位置"""

    def __init__(self, line_spacing: float = 10.0, char_spacing: float = 2.0):
        """
        初始化位置计算器

        Args:
            line_spacing: 行间距（毫米）
            char_spacing: 字符间距（毫米）
        """
        self.line_spacing = line_spacing
        self.char_spacing = char_spacing

    def group_by_lines(self, word_positions: List[WordPosition]) -> Dict[int, List[WordPosition]]:
        """
        按行分组单词

        Args:
            word_positions: 单词位置列表

        Returns:
            {行号: [单词位置列表]}
        """
        lines = defaultdict(list)

        if not word_positions:
            return lines

        # 按Y坐标排序
        sorted_words = sorted(word_positions, key=lambda w: w.center[1])

        # 分组（Y坐标相近的视为同一行）
        current_line = 0
        current_y = sorted_words[0].center[1]

        for word_pos in sorted_words:
            # 如果Y坐标差距大于阈值，认为是新的一行
            if abs(word_pos.center[1] - current_y) > 20:  # 20像素阈值
                current_line += 1
                current_y = word_pos.center[1]

            word_pos.line_index = current_line
            lines[current_line].append(word_pos)

        return dict(lines)

    def calculate_annotation_positions(
        self,
        word_positions: List[WordPosition],
        calibrator: Calibrator
    ) -> List[Annotation]:
        """
        计算标注位置（释义和音标）

        Args:
            word_positions: 单词位置列表
            calibrator: 校准器

        Returns:
            标注列表
        """
        annotations = []

        # 按行分组
        lines = self.group_by_lines(word_positions)

        # 为每个单词计算标注位置
        for line_words in lines.values():
            for i, word_pos in enumerate(line_words):
                # 获取物理坐标
                phys_x, phys_y = calibrator.image_to_physical(word_pos.center)

                # 计算标注位置（在单词下方）
                annotation_y = phys_y + self.line_spacing

                # 音标位置（在单词正下方）
                phonetic_position = (phys_x, annotation_y)

                # 释义位置（在音标下方）
                definition_position = (phys_x, annotation_y + self.line_spacing)

                annotations.append(Annotation(
                    text="",  # 稍后填充
                    position=phonetic_position,
                    is_phonetic=True
                ))

                annotations.append(Annotation(
                    text="",  # 稍后填充
                    position=definition_position,
                    is_phonetic=False
                ))

        return annotations

    def avoid_overlap(self, annotations: List[Annotation]) -> List[Annotation]:
        """
        避免标注重叠

        Args:
            annotations: 标注列表

        Returns:
            调整后的标注列表
        """
        # 简化实现：如果Y坐标太接近，向下移动
        adjusted = annotations.copy()

        for i in range(len(adjusted)):
            for j in range(i + 1, len(adjusted)):
                ann1 = adjusted[i]
                ann2 = adjusted[j]

                # 检查Y坐标是否太接近
                if abs(ann1.position[1] - ann2.position[1]) < self.line_spacing:
                    # 移动下面的那个
                    if ann1.position[1] < ann2.position[1]:
                        new_y = ann1.position[1] + self.line_spacing
                        ann2.position = (ann2.position[0], new_y)
                    else:
                        new_y = ann2.position[1] + self.line_spacing
                        ann1.position = (ann1.position[0], new_y)

        return adjusted


class AutoLookup:
    """自动查单词器 - 整合所有功能"""

    def __init__(
        self,
        known_words_db: str = "known_words.db",
        work_area_width: float = 217.0,
        work_area_height: float = 299.0
    ):
        """
        初始化自动查单词器

        Args:
            known_words_db: 已知单词数据库路径
            work_area_width: 工作区宽度（毫米）
            work_area_height: 工作区高度（毫米）
        """
        self.known_words_db = KnownWordsDatabase(known_words_db)
        self.text_extractor = TextExtractor()
        self.word_lookup = WordLookup(use_semantic_search=True)
        self.position_calculator = PositionCalculator()
        self.writer = WriterMachine(work_area_width=work_area_width, work_area_height=work_area_height)

        self.calibrator = Calibrator()

    def process_exam_image(
        self,
        image_path: str,
        calibration_path: Optional[str] = None,
        save_gcode_path: Optional[str] = None,
        save_annotated_image: Optional[str] = None
    ) -> bool:
        """
        处理试卷图片

        Args:
            image_path: 试卷图片路径
            calibration_path: 校准数据路径
            save_gcode_path: Gcode保存路径
            save_annotated_image: 标注图像保存路径

        Returns:
            是否成功
        """
        # 1. 加载校准数据
        if calibration_path:
            self.calibrator.load_calibration(calibration_path)
        else:
            print("警告: 未提供校准数据，将使用图像坐标")
            # 创建默认变换矩阵（1:1映射）
            self.calibrator.transformation_matrix = np.eye(3)

        # 2. 读取图像
        image = cv2.imread(image_path)
        if image is None:
            print(f"错误: 无法读取图像 {image_path}")
            return False

        # 3. OCR识别
        print("\n正在识别文字...")
        ocr_results = self.text_extractor.extract_text(image)

        if not ocr_results:
            print("未识别到文字")
            return False

        # 4. 过滤英文单词
        print("\n正在过滤英文单词...")
        english_ocr = self.text_extractor.filter_english_words(ocr_results)

        if not english_ocr:
            print("未找到英文单词")
            return False

        print(f"✓ 找到 {len(english_ocr)} 个英文单词")

        # 5. 转换为WordPosition
        word_positions = []
        for ocr_result in english_ocr:
            word_positions.append(WordPosition(
                word=ocr_result.text,
                bbox=ocr_result.bbox,
                center=ocr_result.center,
                line_index=0  # 稍后计算
            ))

        # 6. 查找不会的单词
        print("\n正在查找生词...")
        unknown_words = []
        for word_pos in word_positions:
            if not self.known_words_db.is_known(word_pos.word):
                unknown_words.append(word_pos)

        if not unknown_words:
            print("✓ 所有单词都已掌握！")
            return True

        print(f"✓ 找到 {len(unknown_words)} 个生词")

        # 7. 查询单词释义和音标
        print("\n正在查询单词释义...")
        annotations = []

        # 计算标注位置
        raw_annotations = self.position_calculator.calculate_annotation_positions(
            unknown_words,
            self.calibrator
        )

        # 避免重叠
        adjusted_annotations = self.position_calculator.avoid_overlap(raw_annotations)

        # 为每个生词查询释义
        for i, word_pos in enumerate(unknown_words):
            print(f"\n查询: {word_pos.word}")

            result = self.word_lookup.lookup(word_pos.word)

            if result.success:
                # 获取第一个释义
                definition = result.definitions[0] if result.definitions else ""
                phonetic = result.phonetic

                print(f"  音标: {phonetic}")
                print(f"  释义: {definition}")

                # 填充标注
                if i * 2 < len(adjusted_annotations):
                    adjusted_annotations[i * 2].text = phonetic

                if i * 2 + 1 < len(adjusted_annotations):
                    adjusted_annotations[i * 2 + 1].text = definition

                # 在图像上绘制
                if save_annotated_image:
                    self._draw_annotation(image, word_pos, phonetic, definition)
            else:
                print(f"  查询失败: {result.message}")

        # 保存标注图像
        if save_annotated_image:
            cv2.imwrite(save_annotated_image, image)
            print(f"\n✓ 标注图像已保存到: {save_annotated_image}")

        # 8. 生成书写Gcode
        if save_gcode_path:
            print("\n正在生成书写Gcode...")
            self._generate_writing_gcode(adjusted_annotations, save_gcode_path)

        return True

    def _draw_annotation(
        self,
        image: np.ndarray,
        word_pos: WordPosition,
        phonetic: str,
        definition: str
    ):
        """
        在图像上绘制标注

        Args:
            image: 图像
            word_pos: 单词位置
            phonetic: 音标
            definition: 释义
        """
        center = word_pos.center

        # 绘制音标
        cv2.putText(
            image,
            phonetic,
            (int(center[0]) - 20, int(center[1]) + 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 255, 0),
            1
        )

        # 绘制释义
        cv2.putText(
            image,
            definition,
            (int(center[0]) - 20, int(center[1]) + 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 0, 255),
            1
        )

    def _generate_writing_gcode(self, annotations: List[Annotation], save_path: str):
        """
        生成书写Gcode

        Args:
            annotations: 标注列表
            save_path: 保存路径
        """
        # 这里简化实现，实际应该将标注转换为笔画
        # 暂时创建一个空的Gcode文件
        gcode = "; 自动生成的标注Gcode\n"
        gcode += "G21 ; Set units to millimeters\n"
        gcode += "G90 ; Use absolute coordinates\n"

        for ann in annotations:
            if ann.text:
                x, y = ann.position
                gcode += f"\n; Writing: {ann.text} at ({x:.2f}, {y:.2f})\n"
                # 实际应该调用writer生成完整的书写Gcode

        gcode += "\nM2 ; End of program\n"

        with open(save_path, 'w', encoding='utf-8') as f:
            f.write(gcode)

        print(f"✓ Gcode已保存到: {save_path}")

    def add_known_words(self, words: List[str]):
        """
        批量添加已知单词

        Args:
            words: 单词列表
        """
        for word in words:
            self.known_words_db.add_word(word)
        print(f"✓ 已添加 {len(words)} 个已知单词")


def main():
    """测试函数"""
    print("=" * 70)
    print("自动查单词模块测试")
    print("=" * 70)

    # 创建自动查单词器
    auto_lookup = AutoLookup()

    # 测试添加已知单词
    print("\n1. 测试已知单词数据库...")
    auto_lookup.add_known_words(['hello', 'world', 'test'])

    # 测试处理试卷图片
    print("\n2. 测试处理试卷图片...")
    print("""
使用示例:

    auto_lookup = AutoLookup()

    # 添加已知单词
    auto_lookup.add_known_words(['hello', 'world', 'python'])

    # 处理试卷图片
    auto_lookup.process_exam_image(
        image_path="exam.jpg",
        calibration_path="calibration.pkl",
        save_gcode_path="annotations.gcode",
        save_annotated_image="exam_annotated.jpg"
    )

    # 这将:
    # 1. 识别试卷中的英文单词
    # 2. 与已知单词比对，找出生词
    # 3. 查询生词的释义和音标
    # 4. 计算书写位置
    # 5. 生成Gcode和标注图像
    """)

    print("\n" + "=" * 70)


if __name__ == '__main__':
    main()
