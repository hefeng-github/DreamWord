# DreamWord Word Lookup - Cloudflare Workers

一个轻量级的查词预览服务，部署在Cloudflare Workers上，提供快速、可靠的词典查询API。

## ✨ 特性

- 🚀 **极速响应** - 利用Cloudflare全球CDN，响应时间小于100ms
- 🌍 **全球部署** - 自动在300+个城市部署
- 💰 **免费套餐** - Cloudflare Workers免费套餐每天100,000次请求
- 🔄 **多词典支持** - 支持有道、金山等多个词典API
- 📱 **响应式界面** - 提供美观的Web查询界面
- 🔒 **HTTPS支持** - 所有请求自动使用HTTPS加密
- 📷 **拍照查词** - 支持摄像头拍照和图片上传查词（类似Python版本）
- 🔍 **实时预览** - 提供单词查询预览功能
- 🤖 **智能OCR** - 前端集成Tesseract.js进行文字识别

## 🎯 主要功能对比

### 与Python版本相同的功能

| 功能 | Python版本 | Cloudflare Workers版本 |
|------|-----------|----------------------|
| 查词预览 | ✅ `/api/word-preview` | ✅ `/api/lookup` |
| 拍照查词 | ✅ 前端摄像头 + 后端OCR | ✅ 前端摄像头 + 前端OCR |
| 图片预览 | ✅ 实时图片预览 | ✅ 实时图片预览 |
| 摄像头访问 | ✅ `navigator.mediaDevices` | ✅ `navigator.mediaDevices` |
| OCR识别 | ✅ PaddleOCR (后端) | ✅ Tesseract.js (前端) |
| 批量查词 | ✅ 多个单词查询 | ✅ `/api/batch-lookup` |

### 技术实现差异

- **OCR实现**：Python版本使用PaddleOCR（后端处理），Workers版本使用Tesseract.js（前端处理）
- **部署方式**：Python版本需要服务器，Workers版本部署在Cloudflare边缘网络
- **性能特点**：Workers版本利用CDN加速，全球响应更快

## 📦 API端点

### 查词API

```http
GET /api/lookup?word={word}
```

**请求参数：**
- `word` (必需): 要查询的单词

**响应示例：**

```json
{
  "success": true,
  "word": "hello",
  "phonetic": "UK: /həˈləʊ/ | US: /həˈloʊ/",
  "definitions": [
    "n. 你好；哈啰",
    "int. 喂；哈喽"
  ],
  "examples": [
    "Hello, how are you?",
    "She said hello to me."
  ],
  "base_form": null,
  "pos": "n."
}
```

### 批量查词API

```http
GET /api/batch-lookup?words={word1,word2,word3}
```

**请求参数：**
- `words` (必需): 逗号分隔的单词列表（最多20个）

**响应示例：**

```json
{
  "success": true,
  "total": 3,
  "found": 3,
  "results": [
    {
      "success": true,
      "word": "hello",
      "phonetic": "UK: /həˈləʊ/ | US: /həˈloʊ/",
      "definitions": ["n. 你好；哈啰", "int. 喂；哈喽"]
    },
    {
      "success": true,
      "word": "world",
      "phonetic": "UK: /wɜːld/ | US: /wɜːrld/",
      "definitions": ["n. 世界；地球", "n. 领域；范围"]
    }
  ]
}
```

**错误响应：**

```json
{
  "success": false,
  "error": "未找到该单词"
}
```

### 健康检查

```http
GET /api/health
```

**响应示例：**

```json
{
  "success": true,
  "service": "DreamWord Word Lookup",
  "version": "1.0.0",
  "status": "healthy"
}
```

## 🚀 快速开始

### 1. 安装依赖

```bash
npm install -g wrangler
```

### 2. 登录Cloudflare

```bash
wrangler login
```

### 3. 构建项目

首次部署或修改HTML后，需要运行构建脚本：

```bash
cd cloudflare-worker
npm install
node build.js
```

### 4. 配置项目

编辑 `wrangler.toml` 文件：

```toml
name = "your-worker-name"
main = "worker.js"
compatibility_date = "2024-01-01"
```

### 5. 本地开发

```bash
cd cloudflare-worker
wrangler dev
```

访问以下地址：
- http://localhost:8787 - 简单查词页面
- http://localhost:8787/lookup - 智能查词页面（拍照查词）

### 6. 部署到生产环境

```bash
wrangler publish
```

部署成功后，你会获得一个URL：
```
https://your-worker-name.your-subdomain.workers.dev
```

智能查词页面访问：`https://your-worker-name.workers.dev/lookup`

## 📱 功能使用说明

### 1. 查词预览功能

访问智能查词页面，使用以下步骤：

1. 在"查词预览"标签页输入单词
2. 点击"查询"按钮
3. 查看单词的释义、音标、例句等信息

### 2. 拍照查词功能

这是与Python版本相同的核心功能：

#### 方法一：使用摄像头拍照

