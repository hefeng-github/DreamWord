@echo off
REM AI语义匹配功能 - Windows快速安装脚本

echo ======================================================================
echo              AI智能语义匹配功能 - 依赖安装
echo ======================================================================
echo.

REM 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ✗ 错误: 未找到Python
    echo 请先安装Python 3.8或更高版本
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version') do set PYTHON_VERSION=%%i
echo 检测到 Python 版本: %PYTHON_VERSION%
echo.

echo ======================================================================
echo 安装说明
echo ======================================================================
echo.
echo 本脚本将安装以下依赖:
echo   - sentence-transformers: 语义模型库
echo   - torch: 深度学习框架
echo.
echo 安装后大小:
echo   - 基础库: ~50MB
echo   - 预训练模型: ~200MB (首次运行时自动下载)
echo.

set /p CONTINUE="是否继续安装? (y/n): "
if /i not "%CONTINUE%"=="y" (
    echo 安装已取消
    pause
    exit /b 0
)

echo.
echo ======================================================================
echo 开始安装...
echo ======================================================================
echo.

pip install sentence-transformers torch

if errorlevel 1 (
    echo.
    echo ✗ 安装失败
    echo 请检查网络连接或尝试使用镜像源:
    echo   pip install sentence-transformers torch -i https://pypi.tuna.tsinghua.edu.cn/simple
    pause
    exit /b 1
)

echo.
echo ======================================================================
echo 验证安装
echo ======================================================================
echo.

python -c "import sentence_transformers; import torch; print('✓ sentence-transformers 安装成功'); print('✓ torch 安装成功'); print(''); from sentence_transformers import SentenceTransformer; print('测试模型加载...'); model = SentenceTransformer('all-MiniLM-L6-v2'); print('✓ 模型加载成功'); import torch; print(''); print('✓ CUDA可用' if torch.cuda.is_available() else '○ 使用CPU模式')" 2>nul

if errorlevel 1 (
    echo ✗ 验证失败
    echo 请手动检查安装
) else (
    echo.
    echo ======================================================================
    echo 安装完成！
    echo ======================================================================
    echo.
    echo 现在可以运行:
    echo   python word_lookup.py           # 启动交互界面
    echo   python ai_semantic_demo.py      # 查看演示
)

echo.
pause
