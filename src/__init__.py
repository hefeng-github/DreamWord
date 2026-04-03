"""
智能写字机系统

一个集成单词查询、自动查词注释、智能抄写等功能的写字机控制系统
"""

__version__ = "1.0.0"
__author__ = "Smart Writer Team"

from src.core import (
    GcodePoint,
    Stroke,
    WordEntry,
    LookupResult,
    OCRResult,
    WordPosition,
    Annotation,
    Line,
    WriteArea,
    TextLayout,
    PrinterModel,
    SystemConfig
)

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
