// 打印机配置页面 JavaScript

// 配置键名
const STORAGE_KEY = 'printer_config';

// 默认配置
const defaultConfig = {
    printerModel: 'A1MINI',
    printerIp: '192.168.1.100',
    accessCode: '',
    offsetX: 0.0,
    offsetY: 0.0,
    liftZ: 5.0,
    dropZ: 0.2,
    originMode: 'auto',
    soundEnabled: true,
    currentPage: 1
};

// 当前配置
let currentConfig = { ...defaultConfig };

// 是否已连接
let isConnected = false;

// 页面加载时初始化
document.addEventListener('DOMContentLoaded', function() {
    loadConfig();
    updateUI();
    addLog('系统就绪', 'info');
});

// 加载配置
function loadConfig() {
    try {
        const saved = localStorage.getItem(STORAGE_KEY);
        if (saved) {
            currentConfig = { ...defaultConfig, ...JSON.parse(saved) };
        }
    } catch (e) {
        console.error('加载配置失败:', e);
        addLog('加载配置失败: ' + e.message, 'error');
    }
}

// 保存配置
function saveConfig() {
    try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(currentConfig));
    } catch (e) {
        console.error('保存配置失败:', e);
        addLog('保存配置失败: ' + e.message, 'error');
    }
}

// 更新UI
function updateUI() {
    // 设置表单值
    document.getElementById('printer-model').value = currentConfig.printerModel;
    document.getElementById('printer-ip').value = currentConfig.printerIp;
    document.getElementById('access-code').value = currentConfig.accessCode;
    document.getElementById('offset-x').value = currentConfig.offsetX;
    document.getElementById('offset-y').value = currentConfig.offsetY;
    document.getElementById('lift-z').value = currentConfig.liftZ;
    document.getElementById('drop-z').value = currentConfig.dropZ;
    document.getElementById('origin-mode').value = currentConfig.originMode;
    document.getElementById('sound-enabled').checked = currentConfig.soundEnabled;
    document.getElementById('page-select').value = currentConfig.currentPage;

    // 更新连接状态
    updateConnectionStatus();
}

// 获取表单值
function getFormValues() {
    currentConfig.printerModel = document.getElementById('printer-model').value;
    currentConfig.printerIp = document.getElementById('printer-ip').value;
    currentConfig.accessCode = document.getElementById('access-code').value;
    currentConfig.offsetX = parseFloat(document.getElementById('offset-x').value) || 0;
    currentConfig.offsetY = parseFloat(document.getElementById('offset-y').value) || 0;
    currentConfig.liftZ = parseFloat(document.getElementById('lift-z').value) || 5;
    currentConfig.dropZ = parseFloat(document.getElementById('drop-z').value) || 0.2;
    currentConfig.originMode = document.getElementById('origin-mode').value;
    currentConfig.soundEnabled = document.getElementById('sound-enabled').checked;
    currentConfig.currentPage = parseInt(document.getElementById('page-select').value) || 1;
}

// 调整数值
function adjustValue(fieldId, step) {
    const input = document.getElementById(fieldId);
    const currentValue = parseFloat(input.value) || 0;
    const newValue = (currentValue + step).toFixed(1);
    input.value = parseFloat(newValue);
    addLog(`调整 ${fieldId}: ${currentValue} → ${newValue}`, 'info');
}

// 连接打印机
function connectPrinter() {
    showLoading(true);
    getFormValues();

    addLog(`尝试连接打印机: ${currentConfig.printerIp}`, 'info');

    // 更新连接状态为连接中
    setConnectionStatus('connecting');

    // 模拟连接请求
    fetch('/api/printer/connect', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            printer_model: currentConfig.printerModel,
            ip: currentConfig.printerIp,
            access_code: currentConfig.accessCode
        })
    })
    .then(response => response.json())
    .then(data => {
        showLoading(false);
        if (data.success) {
            isConnected = true;
            setConnectionStatus('online');
            addLog('连接成功', 'success');
            saveConfig();
        } else {
            isConnected = false;
            setConnectionStatus('offline');
            addLog('连接失败: ' + (data.error || '未知错误'), 'error');
        }
    })
    .catch(error => {
        showLoading(false);
        isConnected = false;
        setConnectionStatus('offline');
        addLog('连接失败: ' + error.message, 'error');
    });
}

// 自动搜索打印机
function autoSearch() {
    showLoading(true);
    addLog('正在搜索打印机...', 'info');

    // 模拟搜索
    setTimeout(() => {
        showLoading(false);
        addLog('搜索完成，发现 1 台打印机', 'success');
        // 模拟找到打印机
        document.getElementById('printer-ip').value = '192.168.1.105';
        addLog('已自动填充 IP 地址', 'info');
    }, 2000);
}

