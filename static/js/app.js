const API_BASE = '';

let activeController = null;

function show(el) {
    if (typeof el === 'string') el = document.getElementById(el);
    if (el) el.classList.remove('hidden');
}

function hide(el) {
    if (typeof el === 'string') el = document.getElementById(el);
    if (el) el.classList.add('hidden');
}

async function apiRequest({ url, method = 'POST', json, formData, validate, onSuccess, onError }) {
    if (activeController) {
        activeController.abort();
    }
    activeController = new AbortController();
    const signal = activeController.signal;

    showLoading();

    try {
        const opts = { method, signal };
        if (json) {
            opts.headers = { 'Content-Type': 'application/json' };
            opts.body = JSON.stringify(json);
        } else if (formData) {
            opts.body = formData;
        }

        const resp = await fetch(API_BASE + url, opts);
        const data = await resp.json();

        if (data.success) {
            if (onSuccess) onSuccess(data);
        } else {
            const msg = data.error || '操作失败';
            if (onError) {
                onError(msg, data);
            } else {
                showNotification(msg, 'error');
            }
        }
    } catch (error) {
        if (error.name === 'AbortError') return;
        const msg = '网络错误：' + error.message;
        if (onError) {
            onError(msg);
        } else {
            showNotification(msg, 'error');
        }
    } finally {
        activeController = null;
        hideLoading();
    }
}

function showResultElement(resultId, previewId, previewSrc, downloadId, downloadHref) {
    if (previewId && previewSrc) {
        const preview = document.getElementById(previewId);
        preview.src = previewSrc;
        preview.classList.remove('hidden');
        preview.style.display = 'inline-block';
    }
    if (downloadId && downloadHref) {
        document.getElementById(downloadId).href = downloadHref;
    }
    show(resultId);
}

function showTab(tabName, event) {
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    document.querySelectorAll('.tab-button').forEach(b => b.classList.remove('active'));
    document.getElementById(`tab-${tabName}`).classList.add('active');
    if (event?.target) event.target.classList.add('active');
}

function showLoading() {
    const el = document.getElementById('loading');
    el.classList.remove('hidden');
    el.style.display = 'flex';
}

function hideLoading() {
    const el = document.getElementById('loading');
    el.classList.add('hidden');
    el.style.display = '';
}

function showNotification(message, type = 'info') {
    const n = document.getElementById('notification');
    n.textContent = message;
    n.className = `notification ${type}`;
    n.classList.remove('hidden');
    clearTimeout(n._timer);
    n._timer = setTimeout(() => { n.classList.add('hidden'); }, 3000);
}

function previewImage(input, previewId) {
    const file = input.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = e => {
        const preview = document.getElementById(previewId);
        preview.src = e.target.result;
        preview.classList.remove('hidden');
        preview.style.display = 'inline-block';

        if (previewId === 'lookup-preview') {
            initLookupCropCanvas(file);
        }
    };
    reader.readAsDataURL(file);
}

function toggleCollapse(header) {
    const body = header.nextElementSibling;
    const arrow = header.querySelector('.collapsible-arrow');
    const isHidden = body.classList.contains('hidden');
    if (isHidden) {
        body.classList.remove('hidden');
        arrow.textContent = '▼';
    } else {
        body.classList.add('hidden');
        arrow.textContent = '▶';
    }
}

// ==================== 拍照点词 ====================

let tapWords = [];
let tapMarkedWords = new Set();
let tapImageSrc = null;
let tapScale = 1;
let tapDisplayCanvas = null;
let tapDisplayCtx = null;

function startOcrTap() {
    const imageInput = document.getElementById('tap-image');
    if (!imageInput.files[0]) return showNotification('请先上传图片或拍照', 'error');

    document.getElementById('tap-status').textContent = '正在识别...';

    const fd = new FormData();
    fd.append('image', imageInput.files[0]);

    apiRequest({
        url: '/api/ocr-words',
        formData: fd,
        onSuccess(data) {
            if (!data.words || data.words.length === 0) {
                showNotification('未识别到英文单词', 'error');
                document.getElementById('tap-status').textContent = '';
                return;
            }
            tapWords = data.words;
            tapMarkedWords = new Set();
            tapImageSrc = null;
            showNotification(`识别到 ${data.words.length} 个英文单词，点击单词标记为已会词`, 'success');
            document.getElementById('tap-status').textContent = `识别到 ${data.words.length} 个单词`;
            renderTapCanvas(imageInput.files[0]);
        },
        onError(msg) {
            showNotification(msg, 'error');
            document.getElementById('tap-status').textContent = '';
        }
    });
}

function renderTapCanvas(file) {
    const reader = new FileReader();
    reader.onload = function(e) {
        const img = new Image();
        img.onload = function() {
            tapDisplayCanvas = document.getElementById('tap-display-canvas');
            tapDisplayCtx = tapDisplayCanvas.getContext('2d');

            const maxW = tapDisplayCanvas.parentElement.clientWidth || 800;
            tapScale = Math.min(maxW / img.width, 1);
            tapDisplayCanvas.width = img.width * tapScale;
            tapDisplayCanvas.height = img.height * tapScale;

            tapImageSrc = img;
            drawTapCanvas();
            show('tap-workspace');
        };
        img.src = e.target.result;
    };
    reader.readAsDataURL(file);
}

function drawTapCanvas() {
    if (!tapDisplayCtx || !tapImageSrc) return;
    const ctx = tapDisplayCtx;
    const canvas = tapDisplayCanvas;
    const s = tapScale;

    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(tapImageSrc, 0, 0, canvas.width, canvas.height);

    for (const w of tapWords) {
        const bbox = w.bbox;
        if (!bbox || bbox.length < 4) continue;

        const x1 = bbox[0][0] * s;
        const y1 = bbox[0][1] * s;
        const x2 = bbox[2][0] * s;
        const y2 = bbox[2][1] * s;

        const isMarked = tapMarkedWords.has(w.word.toLowerCase());

        ctx.fillStyle = isMarked ? 'rgba(76, 175, 80, 0.4)' : 'rgba(24, 144, 255, 0.2)';
        ctx.fillRect(x1, y1, x2 - x1, y2 - y1);

        ctx.strokeStyle = isMarked ? '#4caf50' : '#1890ff';
        ctx.lineWidth = 2;
        ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);

        ctx.fillStyle = isMarked ? '#2e7d32' : '#fff';
        ctx.font = `bold ${Math.max(12, Math.min(16, (x2 - x1) / w.word.length))}px sans-serif`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'bottom';

        if (isMarked) {
            ctx.fillText('\u2713 ' + w.word, (x1 + x2) / 2, y1 - 2);
        }
    }

    document.getElementById('tap-marked-count').textContent = `已标记 ${tapMarkedWords.size} 个已会词`;
}

