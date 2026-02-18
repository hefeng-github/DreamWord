// API基础URL
const API_BASE = '';

// 显示/隐藏标签页
function showTab(tabName, event) {
    // 隐藏所有标签内容
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });

    // 移除所有按钮的active类
    document.querySelectorAll('.tab-button').forEach(button => {
        button.classList.remove('active');
    });

    // 显示选中的标签内容
    document.getElementById(`tab-${tabName}`).classList.add('active');

    // 激活对应按钮
    if (event && event.target) {
        event.target.classList.add('active');
    }
}

// 显示/隐藏加载提示
function showLoading() {
    document.getElementById('loading').style.display = 'flex';
}

function hideLoading() {
    document.getElementById('loading').style.display = 'none';
}

// 显示通知
function showNotification(message, type = 'info') {
    const notification = document.getElementById('notification');
    notification.textContent = message;
    notification.className = `notification ${type}`;
    notification.style.display = 'block';

    setTimeout(() => {
        notification.style.display = 'none';
    }, 3000);
}

// 图片预览
function previewImage(input, previewId) {
    const file = input.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = function(e) {
            const preview = document.getElementById(previewId);
            preview.src = e.target.result;
            preview.style.display = 'inline-block';
        };
        reader.readAsDataURL(file);
    }
}

