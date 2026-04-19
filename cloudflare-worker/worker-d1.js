# 🔤 Cloudflare Workers 数据库查词方案

## 📊 方案对比

### Python版本（现有）
- **数据库**: SQLite (word_details.db)
- **格式**: MDX词典格式
- **特点**:
  - 完整的词典数据
  - 语义搜索（Sentence Transformers）
  - 词形还原（NLTK）
  - 语境智能匹配

### Cloudflare Workers方案（推荐）

#### 方案1: Cloudflare D1（最接近Python版本）⭐⭐⭐⭐⭐
```javascript
// 类似Python的SQLite，但运行在边缘
优势：
✅ 完整的SQL支持
✅ 与Python版本数据库格式兼容
✅ 全球分布式部署
✅ 免费额度：5GB存储，每天500万次读取

限制：
• 需要创建D1数据库
• 需要导入词典数据
```

#### 方案2: Cloudflare KV（键值存储）⭐⭐⭐⭐
```javascript
// 简单的键值对存储
优势：
✅ 超快速（< 10ms）
✅ 无限扩展
✅ 免费：1GB存储，每天1亿次读取

限制：
• 只支持简单键值查询
• 不支持SQL
• 需要预先导入数据
```

#### 方案3: 嵌入式词典（最简单）⭐⭐⭐
```javascript
// 直接打包常用单词到Worker代码
优势：
✅ 无需数据库
✅ 最快速度
✅ 零配置

限制：
• 只能包含常用单词（~5000-10000个）
• 增加Worker包大小
```

## 🎯 推荐方案：D1 + KV混合

结合所有方案的优势：

```javascript
// 查词流程
1. 先查KV缓存（最快）
2. KV未命中，查D1数据库
3. D1结果写入KV缓存
4. 定期预热常用词到KV
```

## 📦 实现步骤

### 步骤1: 创建D1数据库

```bash
# 创建数据库
npx wrangler d1 create dreamword-dict

# 记录输出的database_id
```

### 步骤2: 配置wrangler.toml

```toml
# 添加D1绑定
[[d1_databases]]
binding = "DB"
database_name = "dreamword-dict"
database_id = "你的database_id"
```

### 步骤3: 创建数据库表结构

```sql
-- 创建词典表（与Python版本兼容）
CREATE TABLE IF NOT EXISTS mdx (
  entry TEXT PRIMARY KEY,
  paraphrase TEXT NOT NULL
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_entry ON mdx(entry);

-- 创建缓存表（可选）
CREATE TABLE IF NOT EXISTS word_cache (
  word TEXT PRIMARY KEY,
  data JSON NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 步骤4: 导入词典数据

从Python版本的SQLite导入到D1。

## 🚀 现在就开始实现

我将创建完整的实现，包括：
1. D1数据库查词
2. KV缓存优化
3. 词典导入工具
4. 前端界面更新

准备好开始了吗？