document.addEventListener('click', function(e) {
    if (!tapDisplayCanvas) return;
    if (e.target !== tapDisplayCanvas) return;

    const rect = tapDisplayCanvas.getBoundingClientRect();
    const scaleX = tapDisplayCanvas.width / rect.width;
    const scaleY = tapDisplayCanvas.height / rect.height;
    const cx = (e.clientX - rect.left) * scaleX;
    const cy = (e.clientY - rect.top) * scaleY;
    const s = tapScale;

    let hit = null;
    for (const w of tapWords) {
        const bbox = w.bbox;
        if (!bbox || bbox.length < 4) continue;
        const x1 = bbox[0][0] * s;
        const y1 = bbox[0][1] * s;
        const x2 = bbox[2][0] * s;
        const y2 = bbox[2][1] * s;

        if (cx >= x1 && cx <= x2 && cy >= y1 && cy <= y2) {
            hit = w;
            break;
        }
    }

    if (hit) {
        const key = hit.word.toLowerCase();
        if (tapMarkedWords.has(key)) {
            tapMarkedWords.delete(key);
        } else {
            tapMarkedWords.add(key);
        }
        drawTapCanvas();
    }
});

function submitTapWords() {
    if (tapMarkedWords.size === 0) return showNotification('请先点击标记一些单词', 'error');
    const words = Array.from(tapMarkedWords);
    apiRequest({
        url: '/api/add-known-words',
        json: { words },
        onSuccess(data) {
            showNotification(`成功添加 ${data.added_count} 个已会词`, 'success');
            document.getElementById('tap-status').textContent = `已提交 ${data.added_count} 个单词`;
        }
    });
}

function clearTapMarks() {
    tapMarkedWords.clear();
    drawTapCanvas();
}

// ==================== 批量导入 ====================

let importedWords = [];
let currentWordIndex = 0;
let knownWordsInCard = [];
let unknownWordsInCard = [];
let importMode = 'list';
let cardTemplateHTML = null;

