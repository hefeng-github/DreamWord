"""
功能模块包

包含所有核心功能模块：
- calibration: 校准模块
- writer: 写字模块
- word_lookup: 单词查询模块
- auto_lookup: 自动查词模块
- auto_copy: 自动抄写模块
"""

from .calibration import Calibrator, ArUcoMarkerGenerator, ImageUnwarp
from .writer import TextRenderer, Skeletonizer, GcodeGenerator, WriterMachine, MachineController
from .word_lookup import MDXParser, WordLookup
from .auto_lookup import AutoLookup, KnownWordsDatabase, TextExtractor, PositionCalculator
from .auto_copy import AutoCopy, LineDetector, WriteAreaExtractor, TextLayoutEngine

__all__ = [
    # Calibration
    'Calibrator',
    'ArUcoMarkerGenerator',
    'ImageUnwarp',
    
    # Writer
    'TextRenderer',
    'Skeletonizer',
    'GcodeGenerator',
    'WriterMachine',
    'MachineController',
    
    # Word Lookup
    'MDXParser',
    'WordLookup',
    
    # Auto Lookup
    'AutoLookup',
    'KnownWordsDatabase',
    'TextExtractor',
    'PositionCalculator',
    
    # Auto Copy
    'AutoCopy',
    'LineDetector',
    'WriteAreaExtractor',
    'TextLayoutEngine',
]
