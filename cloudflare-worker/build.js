/**
 * 构建脚本 - 将HTML文件嵌入到Worker中
 */

const fs = require('fs');
const path = require('path');

// 读取index.html
const indexPath = path.join(__dirname, 'index.html');
const indexHtml = fs.readFileSync(indexPath, 'utf-8');

// 转义为JavaScript字符串
const escapedHtml = indexHtml
  .replace(/\\/g, '\\\\')
  .replace(/'/g, "\\'")
  .replace(/\n/g, '\\n');

// 读取worker.js
const workerPath = path.join(__dirname, 'worker.js');
let workerCode = fs.readFileSync(workerPath, 'utf-8');

// 替换HTML占位符
if (workerCode.includes('const SMART_LOOKUP_HTML = ')) {
  workerCode = workerCode.replace(
    /const SMART_LOOKUP_HTML = [`'"](?:\\.|[^'"\\])*[`'"];/,
    `const SMART_LOOKUP_HTML = '${escapedHtml}';`
  );
} else {
  // 在配置部分后添加HTML常量
  const configEnd = workerCode.indexOf('// =============================================');
  const insertPoint = workerCode.indexOf('\n', configEnd) + 1;
  workerCode = workerCode.slice(0, insertPoint) +
    `const SMART_LOOKUP_HTML = '${escapedHtml}';\n\n` +
    workerCode.slice(insertPoint);
}

// 写回worker.js
fs.writeFileSync(workerPath, workerCode, 'utf-8');

console.log('✅ 构建完成！index.html已嵌入到worker.js中');