async function uploadWordJSON() {
    const fileInput = document.getElementById('word-json-file');
    if (!fileInput.files[0]) return showNotification('请选择JSON文件', 'error');
    const file = fileInput.files[0];
    if (!file.name.endsWith('.json')) return showNotification('请选择JSON文件', 'error');

    showLoading();

    try {
        const rawText = await file.text();
        let text = rawText.replace(/^\ufeff/, '');
        text = text.replace(/^\s*\/\/.*$/gm, '');
        text = text.replace(/^\s*#.*$/gm, '');
        text = text.replace(/,(\s*[}\]])/g, '$1');

        let wordsData = [];

        try {
            const parsed = JSON.parse(text);
            wordsData = Array.isArray(parsed) ? parsed : [parsed];
        } catch {
            const lines = text.split('\n');
            for (const line of lines) {
                const trimmed = line.trim();
                if (!trimmed || trimmed.startsWith('//') || trimmed.startsWith('#')) continue;
                try {
                    const obj = JSON.parse(trimmed);
                    if (obj.headWord) wordsData.push(obj);
                } catch {}
            }
            if (wordsData.length === 0) throw new Error('无法解析JSON文件，请确保文件格式正确');
        }

        importedWords = [];
        for (const item of wordsData) {
            const word = item.headWord || '';
            const content = item.content?.word?.content;
            if (!word) continue;

            importedWords.push({
                word,
                phonetic: content?.usphone || content?.ukphone || '',
                definitions: (content?.trans || []).map(t => t.tranCn || '').join('\uff1b'),
                examples: (content?.sentence?.sentences || []).slice(0, 2).map(s => ({
                    en: s.sContent || '',
                    cn: s.sCn || ''
                }))
            });
        }

        if (importedWords.length === 0) {
            showNotification('未找到有效的单词数据', 'error');
            return;
        }

        displayWordList();
        hide('import-step-1');
        show('import-step-2');
        showNotification(`成功导入 ${importedWords.length} 个单词`, 'success');
    } catch (error) {
        showNotification('JSON格式错误：' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

function displayWordList() {
    const listEl = document.getElementById('word-list');
    listEl.innerHTML = '';

    const frag = document.createDocumentFragment();
    importedWords.forEach((item, index) => {
        const div = document.createElement('div');
        div.className = 'word-item';
        div.dataset.index = index;

        let examplesHtml = '';
        if (item.examples?.length) {
            examplesHtml = item.examples.map(ex =>
                `<div class="word-item-example">${ex.en}${ex.cn ? ' - ' + ex.cn : ''}</div>`
            ).join('');
        }

        div.innerHTML = `
            <input type="checkbox" data-word-index="${index}">
            <div class="word-item-content">
                <div class="word-item-word">${item.word}</div>
                ${item.phonetic ? `<div class="word-item-phonetic">${item.phonetic}</div>` : ''}
                ${item.definitions ? `<div class="word-item-definition">${item.definitions}</div>` : ''}
                ${examplesHtml}
            </div>
        `;
        frag.appendChild(div);
    });
    listEl.appendChild(frag);
    updateSelectedCount();
}

function updateWordSelection(index) {
    const cb = document.querySelector(`[data-word-index="${index}"]`);
    const item = cb?.closest('.word-item');
    if (item) item.classList.toggle('selected', cb.checked);
    updateSelectedCount();
}

function updateSelectedCount() {
    const count = document.querySelectorAll('#word-list input[type="checkbox"]:checked').length;
    document.getElementById('selected-count').textContent = `已选择: ${count}`;
}

function setAllCheckboxes(checked) {
    document.querySelectorAll('#word-list input[type="checkbox"]').forEach(cb => {
        cb.checked = checked;
        cb.closest('.word-item').classList.toggle('selected', checked);
    });
    updateSelectedCount();
}

function selectAllWords() { setAllCheckboxes(true); }
function deselectAllWords() { setAllCheckboxes(false); }

function invertSelection() {
    document.querySelectorAll('#word-list input[type="checkbox"]').forEach(cb => {
        cb.checked = !cb.checked;
        cb.closest('.word-item').classList.toggle('selected', cb.checked);
    });
    updateSelectedCount();
}

document.addEventListener('change', e => {
    if (e.target.matches('#word-list input[type="checkbox"]')) {
        const idx = parseInt(e.target.dataset.wordIndex);
        updateWordSelection(idx);
    }
});

function submitWords(words, resultDivId) {
    apiRequest({
        url: '/api/add-known-words',
        json: { words },
        onSuccess(data) {
            const r = document.getElementById(resultDivId);
            r.innerHTML = `
                <div class="alert alert-success">
                    <strong>添加成功！</strong><br>
                    成功添加 ${data.added_count} 个单词到数据库。<br>
                    ${data.skipped_count > 0 ? `跳过 ${data.skipped_count} 个已存在的单词。` : ''}
                </div>
            `;
            show(r);
            showNotification('添加成功！', 'success');
        }
    });
}

function addSelectedWords() {
    const checked = document.querySelectorAll('#word-list input[type="checkbox"]:checked');
    if (checked.length === 0) return showNotification('请至少选择一个单词', 'error');
    const words = Array.from(checked, cb => importedWords[parseInt(cb.dataset.wordIndex)].word);
    submitWords(words, 'import-result');
}

function switchImportMode(mode) {
    importMode = mode;
    const isList = mode === 'list';

    if (isList) {
        show('import-mode-list');
        hide('import-mode-card');
    } else {
        hide('import-mode-list');
        show('import-mode-card');
    }

    document.getElementById('mode-list-btn').classList.toggle('active', isList);
    document.getElementById('mode-card-btn').classList.toggle('active', !isList);

    if (isList) {
        document.removeEventListener('keydown', handleCardKeyPress);
    } else {
        initCardMode();
        document.addEventListener('keydown', handleCardKeyPress);
    }
}

function handleCardKeyPress(event) {
    if (importMode !== 'card') return;
    const key = event.key;
    if (key === 'ArrowLeft' || key.toLowerCase() === 'a') {
        event.preventDefault();
        markWord('unknown');
        pulseButton('unknown');
    } else if (key === 'ArrowRight' || key.toLowerCase() === 'd') {
        event.preventDefault();
        markWord('known');
        pulseButton('known');
    }
}

function pulseButton(type) {
    const btn = document.querySelector(`.word-card-btn.${type}`);
    if (btn) {
        btn.style.transform = 'scale(0.95)';
        setTimeout(() => { btn.style.transform = ''; }, 100);
    }
}

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

function updateCardDisplay() {
    if (currentWordIndex >= importedWords.length) {
        showCardSummary();
        return;
    }
    document.getElementById('current-word').textContent = importedWords[currentWordIndex].word;
}

function updateCardProgress() {
    const total = importedWords.length;
    const pct = (currentWordIndex / total) * 100;
    document.getElementById('progress-text').textContent = `进度: ${currentWordIndex} / ${total}`;
    document.getElementById('progress-fill').style.width = `${pct}%`;
}

function markWord(type) {
    if (currentWordIndex >= importedWords.length) return;
    (type === 'known' ? knownWordsInCard : unknownWordsInCard).push(importedWords[currentWordIndex]);
    currentWordIndex++;
    updateCardDisplay();
    updateCardProgress();
}

function showCardSummary() {
    const container = document.querySelector('.word-card-container');
    container.innerHTML = `
        <div class="word-card-summary">
            <h3>完成！</h3>
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
            <p class="summary-note">已标记 ${unknownWordsInCard.length} 个单词为"不认识"，将添加到数据库</p>
            <div class="word-card-complete-actions">
                <button class="btn btn-success" onclick="submitCardResults()">提交到数据库</button>
                <button class="btn btn-secondary" onclick="resetImport()">重新上传</button>
            </div>
        </div>
    `;
}

function submitCardResults() {
    if (unknownWordsInCard.length === 0) {
        showNotification('没有需要添加的单词', 'info');
        resetImport();
        return;
    }
    const words = unknownWordsInCard.map(w => w.word);
    apiRequest({
        url: '/api/add-known-words',
        json: { words },
        onSuccess(data) {
            const r = document.getElementById('import-result');
            r.innerHTML = `
                <div class="alert alert-success">
                    <strong>添加成功！</strong><br>
                    成功添加 ${data.added_count} 个单词到数据库。<br>
                    ${data.skipped_count > 0 ? `跳过 ${data.skipped_count} 个已存在的单词。` : ''}
                </div>
            `;
            show(r);
            showNotification('添加成功！', 'success');
            setTimeout(resetImport, 2000);
        }
    });
}

function resetImport() {
    document.removeEventListener('keydown', handleCardKeyPress);
    importMode = 'list';
    currentWordIndex = 0;
    knownWordsInCard = [];
    unknownWordsInCard = [];

    show('import-step-1');
    hide('import-step-2');
    hide('import-result');
    show('import-mode-list');
    hide('import-mode-card');
    document.getElementById('mode-list-btn').classList.add('active');
    document.getElementById('mode-card-btn').classList.remove('active');

    const cardContainer = document.querySelector('.word-card-container');
    if (cardContainer && cardTemplateHTML) {
        cardContainer.innerHTML = cardTemplateHTML;
    }

    document.getElementById('word-json-file').value = '';
    importedWords = [];
}

// ==================== 已会词管理 ====================

let allKnownWords = [];

async function loadKnownWords() {
    try {
        const resp = await fetch(API_BASE + '/api/get-known-words');
        const data = await resp.json();
        if (data.success) {
            allKnownWords = data.words;
            renderKnownWords(allKnownWords);
        }
    } catch (e) {
        showNotification('加载已会词列表失败', 'error');
    }
}

function renderKnownWords(words) {
    const stats = document.getElementById('known-words-stats');
    const list = document.getElementById('known-words-list');
    stats.textContent = `共 ${words.length} 个已会词`;
    list.innerHTML = '';

    const frag = document.createDocumentFragment();
    words.forEach(word => {
        const item = document.createElement('div');
        item.className = 'known-word-item';
        item.innerHTML = `
            <span class="known-word-text">${word}</span>
            <button class="btn btn-danger btn-small" onclick="removeKnownWord('${word}')">删除</button>
        `;
        frag.appendChild(item);
    });
    list.appendChild(frag);
}

function filterKnownWords() {
    const query = document.getElementById('known-words-search').value.toLowerCase();
    const filtered = allKnownWords.filter(w => w.includes(query));
    renderKnownWords(filtered);
}

function removeKnownWord(word) {
    apiRequest({
        url: '/api/remove-known-word',
        json: { word },
        onSuccess() {
            showNotification(`已删除: ${word}`, 'success');
            loadKnownWords();
        }
    });
}

// ==================== OneDrive 备份 ====================

let onedrivePollTimer = null;

async function checkOnedriveStatus() {
    try {
        const resp = await fetch(API_BASE + '/api/onedrive/status');
        const data = await resp.json();
        const connectBtn = document.getElementById('btn-onedrive-connect');
        const backupBtn = document.getElementById('btn-onedrive-backup');
        const listBtn = document.getElementById('btn-onedrive-list');
        const disconnectBtn = document.getElementById('btn-onedrive-disconnect');
        const statusEl = document.getElementById('onedrive-status');

        if (!data.configured || !data.client_id_set) {
            statusEl.innerHTML = '未配置 Client ID，请在上方输入并保存';
            hide(connectBtn); hide(backupBtn); hide(listBtn); hide(disconnectBtn);
            return;
        }
        if (data.authorized) {
            statusEl.innerHTML = '已连接OneDrive';
            hide(connectBtn);
            show(backupBtn); show(listBtn); show(disconnectBtn);
        } else {
            statusEl.innerHTML = '已配置 Client ID，点击「连接OneDrive」授权';
            show(connectBtn);
            hide(backupBtn); hide(listBtn); hide(disconnectBtn);
        }
    } catch {}
}

function saveOnedriveClientId() {
    const clientId = document.getElementById('onedrive-client-id').value.trim();
    if (!clientId) return showNotification('请输入 Client ID', 'error');
    apiRequest({
        url: '/api/onedrive/config',
        json: { client_id: clientId },
        onSuccess() {
            showNotification('Client ID 已保存', 'success');
            checkOnedriveStatus();
        }
    });
}

function onedriveConnect() {
    apiRequest({
        url: '/api/onedrive/auth',
        onSuccess(data) {
            const instructions = document.getElementById('onedrive-auth-instructions');
            instructions.innerHTML = `
                请在浏览器中打开以下链接并输入代码：<br>
                <strong>${data.verification_uri}</strong><br>
                代码: <strong style="font-size:1.3em; letter-spacing:2px;">${data.user_code}</strong>
            `;
            show('onedrive-auth-modal');
            show('onedrive-polling-spinner');

            if (onedrivePollTimer) clearInterval(onedrivePollTimer);
            onedrivePollTimer = setInterval(() => {
                pollOnedriveToken(data.device_code);
            }, (data.interval || 5) * 1000);
        }
    });
}

function pollOnedriveToken(deviceCode) {
    fetch(API_BASE + '/api/onedrive/poll', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ device_code: deviceCode })
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            clearInterval(onedrivePollTimer);
            onedrivePollTimer = null;
            hide('onedrive-auth-modal');
            hide('onedrive-polling-spinner');
            showNotification('OneDrive授权成功！', 'success');
            checkOnedriveStatus();
        } else if (!data.pending) {
            clearInterval(onedrivePollTimer);
            onedrivePollTimer = null;
            hide('onedrive-polling-spinner');
            showNotification(data.error || '授权失败', 'error');
        }
    })
    .catch(() => {});
}

