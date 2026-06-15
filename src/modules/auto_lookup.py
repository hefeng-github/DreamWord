"""
自动查单词模块 - 自动识别试卷中的生词并书写释义

功能：
1. 输入试卷图片，进行图像矫正
2. 使用 OCR 识别文字和位置
3. 与已会单词数据库比对，找出不会的单词
4. 查询单词释义和音标
5. 计算书写位置（行间区域）
6. 自动避免重叠
7. 生成书写 Gcode
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
    print("警告：PaddleOCR 未安装，OCR 功能将不可用")

from src.modules.word_lookup import WordLookup
from src.modules.calibration import Calibrator, ImageUnwarp
from src.modules.writer import WriterMachine
from src.core import Stroke, GcodePoint


@dataclass
class OCRResult:
    """OCR 识别结果"""
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
            print(f"添加单词失败：{e}")
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
            print(f"检查单词失败：{e}")
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
            print(f"移除单词失败：{e}")
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
            print(f"获取单词列表失败：{e}")
            return []
        finally:
            conn.close()


class TextExtractor:
    """文本提取器 - 使用 OCR"""

    def __init__(self, use_angle_cls: bool = True, lang: str = 'en'):
        """
        初始化文本提取器

        Args:
            use_angle_cls: 是否使用方向分类器
            lang: 语言（en=英文，ch=中文）
        """
        if not PADDLEOCR_AVAILABLE:
            print("错误：PaddleOCR 未安装")
            self.ocr = None
            return

        try:
            print("正在初始化 PaddleOCR...")
            self.ocr = PaddleOCR(
                use_angle_cls=use_angle_cls,
                lang=lang,
                show_log=False
            )
            print("✓ PaddleOCR 初始化成功")
        except Exception as e:
            print(f"PaddleOCR 初始化失败：{e}")
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
            OCR 结果列表
        """
        if self.ocr is None:
            print("错误：OCR 未初始化")
            return []

        # 图像矫正
        if unwarp:
            image = self.unwarper.unwarp_image(image)

        try:
            # 执行 OCR
            result = self.ocr.ocr(image, cls=True)

            if not result or not result[0]:
                print("未检测到文字")
                return []

            # 解析结果
            ocr_results = []
            for line in result[0]:
                bbox = line[0]  # 边界框
                text_info = line[1]  # (文本，置信度)

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
            print(f"OCR 识别失败：{e}")
            return []

    def filter_english_words(self, ocr_results: List[OCRResult]) -> List[OCRResult]:
        """
        过滤出英文单词

        Args:
            ocr_results: OCR 结果列表

        Returns:
            英文单词的 OCR 结果
        """
        english_words = []

        for result in ocr_results:
            # 使用正则表达式提取英文单词
            words = re.findall(r'\b[a-zA-Z]+\b', result.text)

            for word in words:
                # 过滤掉单个字母和常见词
                if len(word) > 1 and not self._is_common_word(word):
                    # 创建新的 OCR 结果
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
            {行号：[单词位置列表]}
        """
        lines = defaultdict(list)

        if not word_positions:
            return lines

        # 按 Y 坐标排序
        sorted_words = sorted(word_positions, key=lambda w: w.center[1])

        # 分组（Y 坐标相近的视为同一行）
        current_line = 0
        current_y = sorted_words[0].center[1]

        for word_pos in sorted_words:
            # 如果 Y 坐标差距大于阈值，认为是新的一行
            if abs(word_pos.center[1] - current_y) > 20:  # 20 像素阈值
                current_line += 1
                current_y = word_pos.center[1]

            word_pos.line_index = current_line
            lines[current_line].append(word_pos)

        return dict(lines)

    def calculate_annotation_positions(
        self,
        word_positions: List[WordPosition],
        calibrator,
        only_phonetics: bool = False
    ):
        annotations = []

        lines = self.group_by_lines(word_positions)

        for line_words in lines.values():
            for i, word_pos in enumerate(line_words):
                phys_x, phys_y = calibrator.image_to_physical(*word_pos.center)

                annotation_y = phys_y + self.line_spacing

                phonetic_position = (phys_x, annotation_y)
                annotations.append(Annotation(
                    text="",
                    position=phonetic_position,
                    is_phonetic=True
                ))

                if not only_phonetics:
                    definition_position = (phys_x, annotation_y + self.line_spacing)
                    annotations.append(Annotation(
                        text="",
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
        # 简化实现：如果 Y 坐标太接近，向下移动
        adjusted = annotations.copy()

        for i in range(len(adjusted)):
            for j in range(i + 1, len(adjusted)):
                ann1 = adjusted[i]
                ann2 = adjusted[j]

                # 检查 Y 坐标是否太接近
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

    def _crop_image(self, image: np.ndarray, crop_x: int, crop_y: int,
                    crop_w: int, crop_h: int) -> np.ndarray:
        h, w = image.shape[:2]
        x1 = max(0, int(crop_x))
        y1 = max(0, int(crop_y))
        x2 = min(w, int(crop_x + crop_w))
        y2 = min(h, int(crop_y + crop_h))
        return image[y1:y2, x1:x2].copy()

    def _find_phrases(self, word_positions: List['WordPosition']) -> List['WordPosition']:
        if not word_positions:
            return word_positions

        sorted_words = sorted(word_positions, key=lambda w: (w.center[1], w.center[0]))

        lines = defaultdict(list)
        current_line = 0
        current_y = sorted_words[0].center[1]
        for w in sorted_words:
            if abs(w.center[1] - current_y) > 20:
                current_line += 1
                current_y = w.center[1]
            w.line_index = current_line
            lines[current_line].append(w)

        phrase_map = {}
        consumed = set()
        phrase_id = len(word_positions)

        for line_idx in lines:
            line_words = sorted(lines[line_idx], key=lambda w: w.center[0])
            for n in (3, 2):
                for i in range(len(line_words) - n + 1):
                    if any(id(line_words[i + j]) in consumed for j in range(n)):
                        continue
                    phrase_text = ' '.join(line_words[i + j].word for j in range(n))
                    result = self.word_lookup.lookup(phrase_text.lower())
                    if result and result.success and result.definitions:
                        all_x = []
                        all_y = []
                        for j in range(n):
                            word_obj = line_words[i + j]
                            all_x.extend([word_obj.bbox[k][0] for k in range(len(word_obj.bbox))])
                            all_y.extend([word_obj.bbox[k][1] for k in range(len(word_obj.bbox))])
                            consumed.add(id(word_obj))

                        merged_bbox = [
                            [min(all_x), min(all_y)],
                            [max(all_x), min(all_y)],
                            [max(all_x), max(all_y)],
                            [min(all_x), max(all_y)]
                        ]
                        phrase_wp = WordPosition(
                            word=phrase_text.lower(),
                            bbox=merged_bbox,
                            center=((min(all_x) + max(all_x)) / 2, (min(all_y) + max(all_y)) / 2),
                            line_index=line_idx
                        )
                        phrase_map[phrase_id] = phrase_wp
                        phrase_id += 1

        result_words = [w for w in word_positions if id(w) not in consumed]
        result_words.extend(phrase_map.values())
        return result_words

    def process_exam_image(
        self,
        image_path: str,
        calibration_path: Optional[str] = None,
        save_gcode_path: Optional[str] = None,
        save_annotated_image: Optional[str] = None,
        crop_x: Optional[int] = None,
        crop_y: Optional[int] = None,
        crop_w: Optional[int] = None,
        crop_h: Optional[int] = None,
        only_phonetics: bool = False
    ) -> bool:
        """
        处理试卷图片

        Args:
            image_path: 试卷图片路径
            calibration_path: 校准数据路径
            save_gcode_path: Gcode 保存路径
            save_annotated_image: 标注图像保存路径
            crop_x: 裁剪区域X坐标（像素）
            crop_y: 裁剪区域Y坐标（像素）
            crop_w: 裁剪区域宽度（像素）
            crop_h: 裁剪区域高度（像素）
            only_phonetics: 是否只写音标

        Returns:
            是否成功
        """
        # 1. 加载校准数据
        if calibration_path:
            self.calibrator.load_calibration(calibration_path)
        else:
            print("警告：未提供校准数据，将使用图像坐标")
            self.calibrator.transformation_matrix = np.eye(3)

        # 2. 读取图像
        image = cv2.imread(image_path)
        if image is None:
            print(f"错误：无法读取图像 {image_path}")
            return False

        full_image = image.copy()
        crop_offset_x = 0
        crop_offset_y = 0

        has_crop = all(v is not None for v in [crop_x, crop_y, crop_w, crop_h])
        if has_crop and crop_w > 0 and crop_h > 0:
            crop_offset_x = int(crop_x)
            crop_offset_y = int(crop_y)
            image = self._crop_image(image, crop_offset_x, crop_offset_y, int(crop_w), int(crop_h))
            print(f"✓ 已裁剪到区域: ({crop_offset_x}, {crop_offset_y}, {crop_w}, {crop_h})")

        # 3. OCR 识别
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

        # 5. 转换为 WordPosition
        word_positions = []
        for ocr_result in english_ocr:
            center_x = ocr_result.center[0] + crop_offset_x
            center_y = ocr_result.center[1] + crop_offset_y
            shifted_bbox = [[p[0] + crop_offset_x, p[1] + crop_offset_y] for p in ocr_result.bbox]
            word_positions.append(WordPosition(
                word=ocr_result.text,
                bbox=shifted_bbox,
                center=(center_x, center_y),
                line_index=0
            ))

        # 5.5 查找固定搭配（N-Gram）
        print("\n正在查找固定搭配...")
        word_positions = self._find_phrases(word_positions)
        print(f"✓ 处理后共 {len(word_positions)} 个词条（含固定搭配）")

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
            self.calibrator,
            only_phonetics=only_phonetics
        )

        # 避免重叠
        adjusted_annotations = self.position_calculator.avoid_overlap(raw_annotations)

        # 为每个生词查询释义
        for i, word_pos in enumerate(unknown_words):
            print(f"\n查询：{word_pos.word}")

            result = self.word_lookup.lookup(word_pos.word)

            if result.success:
                definition = result.definitions[0] if result.definitions else ""
                phonetic = result.phonetic

                print(f"  音标：{phonetic}")
                print(f"  释义：{definition}")

                if only_phonetics:
                    if i < len(adjusted_annotations):
                        adjusted_annotations[i].text = phonetic
                else:
                    if i * 2 < len(adjusted_annotations):
                        adjusted_annotations[i * 2].text = phonetic
                    if i * 2 + 1 < len(adjusted_annotations):
                        adjusted_annotations[i * 2 + 1].text = definition

                # 在图像上绘制（使用完整图像）
                if save_annotated_image:
                    self._draw_annotation(full_image, word_pos, phonetic, definition, only_phonetics)
            else:
                print(f"  查询失败：{result.message}")

        # 保存标注图像
        if save_annotated_image:
            cv2.imwrite(save_annotated_image, full_image)
            print(f"\n✓ 标注图像已保存到：{save_annotated_image}")

        # 8. 生成书写 Gcode
        if save_gcode_path:
            print("\n正在生成书写 Gcode...")
            self._generate_writing_gcode(adjusted_annotations, save_gcode_path)

        return True

    def _draw_annotation(
        self,
        image: np.ndarray,
        word_pos: WordPosition,
        phonetic: str,
        definition: str,
        only_phonetics: bool = False
    ):
        center = word_pos.center

        cv2.putText(
            image,
            phonetic,
            (int(center[0]) - 20, int(center[1]) + 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 255, 0),
            1
        )

        if not only_phonetics:
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
        生成书写 Gcode

        Args:
            annotations: 标注列表
            save_path: 保存路径
        """
        # 这里简化实现，实际应该将标注转换为笔画
        # 暂时创建一个空的 Gcode 文件
        gcode = "; 自动生成的标注 Gcode\n"
        gcode += "G21 ; Set units to millimeters\n"
        gcode += "G90 ; Use absolute coordinates\n"

        for ann in annotations:
            if ann.text:
                x, y = ann.position
                gcode += f"\n; Writing: {ann.text} at ({x:.2f}, {y:.2f})\n"
                # 实际应该调用 writer 生成完整的书写 Gcode

        gcode += "\nM2 ; End of program\n"

        with open(save_path, 'w', encoding='utf-8') as f:
            f.write(gcode)

        print(f"✓ Gcode 已保存到：{save_path}")

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
    # 5. 生成 Gcode 和标注图像
    """)

    print("\n" + "=" * 70)


if __name__ == '__main__':
    main()