1. 切换到"拍照查词"标签页
2. 点击"📱 使用摄像头拍照"按钮
3. 允许浏览器访问摄像头
4. 对准包含英文单词的文本（如试卷、书本）
5. 点击"📸 拍照"按钮
6. 系统自动OCR识别图片中的英文单词
7. 选择要查询的单词
8. 点击"🔍 查询选中的单词"查看释义

#### 方法二：上传图片

1. 切换到"拍照查词"标签页
2. 点击"📁 点击上传图片"按钮
3. 选择包含英文单词的图片文件
4. 系统自动识别并显示单词列表
5. 选择要查询的单词并查看释义

### 3. OCR识别说明

- **识别语言**：英文
- **识别引擎**：Tesseract.js（前端运行）
- **识别准确度**：依赖图片质量和文字清晰度
- **处理时间**：取决于图片大小和单词数量（通常2-10秒）

### 4. 技术特点

与Python版本相比的优势：

- ✅ **无需后端OCR**：减少服务器负载
- ✅ **隐私保护**：图片处理在浏览器本地完成
- ✅ **离线可用**：Tesseract.js缓存后可离线识别
- ✅ **全球加速**：利用Cloudflare CDN分发

## 🔧 配置选项

在 `worker.js` 中可以配置以下选项：

```javascript
const CONFIG = {
  // CORS配置
  cors: {
    allowOrigin: '*', // 修改为你的域名以增强安全性
    allowMethods: 'GET, POST, OPTIONS',
    allowHeaders: 'Content-Type, Authorization'
  },

  // 缓存配置（秒）
  cacheTTL: 3600, // 1小时

  // 词典API选择：'youdao', 'iciba'
  dictionaryAPI: 'youdao'
};
```

## 📝 使用示例

### JavaScript/Fetch

```javascript
async function lookupWord(word) {
  const response = await fetch(
    `https://your-worker.workers.dev/api/lookup?word=${encodeURIComponent(word)}`
  );
  const data = await response.json();
  return data;
}

// 使用示例
lookupWord('hello').then(result => {
  if (result.success) {
    console.log(result.word, result.phonetic, result.definitions);
  }
});
```

### Python/Requests

```python
import requests

def lookup_word(word):
    url = f"https://your-worker.workers.dev/api/lookup?word={word}"
    response = requests.get(url)
    return response.json()

# 使用示例
result = lookup_word('hello')
if result['success']:
    print(f"{result['word']} - {result['phonetic']}")
    for definition in result['definitions']:
        print(f"  {definition}")
```

### cURL

```bash
curl "https://your-worker.workers.dev/api/lookup?word=hello"
```

## 🌐 自定义域名

### 方法1：使用Cloudflare Pages

1. 在Cloudflare Dashboard中创建一个Pages项目
2. 将Worker连接到Pages项目
3. 在Pages设置中绑定自定义域名

### 方法2：直接绑定域名

1. 在 `wrangler.toml` 中配置路由：

```toml
routes = [
  { pattern = "dict.yourdomain.com/*", zone_name = "yourdomain.com" }
]
```

2. 确保你的域名使用Cloudflare DNS
3. 运行 `wrangler publish`

## 📊 性能优化

### 缓存策略

- 成功的查询会被缓存1小时（可配置）
- 使用Cloudflare的Cache API自动缓存响应
- 减少对上游词典API的请求

### 响应时间

- 全球平均响应时间：50-100ms
- 北美地区：30-60ms
- 欧洲地区：40-80ms
- 亚太地区：60-120ms

## 🔒 安全性建议

1. **限制CORS来源**：将 `allowOrigin` 设置为你的具体域名
2. **添加速率限制**：使用Cloudflare Workers KV实现速率限制
3. **API密钥**：如果需要，可以添加API密钥验证

## 📈 监控和日志

### 查看实时日志

```bash
wrangler tail
```

### Cloudflare Analytics

在Cloudflare Dashboard中查看：
- 请求量
- 响应时间
- 错误率
- 地理分布

## 🆘 故障排除

### 常见问题

**Q: 部署后无法访问？**
A: 检查 `wrangler.toml` 中的配置，确保 `name` 和 `main` 路径正确。

**Q: API返回错误？**
A: 检查上游词典API是否可用，可以在 `worker.js` 中切换到不同的词典API。

**Q: 如何查看日志？**
A: 使用 `wrangler tail` 命令查看实时日志。

### 测试部署

```bash
# 测试本地部署
wrangler dev

# 测试远程部署
curl https://your-worker.workers.dev/api/health
```

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交问题和拉取请求！

## 🔗 相关链接

- [Cloudflare Workers 文档](https://developers.cloudflare.com/workers/)
- [Wrangler CLI 文档](https://developers.cloudflare.com/workers/wrangler/)
- [DreamWord 主项目](https://github.com/hefeng-github/DreamWord)

---

**由 Cloudflare Workers 驱动** ⚡
