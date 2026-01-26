"""
智能写字机主程序

整合所有模块：
1. 校准模块
2. 写字模块
3. 自动查单词模块
4. 自动抄写模块
"""

import sys
import argparse
from pathlib import Path

from calibration import Calibrator, ArUcoMarkerGenerator
from writer import WriterMachine, MachineController
from auto_lookup import AutoLookup
from auto_copy import AutoCopy


def print_banner():
    """打印横幅"""
    print("=" * 70)
    print("智能写字机控制系统")
    print("=" * 70)
    print()


def generate_markers(args):
    """生成ArUco标记"""
    print("生成ArUco标记...")

    generator = ArUcoMarkerGenerator(marker_size=args.marker_size)

    if args.marker_id is not None:
        # 生成单个标记
        marker = generator.generate_marker(args.marker_id, args.output)
        print(f"✓ 已生成标记 {args.marker_id} 到 {args.output}")
    else:
        # 生成标记板
        marker_ids = list(range(args.num_markers))
        board = generator.generate_marker_board(marker_ids, args.output)
        print(f"✓ 已生成标记板（{len(marker_ids)}个标记）到 {args.output}")


def calibrate(args):
    """校准"""
    print("校准写字机...")

    calibrator = Calibrator(marker_size=args.marker_size)

    # 定义标记位置（需要用户提供）
    print("\n请提供标记的物理位置（毫米）：")
    print("格式：标记ID X坐标 Y坐标")
    print("例如：0 10 10")
    print("输入空行结束\n")

    marker_positions = {}

    if args.marker_positions:
        # 从命令行参数读取
        for pos_str in args.marker_positions:
            parts = pos_str.split(',')
            if len(parts) == 3:
                marker_id = int(parts[0])
                x = float(parts[1])
                y = float(parts[2])
                marker_positions[marker_id] = (x, y)
                print(f"标记 {marker_id}: ({x}, {y})")
    else:
        # 交互式输入
        while True:
            line = input(f"标记位置: ").strip()
            if not line:
                break

            parts = line.split()
            if len(parts) == 3:
                marker_id = int(parts[0])
                x = float(parts[1])
                y = float(parts[2])
                marker_positions[marker_id] = (x, y)

    if len(marker_positions) < 3:
        print("错误: 需要至少3个标记")
        return False

    # 执行校准
    success = calibrator.calibrate_from_image(
        image_path=args.image,
        marker_positions=marker_positions,
        save_path=args.output
    )

    if success:
        print("✓ 校准完成")
    else:
        print("✗ 校准失败")

    return success


def write_text(args):
    """书写文字"""
    print("书写文字...")

    writer = WriterMachine()

    gcode = writer.write_text(
        text=args.text,
        use_handright=args.handright,
        save_gcode_path=args.output,
        save_image_path=args.preview
    )

    print(f"✓ 已生成Gcode到 {args.output}")

    # 如果指定了串口，直接发送
    if args.port:
        print(f"\n正在连接到 {args.port}...")

        controller = MachineController(port=args.port, baudrate=args.baudrate)

        if controller.connect():
            controller.send_gcode(gcode)
            controller.disconnect()
            print("✓ 已发送到写字机")

    return True


def auto_lookup(args):
    """自动查单词"""
    print("自动查单词...")

    auto_lookup = AutoLookup()

    # 添加已知单词
    if args.known_words:
        words = args.known_words.split(',')
        auto_lookup.add_known_words(words)
        print(f"✓ 已添加 {len(words)} 个已知单词")

    # 处理试卷图片
    success = auto_lookup.process_exam_image(
        image_path=args.image,
        calibration_path=args.calibration,
        save_gcode_path=args.output,
        save_annotated_image=args.preview
    )

    if success:
        print("✓ 处理完成")

    return success


def auto_copy(args):
    """自动抄写"""
    print("自动抄写...")

    auto_copy = AutoCopy()

    success = auto_copy.copy_text(
        notebook_image_path=args.image,
        text=args.text,
        calibration_path=args.calibration,
        save_gcode_path=args.output,
        save_layout_image=args.preview
    )

    if success:
        print("✓ 处理完成")

    return success


