/* DreamWord 安卓版前端
 *
 * 改造自 PC 版 static/js/app.js，核心变化：
 *  1) apiRequest() 不再 fetch，改为 await window.NativeBridge.<method>(json)
 *     —— 所有数据都通过原生桥流转（OCR/查词/词库）
 *  2) 鼠标事件改为 Pointer Events（同时支持触摸和鼠标）
 *  3) 去掉所有硬件相关 UI（串口/抄写/书写/校准）
 *  4) 图片通过 getUserMedia 拍照或 file input 选取，转 base64 传给原生
 */

// ============ 通用工具 ============
const $ = (id) => document.getElementById(id);
const show = (el) => { (typeof el === 'string' ? $(el) : el)?.classList.remove('hidden'); };
const hide = (el) => { (typeof el === 'string' ? $(el) : el)?.classList.add('hidden'); };

let activeTask = null; // 取消令牌（防止并发请求）

function showLoading() { show('loading'); }
function hideLoading() { hide('loading'); }

let notifTimer = null;
function showNotification(msg, type = 'info') {
    const el = $('notification');
    el.textContent = msg;
    el.className = 'notification ' + type;
    show(el);
    clearTimeout(notifTimer);
    notifTimer = setTimeout(() => hide(el), 3000);
}

/**
 * 调用原生 Bridge 的统一封装（替代 PC 版的 fetch + apiRequest）
 * @param method NativeBridge 上的方法名
 * @param payload 要序列化的对象
 * @returns 顶层 JSON（含 success / data 或 error）
 */
async function callNative(method, payload = {}) {
    if (activeTask) { /* 旧任务无法中止（native 同步），简单忽略并发即可 */ }
    showLoading();
    try {
        const raw = await window.NativeBridge[method](JSON.stringify(payload));
        return JSON.parse(raw);
    } catch (e) {
        return { success: false, error: '原生调用失败：' + e.message };
    } finally {
        hideLoading();
    }
}

// ============ Tab 切换 ============
function showTab(name) {
    document.querySelectorAll('.tab-content').forEach(s => s.classList.remove('active'));
    document.querySelectorAll('.tab-button').forEach(b => b.classList.remove('active'));
    show('tab-' + name);
    document.querySelector(`.tab-button[data-tab="${name}"]`)?.classList.add('active');
}

function toggleCollapse(header) {
    const body = header.nextElementSibling;
    const arrow = header.querySelector('.arrow');
    body.classList.toggle('hidden');
    arrow.textContent = body.classList.contains('hidden') ? '▶' : '▼';
}

// ============ 摄像头（WebView getUserMedia）============
const cameraStreams = {};

async function startCamera(prefix) {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({
            video: { facingMode: 'environment', width: { ideal: 1920 }, height: { ideal: 1080 } }
        });
        cameraStreams[prefix] = stream;
        const video = $(prefix + '-video');
        video.srcObject = stream;
        show(prefix + '-camera-container');
    } catch (e) {
        let msg = '无法访问摄像头';
        if (e.name === 'NotAllowedError') msg = '请在系统设置中允许相机权限';
        else if (e.name === 'NotFoundError') msg = '未检测到摄像头';
        showNotification(msg, 'error');
    }
}

function stopCamera(prefix) {
    const stream = cameraStreams[prefix];
    if (stream) stream.getTracks().forEach(t => t.stop());
    delete cameraStreams[prefix];
    hide(prefix + '-camera-container');
}

/** 拍照：video 帧 → canvas → base64 → 填入预览 + 缓存 */
function capturePhoto(prefix) {
    const video = $(prefix + '-video');
    if (!video || !video.videoWidth) return showNotification('摄像头未就绪', 'error');
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext('2d').drawImage(video, 0, 0);
    const dataUrl = canvas.toDataURL('image/jpeg', 0.92);
    window['_' + prefix + 'Image'] = dataUrl;
    const img = $(prefix + '-preview-img') || $(prefix + '-preview');
    if (img) { img.src = dataUrl; show(img); }
    stopCamera(prefix);
    // 拍照查词：初始化裁剪画布
    if (prefix === 'lookup') initCropCanvas(dataUrl);
}

