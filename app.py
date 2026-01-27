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
from calibration import Calibrator, ArUcoMarkerGenerator
from writer import WriterMachine

# 延迟导入标志
AUTO_LOOKUP_AVAILABLE = False
AUTO_COPY_AVAILABLE = False

try:
    from auto_lookup import AutoLookup
    AUTO_LOOKUP_AVAILABLE = True
except Exception as e:
    print(f"警告: 自动查词模块加载失败: {e}")
    print("自动查词功能将不可用")

try:
    from auto_copy import AutoCopy
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

        if not text:
            return jsonify({'success': False, 'error': '文字不能为空'})

        writer = WriterMachine()

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
            'preview_url': f'/api/download/{os.path.basename(preview_path)}'
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
        from auto_lookup import KnownWordsDatabase
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
        from auto_lookup import KnownWordsDatabase
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

        from auto_lookup import KnownWordsDatabase
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


def run_server(host='127.0.0.1', port=5000, debug=True):
    """运行服务器"""
    # 构建功能状态信息
    features = []
    features.append("✓ 生成ArUco标记")
    features.append("✓ 校准写字机")
    features.append("✓ 书写文字")
    features.append("✓ 导入单词")

    if AUTO_LOOKUP_AVAILABLE:
        features.append("✓ 自动查单词")
    else:
        features.append("✗ 自动查单词（依赖未安装）")

    if AUTO_COPY_AVAILABLE:
        features.append("✓ 自动抄写")
    else:
        features.append("✗ 自动抄写（依赖未安装）")

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
