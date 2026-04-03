"""
智能写字机系统 - 配置管理
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class Settings:
    """系统配置类"""
    
    # 应用配置
    app_name: str = "智能写字机系统"
    version: str = "1.0.0"
    debug: bool = False
    
    # 服务器配置
    host: str = "127.0.0.1"
    port: int = 5000
    
    # 硬件参数
    work_area_x: float = 217.0  # X 轴有效行程 (mm)
    work_area_y: float = 299.0  # Y 轴有效行程 (mm)
    marker_size_mm: float = 30.0  # ArUco 标记尺寸 (mm)
    
    # Z 轴参数
    z_pen_up: float = 5.0  # 抬笔高度 (mm)
    z_pen_down: float = 0.0  # 下笔高度 (mm)
    
    # 运动参数
    feed_rate: int = 3000  # 进给速度 (mm/min)
    
    # 字体路径
    chinese_font: str = "Fonts/FZZJ-DLHTJW.TTF"
    english_font: str = "Fonts/NotoSansMath-Regular.ttf"
    
    # 数据库路径
    word_details_db: str = "databases/word_details.db"
    known_words_db: str = "known_words.db"
    
    # 上传目录
    upload_folder: str = "uploads"
    
    # 最大文件上传大小 (字节)
    max_content_length: int = 16 * 1024 * 1024  # 16MB
    
    # 功能开关
    enable_auto_lookup: bool = True
    enable_auto_copy: bool = True
    enable_ai_semantic: bool = False
    
    @classmethod
    def from_env(cls) -> 'Settings':
        """从环境变量加载配置"""
        settings = cls()
        
        # 服务器配置
        if env_host := os.getenv('APP_HOST'):
            settings.host = env_host
        if env_port := os.getenv('APP_PORT'):
            settings.port = int(env_port)
        if env_debug := os.getenv('APP_DEBUG'):
            settings.debug = env_debug.lower() in ('true', '1', 'yes')
        
        # 硬件参数
        if env_work_x := os.getenv('WORK_AREA_X'):
            settings.work_area_x = float(env_work_x)
        if env_work_y := os.getenv('WORK_AREA_Y'):
            settings.work_area_y = float(env_work_y)
        
        return settings
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'app': {
                'name': self.app_name,
                'version': self.version,
                'debug': self.debug
            },
            'server': {
                'host': self.host,
                'port': self.port
            },
            'hardware': {
                'work_area': {'x': self.work_area_x, 'y': self.work_area_y},
                'marker_size_mm': self.marker_size_mm,
                'z_pen_up': self.z_pen_up,
                'z_pen_down': self.z_pen_down,
                'feed_rate': self.feed_rate
            },
            'fonts': {
                'chinese': self.chinese_font,
                'english': self.english_font
            },
            'databases': {
                'word_details': self.word_details_db,
                'known_words': self.known_words_db
            },
            'upload': {
                'folder': self.upload_folder,
                'max_size': self.max_content_length
            },
            'features': {
                'auto_lookup': self.enable_auto_lookup,
                'auto_copy': self.enable_auto_copy,
                'ai_semantic': self.enable_ai_semantic
            }
        }
    
    def get_project_root(self) -> Path:
        """获取项目根目录"""
        return Path(__file__).parent.parent.parent


# 全局配置实例
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """获取全局配置实例"""
    global _settings
    if _settings is None:
        _settings = Settings.from_env()
    return _settings


def init_settings(**kwargs) -> Settings:
    """初始化配置"""
    global _settings
    _settings = Settings(**kwargs)
    return _settings