/** file input 选取图片 */
function onImagePicked(input, prefix) {
    const file = input.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (e) => {
        const dataUrl = e.target.result;
        window['_' + prefix + 'Image'] = dataUrl;
        const img = $(prefix + '-preview-img') || $(prefix + '-preview');
        if (img) { img.src = dataUrl; show(img); }
        if (prefix === 'lookup') initCropCanvas(dataUrl);
    };
    reader.readAsDataURL(file);
}

// ============ 拍照点词 ============
let tapWords = [];
let tapMarkedWords = new Set();
let tapImageSrc = null;
let tapDisplayCanvas = null;
let tapScale = 1;

async function startOcrTap() {
    const imgData = window._tapImage;
    if (!imgData) return showNotification('请先拍照或选择图片', 'error');

    const resp = await callNative('ocrWords', { image: imgData });
    if (!resp.success) return showNotification(resp.error || '识别失败', 'error');

    tapWords = resp.data.words || [];
    if (tapWords.length === 0) return showNotification('未识别到单词', 'info');

    renderTapCanvas();
}

function renderTapCanvas() {
    tapImageSrc = new Image();
    tapImageSrc.onload = () => {
        tapDisplayCanvas = $('tap-display-canvas');
        // 按原图分辨率绘制，CSS 缩放到屏幕宽
        tapDisplayCanvas.width = tapImageSrc.naturalWidth;
        tapDisplayCanvas.height = tapImageSrc.naturalHeight;
        drawTapCanvas();
        show('tap-workspace');
    };
    tapImageSrc.src = window._tapImage;
}

function drawTapCanvas() {
    if (!tapDisplayCanvas || !tapImageSrc) return;
    const ctx = tapDisplayCanvas.getContext('2d');
    ctx.clearRect(0, 0, tapDisplayCanvas.width, tapDisplayCanvas.height);
    ctx.drawImage(tapImageSrc, 0, 0);

    for (const w of tapWords) {
        const bbox = w.bbox;
        if (!bbox || bbox.length < 4) continue;
        const x1 = bbox[0][0], y1 = bbox[0][1];
        const x2 = bbox[2][0], y2 = bbox[2][1];
        const marked = tapMarkedWords.has(w.word.toLowerCase());
        ctx.fillStyle = marked ? 'rgba(16,185,129,0.35)' : 'rgba(59,130,246,0.18)';
        ctx.fillRect(x1, y1, x2 - x1, y2 - y1);
        ctx.strokeStyle = marked ? '#10b981' : '#3b82f6';
        ctx.lineWidth = Math.max(2, tapDisplayCanvas.width * 0.003);
        ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);
        if (marked) {
            ctx.fillStyle = '#10b981';
            ctx.font = `bold ${Math.max(16, tapDisplayCanvas.width * 0.022)}px sans-serif`;
            ctx.fillText('✓ ' + w.word, x1, y1 - 4);
        }
    }
    $('tap-marked-count').textContent = `已标记 ${tapMarkedWords.size} 个`;
}

// ★ 触屏适配：用 Pointer Events（同时支持触摸/鼠标），PC 版是 click
tapDisplayCanvas = null; // 占位，实际在 renderTapCanvas 赋值
document.addEventListener('pointerdown', (e) => {
    const canvas = $('tap-display-canvas');
    if (!canvas || e.target !== canvas) return;

    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    const cx = (e.clientX - rect.left) * scaleX;
    const cy = (e.clientY - rect.top) * scaleY;

    let hit = null;
    for (const w of tapWords) {
        const b = w.bbox;
        if (!b || b.length < 4) continue;
        if (cx >= b[0][0] && cx <= b[2][0] && cy >= b[0][1] && cy <= b[2][1]) {
            hit = w; break;
        }
    }
    if (hit) {
        const key = hit.word.toLowerCase();
        tapMarkedWords.has(key) ? tapMarkedWords.delete(key) : tapMarkedWords.add(key);
        drawTapCanvas();
    }
});