// 上传页面
function uploadPage() {
    if (!isConnected) {
        addLog('请先连接打印机', 'error');
        return;
    }

    showLoading(true);
    getFormValues();

    addLog(`上传页面 ${currentConfig.currentPage}`, 'info');

    fetch('/api/printer/upload', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            page: currentConfig.currentPage,
            config: {
                offsetX: currentConfig.offsetX,
                offsetY: currentConfig.offsetY,
                liftZ: currentConfig.liftZ,
                dropZ: currentConfig.dropZ,
                originMode: currentConfig.originMode
            }
        })
    })
    .then(response => response.json())
    .then(data => {
        showLoading(false);
        if (data.success) {
            addLog('页面上传成功', 'success');
            saveConfig();
        } else {
            addLog('上传失败: ' + (data.error || '未知错误'), 'error');
        }
    })
    .catch(error => {
        showLoading(false);
        addLog('上传失败: ' + error.message, 'error');
    });
}

// 刷新配置
function refreshConfig() {
    showLoading(true);
    addLog('刷新配置...', 'info');

    fetch('/api/printer/config', {
        method: 'GET'
    })
    .then(response => response.json())
    .then(data => {
        showLoading(false);
        if (data.success && data.config) {
            // 更新配置
            if (data.config.offsetX !== undefined) {
                document.getElementById('offset-x').value = data.config.offsetX;
            }
            if (data.config.offsetY !== undefined) {
                document.getElementById('offset-y').value = data.config.offsetY;
            }
            if (data.config.liftZ !== undefined) {
                document.getElementById('lift-z').value = data.config.liftZ;
            }
            if (data.config.dropZ !== undefined) {
                document.getElementById('drop-z').value = data.config.dropZ;
            }

            // 更新当前配置
            getFormValues();
            addLog('配置刷新成功', 'success');
        } else {
            addLog('刷新失败: ' + (data.error || '未知错误'), 'error');
        }
    })
    .catch(error => {
        showLoading(false);
        addLog('刷新失败: ' + error.message, 'error');
    });
}

// 删除页面
function deletePage() {
    if (!isConnected) {
        addLog('请先连接打印机', 'error');
        return;
    }

    if (!confirm('确定要删除当前页面吗？')) {
        return;
    }

    showLoading(true);
    getFormValues();

    addLog(`删除页面 ${currentConfig.currentPage}`, 'info');

    fetch('/api/printer/delete', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            page: currentConfig.currentPage
        })
    })
    .then(response => response.json())
    .then(data => {
        showLoading(false);
        if (data.success) {
            addLog('页面删除成功', 'success');
        } else {
            addLog('删除失败: ' + (data.error || '未知错误'), 'error');
        }
    })
    .catch(error => {
        showLoading(false);
        addLog('删除失败: ' + error.message, 'error');
    });
}

// 更新连接状态显示
function updateConnectionStatus() {
    const statusBox = document.getElementById('connection-status');
    const indicator = statusBox.querySelector('.status-indicator');
    const text = statusBox.querySelector('.status-text');

    if (isConnected) {
        indicator.className = 'status-indicator online';
        text.textContent = '已连接';
    } else {
        indicator.className = 'status-indicator offline';
        text.textContent = '未连接';
    }
}

// 设置连接状态
function setConnectionStatus(status) {
    const statusBox = document.getElementById('connection-status');
    const indicator = statusBox.querySelector('.status-indicator');
    const text = statusBox.querySelector('.status-text');

    indicator.className = 'status-indicator ' + status;

    switch (status) {
        case 'online':
            text.textContent = '已连接';
            isConnected = true;
            break;
        case 'offline':
            text.textContent = '未连接';
            isConnected = false;
            break;
        case 'connecting':
            text.textContent = '连接中...';
            break;
    }
}

// 显示加载遮罩
function showLoading(show) {
    const overlay = document.getElementById('loading-overlay');
    overlay.style.display = show ? 'flex' : 'none';
}

// 添加日志
function addLog(message, type = 'info') {
    const logContent = document.getElementById('operation-log');
    const timestamp = new Date().toLocaleTimeString('zh-CN', { hour12: false });

    const logEntry = document.createElement('div');
    logEntry.className = `log-entry ${type}`;
    logEntry.innerHTML = `<span class="log-time">[${timestamp}]</span>${message}`;

    logContent.appendChild(logEntry);

    // 滚动到底部
    logContent.scrollTop = logContent.scrollHeight;
}

// 显示帮助
function showHelp() {
    document.getElementById('help-modal').style.display = 'flex';
}

// 隐藏帮助
function hideHelp() {
    document.getElementById('help-modal').style.display = 'none';
}

// 关闭页面
function closePage() {
    if (confirm('确定要关闭配置页面吗？未保存的更改将丢失。')) {
        window.location.href = '/';
    }
}

// 点击弹窗外部关闭
document.getElementById('help-modal').addEventListener('click', function(e) {
    if (e.target === this) {
        hideHelp();
    }
});

// 监听所有数值输入变化，自动保存
document.querySelectorAll('input, select').forEach(element => {
    element.addEventListener('change', function() {
        getFormValues();
        saveConfig();
    });
});

// ESC 键关闭弹窗
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        hideHelp();
    }
});
