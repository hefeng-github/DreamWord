"""
智能写字机Web控制界面

基于Flask的Web应用，提供友好的用户界面
"""

from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
import os
from pathlib import Path
import uuid
import json
import threading
from typing import Any, Dict, Tuple

import serial
import serial.tools.list_ports

# 导入项目模块（基础模块，无重型依赖）
from src.modules.calibration import Calibrator, ArUcoMarkerGenerator
from src.modules.writer import WriterMachine

# 导入查词模块
WORD_LOOKUP_AVAILABLE = False
try:
    from src.modules.word_lookup import WordLookup
    WORD_LOOKUP_AVAILABLE = True
except Exception as e:
    print(f"警告: 查词模块加载失败: {e}")
    print("查词预览功能将不可用")

# 延迟导入标志
AUTO_LOOKUP_AVAILABLE = False
AUTO_COPY_AVAILABLE = False

try:
    from src.modules.auto_lookup import AutoLookup
    AUTO_LOOKUP_AVAILABLE = True
except Exception as e:
    print(f"警告: 自动查词模块加载失败: {e}")
    print("自动查词功能将不可用")

try:
    from src.modules.auto_copy import AutoCopy
    AUTO_COPY_AVAILABLE = True
except Exception as e:
    print(f"警告: 自动抄写模块加载失败: {e}")
    print("自动抄写功能将不可用")

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# 创建上传目录
Path(app.config['UPLOAD_FOLDER']).mkdir(exist_ok=True)

# 全局变量存储任务状态
task_status = {}


def _json_data() -> Dict[str, Any]:
    """统一获取JSON请求体，避免空JSON导致的NoneType异常。"""
    return request.get_json(silent=True) or {}


def _error(message: str, code: int = 200):
    return jsonify({'success': False, 'error': message}), code


def _save_uploaded_image(field_name: str = 'image'):
    """保存上传图片并返回文件路径。"""
    if field_name not in request.files:
        return None, _error('未上传图片')

    file = request.files[field_name]
    if not file.filename:
        return None, _error('未选择文件')

    filename = secure_filename(file.filename)
    if not filename:
        filename = f'upload_{uuid.uuid4().hex[:8]}.bin'
    else:
        filename = f'{uuid.uuid4().hex[:8]}_{filename}'

    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    return filepath, None


def _parse_marker_positions(positions_data: Dict[str, Any]) -> Dict[int, Tuple[float, float]]:
    marker_positions = {}
    for marker_id, pos in positions_data.items():
        marker_positions[int(marker_id)] = (float(pos['x']), float(pos['y']))
    return marker_positions


def _get_known_words_db():
    from src.modules.auto_lookup import KnownWordsDatabase
    return KnownWordsDatabase()


@app.route('/')
def index():
    """主页"""
    return render_template('index.html')


