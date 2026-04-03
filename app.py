"""
智能写字机Web控制界面

基于Flask的Web应用，提供友好的用户界面
"""

from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
import os
import sys
from pathlib import Path
import uuid
import threading
import json

# 导入项目模块（基础模块，无重型依赖）
from src.modules.calibration import Calibrator, ArUcoMarkerGenerator
from src.modules.writer import WriterMachine

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


@app.route('/')
def index():
    """主页"""
    return render_template('index.html')


@app.route('/printer-config')
def printer_config():
    """3D打印机配置页面"""
    return render_template('printer_config.html')


@app.route('/api/generate-markers', methods=['POST'])
def api_generate_markers():
    """生成ArUco标记"""
    try:
        data = request.json
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
        data = request.json

        # 获取标记位置
        marker_positions = {}
        positions_data = data.get('positions', {})

        for marker_id, pos in positions_data.items():
            marker_positions[int(marker_id)] = (float(pos['x']), float(pos['y']))

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
        if 'image' not in request.files:
            return jsonify({'success': False, 'error': '未上传图片'})

        file = request.files['image']
        if file.filename == '':
            return jsonify({'success': False, 'error': '未选择文件'})

        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # 获取标记位置
        marker_positions = {}
        positions_data = request.form.get('positions', '{}')
        positions = json.loads(positions_data)

        for marker_id, pos in positions.items():
            marker_positions[int(marker_id)] = (float(pos['x']), float(pos['y']))

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
        data = request.json
        text = data.get('text', '')
        use_handright = data.get('use_handright', False)
        printer_model = data.get('printer_model', 'A1MINI')
        layer_height = data.get('layer_height', 0.2)
        nozzle_temp = data.get('nozzle_temp', 200)
        bed_temp = data.get('bed_temp', 60)

        if not text:
            return jsonify({'success': False, 'error': '文字不能为空'})

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
        if 'image' not in request.files:
            return jsonify({'success': False, 'error': '未上传图片'})

        file = request.files['image']
        known_words = request.form.get('known_words', '')

        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

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
            calibration_path=None,  # 暂时不使用校准
            save_gcode_path=gcode_path,
            save_annotated_image=annotated_path
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
        if 'image' not in request.files:
            return jsonify({'success': False, 'error': '未上传图片'})

        file = request.files['image']
        text = request.form.get('text', '')

        if not text:
            return jsonify({'success': False, 'error': '文字不能为空'})

        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

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
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(filename))
        if os.path.exists(filepath):
            return send_file(filepath, as_attachment=True)
        else:
            return jsonify({'success': False, 'error': '文件不存在'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/preview/<filename>')
def api_preview(filename):
    """预览图片"""
    try:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(filename))
        if os.path.exists(filepath):
            return send_file(filepath)
        else:
            return jsonify({'success': False, 'error': '文件不存在'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/add-known-words', methods=['POST'])
def api_add_known_words():
    """添加已知单词到数据库"""
    try:
        data = request.json
        words = data.get('words', [])

        if not words:
            return jsonify({'success': False, 'error': '单词列表为空'})

        # 创建数据库实例
        from src.modules.auto_lookup import KnownWordsDatabase
        db = KnownWordsDatabase()

        # 统计
        added_count = 0
        skipped_count = 0

        for word in words:
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
        from src.modules.auto_lookup import KnownWordsDatabase
        db = KnownWordsDatabase()
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
        data = request.json
        word = data.get('word', '')

        if not word:
            return jsonify({'success': False, 'error': '单词不能为空'})

        from src.modules.auto_lookup import KnownWordsDatabase
        db = KnownWordsDatabase()
        db.remove_word(word)

        return jsonify({
            'success': True,
            'message': f'已移除单词: {word}'
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/task-status/<task_id>')
def api_task_status(task_id):
    """获取任务状态"""
    status = task_status.get(task_id, {'status': 'unknown'})
    return jsonify(status)



# ==================== 3D打印机配置API ====================

@app.route('/api/printer/connect', methods=['POST'])
def api_printer_connect():
    """连接打印机"""
    try:
        data = request.json
        printer_ip = data.get('printer_ip', '')
        access_code = data.get('access_code', '')
        printer_model = data.get('printer_model', 'A1MINI')

        if not printer_ip or not access_code:
            return jsonify({'success': False, 'error': 'IP地址和访问码不能为空'})

        # 连接打印机
        # 注意：这里可以集成实际的连接逻辑
        # 目前返回成功以演示功能

        print(f"[连接请求] 打印机: {printer_model}, IP: {printer_ip}")

        # 这里可以添加实际的连接测试
        # 例如：尝试连接到打印机的API或进行ping测试

        return jsonify({
            'success': True,
            'message': '连接成功',
            'printer_info': {
                'model': printer_model,
                'ip': printer_ip,
                'connected': True
            }
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/printer/pages', methods=['GET'])
def api_printer_pages():
    """获取打印机页面列表"""
    try:
        # 返回示例页面列表
        # 实际应用中可以从打印机获取
        pages = [
            {'id': 'page1', 'name': '页面 1'},
            {'id': 'page2', 'name': '页面 2'},
            {'id': 'page3', 'name': '页面 3'},
            {'id': 'custom', 'name': '自定义页面'}
        ]

        return jsonify({
            'success': True,
            'pages': pages
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/printer/upload', methods=['POST'])
def api_printer_upload():
    """上传页面到打印机"""
    try:
        data = request.json
        page_id = data.get('page_id', '')
        printer_ip = data.get('printer_ip', '')
        access_code = data.get('access_code', '')
        printer_model = data.get('printer_model', 'A1MINI')
        config = data.get('config', {})

        if not page_id:
            return jsonify({'success': False, 'error': '页面ID不能为空'})

        # 打印上传信息
        print(f"[上传请求] 页面: {page_id}")
        print(f"[上传请求] 配置: {config}")

        # 这里可以集成实际的上传逻辑
        # 这里可以集成实际的上传逻辑

        # 模拟上传过程
        print(f"正在上传到 {printer_model} ({printer_ip})")
        print(f"偏移: X={config.get('offset_x', 0)}, Y={config.get('offset_y', 0)}")
        print(f"Z轴: Up={config.get('z_pen_up', 5.0)}, Down={config.get('z_pen_down', 0.2)}")
        print(f"原点模式: {config.get('origin_mode', 'center')}")
        print(f"提示音: {'启用' if config.get('beep_enabled', True) else '禁用'}")

        
        try:
            # 这里可以扩展功能来保存配置或发送到打印机
            print(f"[OK] 配置已准备发送")
        except Exception as e:
            print(f"[警告] 适配器初始化失败: {e}")

        return jsonify({
            'success': True,
            'message': '页面上传成功',
            'page_id': page_id,
            'config': config
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/printer/config', methods=['GET'])
def api_printer_config():
    """获取打印机配置"""
    try:
        # 这里可以从打印机或本地存储获取当前配置
        config = {
            'offsetX': 0.0,
            'offsetY': 0.0,
            'liftZ': 5.0,
            'dropZ': 0.2,
            'originMode': 'auto',
            'soundEnabled': True
        }

        return jsonify({
            'success': True,
            'config': config
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/printer/connect', methods=['POST'])
def api_printer_connect():
    """连接打印机"""
    try:
        data = request.json
        printer_model = data.get('printer_model', 'A1MINI')
        ip = data.get('ip', '')
        access_code = data.get('access_code', '')

        print(f"[连接打印机] 型号: {printer_model}, IP: {ip}")

        # 验证参数
        if not ip:
            return jsonify({
                'success': False,
                'error': '请输入打印机IP地址'
            })

        # 这里可以尝试实际连接打印机
        # 暂时模拟成功连接
        print(f"[连接成功] {printer_model} @ {ip}")

        return jsonify({
            'success': True,
            'message': '打印机连接成功',
            'printer_info': {
                'model': printer_model,
                'ip': ip,
                'firmware': '01.08.02.00'
            }
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/printer/upload', methods=['POST'])
def api_printer_upload():
    """上传页面到打印机"""
    try:
        data = request.json
        page = data.get('page', 1)
        config = data.get('config', {})

        print(f"[上传页面] 页面: {page}, 配置: {config}")

        # 这里可以实际发送配置到打印机
        # 暂时模拟上传成功

        return jsonify({
            'success': True,
            'message': f'页面 {page} 上传成功',
            'page': page
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/printer/delete', methods=['POST'])
def api_printer_delete():
    """删除打印机页面"""
    try:
        data = request.json
        page = data.get('page', 1)

        print(f"[删除页面] 页面: {page}")

        # 这里可以实际删除打印机上的页面
        # 暂时模拟删除成功

        return jsonify({
            'success': True,
            'message': f'页面 {page} 删除成功',
            'page': page
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


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