function closeOnedriveAuth() {
    if (onedrivePollTimer) {
        clearInterval(onedrivePollTimer);
        onedrivePollTimer = null;
    }
    hide('onedrive-auth-modal');
    hide('onedrive-polling-spinner');
}

function onedriveBackup() {
    apiRequest({
        url: '/api/onedrive/backup',
        onSuccess(data) {
            showNotification(`备份成功！版本 v${data.version}，共 ${data.word_count} 个单词`, 'success');
        }
    });
}

function onedriveListBackups() {
    apiRequest({
        url: '/api/onedrive/backups',
        onSuccess(data) {
            const container = document.getElementById('onedrive-backup-list');
            if (!data.backups || data.backups.length === 0) {
                container.innerHTML = '<p class="hint-text">暂无备份</p>';
            } else {
                container.innerHTML = data.backups.map(b => `
                    <div class="backup-item">
                        <span class="backup-name">${b.name}</span>
                        <span class="backup-meta">${b.size} bytes | ${new Date(b.last_modified).toLocaleString('zh-CN')}</span>
                        <button class="btn btn-primary btn-small" onclick="onedriveRestore('${b.name}')">恢复</button>
                    </div>
                `).join('');
            }
            show(container);
        }
    });
}

function onedriveRestore(backupName) {
    apiRequest({
        url: '/api/onedrive/restore',
        json: { backup_name: backupName, merge: true },
        onSuccess(data) {
            showNotification(`恢复成功！${data.new_words} 个新单词已合并，共 ${data.merged_count} 个`, 'success');
            loadKnownWords();
        }
    });
}

function onedriveDisconnect() {
    if (!confirm('确定要断开OneDrive连接吗？')) return;
    apiRequest({
        url: '/api/onedrive/disconnect',
        onSuccess() {
            showNotification('已断开OneDrive连接', 'success');
            checkOnedriveStatus();
            document.getElementById('onedrive-backup-list').classList.add('hidden');
        }
    });
}

// ==================== 查词预览 ====================

let lookupDebounceTimer = null;

function debounceLookup() {
    clearTimeout(lookupDebounceTimer);
    const word = document.getElementById('preview-word-input').value.trim();
    if (!word) return hideWordPreview();
    lookupDebounceTimer = setTimeout(lookupWord, 500);
}

