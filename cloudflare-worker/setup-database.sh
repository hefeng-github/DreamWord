#!/bin/bash

# Cloudflare Workers D1 数据库设置脚本

set -e

echo "🔤 DreamWord D1 数据库设置"
echo "================================"

# 检查是否安装了wrangler
if ! command -v wrangler &> /dev/null; then
    echo "❌ 错误: 未找到 wrangler CLI"
    echo "请安装: npm install -g wrangler"
    exit 1
fi

# 1. 创建D1数据库
echo ""
echo "📊 步骤 1/4: 创建D1数据库..."
echo "wrangler d1 create dreamword-dict"
npx wrangler d1 create dreamword-dict

echo ""
echo "⚠️  重要: 请复制上面的 database_id，然后更新 wrangler.toml 文件"
read -p "按回车继续..."

# 2. 初始化数据库表
echo ""
echo "📊 步骤 2/4: 创建数据库表..."
echo "wrangler d1 execute dreamword-dict --file=./schema.sql"
npx wrangler d1 execute dreamword-dict --file=./cloudflare-worker/schema.sql

# 3. 导入词典数据（如果存在）
echo ""
echo "📊 步骤 3/4: 导入词典数据..."

# 检查是否存在Python版本的数据库
if [ -f "databases/word_details.db" ]; then
    echo "✅ 找到Python版本的数据库"
    echo "正在转换数据..."

    # 使用Python脚本转换数据
    if [ -f "cloudflare-worker/import-dict.py" ]; then
        python cloudflare-worker/import-dict.py
    else
        echo "❌ 未找到导入脚本: import-dict.py"
    fi
else
    echo "⚠️  未找到 databases/word_details.db"
    echo "请先运行Python版本或手动导入词典数据"
fi

# 4. 创建KV命名空间（可选）
echo ""
echo "📊 步骤 4/4: 创建KV命名空间（用于缓存）..."
echo "wrangler kv:namespace create WORD_CACHE"
npx wrangler kv:namespace create WORD_CACHE

echo ""
echo "⚠️  重要: 请复制上面的 namespace_id，然后更新 wrangler.toml 文件"

echo ""
echo "✅ 数据库设置完成！"
echo ""
echo "下一步："
echo "1. 更新 wrangler.toml，添加 database_id 和 namespace_id"
echo "2. 运行: npm run deploy"
echo "3. 测试: curl https://your-worker.workers.dev/api/health"