@app.route('/api/generate-markers', methods=['POST'])
def api_generate_markers():
    """生成ArUco标记"""
    try:
        data = _json_data()
        num_markers = int(data.get('num_markers', 4))
        marker_size = int(data.get('marker_size', 200))

        generator = ArUcoMarkerGenerator(marker_size=marker_size)
        marker_ids = list(range(num_markers))

        filename = f"aruco_board_{uuid.uuid4().hex[:8]}.png"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

        generator.generate_marker_board(marker_ids, filepath)

        return jsonify({
            'success': True,
            'filename': filename,
            'download_url': f'/api/download/{filename}'
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/draw-markers', methods=['POST'])
def api_draw_markers():
    """生成绘制ArUco标记的Gcode"""
    try:
        data = _json_data()

        # 获取标记位置
        positions_data = data.get('positions', {})
        marker_positions = _parse_marker_positions(positions_data)

        # 获取标记尺寸
        marker_size = float(data.get('marker_size', 30.0))

        # 创建校准器并生成Gcode
        calibrator = Calibrator(marker_size=marker_size)

        gcode_file = f"draw_markers_{uuid.uuid4().hex[:8]}.gcode"
        preview_file = f"draw_markers_{uuid.uuid4().hex[:8]}.png"

        gcode_path = os.path.join(app.config['UPLOAD_FOLDER'], gcode_file)
        preview_path = os.path.join(app.config['UPLOAD_FOLDER'], preview_file)

        gcode = calibrator.generate_markers_gcode(
            marker_positions=marker_positions,
            marker_size_mm=marker_size,
            gcode_path=gcode_path,
            preview_path=preview_path
        )

        if gcode:
            return jsonify({
                'success': True,
                'gcode_file': gcode_file,
                'preview_file': preview_file,
                'gcode_url': f'/api/download/{gcode_file}',
                'preview_url': f'/api/download/{preview_file}',
                'message': '标记绘制Gcode生成成功'
            })
        else:
            return jsonify({'success': False, 'error': 'Gcode生成失败'})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/calibrate', methods=['POST'])
def api_calibrate():
    """校准写字机"""
    try:
        filepath, error_response = _save_uploaded_image('image')
        if error_response:
            return error_response

        # 获取标记位置
        positions_data = request.form.get('positions', '{}')
        positions = json.loads(positions_data)
        marker_positions = _parse_marker_positions(positions)

        # 校准
        calibrator = Calibrator(marker_size=float(request.form.get('marker_size', 30.0)))
        calibration_path = os.path.join(app.config['UPLOAD_FOLDER'], f'calibration_{uuid.uuid4().hex[:8]}.pkl')

        success = calibrator.calibrate_from_image(
            image_path=filepath,
            marker_positions=marker_positions,
            save_path=calibration_path
        )

        if success:
            return jsonify({
                'success': True,
                'calibration_file': os.path.basename(calibration_path),
                'message': '校准成功'
            })
        else:
            return jsonify({'success': False, 'error': '校准失败'})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/write', methods=['POST'])
def api_write():
    """书写文字"""
    try:
        data = _json_data()
        text = data.get('text', '').strip()
        use_handright = data.get('use_handright', False)
        printer_model = data.get('printer_model', 'A1MINI')
        layer_height = data.get('layer_height', 0.2)
        nozzle_temp = data.get('nozzle_temp', 200)
        bed_temp = data.get('bed_temp', 60)

        if not text:
            return _error('文字不能为空')

        writer = WriterMachine(
            printer_model=printer_model,
            layer_height=layer_height,
            nozzle_temp=nozzle_temp,
            bed_temp=bed_temp
        )

        filename = f"write_{uuid.uuid4().hex[:8]}.gcode"
        gcode_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        preview_path = gcode_path.replace('.gcode', '_preview.png')

        gcode = writer.write_text(
            text=text,
            use_handright=use_handright,
            save_gcode_path=gcode_path,
            save_image_path=preview_path
        )

        return jsonify({
            'success': True,
            'gcode_file': filename,
            'preview_file': os.path.basename(preview_path),
            'download_url': f'/api/download/{filename}',
            'preview_url': f'/api/download/{os.path.basename(preview_path)}',
            'printer_model': printer_model
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/auto-lookup', methods=['POST'])
def api_auto_lookup():
    """自动查单词"""
    if not AUTO_LOOKUP_AVAILABLE:
        return jsonify({
            'success': False,
            'error': '自动查词模块未加载，请检查依赖安装（PaddleOCR、OpenCV等）'
        })

    try:
        filepath, error_response = _save_uploaded_image('image')
        if error_response:
            return error_response
        known_words = request.form.get('known_words', '')

        crop_x = request.form.get('crop_x', type=int)
        crop_y = request.form.get('crop_y', type=int)
        crop_w = request.form.get('crop_w', type=int)
        crop_h = request.form.get('crop_h', type=int)
        only_phonetics = request.form.get('only_phonetics', 'false').lower() == 'true'

        # 处理
        auto_lookup = AutoLookup()

        # 添加已知单词
        if known_words:
            words = [w.strip() for w in known_words.split(',')]
            auto_lookup.add_known_words(words)

        # 输出文件
        gcode_file = f"lookup_{uuid.uuid4().hex[:8]}.gcode"
        annotated_file = f"lookup_{uuid.uuid4().hex[:8]}.jpg"

        gcode_path = os.path.join(app.config['UPLOAD_FOLDER'], gcode_file)
        annotated_path = os.path.join(app.config['UPLOAD_FOLDER'], annotated_file)

        success = auto_lookup.process_exam_image(
            image_path=filepath,
            calibration_path=None,
            save_gcode_path=gcode_path,
            save_annotated_image=annotated_path,
            crop_x=crop_x,
            crop_y=crop_y,
            crop_w=crop_w,
            crop_h=crop_h,
            only_phonetics=only_phonetics
        )

        if success:
            return jsonify({
                'success': True,
                'gcode_file': gcode_file,
                'annotated_file': annotated_file,
                'gcode_url': f'/api/download/{gcode_file}',
                'annotated_url': f'/api/download/{annotated_file}'
            })
        else:
            return jsonify({'success': False, 'error': '处理失败'})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/auto-copy', methods=['POST'])
def api_auto_copy():
    """自动抄写"""
    if not AUTO_COPY_AVAILABLE:
        return jsonify({
            'success': False,
            'error': '自动抄写模块未加载，请检查依赖安装（PaddleOCR、OpenCV等）'
        })

    try:
        filepath, error_response = _save_uploaded_image('image')
        if error_response:
            return error_response
        text = request.form.get('text', '')

        if not text:
            return jsonify({'success': False, 'error': '文字不能为空'})

        # 处理
        auto_copy = AutoCopy()

        # 输出文件
        gcode_file = f"copy_{uuid.uuid4().hex[:8]}.gcode"
        layout_file = f"copy_{uuid.uuid4().hex[:8]}.jpg"

        gcode_path = os.path.join(app.config['UPLOAD_FOLDER'], gcode_file)
        layout_path = os.path.join(app.config['UPLOAD_FOLDER'], layout_file)

        success = auto_copy.copy_text(
            notebook_image_path=filepath,
            text=text,
            calibration_path=None,  # 暂时不使用校准
            save_gcode_path=gcode_path,
            save_layout_image=layout_path
        )

        if success:
            return jsonify({
                'success': True,
                'gcode_file': gcode_file,
                'layout_file': layout_file,
                'gcode_url': f'/api/download/{gcode_file}',
                'layout_url': f'/api/download/{layout_file}'
            })
        else:
            return jsonify({'success': False, 'error': '处理失败'})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/download/<filename>')
def api_download(filename):
    """下载文件"""
    try:
        filepath = Path(app.config['UPLOAD_FOLDER']) / secure_filename(filename)
        if filepath.is_file():
            return send_file(str(filepath), as_attachment=True)
        else:
            return _error('文件不存在', 404)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/preview/<filename>')
def api_preview(filename):
    """预览图片"""
    try:
        filepath = Path(app.config['UPLOAD_FOLDER']) / secure_filename(filename)
        if filepath.is_file():
            return send_file(str(filepath))
        else:
            return _error('文件不存在', 404)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/ocr-words', methods=['POST'])
def api_ocr_words():
    """OCR识别图片中的英文单词，返回单词及位置"""
    if not AUTO_LOOKUP_AVAILABLE:
        return jsonify({
            'success': False,
            'error': 'OCR模块未加载，请检查依赖安装（PaddleOCR、OpenCV等）'
        })

    try:
        filepath, error_response = _save_uploaded_image('image')
        if error_response:
            return error_response

        from src.modules.auto_lookup import TextExtractor
        import cv2
        import numpy as np

        image = cv2.imread(filepath)
        if image is None:
            return _error('无法读取图片')

        extractor = TextExtractor()
        ocr_results = extractor.extract_text(image, unwarp=False)

        if not ocr_results:
            return jsonify({'success': True, 'words': [], 'image_size': list(image.shape[:2])})

        english_words = extractor.filter_english_words(ocr_results)

        seen = {}
        for w in english_words:
            key = w.text.lower()
            if key not in seen:
                seen[key] = w

        words = []
        for w in seen.values():
            words.append({
                'word': w.text,
                'bbox': w.bbox,
                'center': list(w.center),
                'confidence': round(w.confidence, 3)
            })

        h, w_img = image.shape[:2]
        return jsonify({
            'success': True,
            'words': words,
            'image_size': [h, w_img]
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/add-known-words', methods=['POST'])
def api_add_known_words():
    """添加已知单词到数据库"""
    try:
        data = _json_data()
        words = data.get('words', [])

        if isinstance(words, str):
            words = [words]
        elif not isinstance(words, list):
            return _error('words 参数必须是数组或字符串')

        if not words:
            return _error('单词列表为空')

        db = _get_known_words_db()

        # 统计
        added_count = 0
        skipped_count = 0

        for word in words:
            if not isinstance(word, str):
                continue
            word = word.strip()
            if not word:
                continue

            # 检查是否已存在
            if db.is_known(word):
                skipped_count += 1
            else:
                db.add_word(word)
                added_count += 1

        return jsonify({
            'success': True,
            'added_count': added_count,
            'skipped_count': skipped_count,
            'message': f'成功添加 {added_count} 个单词'
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/get-known-words', methods=['GET'])
def api_get_known_words():
    """获取所有已知单词"""
    try:
        db = _get_known_words_db()
        words = db.get_all_words()

        return jsonify({
            'success': True,
            'words': words,
            'count': len(words)
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/remove-known-word', methods=['POST'])
def api_remove_known_word():
    """从数据库移除已知单词"""
    try:
        data = _json_data()
        word = data.get('word', '').strip()

        if not word:
            return _error('单词不能为空')

        db = _get_known_words_db()
        db.remove_word(word)

        return jsonify({
            'success': True,
            'message': f'已移除单词: {word}'
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


# ==================== 串口通信（直接发送Gcode） ====================

_serial_port = None
_serial_lock = threading.Lock()
_serial_status = {'connected': False, 'port': '', 'sending': False, 'progress': 0, 'total': 0, 'message': ''}
_serial_paused = False

_last_calibration_matrix = None


def _serial_connect(port: str, baudrate: int = 115200) -> bool:
    global _serial_port
    try:
        _serial_disconnect()
        _serial_port = serial.Serial(port, baudrate, timeout=2)
        import time; time.sleep(2)
        _serial_port.write(b'\n')
        _serial_status['connected'] = True
        _serial_status['port'] = port
        _serial_status['message'] = f'已连接 {port}'
        return True
    except Exception as e:
        _serial_status['message'] = f'连接失败: {e}'
        return False


def _serial_disconnect():
    global _serial_port
    try:
        if _serial_port and _serial_port.is_open:
            _serial_port.close()
    except Exception:
        pass
    _serial_port = None
    _serial_status['connected'] = False
    _serial_status['port'] = ''
    _serial_status['sending'] = False


def _serial_send_gcode(gcode_content: str):
    global _serial_port, _serial_paused
    lines = [l.strip() for l in gcode_content.split('\n') if l.strip() and not l.strip().startswith(';')]
    total = len(lines)
    _serial_status['sending'] = True
    _serial_status['progress'] = 0
    _serial_status['total'] = total
    _serial_status['message'] = f'发送中 0/{total}'
    _serial_paused = False

    try:
        for i, line in enumerate(lines):
            while _serial_paused:
                import time; time.sleep(0.1)
                if not _serial_status['sending']:
                    break
            if not _serial_status['sending']:
                break
            if not _serial_port or not _serial_port.is_open:
                _serial_status['message'] = '串口已断开'
                break
            with _serial_lock:
                _serial_port.write((line + '\n').encode('utf-8'))
                while True:
                    resp = _serial_port.readline().decode('utf-8', errors='ignore').strip()
                    if 'ok' in resp.lower() or 'error' in resp.lower() or not resp:
                        break
            _serial_status['progress'] = i + 1
            _serial_status['message'] = f'发送中 {i + 1}/{total}'

        _serial_status['message'] = f'发送完成 ({total} 行)'
    except Exception as e:
        _serial_status['message'] = f'发送失败: {e}'
    finally:
        _serial_status['sending'] = False
        _serial_paused = False


@app.route('/api/serial/ports', methods=['GET'])
def api_serial_ports():
    try:
        ports = [{'port': p.device, 'desc': p.description} for p in serial.tools.list_ports.comports()]
        return jsonify({'success': True, 'ports': ports})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/serial/connect', methods=['POST'])
def api_serial_connect():
    try:
        data = _json_data()
        port = data.get('port', '')
        baudrate = int(data.get('baudrate', 115200))
        if not port:
            return _error('请选择串口')
        if _serial_connect(port, baudrate):
            return jsonify({'success': True, 'message': f'已连接 {port}'})
        return jsonify({'success': False, 'error': _serial_status['message']})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/serial/disconnect', methods=['POST'])
def api_serial_disconnect():
    _serial_disconnect()
    return jsonify({'success': True, 'message': '已断开连接'})


@app.route('/api/serial/status', methods=['GET'])
def api_serial_status():
    return jsonify({'success': True, **_serial_status})


@app.route('/api/serial/send', methods=['POST'])
def api_serial_send():
    if not _serial_status['connected']:
        return _error('串口未连接')
    if _serial_status['sending']:
        return _error('正在发送中，请等待')

    try:
        data = _json_data()
        gcode_file = data.get('file', '')

        if gcode_file:
            filepath = Path(app.config['UPLOAD_FOLDER']) / secure_filename(gcode_file)
            if not filepath.is_file():
                return _error('Gcode文件不存在')
            gcode_content = filepath.read_text(encoding='utf-8')
        else:
            gcode_content = data.get('gcode', '')

        if not gcode_content.strip():
            return _error('Gcode内容为空')

        thread = threading.Thread(target=_serial_send_gcode, args=(gcode_content,), daemon=True)
        thread.start()
        return jsonify({'success': True, 'message': '开始发送Gcode'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/serial/pause', methods=['POST'])
def api_serial_pause():
    global _serial_paused
    if not _serial_status['connected']:
        return _error('串口未连接')
    if not _serial_status['sending']:
        return _error('当前未在发送')
    _serial_paused = True
    try:
        with _serial_lock:
            if _serial_port and _serial_port.is_open:
                _serial_port.write(b'!\n')
    except Exception:
        pass
    return jsonify({'success': True, 'message': '已暂停发送'})


@app.route('/api/serial/resume', methods=['POST'])
def api_serial_resume():
    global _serial_paused
    if not _serial_status['connected']:
        return _error('串口未连接')
    _serial_paused = False
    try:
        with _serial_lock:
            if _serial_port and _serial_port.is_open:
                _serial_port.write(b'~\n')
    except Exception:
        pass
    return jsonify({'success': True, 'message': '已恢复发送'})


@app.route('/api/generate-corner-markers', methods=['POST'])
def api_generate_corner_markers():
    try:
        data = _json_data()
        frame_width = float(data.get('frame_width', 220.0))
        frame_height = float(data.get('frame_height', 310.0))
        marker_size = float(data.get('marker_size', 30.0))
        margin = float(data.get('margin', 5.0))

        calibrator = Calibrator(marker_size=marker_size)
        filename = f"corner_markers_{uuid.uuid4().hex[:8]}.png"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

        calibrator.generate_corner_marker_paper(
            frame_width_mm=frame_width,
            frame_height_mm=frame_height,
            marker_size_mm=marker_size,
            margin_mm=margin,
            save_path=filepath
        )

        return jsonify({
            'success': True,
            'filename': filename,
            'download_url': f'/api/download/{filename}',
            'message': f'四角标记定位纸已生成 ({frame_width}x{frame_height}mm)'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/check-calibration', methods=['POST'])
def api_check_calibration():
    global _last_calibration_matrix
    try:
        filepath, error_response = _save_uploaded_image('image')
        if error_response:
            return error_response

        import cv2
        image = cv2.imread(filepath)
        if image is None:
            return _error('无法读取图片')

        calibrator = Calibrator()
        new_image_points = calibrator.detect_markers(image)

        if len(new_image_points) < 3:
            return jsonify({
                'success': True,
                'ok': False,
                'warning': f'仅检测到 {len(new_image_points)} 个标记，无法检查'
            })

        if _last_calibration_matrix is None:
            _last_calibration_matrix = calibrator.transformation_matrix
            return jsonify({
                'success': True,
                'ok': True,
                'message': '首次检测，已记录初始矩阵'
            })

        result = calibrator.check_matrix_variance(
            new_matrix=calibrator.transformation_matrix
        )

        if result.get('valid'):
            return jsonify({
                'success': True,
                'ok': result['ok'],
                'translation_mm': result['translation_mm'],
                'rotation_deg': result['rotation_deg'],
                'warning': result.get('warning')
            })
        else:
            return jsonify({
                'success': True,
                'ok': False,
                'warning': result.get('error', '检查失败')
            })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


ONEDRIVE_CONFIG_FILE = 'onedrive_config.json'


def _get_onedrive_client_id():
    env_val = os.environ.get('ONEDRIVE_CLIENT_ID', '')
    if env_val:
        return env_val
    if os.path.exists(ONEDRIVE_CONFIG_FILE):
        try:
            with open(ONEDRIVE_CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f).get('client_id', '')
        except Exception:
            pass
    return ''


def _get_onedrive_backup():
    from src.modules.onedrive_backup import OneDriveBackup
    return OneDriveBackup(client_id=_get_onedrive_client_id())


@app.route('/api/onedrive/auth', methods=['POST'])
def api_onedrive_auth():
    if not ONEDRIVE_CLIENT_ID:
        return _error('未配置OneDrive Client ID，请设置环境变量 ONEDRIVE_CLIENT_ID')
    try:
        backup = _get_onedrive_backup()
        code_info = backup.get_device_code()
        return jsonify({
            'success': True,
            'user_code': code_info['user_code'],
            'device_code': code_info['device_code'],
            'verification_uri': code_info['verification_uri'],
            'interval': code_info.get('interval', 5),
            'message': code_info.get('message', '')
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/onedrive/poll', methods=['POST'])
def api_onedrive_poll():
    try:
        data = _json_data()
        device_code = data.get('device_code', '')
        if not device_code:
            return _error('缺少device_code')
        backup = _get_onedrive_backup()
        result = backup.poll_token(device_code)
        if result:
            return jsonify({'success': True, 'message': '授权成功'})
        return jsonify({'success': False, 'pending': True, 'message': '等待授权中...'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/onedrive/status', methods=['GET'])
def api_onedrive_status():
    try:
        client_id = _get_onedrive_client_id()
        configured = bool(client_id)
        backup = _get_onedrive_backup() if configured else None
        return jsonify({
            'success': True,
            'configured': configured,
            'authorized': backup.is_authorized() if backup else False,
            'client_id_set': bool(client_id)
        })
    except Exception:
        return jsonify({'success': True, 'configured': False, 'authorized': False, 'client_id_set': False})


@app.route('/api/onedrive/config', methods=['POST'])
def api_onedrive_config():
    try:
        data = _json_data()
        client_id = data.get('client_id', '').strip()
        if not client_id:
            return _error('Client ID 不能为空')
        with open(ONEDRIVE_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump({'client_id': client_id}, f, indent=2)
        return jsonify({'success': True, 'message': 'Client ID 已保存'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/onedrive/backup', methods=['POST'])
def api_onedrive_backup():
    try:
        backup = _get_onedrive_backup()
        if not backup.is_authorized():
            return _error('未授权OneDrive，请先完成授权')
        result = backup.backup()
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/onedrive/backups', methods=['GET'])
def api_onedrive_backups():
    try:
        backup = _get_onedrive_backup()
        if not backup.is_authorized():
            return _error('未授权OneDrive')
        backups = backup.list_backups()
        return jsonify({'success': True, 'backups': backups})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/onedrive/restore', methods=['POST'])
def api_onedrive_restore():
    try:
        data = _json_data()
        backup_name = data.get('backup_name')
        merge = data.get('merge', True)
        backup = _get_onedrive_backup()
        if not backup.is_authorized():
            return _error('未授权OneDrive')
        result = backup.restore(backup_name=backup_name, merge=merge)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/onedrive/disconnect', methods=['POST'])
def api_onedrive_disconnect():
    try:
        backup = _get_onedrive_backup()
        backup.disconnect()
        return jsonify({'success': True, 'message': '已断开OneDrive连接'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/word-preview', methods=['GET'])
def api_word_preview():
    """查单词预览"""
    if not WORD_LOOKUP_AVAILABLE:
        return jsonify({
            'success': False,
            'error': '查词模块未加载'
        })

    try:
        word = request.args.get('word', '').strip()

        if not word:
            return jsonify({'success': False, 'error': '单词不能为空'})

        # 查询单词
        word_lookup = WordLookup()
        result = word_lookup.lookup(word)

        return jsonify(result.to_dict())

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/task-status/<task_id>')
def api_task_status(task_id):
    """获取任务状态"""
    status = task_status.get(task_id, {'status': 'unknown'})
    return jsonify(status)



def run_server(host='127.0.0.1', port=5000, debug=True):
    """运行服务器"""
    # 构建功能状态信息
    features = []
    features.append("[OK] 生成ArUco标记")
    features.append("[OK] 校准写字机")
    features.append("[OK] 书写文字")
    features.append("[OK] 导入单词")

    if AUTO_LOOKUP_AVAILABLE:
        features.append("[OK] 自动查单词")
    else:
        features.append("[X] 自动查单词（依赖未安装）")

    if AUTO_COPY_AVAILABLE:
        features.append("[OK] 自动抄写")
    else:
        features.append("[X] 自动抄写（依赖未安装）")

    feature_list = '\n'.join([f'  • {f}' for f in features])

    print(f"""
======================================================================
智能写字机Web控制界面
======================================================================

服务器地址: http://{host}:{port}

功能状态:
{feature_list}

按 Ctrl+C 停止服务器

======================================================================
    """)

    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='智能写字机Web控制界面')
    parser.add_argument('--host', default='127.0.0.1', help='监听地址')
    parser.add_argument('--port', type=int, default=5000, help='监听端口')
    parser.add_argument('--debug', type=lambda x: x.lower() == 'true', default=True, help='调试模式')

    args = parser.parse_args()

    run_server(host=args.host, port=args.port, debug=args.debug)
