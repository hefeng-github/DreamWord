/**
 * DreamWord Word Lookup - Cloudflare Workers Version
 *
 * 一个轻量级的查词预览服务，部署在Cloudflare Workers上
 * 支持查词和预览功能
 */

// =============================================
// 配置
// =============================================

// 智能查词页面HTML（由build.js生成）
const SMART_LOOKUP_HTML = '<!DOCTYPE html>\n<html lang="zh-CN">\n<head>\n    <meta charset="UTF-8">\n    <meta name="viewport" content="width=device-width, initial-scale=1.0">\n    <title>DreamWord - 智能查词预览</title>\n    <style>\n        * {\n            margin: 0;\n            padding: 0;\n            box-sizing: border-box;\n        }\n\n        body {\n            font-family: -apple-system, BlinkMacSystemFont, \'Segoe UI\', Roboto, sans-serif;\n            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);\n            min-height: 100vh;\n            display: flex;\n            justify-content: center;\n            align-items: center;\n            padding: 20px;\n        }\n\n        .container {\n            background: white;\n            border-radius: 16px;\n            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);\n            max-width: 800px;\n            width: 100%;\n            padding: 40px;\n        }\n\n        h1 {\n            color: #333;\n            margin-bottom: 10px;\n            font-size: 28px;\n            text-align: center;\n        }\n\n        .subtitle {\n            color: #666;\n            margin-bottom: 30px;\n            font-size: 14px;\n            text-align: center;\n        }\n\n        /* 标签页导航 */\n        .tabs {\n            display: flex;\n            gap: 10px;\n            margin-bottom: 30px;\n            flex-wrap: wrap;\n            justify-content: center;\n        }\n\n        .tab-button {\n            padding: 12px 24px;\n            background: #f0f0f0;\n            color: #666;\n            border: none;\n            border-radius: 8px;\n            font-size: 14px;\n            font-weight: 600;\n            cursor: pointer;\n            transition: all 0.3s;\n        }\n\n        .tab-button:hover {\n            background: #e0e0e0;\n        }\n\n        .tab-button.active {\n            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);\n            color: white;\n        }\n\n        /* 标签页内容 */\n        .tab-content {\n            display: none;\n        }\n\n        .tab-content.active {\n            display: block;\n        }\n\n        /* 查词输入框 */\n        .search-box {\n            display: flex;\n            gap: 10px;\n            margin-bottom: 30px;\n        }\n\n        input[type="text"], textarea {\n            width: 100%;\n            padding: 15px 20px;\n            border: 2px solid #e0e0e0;\n            border-radius: 8px;\n            font-size: 16px;\n            transition: border-color 0.3s;\n            font-family: inherit;\n        }\n\n        input[type="text"]:focus, textarea:focus {\n            outline: none;\n            border-color: #667eea;\n        }\n\n        textarea {\n            resize: vertical;\n            min-height: 100px;\n        }\n\n        button {\n            padding: 15px 30px;\n            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);\n            color: white;\n            border: none;\n            border-radius: 8px;\n            font-size: 16px;\n            font-weight: 600;\n            cursor: pointer;\n            transition: transform 0.2s;\n            white-space: nowrap;\n        }\n\n        button:hover {\n            transform: translateY(-2px);\n        }\n\n        button:active {\n            transform: translateY(0);\n        }\n\n        button:disabled {\n            opacity: 0.6;\n            cursor: not-allowed;\n        }\n\n        button.secondary {\n            background: #6c757d;\n        }\n\n        button.camera-btn {\n            background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);\n        }\n\n        /* 图片上传和预览 */\n        .upload-section {\n            margin-bottom: 20px;\n        }\n\n        .upload-section label {\n            display: block;\n            margin-bottom: 10px;\n            font-weight: 600;\n            color: #333;\n        }\n\n        input[type="file"] {\n            display: none;\n        }\n\n        .file-upload-btn {\n            display: inline-block;\n            padding: 12px 24px;\n            background: #f0f0f0;\n            border: 2px dashed #ccc;\n            border-radius: 8px;\n            cursor: pointer;\n            text-align: center;\n            width: 100%;\n            transition: all 0.3s;\n        }\n\n        .file-upload-btn:hover {\n            border-color: #667eea;\n            background: #f8f9ff;\n        }\n\n        .preview-section {\n            margin: 20px 0;\n            text-align: center;\n        }\n\n        .preview-section img {\n            max-width: 100%;\n            max-height: 400px;\n            border-radius: 8px;\n            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);\n            display: none;\n        }\n\n        .preview-section img.show {\n            display: inline-block;\n        }\n\n        /* 摄像头区域 */\n        .camera-section {\n            margin: 20px 0;\n        }\n\n        .camera-container {\n            position: relative;\n            margin: 20px 0;\n            display: none;\n        }\n\n        .camera-container.show {\n            display: block;\n        }\n\n        #cameraVideo {\n            width: 100%;\n            max-height: 400px;\n            border-radius: 8px;\n            background: #000;\n        }\n\n        .camera-controls {\n            display: flex;\n            gap: 10px;\n            margin-top: 15px;\n            justify-content: center;\n        }\n\n        .camera-controls button {\n            flex: 1;\n        }\n\n        /* OCR 结果显示 */\n        .ocr-results {\n            margin: 20px 0;\n            padding: 20px;\n            background: #f8f9fa;\n            border-radius: 8px;\n        }\n\n        .ocr-results h3 {\n            margin-bottom: 15px;\n            color: #333;\n        }\n\n        .word-list {\n            display: flex;\n            flex-wrap: wrap;\n            gap: 10px;\n            margin-bottom: 15px;\n        }\n\n        .word-tag {\n            padding: 8px 16px;\n            background: white;\n            border: 2px solid #e0e0e0;\n            border-radius: 20px;\n            cursor: pointer;\n            transition: all 0.3s;\n        }\n\n        .word-tag:hover {\n            border-color: #667eea;\n            background: #f8f9ff;\n        }\n\n        .word-tag.selected {\n            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);\n            color: white;\n            border-color: #667eea;\n        }\n\n        /* 查词结果显示 */\n        .result {\n            background: #f8f9fa;\n            border-radius: 8px;\n            padding: 20px;\n            margin: 20px 0;\n            display: none;\n        }\n\n        .result.show {\n            display: block;\n            animation: fadeIn 0.3s ease;\n        }\n\n        @keyframes fadeIn {\n            from { opacity: 0; transform: translateY(10px); }\n            to { opacity: 1; transform: translateY(0); }\n        }\n\n        .word {\n            font-size: 32px;\n            font-weight: 700;\n            color: #333;\n            margin-bottom: 10px;\n        }\n\n        .phonetic {\n            color: #666;\n            font-size: 18px;\n            margin-bottom: 15px;\n        }\n\n        .definitions {\n            margin-bottom: 15px;\n        }\n\n        .definitions h3 {\n            font-size: 14px;\n            color: #888;\n            margin-bottom: 10px;\n            text-transform: uppercase;\n        }\n\n        .definitions ul {\n            list-style: none;\n        }\n\n        .definitions li {\n            padding: 8px 0;\n            color: #444;\n            border-bottom: 1px solid #e0e0e0;\n        }\n\n        .examples h3 {\n            font-size: 14px;\n            color: #888;\n            margin-bottom: 10px;\n            text-transform: uppercase;\n        }\n\n        .examples li {\n            padding: 8px 0;\n            color: #666;\n            font-style: italic;\n        }\n\n        .loading {\n            text-align: center;\n            padding: 20px;\n            color: #888;\n        }\n\n        .spinner {\n            border: 3px solid #f3f3f3;\n            border-top: 3px solid #667eea;\n            border-radius: 50%;\n            width: 40px;\n            height: 40px;\n            animation: spin 1s linear infinite;\n            margin: 0 auto 15px;\n        }\n\n        @keyframes spin {\n            0% { transform: rotate(0deg); }\n            100% { transform: rotate(360deg); }\n        }\n\n        .error {\n            background: #fee;\n            color: #c33;\n            padding: 15px;\n            border-radius: 8px;\n            text-align: center;\n            margin: 20px 0;\n        }\n\n        .success {\n            background: #efe;\n            color: #3c3;\n            padding: 15px;\n            border-radius: 8px;\n            text-align: center;\n            margin: 20px 0;\n        }\n\n        .info {\n            background: #e3f2fd;\n            color: #1976d2;\n            padding: 15px;\n            border-radius: 8px;\n            margin: 20px 0;\n            font-size: 14px;\n        }\n\n        .progress-bar {\n            width: 100%;\n            height: 4px;\n            background: #e0e0e0;\n            border-radius: 2px;\n            overflow: hidden;\n            margin: 15px 0;\n        }\n\n        .progress-fill {\n            height: 100%;\n            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);\n            width: 0%;\n            transition: width 0.3s;\n        }\n\n        /* 响应式设计 */\n        @media (max-width: 600px) {\n            .container {\n                padding: 20px;\n            }\n\n            .tabs {\n                flex-direction: column;\n            }\n\n            .search-box {\n                flex-direction: column;\n            }\n\n            .camera-controls {\n                flex-direction: column;\n            }\n        }\n    </style>\n</head>\n<body>\n    <div class="container">\n        <h1>🔍 DreamWord 智能查词</h1>\n        <p class="subtitle">拍照查词 • 实时预览 • 智能识别</p>\n\n        <!-- 标签页导航 -->\n        <div class="tabs">\n            <button class="tab-button active" onclick="switchTab(\'lookup\')">📝 查词预览</button>\n            <button class="tab-button" onclick="switchTab(\'camera\')">📷 拍照查词</button>\n        </div>\n\n        <!-- 查词预览标签页 -->\n        <div id="tab-lookup" class="tab-content active">\n            <div class="search-box">\n                <input type="text" id="wordInput" placeholder="输入要查询的单词..." />\n                <button onclick="lookupWord()">查询</button>\n            </div>\n\n            <div id="lookupResult" class="result"></div>\n        </div>\n\n        <!-- 拍照查词标签页 -->\n        <div id="tab-camera" class="tab-content">\n            <div class="upload-section">\n                <label>选择图片或拍照：</label>\n                <label class="file-upload-btn">\n                    <input type="file" id="imageUpload" accept="image/*" onchange="handleImageUpload(event)">\n                    📁 点击上传图片\n                </label>\n            </div>\n\n            <div class="camera-section">\n                <button class="camera-btn" onclick="startCamera()" style="width: 100%;">\n                    📱 使用摄像头拍照\n                </button>\n\n                <div class="camera-container" id="cameraContainer">\n                    <video id="cameraVideo" autoplay playsinline></video>\n                    <canvas id="cameraCanvas" style="display: none;"></canvas>\n                    <div class="camera-controls">\n                        <button onclick="capturePhoto()">📸 拍照</button>\n                        <button class="secondary" onclick="stopCamera()">❌ 关闭</button>\n                    </div>\n                </div>\n            </div>\n\n            <div class="preview-section">\n                <img id="imagePreview" alt="图片预览">\n            </div>\n\n            <div class="ocr-results" id="ocrResults" style="display: none;">\n                <h3>识别到的单词：</h3>\n                <div class="word-list" id="wordList"></div>\n                <div style="text-align: center; margin-top: 15px;">\n                    <button onclick="lookupSelectedWords()" id="lookupSelectedBtn" disabled>\n                        🔍 查询选中的单词\n                    </button>\n                </div>\n            </div>\n\n            <div id="cameraResult" class="result"></div>\n        </div>\n\n        <!-- 加载提示 -->\n        <div id="loadingIndicator" style="display: none; text-align: center; padding: 20px;">\n            <div class="spinner"></div>\n            <p style="color: #888; margin-top: 10px;" id="loadingText">处理中...</p>\n        </div>\n    </div>\n\n    <!-- Tesseract.js CDN -->\n    <script src="https://cdn.jsdelivr.net/npm/tesseract.js@5/dist/tesseract.min.js"></script>\n\n    <script>\n        // 全局变量\n        let cameraStream = null;\n        let selectedWords = new Set();\n        let recognizedWords = [];\n\n        // 切换标签页\n        function switchTab(tabName) {\n            // 隐藏所有标签页\n            document.querySelectorAll(\'.tab-content\').forEach(tab => {\n                tab.classList.remove(\'active\');\n            });\n\n            // 移除所有按钮的active类\n            document.querySelectorAll(\'.tab-button\').forEach(btn => {\n                btn.classList.remove(\'active\');\n            });\n\n            // 显示选中的标签页\n            document.getElementById(`tab-${tabName}`).classList.add(\'active\');\n\n            // 激活对应按钮\n            event.target.classList.add(\'active\');\n\n            // 切换标签时关闭摄像头\n            if (tabName !== \'camera\') {\n                stopCamera();\n            }\n        }\n\n        // 显示加载提示\n        function showLoading(text = \'处理中...\') {\n            document.getElementById(\'loadingText\').textContent = text;\n            document.getElementById(\'loadingIndicator\').style.display = \'block\';\n        }\n\n        // 隐藏加载提示\n        function hideLoading() {\n            document.getElementById(\'loadingIndicator\').style.display = \'none\';\n        }\n\n        // 显示错误信息\n        function showError(message) {\n            const resultDiv = document.getElementById(\'lookupResult\');\n            resultDiv.innerHTML = `<div class="error">${message}</div>`;\n            resultDiv.classList.add(\'show\');\n        }\n\n        // 显示成功信息\n        function showSuccess(message) {\n            const resultDiv = document.getElementById(\'lookupResult\');\n            resultDiv.innerHTML = `<div class="success">${message}</div>`;\n            resultDiv.classList.add(\'show\');\n        }\n\n        // 查询单词\n        async function lookupWord(word = null) {\n            const inputWord = word || document.getElementById(\'wordInput\').value.trim();\n\n            if (!inputWord) {\n                showError(\'请输入要查询的单词\');\n                return;\n            }\n\n            showLoading(\'查询中...\');\n\n            try {\n                const response = await fetch(`/api/lookup?word=${encodeURIComponent(inputWord)}`);\n                const data = await response.json();\n\n                if (data.success) {\n                    displayWordResult(data, \'lookupResult\');\n                } else {\n                    showError(data.error || \'未找到该单词\');\n                }\n            } catch (error) {\n                showError(\'查询失败：\' + error.message);\n            } finally {\n                hideLoading();\n            }\n        }\n\n        // 显示查词结果\n        function displayWordResult(data, containerId) {\n            const resultDiv = document.getElementById(containerId);\n\n            let html = `\n                <div class="word">${data.word}</div>\n                ${data.phonetic ? `<div class="phonetic">${data.phonetic}</div>` : \'\'}\n            `;\n\n            if (data.definitions && data.definitions.length > 0) {\n                html += \'<div class="definitions"><h3>释义</h3><ul>\';\n                data.definitions.forEach(def => {\n                    html += `<li>${def}</li>`;\n                });\n                html += \'</ul></div>\';\n            }\n\n            if (data.examples && data.examples.length > 0) {\n                html += \'<div class="examples"><h3>例句</h3><ul>\';\n                data.examples.slice(0, 3).forEach(ex => {\n                    html += `<li>${ex}</li>`;\n                });\n                html += \'</ul></div>\';\n            }\n\n            resultDiv.innerHTML = html;\n            resultDiv.classList.add(\'show\');\n        }\n\n        // 启动摄像头\n        async function startCamera() {\n            const video = document.getElementById(\'cameraVideo\');\n            const container = document.getElementById(\'cameraContainer\');\n\n            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {\n                showError(\'您的浏览器不支持摄像头功能\');\n                return;\n            }\n\n            try {\n                const stream = await navigator.mediaDevices.getUserMedia({\n                    video: {\n                        facingMode: \'environment\',\n                        width: { ideal: 1920 },\n                        height: { ideal: 1080 }\n                    }\n                });\n\n                cameraStream = stream;\n                video.srcObject = stream;\n                container.classList.add(\'show\');\n            } catch (error) {\n                showError(\'无法访问摄像头：\' + error.message);\n            }\n        }\n\n        // 拍照\n        function capturePhoto() {\n            const video = document.getElementById(\'cameraVideo\');\n            const canvas = document.getElementById(\'cameraCanvas\');\n            const preview = document.getElementById(\'imagePreview\');\n\n            if (!cameraStream) {\n                showError(\'请先启动摄像头\');\n                return;\n            }\n\n            canvas.width = video.videoWidth;\n            canvas.height = video.videoHeight;\n\n            const ctx = canvas.getContext(\'2d\');\n            ctx.drawImage(video, 0, 0);\n\n            const imageUrl = canvas.toDataURL(\'image/png\');\n            preview.src = imageUrl;\n            preview.classList.add(\'show\');\n\n            // 处理图片中的文字\n            processImage(imageUrl);\n\n            // 关闭摄像头\n            stopCamera();\n        }\n\n        // 关闭摄像头\n        function stopCamera() {\n            if (cameraStream) {\n                const tracks = cameraStream.getTracks();\n                tracks.forEach(track => track.stop());\n                cameraStream = null;\n            }\n\n            const video = document.getElementById(\'cameraVideo\');\n            video.srcObject = null;\n            document.getElementById(\'cameraContainer\').classList.remove(\'show\');\n        }\n\n        // 处理图片上传\n        function handleImageUpload(event) {\n            const file = event.target.files[0];\n            if (!file) return;\n\n            const reader = new FileReader();\n            reader.onload = function(e) {\n                const preview = document.getElementById(\'imagePreview\');\n                preview.src = e.target.result;\n                preview.classList.add(\'show\');\n\n                // 处理图片中的文字\n                processImage(e.target.result);\n            };\n            reader.readAsDataURL(file);\n        }\n\n        // 处理图片中的文字（OCR识别）\n        async function processImage(imageData) {\n            showLoading(\'正在识别图片中的文字...\');\n            selectedWords.clear();\n            recognizedWords = [];\n\n            try {\n                // 使用Tesseract.js进行OCR识别\n                const result = await Tesseract.recognize(\n                    imageData,\n                    \'eng\',\n                    {\n                        logger: m => {\n                            if (m.status === \'recognizing text\') {\n                                const progress = Math.round(m.progress * 100);\n                                document.getElementById(\'loadingText\').textContent =\n                                    `识别中... ${progress}%`;\n                            }\n                        }\n                    }\n                );\n\n                // 提取英文单词\n                const text = result.data.text;\n                const words = text\n                    .toLowerCase()\n                    .replace(/[^\\w\\s]/g, \' \')\n                    .split(/\\s+/)\n                    .filter(word => word.length > 2 && /^[a-z]+$/.test(word));\n\n                // 去重\n                recognizedWords = [...new Set(words)];\n\n                if (recognizedWords.length === 0) {\n                    showError(\'未识别到英文单词，请确保图片清晰且包含英文文字\');\n                    return;\n                }\n\n                // 显示识别结果\n                displayOCRResults(recognizedWords);\n\n            } catch (error) {\n                showError(\'OCR识别失败：\' + error.message);\n            } finally {\n                hideLoading();\n            }\n        }\n\n        // 显示OCR识别结果\n        function displayOCRResults(words) {\n            const ocrResults = document.getElementById(\'ocrResults\');\n            const wordList = document.getElementById(\'wordList\');\n\n            wordList.innerHTML = \'\';\n\n            words.forEach(word => {\n                const tag = document.createElement(\'div\');\n                tag.className = \'word-tag\';\n                tag.textContent = word;\n                tag.onclick = () => toggleWordSelection(word, tag);\n                wordList.appendChild(tag);\n            });\n\n            ocrResults.style.display = \'block\';\n            updateLookupButton();\n        }\n\n        // 切换单词选择状态\n        function toggleWordSelection(word, element) {\n            if (selectedWords.has(word)) {\n                selectedWords.delete(word);\n                element.classList.remove(\'selected\');\n            } else {\n                selectedWords.add(word);\n                element.classList.add(\'selected\');\n            }\n            updateLookupButton();\n        }\n\n        // 更新查询按钮状态\n        function updateLookupButton() {\n            const btn = document.getElementById(\'lookupSelectedBtn\');\n            btn.disabled = selectedWords.size === 0;\n            btn.textContent = selectedWords.size > 0\n                ? `🔍 查询选中的单词 (${selectedWords.size})`\n                : \'🔍 查询选中的单词\';\n        }\n\n        // 查询选中的单词\n        async function lookupSelectedWords() {\n            if (selectedWords.size === 0) return;\n\n            const words = Array.from(selectedWords);\n            const resultDiv = document.getElementById(\'cameraResult\');\n\n            showLoading(\'查询中...\');\n            resultDiv.innerHTML = \'\';\n\n            try {\n                // 串行查询所有单词\n                for (const word of words) {\n                    const response = await fetch(`/api/lookup?word=${encodeURIComponent(word)}`);\n                    const data = await response.json();\n\n                    if (data.success) {\n                        const wordResult = document.createElement(\'div\');\n                        wordResult.className = \'result show\';\n                        wordResult.style.marginBottom = \'20px\';\n                        wordResult.innerHTML = `\n                            <div class="word">${data.word}</div>\n                            ${data.phonetic ? `<div class="phonetic">${data.phonetic}</div>` : \'\'}\n                        `;\n\n                        if (data.definitions && data.definitions.length > 0) {\n                            wordResult.innerHTML += \'<div class="definitions"><h3>释义</h3><ul>\';\n                            data.definitions.forEach(def => {\n                                wordResult.innerHTML += `<li>${def}</li>`;\n                            });\n                            wordResult.innerHTML += \'</ul></div>\';\n                        }\n\n                        resultDiv.appendChild(wordResult);\n                    }\n                }\n\n                if (resultDiv.children.length === 0) {\n                    showError(\'未找到任何单词的释义\');\n                }\n\n            } catch (error) {\n                showError(\'查询失败：\' + error.message);\n            } finally {\n                hideLoading();\n            }\n        }\n\n        // 回车键查询\n        document.getElementById(\'wordInput\').addEventListener(\'keypress\', function(e) {\n            if (e.key === \'Enter\') {\n                lookupWord();\n            }\n        });\n\n        // 页面卸载时关闭摄像头\n        window.addEventListener(\'beforeunload\', function() {\n            stopCamera();\n        });\n    </script>\n</body>\n</html>\n';

