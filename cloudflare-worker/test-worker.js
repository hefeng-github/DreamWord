/**
 * Cloudflare Workers 功能测试脚本
 * 用于验证所有API端点和功能是否正常工作
 */

const BASE_URL = process.env.WORKER_URL || 'http://localhost:8787';

// 颜色输出
const colors = {
  reset: '\x1b[0m',
  green: '\x1b[32m',
  red: '\x1b[31m',
  yellow: '\x1b[33m',
  blue: '\x1b[36m'
};

function log(color, message) {
  console.log(`${color}${message}${colors.reset}`);
}

// 测试结果
let passedTests = 0;
let failedTests = 0;

async function test(name, fn) {
  try {
    log(colors.blue, `\n🧪 测试: ${name}`);
    await fn();
    passedTests++;
    log(colors.green, `✅ 通过: ${name}`);
  } catch (error) {
    failedTests++;
    log(colors.red, `❌ 失败: ${name}`);
    log(colors.red, `   错误: ${error.message}`);
  }
}

// API测试函数
async function testHealthCheck() {
  const response = await fetch(`${BASE_URL}/api/health`);
  const data = await response.json();

  if (!data.success || !data.service) {
    throw new Error('健康检查响应格式不正确');
  }

  log(colors.yellow, `   服务: ${data.service}`);
  log(colors.yellow, `   版本: ${data.version}`);
  log(colors.yellow, `   状态: ${data.status}`);
}

async function testLookupAPI() {
  const testWord = 'hello';
  const response = await fetch(`${BASE_URL}/api/lookup?word=${testWord}`);
  const data = await response.json();

  if (!data.success) {
    throw new Error('查词失败');
  }

  if (data.word !== testWord) {
    throw new Error('返回的单词不匹配');
  }

  log(colors.yellow, `   单词: ${data.word}`);
  log(colors.yellow, `   音标: ${data.phonetic || 'N/A'}`);
  log(colors.yellow, `   释义数: ${data.definitions?.length || 0}`);
}

async function testBatchLookupAPI() {
  const words = ['hello', 'world', 'test'];
  const response = await fetch(
    `${BASE_URL}/api/batch-lookup?words=${encodeURIComponent(words.join(','))}`
  );
  const data = await response.json();

  if (!data.success) {
    throw new Error('批量查词失败');
  }

  if (data.total !== words.length) {
    throw new Error(`预期查询 ${words.length} 个单词，实际返回 ${data.total} 个`);
  }

  log(colors.yellow, `   查询单词: ${words.join(', ')}`);
  log(colors.yellow, `   成功: ${data.found}/${data.total}`);
}

async function testInvalidWord() {
  const response = await fetch(`${BASE_URL}/api/lookup?word=invalidword123xyz`);
  const data = await response.json();

  // 未找到单词是预期行为
  log(colors.yellow, `   处理无效单词: ${data.error || '正确返回错误'}`);
}

async function testEmptyWord() {
  const response = await fetch(`${BASE_URL}/api/lookup?word=`);
  const data = await response.json();

  if (data.success) {
    throw new Error('应该返回错误而不是成功');
  }

  log(colors.yellow, `   错误处理: ${data.error}`);
}

async function testPageAccess() {
  const pages = [
    { path: '/', name: '主页' },
    { path: '/lookup', name: '智能查词页面' },
    { path: '/test', name: '测试页面' }
  ];

  for (const page of pages) {
    const response = await fetch(`${BASE_URL}${page.path}`);

    if (!response.ok) {
      throw new Error(`${page.name} 访问失败`);
    }

    const contentType = response.headers.get('content-type');
    if (!contentType || !contentType.includes('text/html')) {
      throw new Error(`${page.name} 内容类型不正确`);
    }

    log(colors.yellow, `   ✅ ${page.name}: ${page.path}`);
  }
}

async function testCORSPolicy() {
  const response = await fetch(`${BASE_URL}/api/lookup?word=test`, {
    headers: {
      'Origin': 'https://example.com'
    }
  });

  const corsHeader = response.headers.get('access-control-allow-origin');
  if (!corsHeader) {
    throw new Error('CORS头未设置');
  }

  log(colors.yellow, `   CORS头: ${corsHeader}`);
}

// 性能测试
async function testPerformance() {
  const testWord = 'hello';
  const iterations = 5;
  const times = [];

  log(colors.yellow, `   进行 ${iterations} 次查询...`);

  for (let i = 0; i < iterations; i++) {
    const start = Date.now();
    await fetch(`${BASE_URL}/api/lookup?word=${testWord}`);
    const end = Date.now();
    times.push(end - start);
  }

  const avgTime = times.reduce((a, b) => a + b, 0) / times.length;
  const minTime = Math.min(...times);
  const maxTime = Math.max(...times);

  log(colors.yellow, `   平均响应时间: ${avgTime.toFixed(0)}ms`);
  log(colors.yellow, `   最快: ${minTime}ms, 最慢: ${maxTime}ms`);

  if (avgTime > 1000) {
    log(colors.red, `   ⚠️  警告: 响应时间较慢`);
  } else {
    log(colors.green, `   ✅ 性能良好`);
  }
}

// 主测试函数
async function runTests() {
  log(colors.blue, '🚀 开始测试 Cloudflare Workers\n');
  log(colors.yellow, `测试环境: ${BASE_URL}\n`);

  // 基础功能测试
  await test('健康检查', testHealthCheck);
  await test('查词API', testLookupAPI);
  await test('批量查词API', testBatchLookupAPI);
  await test('无效单词处理', testInvalidWord);
  await test('空单词处理', testEmptyWord);

  // 页面访问测试
  await test('页面访问', testPageAccess);

  // CORS测试
  await test('CORS策略', testCORSPolicy);

  // 性能测试
  await test('性能测试', testPerformance);

  // 总结
  log(colors.blue, '\n📊 测试总结');
  log(colors.green, `✅ 通过: ${passedTests}`);
  log(colors.red, `❌ 失败: ${failedTests}`);

  const totalTests = passedTests + failedTests;
  const successRate = ((passedTests / totalTests) * 100).toFixed(1);

  log(colors.yellow, `📈 成功率: ${successRate}%`);

  if (failedTests === 0) {
    log(colors.green, '\n🎉 所有测试通过！');
    process.exit(0);
  } else {
    log(colors.red, '\n⚠️  部分测试失败，请检查错误信息');
    process.exit(1);
  }
}

// 运行测试
runTests().catch(error => {
  log(colors.red, `\n💥 测试运行失败: ${error.message}`);
  process.exit(1);
});