async function lookupWord() {
    const word = document.getElementById('preview-word-input').value.trim();
    if (!word) return hideWordPreview();
    showWordPreviewLoading();

    try {
        const resp = await fetch(`${API_BASE}/api/word-preview?word=${encodeURIComponent(word)}`);
        const data = await resp.json();
        data.success ? displayWordPreview(data) : showWordPreviewNoResult();
    } catch {
        showNotification('查询失败', 'error');
        showWordPreviewNoResult();
    }
}

function setWordPreviewVisibility(loading, result, noResult) {
    const l = document.getElementById('word-preview-loading');
    const r = document.getElementById('word-preview-result');
    const n = document.getElementById('word-preview-no-result');
    if (loading) show(l); else hide(l);
    if (result) show(r); else hide(r);
    if (noResult) show(n); else hide(n);
}

function showWordPreviewLoading() { setWordPreviewVisibility(true, false, false); }
function hideWordPreview() { setWordPreviewVisibility(false, false, false); }
function showWordPreviewNoResult() { setWordPreviewVisibility(false, false, true); }

function displayWordPreview(data) {
    setWordPreviewVisibility(false, true, false);

    document.getElementById('preview-word').textContent = data.word;
    document.getElementById('preview-phonetic').textContent = data.phonetic || '';
    document.getElementById('preview-pos').textContent = data.pos || '';

    fillListSection('preview-definitions', 'preview-definitions-section', data.definitions);
    fillListSection('preview-examples', 'preview-examples-section', data.examples);

    const baseSection = document.getElementById('preview-base-form-section');
    if (data.base_form && data.base_form !== data.word) {
        show(baseSection);
        document.getElementById('preview-base-form').textContent = `原形：${data.base_form}`;
    } else {
        hide(baseSection);
    }

    const entriesSection = document.getElementById('preview-all-entries-section');
    if (data.all_entries?.length) {
        show(entriesSection);
        const entriesDiv = document.getElementById('preview-all-entries');
        entriesDiv.innerHTML = data.all_entries.map((entry, i) => {
            let html = `<div class="entry-item${i < data.all_entries.length - 1 ? ' entry-border' : ''}">`;
            html += `<strong class="entry-pos">${entry.pos || '未知词性'}</strong>`;
            if (entry.phonetics?.length) html += ` <span class="entry-phonetic">${entry.phonetics[0]}</span>`;
            if (entry.definitions?.length) {
                html += '<ul class="entry-def-list">';
                entry.definitions.forEach(def => { html += `<li>${def}</li>`; });
                html += '</ul>';
            }
            html += '</div>';
            return html;
        }).join('');
    } else {
        hide(entriesSection);
    }
}

function fillListSection(listId, sectionId, items) {
    const section = document.getElementById(sectionId);
    const list = document.getElementById(listId);
    if (items?.length) {
        show(section);
        list.innerHTML = items.map(d => `<li>${d}</li>`).join('');
    } else {
        hide(section);
    }
}

// ==================== 自动查词 ====================

let lookupCropRect = null;
let lookupCropCanvas = null;
let lookupCropCtx = null;
let lookupCropImg = null;
let lookupCropScale = 1;
let lookupCropDragging = false;
let lookupCropStart = { x: 0, y: 0 };

function autoLookup() {
    const imageInput = document.getElementById('lookup-image');
    if (!imageInput.files[0]) return showNotification('请先上传试卷图片', 'error');

    const fd = new FormData();
    fd.append('image', imageInput.files[0]);
    fd.append('known_words', document.getElementById('known-words-input').value);
    fd.append('only_phonetics', document.getElementById('only-phonetics').checked ? 'true' : 'false');

    if (lookupCropRect) {
        fd.append('crop_x', Math.round(lookupCropRect.x));
        fd.append('crop_y', Math.round(lookupCropRect.y));
        fd.append('crop_w', Math.round(lookupCropRect.w));
        fd.append('crop_h', Math.round(lookupCropRect.h));
    }

    apiRequest({
        url: '/api/auto-lookup',
        formData: fd,
        onSuccess(data) {
            showResultElement('lookup-result', 'lookup-annotated', data.annotated_url, 'lookup-download', data.gcode_url);
            document.getElementById('lookup-gcode-file').value = data.gcode_file;
            showNotification('处理完成！', 'success');
        },
        onError(msg, data) {
            if (data?.error?.includes('未加载')) console.error('自动查词模块不可用:', data.error);
            showNotification(msg, 'error');
        }
    });
}

function initLookupCropCanvas(file) {
    const reader = new FileReader();
    reader.onload = function(e) {
        lookupCropImg = new Image();
        lookupCropImg.onload = function() {
            const overlay = document.getElementById('lookup-crop-overlay');
            const canvas = document.getElementById('lookup-crop-canvas');
            const preview = document.getElementById('lookup-preview');

            preview.style.display = 'none';
            show('lookup-crop-overlay');

            const maxW = overlay.parentElement.clientWidth - 40 || 800;
            lookupCropScale = Math.min(maxW / lookupCropImg.width, 1);
            canvas.width = lookupCropImg.width * lookupCropScale;
            canvas.height = lookupCropImg.height * lookupCropScale;
            canvas.style.width = canvas.width + 'px';
            canvas.style.height = canvas.height + 'px';

            lookupCropCanvas = canvas;
            lookupCropCtx = canvas.getContext('2d');
            lookupCropRect = null;
            drawLookupCropCanvas();
        };
        lookupCropImg.src = e.target.result;
    };
    reader.readAsDataURL(file);
}

