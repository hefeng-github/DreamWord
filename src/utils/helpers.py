"""
智能写字机系统 - 通用工具函数
"""

import os
import json
import base64
from pathlib import Path
from typing import Any, Optional, Union
import numpy as np


def ensure_directory(path: Union[str, Path]) -> Path:
    """
    确保目录存在，如果不存在则创建
    
    Args:
        path: 目录路径
        
    Returns:
        Path 对象
    """
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_json(path: Union[str, Path]) -> Any:
    """
    加载 JSON 文件
    
    Args:
        path: JSON 文件路径
        
    Returns:
        解析后的数据
    """
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(data: Any, path: Union[str, Path], indent: int = 2) -> None:
    """
    保存数据到 JSON 文件
    
    Args:
        data: 要保存的数据
        path: 保存路径
        indent: 缩进空格数
    """
    path = Path(path)
    ensure_directory(path.parent)
    
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=indent)


def image_to_base64(image: np.ndarray, format: str = 'PNG') -> str:
    """
    将图像转换为 Base64 字符串
    
    Args:
        image: OpenCV 图像数组
        format: 图像格式 (PNG, JPEG 等)
        
    Returns:
        Base64 字符串
    """
    import cv2
    
    _, buffer = cv2.imencode(f'.{format.lower()}', image)
    return base64.b64encode(buffer).decode('utf-8')


def base64_to_image(base64_string: str) -> np.ndarray:
    """
    将 Base64 字符串转换为图像
    
    Args:
        base64_string: Base64 字符串
        
    Returns:
        OpenCV 图像数组
    """
    import cv2
    
    image_data = base64.b64decode(base64_string)
    nparr = np.frombuffer(image_data, np.uint8)
    return cv2.imdecode(nparr, cv2.IMREAD_COLOR)


def sanitize_filename(filename: str) -> str:
    """
    清理文件名，移除非法字符
    
    Args:
        filename: 原始文件名
        
    Returns:
        清理后的文件名
    """
    import re
    # 只保留字母、数字、中文、下划线和点
    return re.sub(r'[^\w\u4e00-\u9fff.-]', '_', filename)


def get_project_root() -> Path:
    """
    获取项目根目录
    
    Returns:
        项目根目录的 Path 对象
    """
    return Path(__file__).parent.parent.parent
