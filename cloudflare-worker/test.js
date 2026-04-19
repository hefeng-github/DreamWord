/**
 * Cloudflare Workers 测试脚本
 *
 * 测试查词API的各项功能
 */

const BASE_URL = process.env.WORKER_URL || 'http://localhost:8787';

// 颜色输出
const colors = {
  green: '\x1b[32m',
  red: '\x1b[31m',
  yellow: '\x1b[33m',
  blue: '\x1b[36m',
  reset: '\x1b[0m'
};

function log(message, color = 'reset') {
  console.log(`${colors[color]}${message}${colors.reset}`);
}

function success(message) {
  log(`✓ ${message}`, 'green');
}

function error(message) {
  log(`✗ ${message}`, 'red');
}

function info(message) {
  log(`ℹ ${message}`, 'blue');
}

// 测试用例
const testWords = [
  'hello',
  'world',
  'computer',
  'python',
  'algorithm',
  'database'
];

/**
 * 测试查词API
 */
async function testLookup(word) {
  try {
    const url = `${BASE_URL}/api/lookup?word=${encodeURIComponent(word)}`;
    info(`Testing: ${word}`);

    const response = await fetch(url);
    const data = await response.json();

    if (response.ok && data.success) {
      success(`${word}: ${data.phonetic || 'N/A'}`);

      // 显示释义
      if (data.definitions && data.definitions.length > 0) {
        data.definitions.slice(0, 2).forEach(def => {
          console.log(`    ${def}`);
        });
      }

      return true;
    } else {
      error(`${word}: ${data.error || 'Unknown error'}`);
      return false;
    }
  } catch (err) {
    error(`${word}: ${err.message}`);
    return false;
  }
}

/**
 * 测试健康检查
 */
async function testHealthCheck() {
  try {
    info('Testing health check endpoint...');

    const response = await fetch(`${BASE_URL}/api/health`);
    const data = await response.json();

    if (response.ok && data.status === 'healthy') {
      success('Health check passed');
      return true;
    } else {
      error('Health check failed');
      return false;
    }
  } catch (err) {
    error(`Health check error: ${err.message}`);
    return false;
  }
}

/**
 * 测试错误处理
 */
async function testErrorHandling() {
  try {
    info('Testing error handling...');

    // 测试空单词
    let response = await fetch(`${BASE_URL}/api/lookup?word=`);
    let data = await response.json();

    if (!data.success) {
      success('Empty word error handled correctly');
    } else {
      error('Empty word should return error');
    }

    // 测试不存在的单词
    response = await fetch(`${BASE_URL}/api/lookup?word=nonexistentword12345`);
    data = await response.json();

    if (!data.success) {
      success('Non-existent word error handled correctly');
    } else {
      error('Non-existent word should return error');
    }

    return true;
  } catch (err) {
    error(`Error handling test failed: ${err.message}`);
    return false;
  }
}

/**
 * 性能测试
 */
async function testPerformance() {
  try {
    info('Testing performance...');

    const word = 'hello';
    const iterations = 10;
    const times = [];

    for (let i = 0; i < iterations; i++) {
      const start = Date.now();
      await fetch(`${BASE_URL}/api/lookup?word=${word}`);
      times.push(Date.now() - start);
    }

    const avgTime = times.reduce((a, b) => a + b) / times.length;
    const minTime = Math.min(...times);
    const maxTime = Math.max(...times);

    success(`Performance test completed`);
    console.log(`    Average: ${avgTime}ms`);
    console.log(`    Min: ${minTime}ms`);
    console.log(`    Max: ${maxTime}ms`);

    return true;
  } catch (err) {
    error(`Performance test failed: ${err.message}`);
    return false;
  }
}

/**
 * 主测试函数
 */
async function runTests() {
  log('\n========================================', 'blue');
  log('DreamWord Cloudflare Workers Test Suite', 'blue');
  log('========================================\n', 'blue');

  const results = {
    healthCheck: false,
    lookup: false,
    errorHandling: false,
    performance: false
  };

  // 健康检查
  results.healthCheck = await testHealthCheck();
  console.log('');

  // 查词测试
  log('\n--- Lookup Tests ---\n', 'yellow');
  let lookupPassed = 0;
  for (const word of testWords) {
    if (await testLookup(word)) {
      lookupPassed++;
    }
  }
  results.lookup = lookupPassed === testWords.length;
  console.log('');

  // 错误处理测试
  log('\n--- Error Handling Tests ---\n', 'yellow');
  results.errorHandling = await testErrorHandling();
  console.log('');

  // 性能测试
  log('\n--- Performance Tests ---\n', 'yellow');
  results.performance = await testPerformance();
  console.log('');

  // 总结
  log('\n========================================', 'blue');
  log('Test Summary', 'blue');
  log('========================================\n', 'blue');

  const totalTests = Object.keys(results).length;
  const passedTests = Object.values(results).filter(r => r).length;

  console.log(`Health Check: ${results.healthCheck ? '✓' : '✗'}`);
  console.log(`Lookup (${lookupPassed}/${testWords.length}): ${results.lookup ? '✓' : '✗'}`);
  console.log(`Error Handling: ${results.errorHandling ? '✓' : '✗'}`);
  console.log(`Performance: ${results.performance ? '✓' : '✗'}`);

  console.log(`\nTotal: ${passedTests}/${totalTests} tests passed`);

  if (passedTests === totalTests) {
    log('\n🎉 All tests passed!\n', 'green');
    process.exit(0);
  } else {
    log('\n❌ Some tests failed\n', 'red');
    process.exit(1);
  }
}

// 运行测试
runTests().catch(err => {
  error(`Test suite error: ${err.message}`);
  process.exit(1);
});