function drawLookupCropCanvas() {
    if (!lookupCropCtx || !lookupCropImg) return;
    const ctx = lookupCropCtx;
    const canvas = lookupCropCanvas;

    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(lookupCropImg, 0, 0, canvas.width, canvas.height);

    if (lookupCropRect) {
        ctx.fillStyle = 'rgba(0, 0, 0, 0.3)';
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        ctx.clearRect(lookupCropRect.x, lookupCropRect.y, lookupCropRect.w, lookupCropRect.h);
        ctx.drawImage(lookupCropImg,
            lookupCropRect.x / lookupCropScale, lookupCropRect.y / lookupCropScale,
            lookupCropRect.w / lookupCropScale, lookupCropRect.h / lookupCropScale,
            lookupCropRect.x, lookupCropRect.y, lookupCropRect.w, lookupCropRect.h
        );

        ctx.strokeStyle = '#1890ff';
        ctx.lineWidth = 2;
        ctx.setLineDash([6, 3]);
        ctx.strokeRect(lookupCropRect.x, lookupCropRect.y, lookupCropRect.w, lookupCropRect.h);
        ctx.setLineDash([]);

        document.getElementById('crop-info-text').textContent =
            `框选区域: ${Math.round(lookupCropRect.x / lookupCropScale)}, ${Math.round(lookupCropRect.y / lookupCropScale)} - ${Math.round(lookupCropRect.w / lookupCropScale)}x${Math.round(lookupCropRect.h / lookupCropScale)} px`;
    } else {
        document.getElementById('crop-info-text').textContent = '拖动鼠标框选查词区域（默认全部）';
    }
}

function clearCropSelection() {
    lookupCropRect = null;
    drawLookupCropCanvas();
}

(function() {
    document.addEventListener('mousedown', function(e) {
        if (e.target !== lookupCropCanvas) return;
        lookupCropDragging = true;
        const rect = lookupCropCanvas.getBoundingClientRect();
        lookupCropStart = { x: e.clientX - rect.left, y: e.clientY - rect.top };
        lookupCropRect = null;
    });

    document.addEventListener('mousemove', function(e) {
        if (!lookupCropDragging || !lookupCropCanvas) return;
        const rect = lookupCropCanvas.getBoundingClientRect();
        const mx = e.clientX - rect.left;
        const my = e.clientY - rect.top;
        lookupCropRect = {
            x: Math.min(lookupCropStart.x, mx),
            y: Math.min(lookupCropStart.y, my),
            w: Math.abs(mx - lookupCropStart.x),
            h: Math.abs(my - lookupCropStart.y)
        };
        drawLookupCropCanvas();
    });

    document.addEventListener('mouseup', function() {
        if (lookupCropDragging) {
            lookupCropDragging = false;
            if (lookupCropRect && (lookupCropRect.w < 5 || lookupCropRect.h < 5)) {
                lookupCropRect = null;
                drawLookupCropCanvas();
            }
        }
    });
})();

// ==================== 自动抄写 ====================

function autoCopy() {
    const imageInput = document.getElementById('copy-image');
    const text = document.getElementById('copy-text').value.trim();
    if (!imageInput.files[0]) return showNotification('请先上传横线本图片', 'error');
    if (!text) return showNotification('请输入要抄写的文字', 'error');

    const fd = new FormData();
    fd.append('image', imageInput.files[0]);
    fd.append('text', text);

    apiRequest({
        url: '/api/auto-copy',
        formData: fd,
        onSuccess(data) {
            showResultElement('copy-result', 'copy-layout', data.layout_url, 'copy-download', data.gcode_url);
            showNotification('处理完成！', 'success');
        },
        onError(msg, data) {
            if (data?.error?.includes('未加载')) console.error('自动抄写模块不可用:', data.error);
            showNotification(msg, 'error');
        }
    });
}

// ==================== 书写文字 ====================

function writeText() {
    const text = document.getElementById('write-text').value.trim();
    if (!text) return showNotification('请输入要书写的文字', 'error');

    apiRequest({
        url: '/api/write',
        json: { text, use_handright: document.getElementById('use-handright').checked },
        onSuccess(data) {
            showResultElement('write-result', 'write-preview', data.preview_url, 'write-download', data.download_url);
            document.getElementById('write-gcode-file').value = data.gcode_file;
            showNotification('书写代码生成成功！', 'success');
        }
    });
}

// ==================== 校准与标记 ====================

function generateCornerMarkers() {
    apiRequest({
        url: '/api/generate-corner-markers',
        json: {
            frame_width: parseFloat(document.getElementById('corner-frame-width').value),
            frame_height: parseFloat(document.getElementById('corner-frame-height').value),
            marker_size: parseFloat(document.getElementById('corner-marker-size').value)
        },
        onSuccess(data) {
            showResultElement('corner-markers-result', 'corner-markers-preview', data.download_url, 'corner-markers-download', data.download_url);
            showNotification(data.message || '四角标记定位纸生成成功！', 'success');
        }
    });
}

function calibrate() {
    const imageInput = document.getElementById('calib-image');
    if (!imageInput.files[0]) return showNotification('请先上传校准照片', 'error');

    const positions = collectMarkerPositions();
    const fd = new FormData();
    fd.append('image', imageInput.files[0]);
    fd.append('marker_size', document.getElementById('marker-size').value);
    fd.append('positions', JSON.stringify(positions));

    apiRequest({
        url: '/api/calibrate',
        formData: fd,
        onSuccess() {
            const r = document.getElementById('calib-result');
            r.innerHTML = '<div class="alert alert-success"><strong>校准成功！</strong><br>校准文件已保存，可以开始使用写字机了。</div>';
            show(r);
            showNotification('校准成功！', 'success');
        }
    });
}

function drawMarkers() {
    const positions = collectMarkerPositions();
    if (Object.keys(positions).length < 3) return showNotification('至少需要3个标记位置', 'error');

    apiRequest({
        url: '/api/draw-markers',
        json: {
            positions,
            marker_size: parseFloat(document.getElementById('marker-size').value)
        },
        onSuccess(data) {
            const dl = document.getElementById('draw-markers-download');
            dl.href = data.gcode_url;
            dl.download = data.gcode_file;
            showResultElement('draw-markers-result', 'draw-markers-preview', data.preview_url);
            showNotification('标记绘制Gcode生成成功！', 'success');
        }
    });
}

function generateMarkers() {
    apiRequest({
        url: '/api/generate-markers',
        json: {
            num_markers: parseInt(document.getElementById('num-markers').value),
            marker_size: parseInt(document.getElementById('marker-size-gen').value)
        },
        onSuccess(data) {
            showResultElement('markers-result', 'markers-preview', data.download_url, 'markers-download', data.download_url);
            showNotification('标记生成成功！', 'success');
        }
    });
}