const CONFIG = {
  // CORS配置
  cors: {
    allowOrigin: '*',
    allowMethods: 'GET, POST, OPTIONS',
    allowHeaders: 'Content-Type, Authorization'
  },

  // 缓存配置（秒）
  cacheTTL: 3600, // 1小时

  // API密钥（如果需要）
  apiKey: '', // 留空则使用免费API

  // 使用的词典API类型：'youdao', 'iciba', 'dictionaryapi', 'auto'
  // 'auto' 模式会自动尝试所有可用的API，直到找到可用的
  dictionaryAPI: 'auto',

  // API超时时间（毫秒）
  apiTimeout: 5000
};

// =============================================
// 词典API实现
// =============================================

/**
 * 带超时的fetch请求
 */
async function fetchWithTimeout(url, options = {}, timeout = CONFIG.apiTimeout) {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeout);

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal
    });
    clearTimeout(id);
    return response;
  } catch (error) {
    clearTimeout(id);
    if (error.name === 'AbortError') {
      throw new Error('Request timeout');
    }
    throw error;
  }
}

/**
 * 有道词典API（优化版）
 */
async function fetchYoudao(word) {
  try {
    const url = `https://dict.youdao.com/jsonapi?xmlVersion=5.1&dicts=%7B%22counts%22:%5B2%2C0%2C0%2C0%5D,%22dicts%22:%5B%22ec%22,%22ce%22,%22jc%22,%22ct%22%5D%7D&jsonversion=2&client=mobile&q=${encodeURIComponent(word)}`;

    const response = await fetchWithTimeout(url, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
      }
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    // 检查响应内容类型
    const contentType = response.headers.get('content-type');
    if (!contentType || !contentType.includes('application/json')) {
      // 可能返回了HTML错误页面
      const text = await response.text();
      console.error('Youdao API non-JSON response:', text.substring(0, 200));
      throw new Error('API返回非JSON响应，可能被防火墙拦截');
    }

    const data = await response.json();
    return parseYoudaoResponse(data, word);
  } catch (error) {
    console.error('Youdao API error:', error);
    return {
      success: false,
      error: error.message || '有道词典暂时不可用',
      api: 'youdao'
    };
  }
}

