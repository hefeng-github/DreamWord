"""
智能写字机系统 - API 路由定义
"""

from flask import Blueprint, request, jsonify, send_file
from werkzeug.utils import secure_filename
import os
import uuid
from pathlib import Path
from typing import Tuple, Dict, Any

from src.config import get_settings
from src.utils import ensure_directory, get_logger

logger = get_logger(__name__)


def create_api_routes(app=None):
    """创建 API 路由蓝图"""
    
    api = Blueprint('api', __name__, url_prefix='/api')
    settings = get_settings()
    
    # 确保上传目录存在
    upload_folder = Path(settings.upload_folder)
    ensure_directory(upload_folder)
    
    @api.route('/health')
    def health_check():
        """健康检查"""
        return jsonify({
            'status': 'healthy',
            'version': settings.version
        })
    
    @api.route('/config')
    def get_config():
        """获取系统配置"""
        return jsonify(settings.to_dict())
    
    @api.route('/download/<filename>')
    def download_file(filename: str):
        """下载文件"""
        try:
            filepath = upload_folder / secure_filename(filename)
            if filepath.exists():
                return send_file(str(filepath), as_attachment=True)
            else:
                return jsonify({'success': False, 'error': '文件不存在'}), 404
        except Exception as e:
            logger.error(f"下载文件失败：{e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @api.route('/preview/<filename>')
    def preview_file(filename: str):
        """预览文件"""
        try:
            filepath = upload_folder / secure_filename(filename)
            if filepath.exists():
                return send_file(str(filepath))
            else:
                return jsonify({'success': False, 'error': '文件不存在'}), 404
        except Exception as e:
            logger.error(f"预览文件失败：{e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    # 注册蓝图到应用
    if app:
        app.register_blueprint(api)
    
    return api


__all__ = ['create_api_routes']