function collectMarkerPositions() {
    const positions = {};
    document.querySelectorAll('.marker-position-input').forEach((el, i) => {
        positions[i] = {
            x: parseFloat(el.querySelector('.marker-x').value),
            y: parseFloat(el.querySelector('.marker-y').value)
        };
    });
    return positions;
}

function setMarkerPositions(positions) {
    document.querySelectorAll('.marker-position-input').forEach((el, i) => {
        if (positions[i]) {
            el.querySelector('.marker-x').value = positions[i].x;
            el.querySelector('.marker-y').value = positions[i].y;
        }
    });
}

// ==================== 摄像头 ====================

const cameraStreams = {};

async function startCamera(prefix) {
    const video = document.getElementById(`${prefix}-video`);
    const container = document.getElementById(`${prefix}-camera-container`);
    const button = container.parentElement.querySelector('.camera-button');

    if (!navigator.mediaDevices?.getUserMedia) {
        return showNotification('您的浏览器不支持摄像头功能', 'error');
    }

    try {
        const stream = await navigator.mediaDevices.getUserMedia({
            video: { facingMode: 'environment', width: { ideal: 1920 }, height: { ideal: 1080 } }
        });
        cameraStreams[prefix] = stream;
        video.srcObject = stream;
        video.style.display = 'block';
        show(container);
        button.disabled = true;
        button.textContent = '📷 摄像头已启动';
        showNotification('摄像头已启动', 'success');
    } catch (error) {
        if (error.name === 'NotAllowedError') showNotification('请允许访问摄像头', 'error');
        else if (error.name === 'NotFoundError') showNotification('未检测到摄像头设备', 'error');
        else showNotification('摄像头启动失败: ' + error.message, 'error');
    }
}

function capturePhoto(prefix) {
    const video = document.getElementById(`${prefix}-video`);
    const canvas = document.getElementById(`${prefix}-canvas`);
    const preview = document.getElementById(`${prefix}-preview`);

    if (!cameraStreams[prefix]) return showNotification('请先启动摄像头', 'error');

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);

    const imageUrl = canvas.toDataURL('image/png');
    preview.src = imageUrl;
    preview.classList.remove('hidden');
    preview.style.display = 'inline-block';

    canvas.toBlob(blob => {
        const file = new File([blob], `camera_${prefix}_${Date.now()}.png`, { type: 'image/png' });
        const dt = new DataTransfer();
        dt.items.add(file);
        document.getElementById(`${prefix}-image`).files = dt.files;
        showNotification('拍照成功！', 'success');
        stopCamera(prefix);
    }, 'image/png');
}

function stopCamera(prefix) {
    const video = document.getElementById(`${prefix}-video`);
    const container = document.getElementById(`${prefix}-camera-container`);
    const button = container.parentElement.querySelector('.camera-button');

    if (!cameraStreams[prefix]) return;

    cameraStreams[prefix].getTracks().forEach(t => t.stop());
    cameraStreams[prefix] = null;
    video.srcObject = null;
    video.style.display = 'none';
    hide(container);
    button.disabled = false;
    button.textContent = '📱 使用本机摄像头';
    showNotification('摄像头已关闭', 'info');
}

window.addEventListener('beforeunload', () => {
    Object.values(cameraStreams).forEach(stream => {
        if (stream) stream.getTracks().forEach(t => t.stop());
    });
});

// ==================== 标记位置管理 ====================

const STORAGE_KEY = 'dreamword_marker_positions_v1';

function setMarkerPositionMode(mode) {
    ['manual', 'auto', 'load'].forEach(m => {
        const container = document.getElementById(`marker-position-${m}`);
        const btn = document.getElementById(`mode-${m}-btn`);
        if (container) {
            if (m === mode) {
                show(container);
            } else {
                hide(container);
            }
        }
        if (btn) btn.classList.toggle('active', m === mode);
    });
    if (mode === 'load') updateLastPositionInfo();
}

function autoGeneratePositions() {
    setMarkerPositions([
        { x: 10, y: 10 }, { x: 207, y: 10 },
        { x: 207, y: 289 }, { x: 10, y: 289 }
    ]);
    showNotification('已自动生成推荐位置（四个角落）', 'success');
}

function saveCurrentPositions() {
    const positions = [];
    document.querySelectorAll('.marker-position-input').forEach((el, i) => {
        positions.push({
            id: i,
            x: parseFloat(el.querySelector('.marker-x').value),
            y: parseFloat(el.querySelector('.marker-y').value)
        });
    });
    localStorage.setItem(STORAGE_KEY, JSON.stringify({
        positions,
        timestamp: new Date().toISOString(),
        markerSize: parseFloat(document.getElementById('marker-size').value)
    }));
    showNotification('当前位置配置已保存', 'success');
    updateLastPositionInfo();
}

function loadLastPositions() {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (!saved) return showNotification('未找到保存的位置配置', 'error');

    try {
        const data = JSON.parse(saved);
        setMarkerPositions(data.positions);
        if (data.markerSize) document.getElementById('marker-size').value = data.markerSize;
        showNotification(`已加载 ${new Date(data.timestamp).toLocaleString('zh-CN')} 保存的位置配置`, 'success');
    } catch {
        showNotification('加载位置配置失败', 'error');
    }
}

function clearSavedPositions() {
    if (confirm('确定要清除保存的位置配置吗？')) {
        localStorage.removeItem(STORAGE_KEY);
        showNotification('已清除保存的位置配置', 'success');
        updateLastPositionInfo();
    }
}

function updateLastPositionInfo() {
    const infoDiv = document.getElementById('last-position-info');
    if (!infoDiv) return;
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
        try {
            const data = JSON.parse(saved);
            infoDiv.innerHTML = `已保存: ${new Date(data.timestamp).toLocaleString('zh-CN')} (${data.positions.length} 个标记)`;
        } catch {
            infoDiv.innerHTML = '';
        }
    } else {
        infoDiv.innerHTML = '暂无保存的位置配置';
    }
}

// ==================== 串口通信（直接发送Gcode） ====================

let serialPollTimer = null;
let calibCheckTimer = null;