/**
 * 解析有道词典API响应
 */
function parseYoudaoResponse(data, word) {
  try {
    if (!data || !data.ec) {
      return {
        success: false,
        error: '未找到该单词'
      };
    }

    const ec = data.ec.word;
    if (!ec) {
      return {
        success: false,
        error: '未找到该单词'
      };
    }

    // 提取音标
    let phonetic = 'N/A';
    if (ec.ukphone && ec.usphone) {
      phonetic = `UK: ${ec.ukphone} | US: ${ec.usphone}`;
    } else if (ec.ukphone) {
      phonetic = `UK: ${ec.ukphone}`;
    } else if (ec.usphone) {
      phonetic = `US: ${ec.usphone}`;
    } else if (ec.phonetic) {
      phonetic = ec.phonetic;
    }

    // 提取释义
    const definitions = [];
    if (ec.trs && ec.trs.length > 0) {
      for (const tr of ec.trs) {
        if (tr.tr && tr.tr.length > 0) {
          for (const item of tr.tr) {
            if (item.l && item.l.i) {
              const pos = tr.pos ? `${tr.pos}. ` : '';
              definitions.push(`${pos}${item.l.i.join('; ')}`);
            }
          }
        }
      }
    }

    // 提取例句
    const examples = [];
    if (ec.sentencePair && ec.sentencePair.length > 0) {
      for (const pair of ec.sentencePair.slice(0, 5)) { // 最多5个例句
        if (pair.sentence) {
          examples.push(pair.sentence);
        }
      }
    }

    // 提取词形变化
    let baseForm = null;
    if (ec.inflection && ec.inflection.length > 0) {
      for (const inf of ec.inflection) {
        if (inf.baseForm && inf.baseForm.pos) {
          baseForm = `${inf.baseForm.pos}: ${inf.baseForm.content}`;
          break;
        }
      }
    }

    return {
      success: true,
      word: word,
      phonetic: phonetic,
      definitions: definitions,
      examples: examples,
      base_form: baseForm,
      pos: ec.pos || null
    };
  } catch (error) {
    console.error('Parse error:', error);
    return {
      success: false,
      error: '解析词典数据失败'
    };
  }
}