function clearTapMarks() {
    tapMarkedWords.clear();
    drawTapCanvas();
}

async function submitTapWords() {
    if (tapMarkedWords.size === 0) return showNotification('请先标记单词', 'error');
    const resp = await callNative('addKnownWords', { words: Array.from(tapMarkedWords) });
    if (resp.success) {
        showNotification(`已添加 ${resp.data.added} 个，共 ${resp.data.total} 个`, 'success');
        tapMarkedWords.clear();
        drawTapCanvas();
    } else {
        showNotification(resp.error || '提交失败', 'error');
    }
}

// ============ 手动查词 ============
let lookupDebounceTimer = null;
function debounceLookup() {
    clearTimeout(lookupDebounceTimer);
    const word = $('preview-word-input').value.trim();
    if (!word) return setWordPreviewVisibility(false, false, false);
    lookupDebounceTimer = setTimeout(lookupWord, 400);
}

async function lookupWord() {
    const word = $('preview-word-input').value.trim();
    if (!word) return;
    setWordPreviewVisibility(true, false, false);

    const resp = await callNative('wordPreview', { word });
    if (resp.success && resp.data.success) {
        displayWordPreview(resp.data);
    } else {
        setWordPreviewVisibility(false, false, true);
    }
}

function setWordPreviewVisibility(loading, result, noResult) {
    $('word-preview-loading').classList.toggle('hidden', !loading);
    $('word-preview-result').classList.toggle('hidden', !result);
    $('word-preview-no-result').classList.toggle('hidden', !noResult);
}

function displayWordPreview(data) {
    setWordPreviewVisibility(false, true, false);
    $('preview-word').textContent = data.word;
    $('preview-phonetic').textContent = data.phonetic || '';
    $('preview-pos').textContent = data.pos || '';
    $('preview-pos').classList.toggle('hidden', !data.pos);

    fillList('preview-definitions', data.definitions || []);
    fillList('preview-examples', data.examples || [], true);

    $('preview-definitions-section').classList.toggle('hidden', !(data.definitions && data.definitions.length));
    $('preview-examples-section').classList.toggle('hidden', !(data.examples && data.examples.length));
}

function fillList(id, items, asUl = false) {
    const el = $(id);
    el.innerHTML = '';
    for (const t of items) {
        const li = document.createElement(asUl ? 'li' : 'li');
        li.textContent = t;
        el.appendChild(li);
    }
}

// ============ 拍照查词书写 ============
let lookupCropCanvas = null, lookupCropCtx = null;
let lookupCropRect = null, lookupCropDragging = false, lookupCropStart = null;
let lookupImageObj = null;

function initCropCanvas(dataUrl) {
    show('lookup-crop-workspace');
    lookupCropCanvas = $('lookup-crop-canvas');
    lookupCropCtx = lookupCropCanvas.getContext('2d');
    lookupImageObj = new Image();
    lookupImageObj.onload = () => {
        lookupCropCanvas.width = lookupImageObj.naturalWidth;
        lookupCropCanvas.height = lookupImageObj.naturalHeight;
        drawCropCanvas();
    };
    lookupImageObj.src = dataUrl;
    // 绑定一次（避免重复）
    if (!lookupCropCanvas._bound) {
        bindCropPointerEvents();
        lookupCropCanvas._bound = true;
    }
}