async function serialRefreshPorts() {
    try {
        const resp = await fetch(API_BASE + '/api/serial/ports');
        const data = await resp.json();
        const sel = document.getElementById('serial-port');
        sel.innerHTML = '<option value="">选择串口...</option>';
        if (data.success && data.ports) {
            data.ports.forEach(p => {
                const opt = document.createElement('option');
                opt.value = p.port;
                opt.textContent = `${p.port} - ${p.desc}`;
                sel.appendChild(opt);
            });
            if (data.ports.length === 0) {
                showNotification('未检测到串口设备', 'info');
            }
        }
    } catch {
        showNotification('获取串口列表失败', 'error');
    }
}

function serialConnect() {
    const port = document.getElementById('serial-port').value;
    if (!port) return showNotification('请先选择串口', 'error');
    apiRequest({
        url: '/api/serial/connect',
        json: { port },
        onSuccess() {
            showNotification('写字机已连接', 'success');
            updateSerialUI(true, port);
            startSerialPoll();
        }
    });
}

function serialDisconnect() {
    apiRequest({
        url: '/api/serial/disconnect',
        onSuccess() {
            showNotification('已断开连接', 'info');
            updateSerialUI(false);
            stopSerialPoll();
        }
    });
}

function updateSerialUI(connected, port) {
    const connectBtn = document.getElementById('btn-serial-connect');
    const disconnectBtn = document.getElementById('btn-serial-disconnect');
    const statusEl = document.getElementById('serial-status');
    if (connected) {
        connectBtn.classList.add('hidden');
        disconnectBtn.classList.remove('hidden');
        statusEl.textContent = `已连接: ${port}`;
    } else {
        connectBtn.classList.remove('hidden');
        disconnectBtn.classList.add('hidden');
        statusEl.textContent = '';
    }
}

function serialSendFile(hiddenInputId) {
    const file = document.getElementById(hiddenInputId).value;
    if (!file) return showNotification('没有可发送的Gcode文件', 'error');
    apiRequest({
        url: '/api/serial/send',
        json: { file },
        onSuccess() {
            showNotification('开始发送Gcode到写字机', 'success');
            startSerialPoll();
        }
    });
}

function startSerialPoll() {
    stopSerialPoll();
    serialPollTimer = setInterval(async () => {
        try {
            const resp = await fetch(API_BASE + '/api/serial/status');
            const data = await resp.json();
            if (data.connected) {
                updateSerialUI(true, data.port);
            } else {
                updateSerialUI(false);
            }
            if (data.sending) {
                const pct = data.total > 0 ? (data.progress / data.total * 100) : 0;
                document.getElementById('serial-progress-fill').style.width = pct + '%';
                document.getElementById('serial-progress-text').textContent = data.message;
                show('serial-progress-bar');
            } else {
                if (data.message && data.message.includes('完成')) {
                    document.getElementById('serial-progress-text').textContent = data.message;
                    setTimeout(() => { hide('serial-progress-bar'); }, 3000);
                }
                if (!data.sending) {
                    stopSerialPoll();
                    stopCalibCheck();
                }
            }
        } catch {}
    }, 1000);

    const autoCheck = document.getElementById('auto-calib-check');
    if (autoCheck && autoCheck.checked) {
        startCalibCheck();
    }
}

function startCalibCheck() {
    stopCalibCheck();
    const intervalSec = parseInt(document.getElementById('calib-check-interval').value) || 30;
    calibCheckTimer = setInterval(async () => {
        try {
            const resp = await fetch(API_BASE + '/api/serial/status');
            const data = await resp.json();
            if (!data.sending) {
                stopCalibCheck();
                return;
            }

            const statusResp = await fetch(API_BASE + '/api/check-calibration', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            const calibData = await statusResp.json();

            if (calibData.success && !calibData.ok) {
                await fetch(API_BASE + '/api/serial/pause', { method: 'POST' });
                showCalibWarning(calibData.warning || '检测到纸张位置偏移，请重新校准');
                stopCalibCheck();
            }
        } catch {}
    }, intervalSec * 1000);
}

function stopCalibCheck() {
    if (calibCheckTimer) {
        clearInterval(calibCheckTimer);
        calibCheckTimer = null;
    }
}

function showCalibWarning(message) {
    const overlay = document.createElement('div');
    overlay.className = 'calib-warning-overlay';
    overlay.id = 'calib-warning-modal';
    overlay.innerHTML = `
        <div class="calib-warning-box">
            <h3>⚠️ 定位异常提醒</h3>
            <p>${message}</p>
            <div class="btn-row">
                <button class="btn btn-primary" onclick="dismissCalibWarningAndResume()">已校准，继续书写</button>
                <button class="btn btn-secondary" onclick="dismissCalibWarning()">停止书写</button>
            </div>
        </div>
    `;
    document.body.appendChild(overlay);
}

function dismissCalibWarning() {
    const modal = document.getElementById('calib-warning-modal');
    if (modal) modal.remove();
}

function dismissCalibWarningAndResume() {
    dismissCalibWarning();
    apiRequest({
        url: '/api/serial/resume',
        onSuccess() {
            showNotification('已恢复书写', 'success');
            const autoCheck = document.getElementById('auto-calib-check');
            if (autoCheck && autoCheck.checked) {
                startCalibCheck();
            }
        }
    });
}

function stopSerialPoll() {
    if (serialPollTimer) {
        clearInterval(serialPollTimer);
        serialPollTimer = null;
    }
    stopCalibCheck();
}

// ==================== 初始化 ====================

function init() {
    console.log('智能写字机Web界面已加载');

    if (document.getElementById('marker-position-manual')) {
        setMarkerPositionMode('manual');
        updateLastPositionInfo();
    }

    const wordInput = document.getElementById('preview-word-input');
    if (wordInput) {
        wordInput.addEventListener('keypress', e => {
            if (e.key === 'Enter') {
                clearTimeout(lookupDebounceTimer);
                lookupWord();
            }
        });
    }

    const cardContainer = document.querySelector('.word-card-container');
    if (cardContainer) cardTemplateHTML = cardContainer.innerHTML;

    checkOnedriveStatus();
}

document.addEventListener('DOMContentLoaded', init);
