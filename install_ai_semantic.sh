#!/bin/bash
# AI语义匹配功能 - 快速安装脚本

echo "======================================================================"
echo "             AI智能语义匹配功能 - 依赖安装"
echo "======================================================================"
echo ""

# 检查Python版本
python_version=$(python --version 2>&1 | awk '{print $2}')
echo "检测到 Python 版本: $python_version"

# 版本检查
if command -v python &> /dev/null; then
    major=$(python -c 'import sys; print(sys.version_info.major)')
    minor=$(python -c 'import sys; print(sys.version_info.minor)')

    if [ $major -lt 3 ] || ([ $major -eq 3 ] && [ $minor -lt 8 ]); then
        echo "⚠ 警告: 需要Python 3.8或更高版本"
        exit 1
    fi
else
    echo "✗ 错误: 未找到Python"
    exit 1
fi

echo ""
echo "======================================================================"
echo "安装说明"
echo "======================================================================"
echo ""
echo "本脚本将安装以下依赖:"
echo "  - sentence-transformers: 语义模型库"
echo "  - torch: 深度学习框架"
echo ""
echo "安装后大小:"
echo "  - 基础库: ~50MB"
echo "  - 预训练模型: ~200MB (首次运行时自动下载)"
echo ""

read -p "是否继续安装? (y/n): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "安装已取消"
    exit 0
fi

echo ""
echo "======================================================================"
echo "开始安装..."
echo "======================================================================"
echo ""

# 安装命令
if command -v pip &> /dev/null; then
    pip install sentence-transformers torch
else
    echo "✗ 错误: 未找到pip"
    exit 1
fi

# 检查安装结果
echo ""
echo "======================================================================"
echo "验证安装"
echo "======================================================================"
echo ""

python -c "
try:
    import sentence_transformers
    import torch
    print('✓ sentence-transformers 安装成功')
    print('✓ torch 安装成功')

    # 测试模型加载
    from sentence_transformers import SentenceTransformer
    print('')
    print('测试模型加载...')
    model = SentenceTransformer('all-MiniLM-L6-v2')
    print('✓ 模型加载成功')

    # 检查CUDA
    if torch.cuda.is_available():
        print('✓ CUDA可用 (GPU加速已启用)')
    else:
        print('○ 使用CPU模式')

    print('')
    print('======================================================================')
    print('安装完成！')
    print('======================================================================')
    print('')
    print('现在可以运行:')
    print('  python word_lookup.py           # 启动交互界面')
    print('  python ai_semantic_demo.py      # 查看演示')

except ImportError as e:
    print(f'✗ 安装失败: {e}')
    exit(1)
except Exception as e:
    print(f'⚠ 警告: {e}')
    print('基础功能可用，但模型加载可能有问题')
"

echo ""