function drawCropCanvas() {
    if (!lookupCropCtx || !lookupImageObj) return;
    lookupCropCtx.clearRect(0, 0, lookupCropCanvas.width, lookupCropCanvas.height);
    lookupCropCtx.drawImage(lookupImageObj, 0, 0);
    if (lookupCropRect) {
        // 暗化非选区
        lookupCropCtx.fillStyle = 'rgba(0,0,0,0.5)';
        lookupCropCtx.fillRect(0, 0, lookupCropCanvas.width, lookupCropCanvas.height);
        // 透出选区
        lookupCropCtx.clearRect(lookupCropRect.x, lookupCropRect.y, lookupCropRect.w, lookupCropRect.h);
        lookupCropCtx.drawImage(lookupImageObj,
            lookupCropRect.x, lookupCropRect.y, lookupCropRect.w, lookupCropRect.h,
            lookupCropRect.x, lookupCropRect.y, lookupCropRect.w, lookupCropRect.h);
        // 蓝色虚线框
        lookupCropCtx.strokeStyle = '#3b82f6';
        lookupCropCtx.lineWidth = Math.max(2, lookupCropCanvas.width * 0.004);
        lookupCropCtx.setLineDash([12, 8]);
        lookupCropCtx.strokeRect(lookupCropRect.x, lookupCropRect.y, lookupCropRect.w, lookupCropRect.h);
        lookupCropCtx.setLineDash([]);
    }
}

// ★ 触屏适配：Pointer Events 替代 PC 版的 mousedown/move/up
function bindCropPointerEvents() {
    const canvas = lookupCropCanvas;
    canvas.addEventListener('pointerdown', (e) => {
        canvas.setPointerCapture(e.pointerId);
        lookupCropDragging = true;
        const rect = canvas.getBoundingClientRect();
        const sx = canvas.width / rect.width, sy = canvas.height / rect.height;
        lookupCropStart = { x: (e.clientX - rect.left) * sx, y: (e.clientY - rect.top) * sy };
        lookupCropRect = null;
        drawCropCanvas();
    });
    canvas.addEventListener('pointermove', (e) => {
        if (!lookupCropDragging) return;
        const rect = canvas.getBoundingClientRect();
        const sx = canvas.width / rect.width, sy = canvas.height / rect.height;
        const mx = (e.clientX - rect.left) * sx, my = (e.clientY - rect.top) * sy;
        lookupCropRect = {
            x: Math.min(lookupCropStart.x, mx),
            y: Math.min(lookupCropStart.y, my),
            w: Math.abs(mx - lookupCropStart.x),
            h: Math.abs(my - lookupCropStart.y)
        };
        drawCropCanvas();
    });
    const endHandler = (e) => {
        if (lookupCropDragging) {
            lookupCropDragging = false;
            if (lookupCropRect && (lookupCropRect.w < 10 || lookupCropRect.h < 10)) {
                lookupCropRect = null;
                drawCropCanvas();
            }
        }
    };
    canvas.addEventListener('pointerup', endHandler);
    canvas.addEventListener('pointercancel', endHandler);
}

function clearCropSelection() {
    lookupCropRect = null;
    drawCropCanvas();
}

async function autoLookup() {
    const imgData = window._lookupImage;
    if (!imgData) return showNotification('请先拍照或选择图片', 'error');

    const payload = { image: imgData };
    if (lookupCropRect && lookupCropRect.w > 10 && lookupCropRect.h > 10) {
        payload.crop = {
            x: Math.round(lookupCropRect.x), y: Math.round(lookupCropRect.y),
            w: Math.round(lookupCropRect.w), h: Math.round(lookupCropRect.h)
        };
    }
    const resp = await callNative('autoLookup', payload);
    if (!resp.success) return showNotification(resp.error || '查词失败', 'error');

    const annotated = $('lookup-annotated');
    annotated.src = resp.data.annotated_image;
    show(annotated);
    const n = (resp.data.words || []).length;
    showNotification(`识别完成，标注 ${n} 个生词`, n > 0 ? 'success' : 'info');
}

// ============ 词库导入 ============
let pendingImportWords = [];