def interactive_mode():
    """交互模式"""
    print("进入交互模式...")
    print("输入 'help' 查看可用命令\n")

    while True:
        try:
            cmd = input(">>> ").strip()

            if not cmd:
                continue

            if cmd.lower() in ['exit', 'quit']:
                print("再见！")
                break

            elif cmd.lower() == 'help':
                print_help()

            elif cmd.lower() == 'calibrate':
                print("请使用命令行模式进行校准")
                print("python main.py calibrate -h")

            elif cmd.lower().startswith('write '):
                text = cmd[6:].strip()
                if text:
                    args = argparse.Namespace(
                        text=text,
                        output='output.gcode',
                        preview='preview.png',
                        handright=False,
                        port=None,
                        baudrate=115200
                    )
                    write_text(args)

            elif cmd.lower() == 'test':
                print("测试模式...")
                print("正在生成测试Gcode...")

                writer = WriterMachine()
                writer.write_text(
                    text="Hello World",
                    save_gcode_path="test.gcode",
                    save_image_path="test.png"
                )

                print("✓ 测试完成")
                print("生成的文件: test.gcode, test.png")

            else:
                print(f"未知命令: {cmd}")
                print("输入 'help' 查看可用命令")

        except KeyboardInterrupt:
            print("\n\n再见！")
            break
        except Exception as e:
            print(f"错误: {e}")


def print_help():
    """打印帮助信息"""
    print("\n可用命令:")
    print("  write <text>   - 书写文字")
    print("  test           - 测试模式")
    print("  help           - 显示帮助")
    print("  exit/quit      - 退出程序")
    print()


def main():
    """主函数"""
    print_banner()

    parser = argparse.ArgumentParser(description='智能写字机控制系统')

    subparsers = parser.add_subparsers(dest='command', help='可用命令')

    # 生成标记命令
    marker_parser = subparsers.add_parser('generate-markers', help='生成ArUco标记')
    marker_parser.add_argument('-s', '--marker-size', type=int, default=200, help='标记大小（像素）')
    marker_parser.add_argument('-i', '--marker-id', type=int, help='生成单个标记的ID')
    marker_parser.add_argument('-n', '--num-markers', type=int, default=4, help='标记板中的标记数量')
    marker_parser.add_argument('-o', '--output', default='aruco_markers.png', help='输出文件路径')

    # 校准命令
    cal_parser = subparsers.add_parser('calibrate', help='校准写字机')
    cal_parser.add_argument('-i', '--image', required=True, help='包含ArUco标记的图像')
    cal_parser.add_argument('-s', '--marker-size', type=float, default=30.0, help='标记物理尺寸（毫米）')
    cal_parser.add_argument('-p', '--marker-positions', nargs='+', help='标记位置（ID,X,Y）')
    cal_parser.add_argument('-o', '--output', default='calibration.pkl', help='校准数据输出路径')

    # 写字命令
    write_parser = subparsers.add_parser('write', help='书写文字')
    write_parser.add_argument('-t', '--text', required=True, help='要书写的文字')
    write_parser.add_argument('-o', '--output', default='output.gcode', help='Gcode输出路径')
    write_parser.add_argument('--preview', default='preview.png', help='预览图像路径')
    write_parser.add_argument('--handright', action='store_true', help='使用Handright渲染手写体')
    write_parser.add_argument('--port', help='串口（直接发送到机器）')
    write_parser.add_argument('--baudrate', type=int, default=115200, help='波特率')

    # 自动查单词命令
    lookup_parser = subparsers.add_parser('auto-lookup', help='自动查单词')
    lookup_parser.add_argument('-i', '--image', required=True, help='试卷图片路径')
    lookup_parser.add_argument('-c', '--calibration', help='校准数据路径')
    lookup_parser.add_argument('-k', '--known-words', help='已知单词（逗号分隔）')
    lookup_parser.add_argument('-o', '--output', default='annotations.gcode', help='Gcode输出路径')
    lookup_parser.add_argument('--preview', default='annotated.jpg', help='标注图像路径')

    # 自动抄写命令
    copy_parser = subparsers.add_parser('auto-copy', help='自动抄写')
    copy_parser.add_argument('-i', '--image', required=True, help='横线本图片路径')
    copy_parser.add_argument('-t', '--text', required=True, help='要抄写的文字')
    copy_parser.add_argument('-c', '--calibration', help='校准数据路径')
    copy_parser.add_argument('-o', '--output', default='copy.gcode', help='Gcode输出路径')
    copy_parser.add_argument('--preview', default='layout.jpg', help='布局预览路径')

    args = parser.parse_args()

    # 如果没有命令，进入交互模式
    if not args.command:
        interactive_mode()
        return

    # 执行命令
    if args.command == 'generate-markers':
        generate_markers(args)

    elif args.command == 'calibrate':
        calibrate(args)

    elif args.command == 'write':
        write_text(args)

    elif args.command == 'auto-lookup':
        auto_lookup(args)

    elif args.command == 'auto-copy':
        auto_copy(args)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n程序已中断")
        sys.exit(0)
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
