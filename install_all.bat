@echo off
chcp 65001 >nul
echo ======================================================================
echo 智能写字机系统 - 统一安装脚本
echo ======================================================================
echo.

echo [1/3] 安装基础依赖（必需）...
echo.
echo 正在安装 Flask、OpenCV、Pillow、NumPy...
pip install flask werkzeug opencv-python pillow numpy
if errorlevel 1 (
    echo [ERROR] 基础依赖安装失败
    pause
    exit /b 1
)
echo [OK] 基础依赖安装完成
echo.

echo [2/3] 安装OCR功能（可选，推荐）...
echo.
set /p install_ocr="是否安装OCR功能？[Y/n]: "
if /i "%install_ocr%"=="Y" or "%install_ocr%"=="y" (
    echo 正在安装 PaddlePaddle、PaddleOCR...
    pip install paddlepaddle paddleocr
    if errorlevel 1 (
        echo [WARNING] OCR依赖安装失败，自动查词和自动抄写功能将不可用
    ) else (
        echo [OK] OCR依赖安装完成
    )
) else (
    echo [SKIP] 已跳过OCR功能安装
)
echo.

echo [3/3] 安装手写体渲染（可选）...
echo.
set /p install_handright="是否安装手写体渲染？[Y/n]: "
if /i "%install_handright%"=="Y" or "%install_handright%"=="y" (
    echo 正在安装 Handright...
    pip install handright
    if errorlevel 1 (
        echo [WARNING] Handright安装失败，手写体渲染功能将不可用
    ) else (
        echo [OK] Handright安装完成
    )
) else (
    echo [SKIP] 已跳过手写体渲染安装
)
echo.

echo ======================================================================
echo 安装完成！
echo ======================================================================
echo.
echo 功能状态：
echo   [OK] 书写文字          - 生成文字的Gcode
echo   [OK] 导入单词          - 管理已知词库
echo   [OK] 生成ArUco标记    - 用于校准
echo   [OK] 校准写字机        - 坐标校准
echo.

if /i "%install_ocr%"=="Y" or "%install_ocr%"=="y" (
    echo   [OK] 自动查单词        - OCR识别试卷并标注生词
    echo   [OK] 自动抄写          - 识别横线本并智能抄写
) else (
    echo   [--] 自动查单词        - 需要安装OCR功能
    echo   [--] 自动抄写          - 需要安装OCR功能
)
echo.

if /i "%install_handright%"=="Y" or "%install_handright%"=="y" (
    echo   [OK] 手写体渲染        - 中文手写体效果
) else (
    echo   [--] 手写体渲染        - 需要安装Handright
)
echo.

echo 下一步：
echo   1. 启动Web服务器：python app.py
echo   2. 浏览器访问：http://127.0.0.1:5000
echo   3. 或运行测试：python test_web.py
echo.
echo 可选安装：
echo   - AI语义匹配：运行 install_ai_semantic.bat
echo.
echo ======================================================================
pause