async function onWordJsonPicked(input) {
    const file = input.files[0];
    if (!file) return;
    const text = await file.text();
    const words = parseWordJson(text);
    if (words.length === 0) return showNotification('未解析到单词，请检查格式', 'error');

    pendingImportWords = words;
    const preview = $('import-preview');
    preview.innerHTML = `<p class="hint">解析到 ${words.length} 个单词，前 10 个预览：</p>
        <div class="word-list">` +
        words.slice(0, 10).map(w => `<div class="word-list-item"><span>${w}</span></div>`).join('') +
        `</div>`;
    show('import-submit-btn');
}

/** 容错 JSON 解析（移植自 PC 版 app.js:298-362，兼容 BOM/注释/尾逗号/JSON Lines） */
function parseWordJson(text) {
    let t = text.replace(/^\uFEFF/, '').trim();
    if (!t) return [];
    // JSON Lines
    if (t.includes('\n') && !t.trim().startsWith('[')) {
        const words = [];
        for (const line of t.split('\n')) {
            const s = line.trim();
            if (!s || s.startsWith('//')) continue;
            try {
                const o = JSON.parse(s);
                const w = o.word || o.name || o.headword;
                if (w) words.push(String(w));
            } catch {}
        }
        if (words.length) return [...new Set(words)];
    }
    // 标准数组
    try {
        const arr = JSON.parse(t);
        if (Array.isArray(arr)) {
            return [...new Set(arr.map(o => {
                if (typeof o === 'string') return o;
                return o.word || o.name || o.headword || '';
            }).filter(Boolean))];
        }
    } catch (e) {
        showNotification('JSON 解析失败：' + e.message, 'error');
    }
    return [];
}

async function submitImport() {
    if (pendingImportWords.length === 0) return;
    const resp = await callNative('addKnownWords', { words: pendingImportWords });
    if (resp.success) {
        showNotification(`已导入 ${resp.data.added} 个`, 'success');
        pendingImportWords = [];
        $('import-preview').innerHTML = '';
        hide('import-submit-btn');
    } else {
        showNotification(resp.error || '导入失败', 'error');
    }
}

// ============ 已会词库管理 ============
let allKnownWords = [];

async function loadKnownWords() {
    const resp = await callNative('getKnownWords', {});
    if (resp.success) {
        allKnownWords = resp.data.words || [];
        renderKnownWords();
    }
}

function renderKnownWords() {
    const q = ($('known-words-search')?.value || '').trim().toLowerCase();
    const list = q ? allKnownWords.filter(w => w.includes(q)) : allKnownWords;
    const el = $('known-words-list');
    el.innerHTML = list.map(w =>
        `<div class="word-list-item"><span>${w}</span>
         <button class="btn btn-danger btn-small" onclick="removeKnown('${w}')">删除</button></div>`
    ).join('');
    $('known-words-count').textContent = `共 ${allKnownWords.length} 个`;
}

async function removeKnown(word) {
    const resp = await callNative('removeKnownWord', { word });
    if (resp.success) loadKnownWords();
}

// ============ OneDrive 备份/恢复 ============
let onedrivePollTimer = null;
let onedriveDeviceCode = null;

// 进入词库 Tab / 展开时刷新授权状态
async function onedriveCheckStatus() {
    const statusEl = $('onedrive-status');
    const authArea = $('onedrive-auth-area');
    const actionsEl = $('onedrive-actions');
    if (!statusEl) return;

    try {
        const resp = await callNative('onedrive', { action: 'status' });
        if (!resp.success) {
            // 多半是未配置 Client ID
            statusEl.textContent = resp.error || '未配置 Client ID';
            show(authArea); hide(actionsEl);
            return;
        }
        const authorized = resp.data.authorized;
        if (authorized) {
            statusEl.textContent = '✓ 已连接 OneDrive';
            hide(authArea); show(actionsEl);
        } else {
            statusEl.textContent = '未授权';
            show(authArea); hide(actionsEl);
        }
    } catch (e) {
        statusEl.textContent = '状态检查失败';
    }
}

