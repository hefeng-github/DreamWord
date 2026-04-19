#!/usr/bin/env node

/**
 * API测试脚本
 * 用于验证修复后的API是否正常工作
 */

const WORKER_URL = process.env.WORKER_URL || 'http://localhost:8787/';

// 颜色输出
const colors = {
  reset: '\x1b[0m',
  green: '\x1b[32m',
  red: '\x1b[31m',
  yellow: '\x1b[33m',
  blue: '\x1b[36m'
};

function log(message, color = 'reset') {
  console.log(`${colors[color]}${message}${colors.reset}`);
}

async function testAPI() {
  log('\n🧪 DreamWord API 测试', 'blue');
  log('='.repeat(50), 'blue');
  log(`Worker URL: ${WORKER_URL}`, 'blue');

  let passCount = 0;
  let failCount = 0;

  // 测试1：健康检查
  log('\n📊 测试1: 健康检查', 'blue');
  try {
    const response = await fetch(WORKER_URL + 'api/health');
    const data = await response.json();

    if (data.status === 'healthy') {
      log('✅ PASS: 健康检查正常', 'green');
      log(`   服务: ${data.service}`, 'green');
      log(`   版本: ${data.version}`, 'green');
      passCount++;
    } else {
      log('❌ FAIL: 健康状态异常', 'red');
      failCount++;
    }
  } catch (error) {
    log(`❌ FAIL: ${error.message}`, 'red');
    failCount++;
  }

  // 测试2：调试端点
  log('\n🔧 测试2: 调试端点', 'blue');
  try {
    const response = await fetch(WORKER_URL + 'api/debug');
    const data = await response.json();

    if (data.success) {
      log('✅ PASS: 调试端点正常', 'green');
      log(`   API模式: ${data.config.dictionaryAPI}`, 'green');
      log(`   超时设置: ${data.config.apiTimeout}ms`, 'green');
      passCount++;
    } else {
      log('❌ FAIL: 调试端点异常', 'red');
      failCount++;
    }
  } catch (error) {
    log(`❌ FAIL: ${error.message}`, 'red');
    failCount++;
  }

  // 测试3：查词API
  log('\n🔍 测试3: 查词API', 'blue');
  const testWords = ['hello', 'world', 'test'];
  let wordPassCount = 0;

  for (const word of testWords) {
    try {
      const startTime = Date.now();
      const response = await fetch(`${WORKER_URL}api/lookup?word=${word}`);

      // 检查内容类型
      const contentType = response.headers.get('content-type');
      if (!contentType || !contentType.includes('application/json')) {
        log(`❌ FAIL: "${word}" - 非JSON响应 (${contentType})`, 'red');
        failCount++;
        continue;
      }

      const data = await response.json();
      const responseTime = Date.now() - startTime;

      if (data.success) {
        log(`✅ PASS: "${word}" - ${responseTime}ms`, 'green');
        if (data.api_used) {
          log(`   使用API: ${data.api_used}`, 'green');
        }
        wordPassCount++;
        passCount++;
      } else {
        log(`⚠️  WARN: "${word}" - ${data.error}`, 'yellow');
        failCount++;
      }
    } catch (error) {
      log(`❌ FAIL: "${word}" - ${error.message}`, 'red');
      failCount++;
    }
  }

  // 测试4：批量查词API
  log('\n📚 测试4: 批量查词API', 'blue');
  try {
    const startTime = Date.now();
    const response = await fetch(`${WORKER_URL}api/batch-lookup?words=${testWords.join(',')}`);

    const contentType = response.headers.get('content-type');
    if (!contentType || !contentType.includes('application/json')) {
      log('❌ FAIL: 批量查词 - 非JSON响应', 'red');
      failCount++;
    } else {
      const data = await response.json();
      const responseTime = Date.now() - startTime;

      if (data.success) {
        log(`✅ PASS: 批量查词 ${data.total}个单词 - ${responseTime}ms`, 'green');
        log(`   成功: ${data.found}/${data.total}`, 'green');
        passCount++;
      } else {
        log(`❌ FAIL: 批量查词失败`, 'red');
        failCount++;
      }
    }
  } catch (error) {
    log(`❌ FAIL: 批量查词 - ${error.message}`, 'red');
    failCount++;
  }

  // 测试5：主页访问
  log('\n🏠 测试5: 主页访问', 'blue');
  try {
    const response = await fetch(WORKER_URL);

    if (response.ok) {
      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('text/html')) {
        log('✅ PASS: 主页正常', 'green');
        passCount++;
      } else {
        log(`❌ FAIL: 主页返回非HTML内容 (${contentType})`, 'red');
        failCount++;
      }
    } else {
      log(`❌ FAIL: 主页返回状态码 ${response.status}`, 'red');
      failCount++;
    }
  } catch (error) {
    log(`❌ FAIL: ${error.message}`, 'red');
    failCount++;
  }

  // 总结
  log('\n' + '='.repeat(50), 'blue');
  log('📊 测试总结', 'blue');
  log('='.repeat(50), 'blue');
  log(`总计测试: ${passCount + failCount}`, 'blue');
  log(`通过: ${passCount}`, 'green');
  log(`失败: ${failCount}`, failCount > 0 ? 'red' : 'green');

  if (failCount === 0) {
    log('\n🎉 所有测试通过！系统运行正常！', 'green');
  } else {
    log('\n⚠️  部分测试失败，请检查错误信息', 'yellow');
    log('\n建议:', 'yellow');
    log('1. 确认Worker已正确部署', 'yellow');
    log('2. 访问调试工具: /debug.html', 'yellow');
    log('3. 检查网络连接', 'yellow');
    log('4. 查看浏览器控制台', 'yellow');
  }

  log('\n', 'reset');

  // 返回退出码
  process.exit(failCount > 0 ? 1 : 0);
}

// 运行测试
testAPI().catch(error => {
  log(`\n❌ 测试脚本错误: ${error.message}`, 'red');
  console.error(error);
  process.exit(1);
});
