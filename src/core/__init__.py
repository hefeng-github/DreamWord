"""
智能写字机系统 - 核心包

提供基础数据结构和接口定义
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Any
from enum import Enum


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


@dataclass
class WordEntry:
    """单词条目数据类"""
    headword: str
    phonetics: List[str] = field(default_factory=list)
    definitions: List[str] = field(default_factory=list)
    chinese_definitions: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    base_form: Optional[str] = None
    pos: Optional[str] = None  # Part of Speech (词性)


@dataclass
class LookupResult:
    """查词结果数据类"""
    success: bool
    word: str
    phonetic: str = "N/A"
    definitions: List[str] = field(default_factory=list)
    base_form: Optional[str] = None
    pos: Optional[str] = None
    examples: List[str] = field(default_factory=list)
    message: Optional[str] = None
    all_entries: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = {
            'success': self.success,
            'word': self.word,
        }

        if self.success:
            result.update({
                'phonetic': self.phonetic,
                'definitions': self.definitions,
                'base_form': self.base_form or self.word,
                'pos': self.pos,
                'examples': self.examples
            })
            if self.all_entries:
                result['all_entries'] = self.all_entries
        else:
            result['message'] = self.message

        return result


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
    y_start: float  # 起始 Y 坐标
    y_end: float  # 结束 Y 坐标
    x_start: float  # 起始 X 坐标
    x_end: float  # 结束 X 坐标


@dataclass
class TextLayout:
    """文字布局"""
    text: str
    x: float  # X 坐标（毫米）
    y: float  # Y 坐标（毫米）
    font_size: float  # 字体大小


class PrinterModel(Enum):
    """支持的打印机型号"""
    A1MINI = "A1MINI"
    X1C = "X1C"
    P1P = "P1P"
    CUSTOM = "CUSTOM"


class SystemConfig:
    """系统配置"""
    
    # 硬件参数
    WORK_AREA_X = 217.0  # X 轴有效行程 (mm)
    WORK_AREA_Y = 299.0  # Y 轴有效行程 (mm)
    MARKER_SIZE_MM = 30.0  # ArUco 标记尺寸 (mm)
    
    # Z 轴参数
    Z_PEN_UP = 5.0  # 抬笔高度 (mm)
    Z_PEN_DOWN = 0.0  # 下笔高度 (mm)
    
    # 运动参数
    FEED_RATE = 3000  # 进给速度 (mm/min)
    
    # 默认字体路径
    CHINESE_FONT = "Fonts/FZZJ-DLHTJW.TTF"
    ENGLISH_FONT = "Fonts/NotoSansMath-Regular.ttf"
    
    # 数据库路径
    WORD_DETAILS_DB = "databases/word_details.db"
    KNOWN_WORDS_DB = "known_words.db"
    
    # 上传目录
    UPLOAD_FOLDER = "uploads"
    
    @classmethod
    def get_defaults(cls) -> Dict[str, Any]:
        """获取默认配置字典"""
        return {
            'work_area': {'x': cls.WORK_AREA_X, 'y': cls.WORK_AREA_Y},
            'marker_size_mm': cls.MARKER_SIZE_MM,
            'z_pen_up': cls.Z_PEN_UP,
            'z_pen_down': cls.Z_PEN_DOWN,
            'feed_rate': cls.FEED_RATE,
            'fonts': {
                'chinese': cls.CHINESE_FONT,
                'english': cls.ENGLISH_FONT
            },
            'databases': {
                'word_details': cls.WORD_DETAILS_DB,
                'known_words': cls.KNOWN_WORDS_DB
            },
            'upload_folder': cls.UPLOAD_FOLDER
        }


__all__ = [
    'GcodePoint',
    'Stroke',
    'WordEntry',
    'LookupResult',
    'OCRResult',
    'WordPosition',
    'Annotation',
    'Line',
    'WriteArea',
    'TextLayout',
    'PrinterModel',
    'SystemConfig'
]