// 启动授权：拿设备码 → 显示引导 → 轮询
async function onedriveStartAuth() {
    const resp = await callNative('onedrive', { action: 'auth' });
    if (!resp.success) return showNotification(resp.error || '获取设备码失败', 'error');

    const data = resp.data;
    onedriveDeviceCode = data.device_code;
    $('onedrive-verify-url').textContent = data.verification_uri || data.verification_url || '';
    $('onedrive-user-code').textContent = data.user_code || '';
    show('onedrive-auth-instructions');
    showNotification('请按提示在浏览器完成授权', 'info');

    // 开始轮询（PC 版默认 interval 5 秒）
    onedrivePoll(data.interval || 5, (data.expires_in || 900));
}

// 轮询 token：每 interval 秒调一次 poll，直到授权成功或超时
function onedrivePoll(interval, expiresIn) {
    clearTimeout(onedrivePollTimer);
    const deadline = Date.now() + expiresIn * 1000;

    const tick = async () => {
        if (Date.now() > deadline) {
            hide('onedrive-auth-instructions');
            showNotification('授权超时，请重试', 'error');
            return;
        }
        try {
            // 轮询不走 callNative（避免每次闪 loading 蒙层）
            const raw = await window.NativeBridge.onedrive(
                JSON.stringify({ action: 'poll', device_code: onedriveDeviceCode })
            );
            const resp = JSON.parse(raw);
            if (resp.success && resp.data && resp.data.authorized) {
                hide('onedrive-auth-instructions');
                showNotification('授权成功', 'success');
                onedriveCheckStatus();
                return;
            }
            // pending：继续等
        } catch (e) {
            // 单次失败不中断轮询
        }
        onedrivePollTimer = setTimeout(tick, (interval || 5) * 1000);
    };
    tick();
}

// 备份
async function onedriveBackup() {
    const resp = await callNative('onedrive', { action: 'backup' });
    if (resp.success) {
        showNotification(`备份成功！版本 v${resp.data.version}，共 ${resp.data.word_count} 个单词`, 'success');
        onedriveListBackups();
    } else {
        showNotification(resp.error || '备份失败', 'error');
    }
}

// 列出云端备份
async function onedriveListBackups() {
    const resp = await callNative('onedrive', { action: 'list' });
    const el = $('onedrive-backup-list');
    if (!resp.success) {
        el.innerHTML = `<p class="hint">${resp.error || '读取失败'}</p>`;
        return;
    }
    const backups = resp.data.backups || [];
    if (backups.length === 0) {
        el.innerHTML = '<p class="hint">云端暂无备份</p>';
        return;
    }
    el.innerHTML = '<h4>云端备份</h4>' + backups.map(b => {
        const name = b.name || '';
        const size = b.size ? `(${(b.size / 1024).toFixed(1)} KB)` : '';
        const time = b.last_modified ? new Date(b.last_modified).toLocaleString() : '';
        return `<div class="word-list-item">
            <div><div><b>${name}</b> ${size}</div><div class="hint">${time}</div></div>
            <button class="btn btn-primary btn-small" onclick="onedriveRestore('${name}')">恢复</button>
        </div>`;
    }).join('');
}

// 恢复（默认合并模式）
async function onedriveRestore(backupName) {
    if (!confirm(`从 ${backupName} 恢复？将与本地词库合并（不删除现有词）。`)) return;
    const resp = await callNative('onedrive', {
        action: 'restore', backup_name: backupName, merge: true
    });
    if (resp.success) {
        const d = resp.data;
        const msg = d.action === 'merged'
            ? `恢复成功：本地 ${d.local_count} + 云端 ${d.cloud_count} → 合并 ${d.merged_count}（新增 ${d.new_words}）`
            : `恢复成功：替换为 ${d.word_count} 个词`;
        showNotification(msg, 'success');
        loadKnownWords();  // 刷新本地词库列表
    } else {
        showNotification(resp.error || '恢复失败', 'error');
    }
}

