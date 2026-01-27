"""
测试Web服务器是否能正常启动
"""

print("正在测试Web服务器依赖...")

try:
    from flask import Flask
    print("[OK] Flask 已安装")
except ImportError:
    print("[FAIL] Flask 未安装")
    exit(1)

try:
    import cv2
    print("[OK] OpenCV 已安装")
except ImportError:
    print("[FAIL] OpenCV 未安装")

try:
    from PIL import Image
    print("[OK] Pillow 已安装")
except ImportError:
    print("[FAIL] Pillow 未安装")

try:
    import numpy
    print("[OK] NumPy 已安装")
except ImportError:
    print("[FAIL] NumPy 未安装")

# 检查可选依赖
print("\n可选依赖检查：")

try:
    import paddleocr
    print("[OK] PaddleOCR 已安装（支持自动查词和自动抄写）")
except ImportError:
    print("[SKIP] PaddleOCR 未安装（自动查词和自动抄写功能将不可用）")

try:
    import handright
    print("[OK] Handright 已安装（支持手写体渲染）")
except ImportError:
    print("[SKIP] Handright 未安装（手写体渲染功能将不可用）")

try:
    from calibration import Calibrator, ArUcoMarkerGenerator
    print("[OK] 校准模块可用")
except Exception as e:
    print(f"[FAIL] 校准模块加载失败: {e}")

try:
    from writer import WriterMachine
    print("[OK] 写字模块可用")
except Exception as e:
    print(f"[FAIL] 写字模块加载失败: {e}")

try:
    from auto_lookup import AutoLookup
    print("[OK] 自动查词模块可用")
except Exception as e:
    print(f"[SKIP] 自动查词模块加载失败: {e}")

try:
    from auto_copy import AutoCopy
    print("[OK] 自动抄写模块可用")
except Exception as e:
    print(f"[SKIP] 自动抄写模块加载失败: {e}")

print("\n" + "="*50)
print("测试完成！")
print("\n提示：")
print("- 基础功能（书写文字、导入单词）只需要Flask和OpenCV")
print("- OCR功能（自动查词、自动抄写）需要PaddleOCR")
print("- 如果PaddleOCR未安装，系统会自动禁用相关功能")
print("="*50)