/**
 * 金山词典API（备用）
 */
async function fetchIciba(word) {
  try {
    const url = `https://open.iciba.com/dsapi/?word=${encodeURIComponent(word)}`;

    const response = await fetchWithTimeout(url);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    // 检查响应内容类型
    const contentType = response.headers.get('content-type');
    if (!contentType || !contentType.includes('application/json')) {
      const text = await response.text();
      console.error('Iciba API non-JSON response:', text.substring(0, 200));
      throw new Error('API返回非JSON响应');
    }

    const data = await response.json();
    return parseIcibaResponse(data, word);
  } catch (error) {
    console.error('Iciba API error:', error);
    return {
      success: false,
      error: error.message || '金山词典暂时不可用',
      api: 'iciba'
    };
  }
}

/**
 * Free Dictionary API（完全免费的英文词典API）
 * 无需API密钥，无限制
 */
async function fetchDictionaryAPI(word) {
  try {
    const url = `https://api.dictionaryapi.dev/api/v2/entries/en/${encodeURIComponent(word)}`;

    const response = await fetchWithTimeout(url);
    if (!response.ok) {
      if (response.status === 404) {
        return { success: false, error: '未找到该单词', api: 'dictionaryapi' };
      }
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    // 检查响应内容类型
    const contentType = response.headers.get('content-type');
    if (!contentType || !contentType.includes('application/json')) {
      const text = await response.text();
      console.error('Dictionary API non-JSON response:', text.substring(0, 200));
      throw new Error('API返回非JSON响应');
    }

    const data = await response.json();
    return parseDictionaryAPIResponse(data, word);
  } catch (error) {
    console.error('Dictionary API error:', error);
    return {
      success: false,
      error: error.message || 'Dictionary API暂时不可用',
      api: 'dictionaryapi'
    };
  }
}

/**
 * 解析Free Dictionary API响应
 */
function parseDictionaryAPIResponse(data, word) {
  try {
    if (!data || data.length === 0) {
      return {
        success: false,
        error: '未找到该单词'
      };
    }

    const entry = data[0];
    const phoneticText = entry.phonetic || '';
    const phonetics = entry.phonetics || [];

    // 提取音标
    let phonetic = 'N/A';
    if (phoneticText) {
      phonetic = phoneticText;
    } else if (phonetics.length > 0) {
      const textPhonetic = phonetics.find(p => p.text);
      if (textPhonetic) {
        phonetic = textPhonetic.text;
      }
    }

    // 提取释义和词性
    const definitions = [];
    const examples = [];

    for (const meaning of entry.meanings || []) {
      const partOfSpeech = meaning.partOfSpeech || '';

      for (const def of meaning.definitions || []) {
        // 添加释义
        if (def.definition) {
          definitions.push(`${partOfSpeech} ${def.definition}`);
        }

        // 添加例句
        if (def.example && examples.length < 5) {
          examples.push(def.example);
        }
      }
    }

    return {
      success: true,
      word: word,
      phonetic: phonetic,
      definitions: definitions,
      examples: examples,
      base_form: null,
      pos: null
    };
  } catch (error) {
    console.error('Parse error:', error);
    return {
      success: false,
      error: '解析词典数据失败'
    };
  }
}

/**
 * 解析金山词典API响应
 */
function parseIcibaResponse(data, word) {
  try {
    if (!data || !data.word_name) {
      return {
        success: false,
        error: '未找到该单词'
      };
    }

    // 提取音标
    const phonetic = data.symbol || 'N/A';

    // 提取释义
    const definitions = [];
    if (data.means && data.means.length > 0) {
      for (const mean of data.means) {
        definitions.push(mean);
      }
    }

    // 提取例句
    const examples = [];
    if (data.sentences && data.sentences.length > 0) {
      for (const item of data.sentences.slice(0, 5)) {
        if (item.sent) {
          examples.push(`${item.sent}`);
        }
      }
    }

    return {
      success: true,
      word: word,
      phonetic: phonetic,
      definitions: definitions,
      examples: examples,
      base_form: null,
      pos: null
    };
  } catch (error) {
    console.error('Parse error:', error);
    return {
      success: false,
      error: '解析词典数据失败'
    };
  }
}

// =============================================
// 路由处理
// =============================================

/**
 * 处理查词请求（优化版 - 支持自动尝试多个API）
 */
async function handleLookup(request) {
  try {
    const url = new URL(request.url);
    const word = url.searchParams.get('word');

    if (!word) {
      return jsonResponse({
        success: false,
        error: '请提供要查询的单词'
      }, 400);
    }

    // 验证单词格式
    if (!/^[a-zA-Z\s-]+$/.test(word)) {
      return jsonResponse({
        success: false,
        error: '单词格式不正确'
      }, 400);
    }

    let result;

    // 根据配置选择API或自动尝试所有API
    if (CONFIG.dictionaryAPI === 'auto') {
      // 自动模式：尝试所有API，直到找到可用的
      const apis = [fetchDictionaryAPI, fetchYoudao, fetchIciba];
      const errors = [];

      for (const api of apis) {
        result = await api(word);
        if (result.success) {
          result.api_used = result.api || 'auto';
          return jsonResponse(result);
        }
        errors.push(result.error);
      }

      // 所有API都失败
      return jsonResponse({
        success: false,
        error: '所有词典服务暂时不可用，请稍后重试',
        errors: errors
      });
    } else {
      // 指定API模式
      if (CONFIG.dictionaryAPI === 'youdao') {
        result = await fetchYoudao(word);
      } else if (CONFIG.dictionaryAPI === 'iciba') {
        result = await fetchIciba(word);
      } else if (CONFIG.dictionaryAPI === 'dictionaryapi') {
        result = await fetchDictionaryAPI(word);
      } else {
        result = await fetchDictionaryAPI(word);
      }

      return jsonResponse(result);
    }
  } catch (error) {
    console.error('Lookup error:', error);
    return jsonResponse({
      success: false,
      error: '查询失败，请稍后重试'
    }, 500);
  }
}

/**
 * 处理批量查词请求（优化版）
 */
async function handleBatchLookup(request) {
  try {
    const url = new URL(request.url);
    const wordsParam = url.searchParams.get('words');

    if (!wordsParam) {
      return jsonResponse({
        success: false,
        error: '请提供要查询的单词列表'
      }, 400);
    }

    // 解析单词列表
    const words = wordsParam.split(',').map(w => w.trim()).filter(w => w.length > 0);

    if (words.length === 0) {
      return jsonResponse({
        success: false,
        error: '单词列表不能为空'
      }, 400);
    }

    if (words.length > 20) {
      return jsonResponse({
        success: false,
        error: '一次最多查询20个单词'
      }, 400);
    }

    // 批量查询所有单词
    const results = [];
    for (const word of words) {
      if (/^[a-zA-Z\s-]+$/.test(word)) {
        let result;

        // 根据配置选择API
        if (CONFIG.dictionaryAPI === 'auto') {
          // 自动模式：尝试所有API
          const apis = [fetchDictionaryAPI, fetchYoudao, fetchIciba];
          for (const api of apis) {
            result = await api(word);
            if (result.success) break;
          }
        } else if (CONFIG.dictionaryAPI === 'youdao') {
          result = await fetchYoudao(word);
        } else if (CONFIG.dictionaryAPI === 'iciba') {
          result = await fetchIciba(word);
        } else if (CONFIG.dictionaryAPI === 'dictionaryapi') {
          result = await fetchDictionaryAPI(word);
        } else {
          result = await fetchDictionaryAPI(word);
        }

        results.push(result);
      } else {
        results.push({
          success: false,
          word: word,
          error: '单词格式不正确'
        });
      }
    }

    return jsonResponse({
      success: true,
      results: results,
      total: results.length,
      found: results.filter(r => r.success).length
    });
  } catch (error) {
    console.error('Batch lookup error:', error);
    return jsonResponse({
      success: false,
      error: '批量查询失败，请稍后重试'
    }, 500);
  }
}

/**
 * 处理健康检查
 */
function handleHealthCheck() {
  return jsonResponse({
    success: true,
    service: 'DreamWord Word Lookup',
    version: '1.1.0',
    status: 'healthy',
    timestamp: new Date().toISOString(),
    features: {
      ocr: true,
      dictionary: true,
      batch_lookup: true,
      auto_failover: true
    },
    apis: {
      primary: 'Free Dictionary API',
      fallback: ['Youdao', 'Iciba'],
      mode: CONFIG.dictionaryAPI
    }
  });
}

/**
 * 处理OPTIONS请求（CORS预检）
 */
function handleOptions() {
  return new Response(null, {
    status: 204,
    headers: {
      'Access-Control-Allow-Origin': CONFIG.cors.allowOrigin,
      'Access-Control-Allow-Methods': CONFIG.cors.allowMethods,
      'Access-Control-Allow-Headers': CONFIG.cors.allowHeaders
    }
  });
}

// =============================================
// 工具函数
// =============================================

/**
 * 返回JSON响应
 */
function jsonResponse(data, status = 200) {
  const headers = {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': CONFIG.cors.allowOrigin,
    'Access-Control-Allow-Methods': CONFIG.cors.allowMethods,
    'Access-Control-Allow-Headers': CONFIG.cors.allowHeaders
  };

  // 添加缓存头
  if (status === 200 && data.success) {
    headers['Cache-Control'] = `public, max-age=${CONFIG.cacheTTL}`;
  }

  return new Response(JSON.stringify(data, null, 2), {
    status,
    headers
  });
}

/**
 * 返回HTML响应
 */
function htmlResponse(html) {
  return new Response(html, {
    headers: {
      'Content-Type': 'text/html;charset=UTF-8',
      'Access-Control-Allow-Origin': CONFIG.cors.allowOrigin
    }
  });
}

/**
 * 生成测试页面HTML
 */
function getTestPage() {
  return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DreamWord - 功能测试页面</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 50px auto;
            padding: 20px;
            background: #f5f5f5;
        }
        .test-section {
            background: white;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h2 {
            color: #333;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }
        button {
            padding: 10px 20px;
            margin: 5px;
            border: none;
            border-radius: 4px;
            background: #667eea;
            color: white;
            cursor: pointer;
        }
        button:hover {
            background: #5568d3;
        }
        .result {
            margin-top: 15px;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 4px;
            font-family: monospace;
            white-space: pre-wrap;
            max-height: 300px;
            overflow-y: auto;
        }
        .success { color: #28a745; }
        .error { color: #dc3545; }
        .info { color: #17a2b8; }
        input[type="text"] {
            padding: 8px 12px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <h1>🧪 DreamWord 功能测试</h1>

    <div class="test-section">
        <h2>1. 查词API测试</h2>
        <input type="text" id="testWord" placeholder="输入要测试的单词" value="hello">
        <button onclick="testLookup()">测试查词API</button>
        <button onclick="testBatchLookup()">测试批量查词API</button>
        <div id="lookupResult" class="result"></div>
    </div>

    <div class="test-section">
        <h2>2. 页面访问测试</h2>
        <button onclick="window.location.href='/lookup'">访问智能查词页面</button>
        <button onclick="testHealthAPI()">测试健康检查API</button>
        <div id="pageResult" class="result"></div>
    </div>

    <script>
        // 测试查词API
        async function testLookup() {
            const word = document.getElementById('testWord').value;
            const resultDiv = document.getElementById('lookupResult');
            resultDiv.innerHTML = '<div class="info">测试中...</div>';

            try {
                const response = await fetch(\`/api/lookup?word=\${encodeURIComponent(word)}\`);
                const data = await response.json();

                resultDiv.innerHTML = '<div class="success">✅ 查词API测试成功</div>' +
                    '响应数据：\\n' + JSON.stringify(data, null, 2);
            } catch (error) {
                resultDiv.innerHTML = '<div class="error">❌ 查词API测试失败：' + error.message + '</div>';
            }
        }

        // 测试批量查词API
        async function testBatchLookup() {
            const words = ['hello', 'world', 'test'];
            const resultDiv = document.getElementById('lookupResult');
            resultDiv.innerHTML = '<div class="info">测试中...</div>';

            try {
                const response = await fetch(\`/api/batch-lookup?words=\${encodeURIComponent(words.join(','))}\`);
                const data = await response.json();

                resultDiv.innerHTML = '<div class="success">✅ 批量查词API测试成功</div>' +
                    '查询单词：' + words.join(', ') + '\\n\\n' +
                    '响应数据：\\n' + JSON.stringify(data, null, 2);
            } catch (error) {
                resultDiv.innerHTML = '<div class="error">❌ 批量查词API测试失败：' + error.message + '</div>';
            }
        }

        // 测试健康检查API
        async function testHealthAPI() {
            const resultDiv = document.getElementById('pageResult');
            resultDiv.innerHTML = '<div class="info">测试中...</div>';

            try {
                const response = await fetch('/api/health');
                const data = await response.json();

                resultDiv.innerHTML = '<div class="success">✅ 健康检查API测试成功</div>' +
                    '响应数据：\\n' + JSON.stringify(data, null, 2);
            } catch (error) {
                resultDiv.innerHTML = '<div class="error">❌ 健康检查API测试失败：' + error.message + '</div>';
            }
        }

        // 页面加载时自动测试健康检查
        window.addEventListener('load', () => {
            testHealthAPI();
        });
    </script>
</body>
</html>`;
}

/**
 * 生成主页HTML
 */
function generateHomePage() {
  return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DreamWord Word Lookup API</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        .container {
            background: white;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            max-width: 600px;
            width: 100%;
            padding: 40px;
        }
        h1 {
            color: #333;
            margin-bottom: 10px;
            font-size: 28px;
        }
        .subtitle {
            color: #666;
            margin-bottom: 30px;
            font-size: 14px;
        }
        .search-box {
            display: flex;
            gap: 10px;
            margin-bottom: 30px;
        }
        input {
            flex: 1;
            padding: 15px 20px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 16px;
            transition: border-color 0.3s;
        }
        input:focus {
            outline: none;
            border-color: #667eea;
        }
        button {
            padding: 15px 30px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s;
        }
        button:hover {
            transform: translateY(-2px);
        }
        button:active {
            transform: translateY(0);
        }
        .result {
            background: #f8f9fa;
            border-radius: 8px;
            padding: 20px;
            display: none;
        }
        .result.show {
            display: block;
            animation: fadeIn 0.3s ease;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .word {
            font-size: 32px;
            font-weight: 700;
            color: #333;
            margin-bottom: 10px;
        }
        .phonetic {
            color: #666;
            font-size: 18px;
            margin-bottom: 15px;
        }
        .definitions {
            margin-bottom: 15px;
        }
        .definitions h3 {
            font-size: 14px;
            color: #888;
            margin-bottom: 10px;
            text-transform: uppercase;
        }
        .definitions ul {
            list-style: none;
        }
        .definitions li {
            padding: 8px 0;
            color: #444;
            border-bottom: 1px solid #e0e0e0;
        }
        .examples h3 {
            font-size: 14px;
            color: #888;
            margin-bottom: 10px;
            text-transform: uppercase;
        }
        .examples li {
            padding: 8px 0;
            color: #666;
            font-style: italic;
        }
        .loading {
            text-align: center;
            padding: 20px;
            color: #888;
        }
        .error {
            background: #fee;
            color: #c33;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
        }
        .api-info {
            margin-top: 30px;
            padding: 20px;
            background: #f0f0f0;
            border-radius: 8px;
        }
        .api-info h2 {
            font-size: 18px;
            margin-bottom: 15px;
            color: #333;
        }
        .api-info code {
            background: white;
            padding: 2px 6px;
            border-radius: 4px;
            font-family: 'Courier New', monospace;
            font-size: 13px;
        }
        .api-info p {
            margin: 10px 0;
            color: #666;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔍 DreamWord Word Lookup</h1>
        <p class="subtitle">快速查词预览服务 - Cloudflare Workers</p>

        <div class="search-box">
            <input type="text" id="wordInput" placeholder="输入要查询的单词..." />
            <button onclick="lookupWord()">查询</button>
        </div>

        <div id="result" class="result"></div>

        <div class="api-info">
            <h2>📚 API使用说明</h2>
            <p><strong>查词API：</strong></p>
            <p><code>GET /api/lookup?word=hello</code></p>
            <p><strong>健康检查：</strong></p>
            <p><code>GET /api/health</code></p>
            <p style="margin-top: 15px; font-size: 12px; color: #888;">
                由 Cloudflare Workers 驱动 | 响应时间 &lt; 100ms
            </p>
        </div>
    </div>

    <script>
        async function lookupWord() {
            const word = document.getElementById('wordInput').value.trim();
            const resultDiv = document.getElementById('result');

            if (!word) {
                resultDiv.innerHTML = '<div class="error">请输入要查询的单词</div>';
                resultDiv.classList.add('show');
                return;
            }

            resultDiv.innerHTML = '<div class="loading">查询中...</div>';
            resultDiv.classList.add('show');

            try {
                const response = await fetch(\`/api/lookup?word=\${encodeURIComponent(word)}\`);
                const data = await response.json();

                if (data.success) {
                    displayResult(data);
                } else {
                    resultDiv.innerHTML = \`<div class="error">\${data.error}</div>\`;
                }
            } catch (error) {
                resultDiv.innerHTML = '<div class="error">查询失败，请稍后重试</div>';
            }
        }

        function displayResult(data) {
            const resultDiv = document.getElementById('result');

            let html = \`
                <div class="word">\${data.word}</div>
                \${data.phonetic ? \`<div class="phonetic">\${data.phonetic}</div>\` : ''}
            \`;

            if (data.definitions && data.definitions.length > 0) {
                html += '<div class="definitions"><h3>释义</h3><ul>';
                data.definitions.forEach(def => {
                    html += \`<li>\${def}</li>\`;
                });
                html += '</ul></div>';
            }

            if (data.examples && data.examples.length > 0) {
                html += '<div class="examples"><h3>例句</h3><ul>';
                data.examples.slice(0, 3).forEach(ex => {
                    html += \`<li>\${ex}</li>\`;
                });
                html += '</ul></div>';
            }

            resultDiv.innerHTML = html;
        }

        // 回车键查询
        document.getElementById('wordInput').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                lookupWord();
            }
        });
    </script>
</body>
</html>`;
}

// =============================================
// 主处理函数
// =============================================

/**
 * Cloudflare Workers 主处理函数
 */
export default {
  async fetch(request) {
    const url = new URL(request.url);
    const path = url.pathname;

    // 路由处理
    if (path === '/' || path === '/index.html' || path === '/home') {
      return htmlResponse(generateHomePage());
    }

    // 新的智能查词页面
    if (path === '/smart-lookup' || path === '/lookup') {
      return new Response(SMART_LOOKUP_HTML, {
        headers: {
          'Content-Type': 'text/html;charset=UTF-8',
          'Access-Control-Allow-Origin': CONFIG.cors.allowOrigin
        }
      });
    }

    // 测试页面
    if (path === '/test' || path === '/test-camera') {
      return htmlResponse(getTestPage());
    }

    if (path === '/api/lookup' || path === '/api/word-preview') {
      return handleLookup(request);
    }

    if (path === '/api/batch-lookup') {
      return handleBatchLookup(request);
    }

    if (path === '/api/health') {
      return handleHealthCheck();
    }

    if (path === '/api/status' || path === '/api') {
      return handleHealthCheck();
    }

    // 调试端点 - 测试Worker是否正常
    if (path === '/api/debug') {
      return jsonResponse({
        success: true,
        worker: 'DreamWord Word Lookup',
        version: '1.1.0',
        config: {
          dictionaryAPI: CONFIG.dictionaryAPI,
          apiTimeout: CONFIG.apiTimeout,
          cacheTTL: CONFIG.cacheTTL
        },
        timestamp: new Date().toISOString()
      });
    }

    // 404
    return jsonResponse({
      success: false,
      error: '未找到请求的端点'
    }, 404);
  }
};
