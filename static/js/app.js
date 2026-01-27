// API基础URL
const API_BASE = '';

// 显示/隐藏标签页
function showTab(tabName) {
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
    event.target.classList.add('active');
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
        displayWordList();

        // 切换到步骤2
        document.getElementById('import-step-1').style.display = 'none';
        document.getElementById('import-step-2').style.display = 'block';

        showNotification(`成功导入 ${importedWords.length} 个单词`, 'success');

    } catch (error) {
        showNotification('文件读取失败：' + error.message, 'error');
        console.error('错误详情:', error);
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
    document.getElementById('import-step-1').style.display = 'block';
    document.getElementById('import-step-2').style.display = 'none';
    document.getElementById('import-result').style.display = 'none';
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
