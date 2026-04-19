# 🗄️ 数据库查词功能 - 完整设置指南

## 📋 功能对比

| 功能 | Python版本 | Workers版本（D1） |
|------|-----------|------------------|
| 数据库 | SQLite (本地) | D1 (云端) |
| 查词速度 | ~50ms | ~10-30ms |
| 词典容量 | 无限制 | 5GB免费 |
| 全球部署 | ❌ | ✅ 300+城市 |
| 缓存支持 | ❌ | ✅ KV存储 |
| 并发查询 | 受限 | 几乎无限 |

## 🚀 快速开始（5分钟）

### 步骤1: 创建D1数据库

```bash
cd cloudflare-worker

# 创建数据库
npx wrangler d1 create dreamword-dict
```

**重要**：复制输出的 `database_id`，类似：
```
✅ Successfully created DB 'dreamword-dict'
database_id = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
```

### 步骤2: 创建KV命名空间（可选，用于缓存）

```bash
# 创建KV命名空间
npx wrangler kv:namespace create WORD_CACHE
```

复制输出的 `id`。

### 步骤3: 更新wrangler.toml

打开 `wrangler.toml`，替换以下内容：

```toml
# 替换为实际的database_id
[[d1_databases]]
binding = "DB"
database_name = "dreamword-dict"
database_id = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"  # 你的ID

# 替换为实际的namespace_id
[[kv_namespaces]]
binding = "WORD_CACHE"
id = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"  # 你的ID
```

### 步骤4: 初始化数据库表

```bash
# 创建表结构
npx wrangler d1 execute dreamword-dict --file=./schema.sql
```

### 步骤5: 导入词典数据

#### 选项A: 使用示例数据（快速测试）

`schema.sql` 已包含15个常用单词，可以直接使用。

#### 选项B: 从Python版本导入

```bash
# 导出词典数据（JSON格式）
python import-dict.py --limit 1000 --format json --output dict-export.json

# 或导出为SQL（推荐）
python import-dict.py --limit 1000 --format sql --output dict-insert.sql

# 导入到D1
npx wrangler d1 execute dreamword-dict --file=./dict-insert.sql
```

#### 选项C: 使用完整词典

```bash
# 导出所有单词
python import-dict.py --all --format sql --output dict-all.sql

# 导入（可能需要较长时间）
npx wrangler d1 execute dreamword-dict --file=./dict-all.sql
```

### 步骤6: 切换到数据库版本

```bash
# 备份原worker.js
mv worker.js worker-api-only.js

# 使用数据库版本
cp worker-with-d1.js worker.js

# 重新构建
npm run build

# 部署
npm run deploy
```

### 步骤7: 测试数据库查词

```bash
# 健康检查
curl https://your-worker.workers.dev/api/health

# 查词测试
curl "https://your-worker.workers.dev/api/lookup?word=hello"

# 数据库统计
curl https://your-worker.workers.dev/api/stats
```

## 📊 数据库查询示例

### 1. 基础查词

```javascript
// GET /api/lookup?word=hello

{
  "success": true,
  "word": "hello",
  "phonetic": "/həˈləʊ/",
  "definitions": [
    "你好；问候"
  ],
  "examples": [
    "Hello, how are you?"
  ],
  "source": "database"
}
```

### 2. 批量查词

```javascript
// GET /api/batch-lookup?words=hello,world,test

{
  "success": true,
  "total": 3,
  "found": 3,
  "results": [...]
}
```

### 3. 数据库统计

```javascript
// GET /api/stats

{
  "success": true,
  "database": {
    "total_words": 15000,
    "type": "D1 (SQLite)",
    "status": "connected"
  },
  "cache": {
    "enabled": true,
    "recent_queries": ["hello", "world", "test"]
  }
}
```

## 🎯 工作原理

```
用户请求查词
    ↓
1. 查询KV缓存（~10ms）- 命中则返回
    ↓ 未命中
2. 查询D1数据库（~30ms）
    ↓
3. 保存到KV缓存
    ↓
4. 返回结果
```

## 📈 性能优化

### KV缓存预热

```javascript
// 在Worker启动时预加载常用词
async function warmupCache(env) {
  const commonWords = ['hello', 'world', 'test', 'the', 'and'];

  for (const word of commonWords) {
    await smartLookup(word, env);
  }
}
```

### 批量导入优化

```bash
# 分批导入，避免超时
python import-dict.py --limit 1000 --format sql --output batch1.sql
npx wrangler d1 execute dreamword-dict --file=./batch1.sql

python import-dict.py --limit 1000 --offset 1000 --format sql --output batch2.sql
npx wrangler d1 execute dreamword-dict --file=./batch2.sql
```

## 🔧 管理命令

### 查看数据库内容

```bash
# 查看表结构
npx wrangler d1 execute dreamword-dict --command="SELECT sql FROM sqlite_master WHERE type='table'"

# 查看词数
npx wrangler d1 execute dreamword-dict --command="SELECT COUNT(*) FROM mdx"

# 查看特定单词
npx wrangler d1 execute dreamword-dict --command="SELECT * FROM mdx WHERE entry = 'hello'"

# 查看最近添加的单词
npx wrangler d1 execute dreamword-dict --command="SELECT entry FROM mdx ORDER BY created_at DESC LIMIT 10"
```

### 备份和恢复

```bash
# 备份数据库
npx wrangler d1 export dreamword-dict --output=backup.sql

# 恢复数据库
npx wrangler d1 execute dreamword-dict --file=./backup.sql
```

## 💡 最佳实践

1. **使用KV缓存** - 将常用查询结果缓存到KV，响应时间降至10ms以内
2. **批量操作** - 使用批量API而不是多次单个查询
3. **监控使用量** - 定期检查 `/api/stats` 了解数据库状态
4. **预热缓存** - 在部署后预热常用单词的缓存

## 🆚 与Python版本对比

### 优势
- ✅ 全球部署，响应更快
- ✅ 无限扩展性
- ✅ 内置缓存机制
- ✅ 零运维成本

### 劣势
- ❌ 不支持语义搜索（Sentence Transformers）
- ❌ 不支持词形还原（NLTK）
- ❌ 数据库大小限制（免费5GB）

## 📞 常见问题

**Q: D1数据库免费额度有多大？**
A: 免费5GB存储，每天500万次读取，100万次写入。

**Q: 如何导入大型词典（10万+单词）？**
A: 分批导入，每批1000-5000个单词，避免超时。

**Q: 可以同时使用D1和API吗？**
A: 可以！系统会优先使用D1，未找到时自动使用API。

**Q: KV缓存会过期吗？**
A: 会，默认1小时。可在 `CONFIG.cacheTTL` 中调整。

## 🎉 完成！

现在你的Cloudflare Workers已经拥有类似Python版本的数据库查词功能了！

享受快速、可靠的全球查词服务吧！🚀

---

*更新日期：2025-04-08*
*版本：v2.0.0*