// 断开连接
async function onedriveDisconnect() {
    if (!confirm('断开 OneDrive 连接？本地词库不受影响。')) return;
    const resp = await callNative('onedrive', { action: 'disconnect' });
    if (resp.success) {
        showNotification('已断开连接', 'info');
        onedriveCheckStatus();
    }
}

// ============ 词典导入（SAF 选文件，流式拷贝，不 OOM）===========

// 触发系统文件选择器选 .db 文件
async function pickDictFile() {
    // 先注册回调（原生选完文件后异步调用）
    window.__dictImportCallback = async (result) => {
        if (result && result.success) {
            const mb = (result.data.size / 1024 / 1024).toFixed(1);
            showNotification(`词典导入成功（${mb}MB）！`, 'success');
            // 触发原生 reloadDict 刷新 bridge 内部 dict 引用 + 更新状态
            await callNative('reloadDict', {});
            await loadDictInfo();
        } else {
            showNotification((result && result.error) || '导入失败', 'error');
        }
        window.__dictImportCallback = null;
    };
    // 触发原生 SAF 选择器
    const resp = await callNative('pickAndImportDict', {});
    if (!resp.success) {
        showNotification(resp.error || '无法打开文件选择器', 'error');
        window.__dictImportCallback = null;
    }
}

// 查询词典状态 + 导入路径（不走 base64，避免大文件撑爆内存闪退）
async function loadDictInfo() {
    try {
        const resp = await callNative('dictInfo', {});
        if (resp.success) {
            const d = resp.data;
            $('dict-import-path').textContent = d.import_path || '';
            updateDictStatus(d.dict_ready);
        }
    } catch (e) {
        // 忽略
    }
}

// 用户把 .db 放到公共目录后，点击重新加载
async function reloadDict() {
    showNotification('正在重新加载词典…', 'info');
    const resp = await callNative('reloadDict', {});
    if (resp.success) {
        if (resp.data.dict_ready) {
            showNotification('词典加载成功，可以查词了！', 'success');
        } else {
            showNotification('未检测到词典文件，请确认 .db 已放到指定路径', 'error');
        }
        updateDictStatus(resp.data.dict_ready);
    } else {
        showNotification(resp.error || '加载失败', 'error');
    }
}

// 更新词典状态卡片
function updateDictStatus(dictReady) {
    const el = $('dict-status-line');
    if (!el) return;
    el.textContent = dictReady
        ? '✓ 词典已就绪，可正常查词'
        : '✗ 词典未就绪。请把 word_details.db 放到下方路径后点重新加载。';
}

// ============ 启动自检 ============
async function checkStatus() {
    try {
        const resp = JSON.parse(await window.NativeBridge.getStatus());
        const data = resp.data || {};
        const parts = [];
        parts.push(data.ocr_ready ? '✓ OCR' : '✗ OCR');
        parts.push(data.dict_ready ? '✓ 词典' : '✗ 词典');
        parts.push(`词库 ${data.known_words_count || 0}`);
        $('status-line').textContent = parts.join(' · ');
        if (!data.dict_ready) $('status-line').textContent += '（请到词库页导入）';
        updateDictStatus(data.dict_ready);
    } catch (e) {
        $('status-line').textContent = '状态检查失败';
    }
}

// ============ 初始化 ============
document.addEventListener('DOMContentLoaded', () => {
    checkStatus();
    loadDictInfo();
    loadKnownWords();
    // 切到词库 tab 时刷新本地词库 + 词典信息 + OneDrive 状态
    document.querySelector('.tab-button[data-tab="words"]')?.addEventListener('click', () => {
        loadKnownWords();
        loadDictInfo();
        onedriveCheckStatus();
    });
});

// 页面卸载时关闭摄像头
window.addEventListener('beforeunload', () => {
    Object.keys(cameraStreams).forEach(stopCamera);
});