// 生成ArUco标记
async function generateMarkers() {
    const numMarkers = document.getElementById('num-markers').value;
    const markerSize = document.getElementById('marker-size-gen').value;

    showLoading();

    try {
        const response = await fetch(`${API_BASE}/api/generate-markers`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                num_markers: parseInt(numMarkers),
                marker_size: parseInt(markerSize)
            })
        });

        const data = await response.json();

        if (data.success) {
            // 显示预览
            const preview = document.getElementById('markers-preview');
            preview.src = data.download_url;
            preview.style.display = 'inline-block';

            // 设置下载链接
            const downloadBtn = document.getElementById('markers-download');
            downloadBtn.href = data.download_url;

            // 显示结果
            document.getElementById('markers-result').style.display = 'block';

            showNotification('标记生成成功！', 'success');
        } else {
            showNotification(data.error || '生成失败', 'error');
        }
    } catch (error) {
        showNotification('网络错误：' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

// 校准
async function calibrate() {
    const imageInput = document.getElementById('calib-image');
    const markerSize = document.getElementById('marker-size').value;

    if (!imageInput.files[0]) {
        showNotification('请先上传校准照片', 'error');
        return;
    }

    // 收集标记位置
    const positionInputs = document.querySelectorAll('.marker-position-input');
    const positions = {};

    positionInputs.forEach((input, index) => {
        const x = input.querySelector('.marker-x').value;
        const y = input.querySelector('.marker-y').value;
        positions[index] = { x: parseFloat(x), y: parseFloat(y) };
    });

    showLoading();

    const formData = new FormData();
    formData.append('image', imageInput.files[0]);
    formData.append('marker_size', markerSize);
    formData.append('positions', JSON.stringify(positions));

    try {
        const response = await fetch(`${API_BASE}/api/calibrate`, {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (data.success) {
            const resultDiv = document.getElementById('calib-result');
            resultDiv.innerHTML = `
                <div class="alert alert-success">
                    <strong>校准成功！</strong><br>
                    校准文件已保存，可以开始使用写字机了。
                </div>
            `;
            resultDiv.style.display = 'block';

            showNotification('校准成功！', 'success');
        } else {
            showNotification(data.error || '校准失败', 'error');
        }
    } catch (error) {
        showNotification('网络错误：' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

// 书写文字
async function writeText() {
    const text = document.getElementById('write-text').value;
    const useHandright = document.getElementById('use-handright').checked;

    if (!text.trim()) {
        showNotification('请输入要书写的文字', 'error');
        return;
    }

    showLoading();

    try {
        const response = await fetch(`${API_BASE}/api/write`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                text: text,
                use_handright: useHandright
            })
        });

        const data = await response.json();

        if (data.success) {
            // 显示预览
            const preview = document.getElementById('write-preview');
            preview.src = data.preview_url;
            preview.style.display = 'inline-block';

            // 设置下载链接
            const downloadBtn = document.getElementById('write-download');
            downloadBtn.href = data.download_url;

            // 显示结果
            document.getElementById('write-result').style.display = 'block';

            showNotification('书写代码生成成功！', 'success');
        } else {
            showNotification(data.error || '生成失败', 'error');
        }
    } catch (error) {
        showNotification('网络错误：' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

// 自动查单词
async function autoLookup() {
    const imageInput = document.getElementById('lookup-image');
    const knownWords = document.getElementById('known-words').value;

    if (!imageInput.files[0]) {
        showNotification('请先上传试卷图片', 'error');
        return;
    }

    showLoading();

    const formData = new FormData();
    formData.append('image', imageInput.files[0]);
    formData.append('known_words', knownWords);

    try {
        const response = await fetch(`${API_BASE}/api/auto-lookup`, {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (data.success) {
            // 显示标注结果
            const annotated = document.getElementById('lookup-annotated');
            annotated.src = data.annotated_url;
            annotated.style.display = 'inline-block';

            // 设置下载链接
            const downloadBtn = document.getElementById('lookup-download');
            downloadBtn.href = data.gcode_url;

            // 显示结果
            document.getElementById('lookup-result').style.display = 'block';

            showNotification('处理完成！', 'success');
        } else {
            // 检查是否是模块未加载错误
            if (data.error && data.error.includes('未加载')) {
                showNotification(data.error, 'error');
                console.error('自动查词模块不可用:', data.error);
            } else {
                showNotification(data.error || '处理失败', 'error');
            }
        }
    } catch (error) {
        showNotification('网络错误：' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

// 自动抄写
async function autoCopy() {
    const imageInput = document.getElementById('copy-image');
    const text = document.getElementById('copy-text').value;

    if (!imageInput.files[0]) {
        showNotification('请先上传横线本图片', 'error');
        return;
    }

    if (!text.trim()) {
        showNotification('请输入要抄写的文字', 'error');
        return;
    }

    showLoading();

    const formData = new FormData();
    formData.append('image', imageInput.files[0]);
    formData.append('text', text);

    try {
        const response = await fetch(`${API_BASE}/api/auto-copy`, {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (data.success) {
            // 显示布局预览
            const layout = document.getElementById('copy-layout');
            layout.src = data.layout_url;
            layout.style.display = 'inline-block';

            // 设置下载链接
            const downloadBtn = document.getElementById('copy-download');
            downloadBtn.href = data.gcode_url;

            // 显示结果
            document.getElementById('copy-result').style.display = 'block';

            showNotification('处理完成！', 'success');
        } else {
            // 检查是否是模块未加载错误
            if (data.error && data.error.includes('未加载')) {
                showNotification(data.error, 'error');
                console.error('自动抄写模块不可用:', data.error);
            } else {
                showNotification(data.error || '处理失败', 'error');
            }
        }
    } catch (error) {
        showNotification('网络错误：' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

// 导入单词相关变量
let importedWords = [];
let currentWordIndex = 0;
let knownWordsInCard = [];
let unknownWordsInCard = [];
let importMode = 'list'; // 'list' 或 'card'

// 上传并解析单词JSON文件
async function uploadWordJSON() {
    const fileInput = document.getElementById('word-json-file');

    if (!fileInput.files[0]) {
        showNotification('请选择JSON文件', 'error');
        return;
    }

    const file = fileInput.files[0];

    // 检查文件类型
    if (!file.name.endsWith('.json')) {
        showNotification('请选择JSON文件', 'error');
        return;
    }

    showLoading();

    try {
        // 读取文件
        const text = await file.text();

        // 预处理：移除BOM
        let cleanedText = text.replace(/^\ufeff/, '');

        // 预处理：移除注释（某些JSON文件可能有）
        cleanedText = cleanedText.replace(/^\s*\/\/.*$/gm, '');
        cleanedText = cleanedText.replace(/^\s*#.*$/gm, '');

        // 预处理：移除尾部逗号（常见错误）
        cleanedText = cleanedText.replace(/,(\s*[}\]])/g, '$1');

        // 解析JSON（支持多种格式）
        let wordsData = [];

        try {
            // 尝试1: 标准JSON数组
            console.log('尝试解析为标准JSON数组...');
            const parsed = JSON.parse(cleanedText);
            wordsData = Array.isArray(parsed) ? parsed : [parsed];
            console.log('✓ 标准JSON数组格式');
        } catch (e) {
            console.log('标准JSON解析失败，尝试JSON Lines格式...');

            // 尝试2: JSON Lines格式（每行一个JSON对象）
            try {
                const lines = cleanedText.split('\n');
                let parseCount = 0;
                let errorCount = 0;

                for (let i = 0; i < lines.length; i++) {
                    const line = lines[i].trim();

                    // 跳过空行和注释
                    if (!line || line.startsWith('//') || line.startsWith('#')) {
                        continue;
                    }

                    try {
                        const obj = JSON.parse(line);
                        if (obj.headWord) {
                            wordsData.push(obj);
                            parseCount++;
                        }
                    } catch (err) {
                        errorCount++;
                        if (errorCount <= 5) {
                            console.warn(`第 ${i+1} 行解析失败:`, err);
                        }
                    }
                }

                if (wordsData.length > 0) {
                    console.log(`✓ JSON Lines格式，成功解析 ${parseCount} 个单词`);
                } else {
                    throw new Error('未找到有效的JSON对象');
                }
            } catch (e2) {
                console.log('JSON Lines格式也失败');
                throw new Error('无法解析JSON文件，请确保文件格式正确');
            }
        }

        // 提取单词信息
        importedWords = [];
        let skippedCount = 0;

        for (const item of wordsData) {
            const word = item.headWord || '';
            const content = item.content?.word?.content;

            if (!word) {
                skippedCount++;
                continue;
            }

            // 提取音标
            const usphone = content?.usphone || '';
            const ukphone = content?.ukphone || '';
            const phonetic = usphone || ukphone || '';

            // 提取释义
            const trans = content?.trans || [];
            const definitions = trans.map(t => t.tranCn || '').join('；');

            // 提取例句
            const sentences = content?.sentence?.sentences || [];
            const examples = sentences.slice(0, 2).map(s => ({
                en: s.sContent || '',
                cn: s.sCn || ''
            }));

            importedWords.push({
                word: word,
                phonetic: phonetic,
                definitions: definitions,
                examples: examples
            });
        }

        if (importedWords.length === 0) {
            showNotification('未找到有效的单词数据', 'error');
            return;
        }

        console.log(`成功解析 ${importedWords.length} 个单词`);
        if (skippedCount > 0) {
            console.log(`跳过 ${skippedCount} 个无效条目`);
        }

        // 显示单词列表
        displayWordList();

        // 切换到步骤2
        document.getElementById('import-step-1').style.display = 'none';
        document.getElementById('import-step-2').style.display = 'block';

        showNotification(`成功导入 ${importedWords.length} 个单词`, 'success');

    } catch (error) {
        showNotification('JSON格式错误：' + error.message, 'error');
        console.error('JSON解析错误:', error);
        console.log('文件内容前500字符:', text.substring(0, 500));
        console.log('建议：使用 python validate_json.py 检查文件格式');
    } finally {
        hideLoading();
    }
}

// 显示单词列表
function displayWordList() {
    const wordList = document.getElementById('word-list');
    wordList.innerHTML = '';

    importedWords.forEach((item, index) => {
        const div = document.createElement('div');
        div.className = 'word-item';
        div.id = `word-${index}`;

        // 构建例句HTML
        let examplesHtml = '';
        if (item.examples && item.examples.length > 0) {
            examplesHtml = item.examples.map(ex =>
                `<div class="word-item-example">${ex.en} ${ex.cn ? '- ' + ex.cn : ''}</div>`
            ).join('');
        }

        div.innerHTML = `
            <input type="checkbox" id="checkbox-${index}" onchange="updateWordSelection(${index})">
            <div class="word-item-content">
                <div class="word-item-word">${item.word}</div>
                ${item.phonetic ? `<div class="word-item-phonetic">${item.phonetic}</div>` : ''}
                ${item.definitions ? `<div class="word-item-definition">${item.definitions}</div>` : ''}
                ${examplesHtml}
            </div>
        `;

        wordList.appendChild(div);
    });

    updateSelectedCount();
}

// 更新单词选择状态
function updateWordSelection(index) {
    const checkbox = document.getElementById(`checkbox-${index}`);
    const wordItem = document.getElementById(`word-${index}`);

    if (checkbox.checked) {
        wordItem.classList.add('selected');
    } else {
        wordItem.classList.remove('selected');
    }

    updateSelectedCount();
}

// 更新选中计数
function updateSelectedCount() {
    const checkboxes = document.querySelectorAll('.word-list input[type="checkbox"]');
    const checked = Array.from(checkboxes).filter(cb => cb.checked).length;
    document.getElementById('selected-count').textContent = `已选择: ${checked}`;
}

// 全选
function selectAllWords() {
    const checkboxes = document.querySelectorAll('.word-list input[type="checkbox"]');
    checkboxes.forEach((cb, index) => {
        cb.checked = true;
        document.getElementById(`word-${index}`).classList.add('selected');
    });
    updateSelectedCount();
}

// 取消全选
function deselectAllWords() {
    const checkboxes = document.querySelectorAll('.word-list input[type="checkbox"]');
    checkboxes.forEach((cb, index) => {
        cb.checked = false;
        document.getElementById(`word-${index}`).classList.remove('selected');
    });
    updateSelectedCount();
}

// 反选
function invertSelection() {
    const checkboxes = document.querySelectorAll('.word-list input[type="checkbox"]');
    checkboxes.forEach((cb, index) => {
        cb.checked = !cb.checked;
        updateWordSelection(index);
    });
}

// 添加选中的单词到数据库
async function addSelectedWords() {
    const checkboxes = document.querySelectorAll('.word-list input[type="checkbox"]:checked');

    if (checkboxes.length === 0) {
        showNotification('请至少选择一个单词', 'error');
        return;
    }

    showLoading();

    // 收集选中的单词
    const selectedWords = [];
    checkboxes.forEach(cb => {
        const index = parseInt(cb.id.replace('checkbox-', ''));
        selectedWords.push(importedWords[index].word);
    });

    try {
        const response = await fetch(`${API_BASE}/api/add-known-words`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                words: selectedWords
            })
        });

        const data = await response.json();

        if (data.success) {
            const resultDiv = document.getElementById('import-result');
            resultDiv.innerHTML = `
                <div class="alert alert-success">
                    <strong>添加成功！</strong><br>
                    成功添加 ${data.added_count} 个单词到数据库。<br>
                    ${data.skipped_count > 0 ? `跳过 ${data.skipped_count} 个已存在的单词。` : ''}
                </div>
            `;
            resultDiv.style.display = 'block';

            showNotification('添加成功！', 'success');
        } else {
            showNotification(data.error || '添加失败', 'error');
        }
    } catch (error) {
        showNotification('网络错误：' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

// 重置导入
function resetImport() {
    // 移除键盘监听
    document.removeEventListener('keydown', handleCardKeyPress);

    // 重置状态
    importMode = 'list';
    currentWordIndex = 0;
    knownWordsInCard = [];
    unknownWordsInCard = [];

    // 重置UI
    document.getElementById('import-step-1').style.display = 'block';
    document.getElementById('import-step-2').style.display = 'none';
    document.getElementById('import-result').style.display = 'none';
    document.getElementById('import-mode-list').style.display = 'block';
    document.getElementById('import-mode-card').style.display = 'none';
    document.getElementById('mode-list-btn').classList.add('active');
    document.getElementById('mode-card-btn').classList.remove('active');

    // 重新创建卡片容器（恢复初始状态）
    const cardContainer = document.querySelector('.word-card-container');
    if (cardContainer) {
        cardContainer.innerHTML = `
            <div class="word-card">
                <div class="word-card-current" id="current-word">加载中...</div>
                <div class="word-card-actions">
                    <button class="word-card-btn unknown" onclick="markWord('unknown')">
                        不认识
                        <span style="display: block; font-size: 0.7em; margin-top: 5px; opacity: 0.8;">
                            ← 或 A
                        </span>
                    </button>
                    <button class="word-card-btn known" onclick="markWord('known')">
                        认识
                        <span style="display: block; font-size: 0.7em; margin-top: 5px; opacity: 0.8;">
                            → 或 D
                        </span>
                    </button>
                </div>
            </div>
            <div class="word-card-progress">
                <div class="word-card-progress-text" id="progress-text">进度: 0 / 0</div>
                <div class="word-card-progress-bar">
                    <div class="word-card-progress-fill" id="progress-fill" style="width: 0%"></div>
                </div>
            </div>
            <div style="text-align: center; margin-top: 15px; color: #6c757d; font-size: 0.9em;">
                💡 提示：使用键盘方向键或 A/D 键快速标记
            </div>
        `;
    }

    document.getElementById('word-json-file').value = '';
    importedWords = [];
}

// 页面加载完成后的初始化
document.addEventListener('DOMContentLoaded', function() {
    console.log('智能写字机Web界面已加载');

    // 检测后端功能可用性
    checkBackendFeatures();
});

// 检测后端功能
async function checkBackendFeatures() {
    try {
        // 尝试调用一个简单的API来检测后端是否可用
        const response = await fetch(`${API_BASE}/api/get-known-words`, {
            method: 'GET',
            timeout: 2000
        });

        if (response.ok) {
            console.log('✓ 后端服务正常运行');
        }
    } catch (error) {
        console.warn('⚠ 后端服务连接失败:', error);
        showNotification('无法连接到后端服务，某些功能可能不可用', 'info');
    }
}

// 切换导入模式
function switchImportMode(mode) {
    importMode = mode;

    const listMode = document.getElementById('import-mode-list');
    const cardMode = document.getElementById('import-mode-card');
    const listBtn = document.getElementById('mode-list-btn');
    const cardBtn = document.getElementById('mode-card-btn');

    if (mode === 'list') {
        listMode.style.display = 'block';
        cardMode.style.display = 'none';
        listBtn.classList.add('active');
        cardBtn.classList.remove('active');

        // 移除键盘监听
        document.removeEventListener('keydown', handleCardKeyPress);
    } else {
        listMode.style.display = 'none';
        cardMode.style.display = 'block';
        listBtn.classList.remove('active');
        cardBtn.classList.add('active');

        // 初始化卡片模式
        initCardMode();

        // 添加键盘监听
        document.addEventListener('keydown', handleCardKeyPress);
    }
}

// 处理卡片模式的键盘按键
function handleCardKeyPress(event) {
    // 只在卡片模式下响应
    if (importMode !== 'card') return;

    // 防止按键触发其他行为
    const key = event.key.toLowerCase();

    // 左箭头 或 A键：不认识
    if (event.key === 'ArrowLeft' || key === 'a') {
        event.preventDefault();
        markWord('unknown');
        addButtonAnimation('unknown');
    }
    // 右箭头 或 D键：认识
    else if (event.key === 'ArrowRight' || key === 'd') {
        event.preventDefault();
        markWord('known');
        addButtonAnimation('known');
    }
}

// 按钮点击动画效果
function addButtonAnimation(type) {
    const button = document.querySelector(`.word-card-btn.${type}`);
    if (button) {
        button.style.transform = 'scale(0.95)';
        setTimeout(() => {
            button.style.transform = '';
        }, 100);
    }
}

// 初始化卡片模式
function initCardMode() {
    currentWordIndex = 0;
    knownWordsInCard = [];
    unknownWordsInCard = [];

    if (importedWords.length === 0) {
        showNotification('没有可用的单词', 'error');
        switchImportMode('list');
        return;
    }

    updateCardDisplay();
    updateCardProgress();
}

// 更新卡片显示
function updateCardDisplay() {
    const currentWordEl = document.getElementById('current-word');

    if (currentWordIndex >= importedWords.length) {
        // 完成所有单词
        showCardSummary();
        return;
    }

    const word = importedWords[currentWordIndex];
    currentWordEl.textContent = word.word;
}

// 更新卡片进度
function updateCardProgress() {
    const progressText = document.getElementById('progress-text');
    const progressFill = document.getElementById('progress-fill');

    const total = importedWords.length;
    const current = currentWordIndex;
    const percentage = (current / total) * 100;

    progressText.textContent = `进度: ${current} / ${total}`;
    progressFill.style.width = `${percentage}%`;
}

// 标记单词
function markWord(type) {
    if (currentWordIndex >= importedWords.length) {
        return;
    }

    const word = importedWords[currentWordIndex];

    if (type === 'known') {
        knownWordsInCard.push(word);
    } else {
        unknownWordsInCard.push(word);
    }

    currentWordIndex++;
    updateCardDisplay();
    updateCardProgress();
}

// 显示卡片完成摘要
function showCardSummary() {
    const container = document.querySelector('.word-card-container');

    container.innerHTML = `
        <div class="word-card-summary">
            <h3>🎉 完成！</h3>
            <div class="word-card-summary-stats">
                <div class="word-card-summary-stat">
                    <div class="word-card-summary-stat-value known">${knownWordsInCard.length}</div>
                    <div class="word-card-summary-stat-label">认识</div>
                </div>
                <div class="word-card-summary-stat">
                    <div class="word-card-summary-stat-value unknown">${unknownWordsInCard.length}</div>
                    <div class="word-card-summary-stat-label">不认识</div>
                </div>
            </div>
            <p style="color: #6c757d; margin-bottom: 20px;">
                已标记 ${unknownWordsInCard.length} 个单词为"不认识"，将添加到数据库
            </p>
            <div class="word-card-complete-actions">
                <button class="btn btn-success" onclick="submitCardResults()">提交到数据库</button>
                <button class="btn btn-secondary" onclick="resetImport()">重新上传</button>
            </div>
        </div>
    `;
}

// 提交卡片结果
async function submitCardResults() {
    if (unknownWordsInCard.length === 0) {
        showNotification('没有需要添加的单词', 'info');
        resetImport();
        return;
    }

    showLoading();

    const wordsToAdd = unknownWordsInCard.map(item => item.word);

    try {
        const response = await fetch(`${API_BASE}/api/add-known-words`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                words: wordsToAdd
            })
        });

        const data = await response.json();

        if (data.success) {
            const resultDiv = document.getElementById('import-result');
            resultDiv.innerHTML = `
                <div class="alert alert-success">
                    <strong>添加成功！</strong><br>
                    成功添加 ${data.added_count} 个单词到数据库。<br>
                    ${data.skipped_count > 0 ? `跳过 ${data.skipped_count} 个已存在的单词。` : ''}
                </div>
            `;
            resultDiv.style.display = 'block';

            showNotification('添加成功！', 'success');
            setTimeout(() => {
                resetImport();
            }, 2000);
        } else {
            showNotification(data.error || '添加失败', 'error');
        }
    } catch (error) {
        showNotification('网络错误：' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

// ==================== 摄像头功能 ====================

// 存储摄像头流
const cameraStreams = {
    lookup: null,
    copy: null,
    calib: null
};

// 启动摄像头
async function startCamera(prefix) {
    const video = document.getElementById(`${prefix}-video`);
    const container = document.getElementById(`${prefix}-camera-container`);
    const button = container.parentElement.querySelector('.camera-button');

    // 检查浏览器支持
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        showNotification('您的浏览器不支持摄像头功能', 'error');
        return;
    }

    try {
        // 请求摄像头权限
        const stream = await navigator.mediaDevices.getUserMedia({
            video: {
                facingMode: 'environment', // 优先使用后置摄像头
                width: { ideal: 1920 },
                height: { ideal: 1080 }
            }
        });

        // 保存流
        cameraStreams[prefix] = stream;

        // 设置视频源
        video.srcObject = stream;
        video.style.display = 'block';

        // 显示视频容器
        container.style.display = 'block';
        button.disabled = true;
        button.textContent = '📷 摄像头已启动';

        showNotification('摄像头已启动', 'success');

    } catch (error) {
        console.error('摄像头访问失败:', error);
        if (error.name === 'NotAllowedError') {
            showNotification('请允许访问摄像头', 'error');
        } else if (error.name === 'NotFoundError') {
            showNotification('未检测到摄像头设备', 'error');
        } else {
            showNotification('摄像头启动失败: ' + error.message, 'error');
        }
    }
}

// 拍照
function capturePhoto(prefix) {
    const video = document.getElementById(`${prefix}-video`);
    const canvas = document.getElementById(`${prefix}-canvas`);
    const preview = document.getElementById(`${prefix}-preview`);

    if (!cameraStreams[prefix]) {
        showNotification('请先启动摄像头', 'error');
        return;
    }

    // 设置canvas尺寸与视频一致
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    // 绘制当前帧
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    // 转换为图片URL
    const imageUrl = canvas.toDataURL('image/png');

    // 显示预览
    preview.src = imageUrl;
    preview.style.display = 'inline-block';

    // 创建文件对象
    canvas.toBlob(function(blob) {
        // 创建File对象
        const file = new File([blob], `camera_${prefix}_${Date.now()}.png`, {
            type: 'image/png'
        });

        // 创建FileList对象
        const dataTransfer = new DataTransfer();
        dataTransfer.items.add(file);

        // 设置到文件输入框
        const fileInput = document.getElementById(`${prefix === 'lookup' ? 'lookup' : prefix === 'copy' ? 'copy' : 'calib'}-image`);
        fileInput.files = dataTransfer.files;

        showNotification('拍照成功！', 'success');

        // 关闭摄像头
        stopCamera(prefix);
    }, 'image/png');
}

// 关闭摄像头
function stopCamera(prefix) {
    const video = document.getElementById(`${prefix}-video`);
    const container = document.getElementById(`${prefix}-camera-container`);
    const button = container.parentElement.querySelector('.camera-button');

    if (cameraStreams[prefix]) {
        // 停止所有轨道
        const tracks = cameraStreams[prefix].getTracks();
        tracks.forEach(track => track.stop());

        // 清空流
        cameraStreams[prefix] = null;

        // 清空视频源
        video.srcObject = null;
        video.style.display = 'none';

        // 隐藏视频容器
        container.style.display = 'none';
        button.disabled = false;
        button.textContent = '📷 使用摄像头拍照';

        showNotification('摄像头已关闭', 'info');
    }
}

// 页面卸载时关闭所有摄像头
window.addEventListener('beforeunload', function() {
    Object.keys(cameraStreams).forEach(prefix => {
        if (cameraStreams[prefix]) {
            const tracks = cameraStreams[prefix].getTracks();
            tracks.forEach(track => track.stop());
        }
    });
});

// ==================== Bambu 打印机摄像头功能 ====================

// Bambu 摄像头配置
let bambuCameraConfigs = [];
let selectedBambuConfig = null;

// 检查 Bambu 摄像头功能是否可用
async function checkBambuCameraAvailable() {
    try {
        const response = await fetch(`${API_BASE}/api/bambu/camera/available`);
        const data = await response.json();
        return data.available;
    } catch (error) {
        console.error('检查 Bambu 摄像头失败:', error);
        return false;
    }
}

// 加载 Bambu 摄像头配置列表
async function loadBambuCameraConfigs() {
    try {
        const response = await fetch(`${API_BASE}/api/bambu/camera/configs`);
        const data = await response.json();
        if (data.success) {
            bambuCameraConfigs = Object.entries(data.configs).map(([name, config]) => ({
                name,
                ...config
            }));
            return bambuCameraConfigs;
        }
    } catch (error) {
        console.error('加载配置失败:', error);
    }
    return [];
}

// 显示 Bambu 摄像头配置对话框
function showBambuCameraDialog(targetInputId) {
    const dialog = document.getElementById('bambu-camera-dialog');
    const targetInput = document.getElementById('target-input-id');
    targetInput.value = targetInputId;
    dialog.style.display = 'flex';

    // 加载配置列表
    loadAndDisplayBambuConfigs();
}

// 隐藏 Bambu 摄像头配置对话框
function hideBambuCameraDialog() {
    document.getElementById('bambu-camera-dialog').style.display = 'none';
}

// 加载并显示配置列表
async function loadAndDisplayBambuConfigs() {
    const configs = await loadBambuCameraConfigs();
    const configList = document.getElementById('bambu-config-list');

    if (configs.length === 0) {
        configList.innerHTML = '<div class="bambu-no-config">暂无配置，请先添加打印机配置</div>';
        return;
    }

    configList.innerHTML = configs.map(config => {
        // 获取工作区域
        const workAreas = {
            'A1MINI': '180×180×180mm',
            'A1': '256×256×256mm',
            'P1P': '256×256×256mm',
            'P1S': '256×256×256mm',
            'X1C': '256×256×256mm'
        };
        const workArea = workAreas[config.model] || '未知';

        return `
        <div class="bambu-config-item" data-config-name="${config.name}">
            <div class="bambu-config-name">${config.name}</div>
            <div class="bambu-config-info">
                <span>IP: ${config.ip}</span>
                <span>型号: ${config.model}</span>
                <span>行程: ${workArea}</span>
            </div>
        </div>
        `;
    }).join('');

    // 为每个配置项添加点击事件监听器
    setTimeout(() => {
        document.querySelectorAll('.bambu-config-item').forEach(item => {
            item.addEventListener('click', function() {
                const configName = this.getAttribute('data-config-name');
                selectBambuConfig(configName, this);
            });
        });
    }, 0);
}

// 选择 Bambu 配置
function selectBambuConfig(configName, element) {
    selectedBambuConfig = configName;
    document.querySelectorAll('.bambu-config-item').forEach(item => {
        item.classList.remove('selected');
    });
    element.classList.add('selected');

    // 启用拍照按钮
    document.getElementById('bambu-capture-btn').disabled = false;
}

// 显示添加配置表单
function showAddBambuConfigForm() {
    document.getElementById('bambu-config-form').style.display = 'block';
    document.getElementById('bambu-config-list-panel').style.display = 'none';
}

// 隐藏添加配置表单
function hideAddBambuConfigForm() {
    document.getElementById('bambu-config-form').style.display = 'none';
    document.getElementById('bambu-config-list-panel').style.display = 'block';
}

// 添加 Bambu 摄像头配置
async function addBambuCameraConfig() {
    const name = document.getElementById('bambu-config-name').value.trim();
    const printerIp = document.getElementById('bambu-printer-ip').value.trim();
    const accessCode = document.getElementById('bambu-access-code').value.trim();
    const printerModel = document.getElementById('bambu-printer-model').value;

    if (!name || !printerIp || !accessCode) {
        showNotification('请填写所有必填项', 'error');
        return;
    }

    showLoading();

    try {
        const response = await fetch(`${API_BASE}/api/bambu/camera/add-config`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                name,
                printer_ip: printerIp,
                access_code: accessCode,
                printer_model: printerModel
            })
        });

        const data = await response.json();

        if (data.success) {
            showNotification('配置添加成功', 'success');
            hideAddBambuConfigForm();

            // 清空表单
            document.getElementById('bambu-config-name').value = '';
            document.getElementById('bambu-printer-ip').value = '';
            document.getElementById('bambu-access-code').value = '';

            // 重新加载配置列表
            loadAndDisplayBambuConfigs();
        } else {
            showNotification(data.error || '添加失败', 'error');
        }
    } catch (error) {
        showNotification('网络错误：' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

// 测试 Bambu 摄像头连接
async function testBambuCameraConnection() {
    const printerIp = document.getElementById('bambu-printer-ip').value.trim();
    const accessCode = document.getElementById('bambu-access-code').value.trim();
    const printerModel = document.getElementById('bambu-printer-model').value;

    if (!printerIp || !accessCode) {
        showNotification('请填写 IP 地址和访问码', 'error');
        return;
    }

    showLoading();

    try {
        const response = await fetch(`${API_BASE}/api/bambu/camera/test-connection`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                printer_ip: printerIp,
                access_code: accessCode,
                printer_model: printerModel
            })
        });

        const data = await response.json();

        if (data.success) {
            showNotification('连接测试成功！摄像头工作正常', 'success');
        } else {
            showNotification(data.error || '连接测试失败', 'error');
        }
    } catch (error) {
        showNotification('网络错误：' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

// 使用 Bambu 摄像头拍照
async function captureWithBambuCamera() {
    if (!selectedBambuConfig) {
        showNotification('请先选择打印机配置', 'error');
        return;
    }

    showLoading();

    try {
        const response = await fetch(`${API_BASE}/api/bambu/camera/capture`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                config_name: selectedBambuConfig
            })
        });

        const data = await response.json();

        if (data.success) {
            // 获取目标输入框
            const targetInputId = document.getElementById('target-input-id').value;
            const previewId = targetInputId.replace('-image', '-preview');

            // 设置预览图
            const preview = document.getElementById(previewId);
            preview.src = data.preview_url;
            preview.style.display = 'inline-block';

            // 下载图片并设置为文件输入
            const imgResponse = await fetch(data.preview_url);
            const blob = await imgResponse.blob();
            const file = new File([blob], data.filename, { type: 'image/jpeg' });

            const dataTransfer = new DataTransfer();
            dataTransfer.items.add(file);

            const fileInput = document.getElementById(targetInputId);
            fileInput.files = dataTransfer.files;

            showNotification('拍照成功！', 'success');
            hideBambuCameraDialog();
        } else {
            showNotification(data.error || '拍照失败', 'error');
        }
    } catch (error) {
        showNotification('网络错误：' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

// 删除 Bambu 配置
async function removeBambuConfig(configName) {
    if (!confirm(`确定要删除配置 "${configName}" 吗？`)) {
        return;
    }

    showLoading();

    try {
        const response = await fetch(`${API_BASE}/api/bambu/camera/remove-config`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                name: configName
            })
        });

        const data = await response.json();

        if (data.success) {
            showNotification('配置已删除', 'success');
            loadAndDisplayBambuConfigs();
        } else {
            showNotification(data.error || '删除失败', 'error');
        }
    } catch (error) {
        showNotification('网络错误：' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

// 更新工作区域显示
function updateWorkAreaDisplay() {
    const modelSelect = document.getElementById('bambu-printer-model');
    const workAreaDisplay = document.getElementById('work-area-display');

    const workAreas = {
        'A1MINI': '180×180×180mm',
        'A1': '256×256×256mm',
        'P1P': '256×256×256mm',
        'P1S': '256×256×256mm',
        'X1C': '256×256×256mm'
    };

    const selectedModel = modelSelect.value;
    const workArea = workAreas[selectedModel] || '180×180×180mm';

    workAreaDisplay.textContent = `📐 工作区域: ${workArea}`;
}

// 页面加载时初始化工作区域显示
document.addEventListener('DOMContentLoaded', function() {
    // 初始化工作区域显示
    updateWorkAreaDisplay();
});

// ==================== 自动绘制标记功能 ====================

// 标记位置设置模式
let currentMarkerMode = 'manual';
const STORAGE_KEY = 'calibration_marker_positions';

// 页面加载时检查是否有保存的位置
document.addEventListener('DOMContentLoaded', function() {
    updateLastPositionInfo();
});

// 设置标记位置模式
function setMarkerPositionMode(mode) {
    currentMarkerMode = mode;

    // 更新按钮状态
    document.querySelectorAll('.mode-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    document.getElementById(`mode-${mode}-btn`).classList.add('active');

    // 显示对应的面板
    document.querySelectorAll('.marker-position-mode').forEach(panel => {
        panel.style.display = 'none';
    });
    document.getElementById(`marker-position-${mode}`).style.display = 'block';
}

// 自动生成推荐位置
function autoGeneratePositions() {
    // 工作区尺寸（毫米）
    const workAreaWidth = 217;
    const workAreaHeight = 299;
    const margin = 10; // 边距

    // 生成四个角落的位置
    const positions = [
        { x: margin, y: margin },                        // 左上角
        { x: workAreaWidth - margin, y: margin },        // 右上角
        { x: workAreaWidth - margin, y: workAreaHeight - margin },  // 右下角
        { x: margin, y: workAreaHeight - margin }        // 左下角
    ];

    // 更新输入框
    const positionInputs = document.querySelectorAll('.marker-position-input');
    positions.forEach((pos, index) => {
        if (positionInputs[index]) {
            positionInputs[index].querySelector('.marker-x').value = pos.x;
            positionInputs[index].querySelector('.marker-y').value = pos.y;
        }
    });

    showNotification('已自动生成推荐位置（四个角落）', 'success');
}

// 保存当前位置
function saveCurrentPositions() {
    const positionInputs = document.querySelectorAll('.marker-position-input');
    const positions = [];

    positionInputs.forEach((input, index) => {
        const x = input.querySelector('.marker-x').value;
        const y = input.querySelector('.marker-y').value;
        positions.push({
            id: index,
            x: parseFloat(x),
            y: parseFloat(y)
        });
    });

    // 保存到localStorage
    const data = {
        positions: positions,
        timestamp: new Date().toISOString(),
        markerSize: parseFloat(document.getElementById('marker-size').value)
    };

    localStorage.setItem(STORAGE_KEY, JSON.stringify(data));

    showNotification('当前位置配置已保存', 'success');
    updateLastPositionInfo();
}

// 加载上次位置
function loadLastPositions() {
    const savedData = localStorage.getItem(STORAGE_KEY);

    if (!savedData) {
        showNotification('未找到保存的位置配置', 'error');
        return;
    }

    try {
        const data = JSON.parse(savedData);

        // 恢复位置
        const positionInputs = document.querySelectorAll('.marker-position-input');
        data.positions.forEach((pos, index) => {
            if (positionInputs[index]) {
                positionInputs[index].querySelector('.marker-x').value = pos.x;
                positionInputs[index].querySelector('.marker-y').value = pos.y;
            }
        });

        // 恢复标记尺寸
        if (data.markerSize) {
            document.getElementById('marker-size').value = data.markerSize;
        }

        const saveTime = new Date(data.timestamp).toLocaleString('zh-CN');
        showNotification(`已加载 ${saveTime} 保存的位置配置`, 'success');

    } catch (error) {
        showNotification('加载位置配置失败', 'error');
        console.error(error);
    }
}

// 清除保存的位置
function clearSavedPositions() {
    if (confirm('确定要清除保存的位置配置吗？')) {
        localStorage.removeItem(STORAGE_KEY);
        showNotification('已清除保存的位置配置', 'success');
        updateLastPositionInfo();
    }
}

// 更新上次位置的信息显示
function updateLastPositionInfo() {
    const infoDiv = document.getElementById('last-position-info');
    const savedData = localStorage.getItem(STORAGE_KEY);

    if (savedData) {
        try {
            const data = JSON.parse(savedData);
            const saveTime = new Date(data.timestamp).toLocaleString('zh-CN');
            infoDiv.innerHTML = `✅ 已保存: ${saveTime} (${data.positions.length} 个标记)`;
        } catch (error) {
            infoDiv.innerHTML = '';
        }
    } else {
        infoDiv.innerHTML = 'ℹ️ 暂无保存的位置配置';
    }
}

// 绘制ArUco标记
async function drawMarkers() {
    const markerSize = document.getElementById('marker-size').value;

    // 收集标记位置
    const positionInputs = document.querySelectorAll('.marker-position-input');
    const positions = {};

    positionInputs.forEach((input, index) => {
        const x = input.querySelector('.marker-x').value;
        const y = input.querySelector('.marker-y').value;
        positions[index] = { x: parseFloat(x), y: parseFloat(y) };
    });

    // 验证位置
    if (Object.keys(positions).length < 3) {
        showNotification('至少需要3个标记位置', 'error');
        return;
    }

    showLoading();

    try {
        const response = await fetch(`${API_BASE}/api/draw-markers`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                positions: positions,
                marker_size: parseFloat(markerSize)
            })
        });

        const data = await response.json();

        if (data.success) {
            // 显示预览
            const preview = document.getElementById('draw-markers-preview');
            preview.src = data.preview_url;
            preview.style.display = 'inline-block';

            // 设置下载链接
            const downloadBtn = document.getElementById('draw-markers-download');
            downloadBtn.href = data.gcode_url;
            downloadBtn.download = data.gcode_file;

            // 显示结果
            document.getElementById('draw-markers-result').style.display = 'block';

            showNotification('标记绘制Gcode生成成功！', 'success');
        } else {
            showNotification(data.error || '生成失败', 'error');
        }
    } catch (error) {
        showNotification('网络错误：' + error.message, 'error');
    } finally {
        hideLoading();
    }
}
