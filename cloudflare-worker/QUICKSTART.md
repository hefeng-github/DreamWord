# 🚀 快速开始指南

本指南将帮助你在5分钟内部署和使用DreamWord Cloudflare Workers版本。

## 📋 前置要求

- Node.js 16.0 或更高版本
- npm 或 yarn
- Cloudflare 账户（免费）
- 基本的命令行操作知识

## 🛠️ 安装步骤

### 1. 克隆或下载项目

```bash
cd G:\Documents\trae_projects\DreamWord\cloudflare-worker
```

### 2. 安装依赖

```bash
npm install
```

### 3. 构建项目

```bash
npm run build
```

### 4. 登录 Cloudflare

```bash
npm run login
```

这将打开浏览器进行OAuth授权。

### 5. 部署到 Cloudflare Workers

```bash
npm run deploy
```

部署完成后，你会看到类似这样的输出：
```
✨ Successfully published your Worker to
  https://dreamword-word-lookup.your-subdomain.workers.dev
```

## 🎯 使用指南

### 访问你的部署

部署成功后，你可以访问以下地址：

- **主页**（简单查词）：`https://your-worker.workers.dev/`
- **智能查词页面**（拍照查词）：`https://your-worker.workers.dev/lookup`
- **测试页面**：`https://your-worker.workers.dev/test`

### 1. 查词预览功能

1. 访问智能查词页面
2. 在"查词预览"标签页输入单词（如 "hello"）
3. 点击"查询"按钮
4. 查看单词的释义、音标、例句等

### 2. 拍照查词功能

#### 使用摄像头拍照：

1. 切换到"拍照查词"标签页
2. 点击"📱 使用摄像头拍照"
3. 允许浏览器访问摄像头权限
4. 对准包含英文单词的文本
5. 点击"📸 拍照"
6. 等待OCR识别完成（2-10秒）
7. 选择要查询的单词（点击标签选中/取消）
8. 点击"🔍 查询选中的单词"

#### 上传图片：

1. 切换到"拍照查词"标签页
2. 点击"📁 点击上传图片"
3. 选择包含英文单词的图片
4. 等待OCR识别完成
5. 选择单词并查询

### 3. API调用

#### JavaScript示例：

```javascript
// 查询单词
async function lookupWord(word) {
  const response = await fetch(
    `https://your-worker.workers.dev/api/lookup?word=${word}`
  );
  return await response.json();
}

// 批量查词
async function batchLookup(words) {
  const response = await fetch(
    `https://your-worker.workers.dev/api/batch-lookup?words=${words.join(',')}`
  );
  return await response.json();
}
```

#### Python示例：

```python
import requests

# 查询单词
def lookup_word(word):
    url = f"https://your-worker.workers.dev/api/lookup?word={word}"
    response = requests.get(url)
    return response.json()

# 批量查词
def batch_lookup(words):
    url = f"https://your-worker.workers.dev/api/batch-lookup?words={','.join(words)}"
    response = requests.get(url)
    return response.json()
```

#### cURL示例：

```bash
# 查询单词
curl "https://your-worker.workers.dev/api/lookup?word=hello"

# 批量查词
curl "https://your-worker.workers.dev/api/batch-lookup?words=hello,world,test"
```

## 🔧 配置选项

### 修改词典API源

编辑 `worker.js` 文件中的配置：

```javascript
const CONFIG = {
  // 使用的词典API：'youdao' 或 'iciba'
  dictionaryAPI: 'youdao',

  // CORS配置（建议修改为你的域名）
  cors: {
    allowOrigin: '*', // 修改为你的域名以增强安全性
    allowMethods: 'GET, POST, OPTIONS',
    allowHeaders: 'Content-Type, Authorization'
  }
};
```

### 自定义域名

#### 方法1：使用 Cloudflare Pages

1. 在Cloudflare Dashboard创建Pages项目
2. 连接你的Worker
3. 绑定自定义域名

#### 方法2：直接绑定

1. 编辑 `wrangler.toml`：
```toml
routes = [
  { pattern = "dict.yourdomain.com/*", zone_name = "yourdomain.com" }
]
```

2. 确保你的域名使用Cloudflare DNS
3. 重新部署：`npm run deploy`

## 📊 监控和日志

### 查看实时日志

```bash
npm run tail
```

### Cloudflare Analytics

访问 [Cloudflare Dashboard](https://dash.cloudflare.com) 查看：
- 请求量统计
- 响应时间
- 错误率
- 地理分布

## 🆘 常见问题

### Q: 部署后无法访问？
A: 检查 `wrangler.toml` 中的 `name` 配置，确保名称正确。等待1-2分钟让全球CDN同步。

### Q: 查词失败？
A:
1. 检查网络连接
2. 尝试切换词典API（修改 `dictionaryAPI` 配置）
3. 查看 Cloudflare Dashboard 中的日志

### Q: OCR识别不准确？
A:
1. 确保图片清晰，文字完整
2. 使用良好的光线条件
3. 确保文字水平排列
4. 尝试裁剪图片只包含文字部分

### Q: 摄像头无法访问？
A:
1. 检查浏览器是否支持摄像头API
2. 确保在HTTPS环境（Cloudflare Workers自动提供）
3. 检查浏览器权限设置
4. 尝试使用不同的浏览器（Chrome、Firefox、Edge）

### Q: 如何查看当前部署版本？
A: 访问 `/api/health` 端点查看版本信息。

## 💡 性能优化建议

1. **使用缓存**：成功查询会被缓存1小时，减少API调用
2. **批量查询**：使用批量API一次性查询多个单词
3. **CDN加速**：Cloudflare全球CDN自动加速，无需额外配置

## 📈 升级和维护

### 更新代码

1. 修改代码
2. 运行构建：`npm run build`
3. 重新部署：`npm run deploy`

### 回滚版本

如果新版本有问题，可以快速回滚：

```bash
# 查看部署历史
wrangler deployments list

# 回滚到特定版本
wrangler rollback [deployment-id]
```

## 🔗 相关链接

- [Cloudflare Workers 文档](https://developers.cloudflare.com/workers/)
- [Wrangler CLI 文档](https://developers.cloudflare.com/workers/wrangler/)
- [DreamWord 主项目](https://github.com/hefeng-github/DreamWord)

## 📞 支持

如有问题，请在 [GitHub Issues](https://github.com/hefeng-github/DreamWord/issues) 提问。

---

**享受使用 DreamWord！** 🎉
