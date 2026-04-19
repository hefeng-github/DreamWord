/**
 * DreamWord Word Lookup - Cloudflare Workers + D1 Database Version
 *
 * 完整的数据库查词实现，类似Python版本
 */

// =============================================
// 配置
// =============================================

const CONFIG = {
  // CORS配置
  cors: {
    allowOrigin: '*',
    allowMethods: 'GET, POST, OPTIONS',
    allowHeaders: 'Content-Type, Authorization'
  },

  // 缓存配置（秒）
  cacheTTL: 3600, // 1小时

  // API超时时间（毫秒）
  apiTimeout: 5000,

  // 查词优先级：'database'优先，'api'备用
  lookupPriority: ['database', 'api'],

  // 是否启用KV缓存
  enableKVCache: true
};

// =============================================
// 数据库查词实现
// =============================================

/**
 * 从D1数据库查词（类似Python版本）
 */
async function lookupFromDatabase(word, env) {
  try {
    // 如果没有D1绑定，返回失败
    if (!env || !env.DB) {
      return {
        success: false,
        error: '数据库未配置',
        suggestion: '请在wrangler.toml中配置D1数据库绑定'
      };
    }

    // 查询数据库
    const stmt = env.DB.prepare('SELECT entry, paraphrase FROM mdx WHERE entry = ? LIMIT 1');
    const result = await stmt.bind(word.toLowerCase()).first();

    if (!result) {
      return {
        success: false,
        error: '数据库中未找到该单词',
        word: word
      };
    }

    // 解析MDX格式的HTML
    const parsed = parseMDXHTML(result.paraphrase);

    return {
      success: true,
      word: word,
      phonetic: parsed.phonetic || 'N/A',
      definitions: parsed.definitions || [],
      examples: parsed.examples || [],
      base_form: parsed.base_form,
      pos: parsed.pos,
      source: 'database'
    };

  } catch (error) {
    console.error('Database lookup error:', error);
    return {
      success: false,
      error: '数据库查询失败: ' + error.message
    };
  }
}

/**
 * 解析MDX格式的HTML（简化版Python MDXParser）
 */
function parseMDXHTML(html) {
  const result = {
    phonetic: null,
    definitions: [],
    examples: [],
    base_form: null,
    pos: null
  };

  try {
    // 提取音标
    const phonMatch = html.match(/<span[^>]*class="[^"]*phon[^"]*"[^>]*>(.*?)<\/span>/is);
    if (phonMatch) {
      result.phonetic = phonMatch[1].replace(/<[^>]+>/g, '').trim();
    }

    // 提取词性
    const posMatch = html.match(/<span[^>]*class="[^"]*pos[^"]*"[^>]*>(.*?)<\/span>/is);
    if (posMatch) {
      result.pos = posMatch[1].replace(/<[^>]+>/g, '').trim();
    }

    // 提取释义
    const defMatches = html.match(/<span[^>]*class="[^"]*def[^"]*"[^>]*>(.*?)<\/span>/gis);
    if (defMatches) {
      defMatches.forEach(match => {
        const def = match.replace(/<[^>]+>/g, '').trim();
        if (def) result.definitions.push(def);
      });
    }

    // 提取中文释义
    const chnMatches = html.match(/<chn>(.*?)<\/chn>/gis);
    if (chnMatches) {
      chnMatches.forEach(match => {
        const def = match.replace(/<\/?chn>/gi, '').trim();
        if (def && !result.definitions.includes(def)) {
          result.definitions.unshift(def); // 中文释义优先
        }
      });
    }

    // 提取例句
    const exMatches = html.match(/<span[^>]*class="[^"]*x[^"]*"[^>]*>(.*?)<\/span>/gis);
    if (exMatches) {
      exMatches.forEach(match => {
        const ex = match.replace(/<[^>]+>/g, '').trim();
        if (ex) result.examples.push(ex);
      });
    }

    // 提取基本形式
    const baseMatch = html.match(/<span[^>]*class="[^"]*xh[^"]*"[^>]*>(.*?)<\/span>/is);
    if (baseMatch) {
      result.base_form = baseMatch[1].replace(/<[^>]+>/g, '').trim();
    }

  } catch (error) {
    console.error('Parse MDX error:', error);
  }

  return result;
}

/**
 * 批量查词（数据库）
 */
async function batchLookupFromDatabase(words, env) {
  const results = [];

  for (const word of words) {
    const result = await lookupFromDatabase(word, env);
    results.push(result);
  }

  return results;
}

// =============================================
// KV缓存实现
// =============================================

/**
 * 从KV缓存查词
 */
async function lookupFromKV(word, env) {
  try {
    if (!env || !env.WORD_CACHE || !CONFIG.enableKVCache) {
      return null;
    }

    const cacheKey = `word:${word.toLowerCase()}`;
    const cached = await env.WORD_CACHE.get(cacheKey, 'json');

    if (cached) {
      return {
        ...cached,
        source: 'kv-cache'
      };
    }

    return null;
  } catch (error) {
    console.error('KV lookup error:', error);
    return null;
  }
}

/**
 * 保存到KV缓存
 */
async function saveToKV(word, data, env) {
  try {
    if (!env || !env.WORD_CACHE || !CONFIG.enableKVCache) {
      return;
    }

    const cacheKey = `word:${word.toLowerCase()}`;
    await env.WORD_CACHE.put(cacheKey, JSON.stringify(data), {
      expirationTtl: CONFIG.cacheTTL
    });
  } catch (error) {
    console.error('KV save error:', error);
  }
}

// =============================================
// 智能查词（混合模式）
// =============================================

/**
 * 智能查词 - 结合数据库、缓存和API
 */
async function smartLookup(word, env, request) {
  const wordLower = word.toLowerCase().trim();

  // 1. 尝试KV缓存（最快）
  const kvResult = await lookupFromKV(wordLower, env);
  if (kvResult && kvResult.success) {
    return kvResult;
  }

  // 2. 尝试数据库查询
  const dbResult = await lookupFromDatabase(wordLower, env);
  if (dbResult.success) {
    // 保存到KV缓存
    await saveToKV(wordLower, dbResult, env);
    return dbResult;
  }

  // 3. 数据库未找到，尝试API（作为备用）
  // 这里可以调用之前的API函数
  // import { fetchDictionaryAPI } from './worker-api.js';
  // const apiResult = await fetchDictionaryAPI(word);
  // if (apiResult.success) {
  //   await saveToKV(wordLower, apiResult, env);
  //   return apiResult;
  // }

  // 4. 所有方法都失败
  return {
    success: false,
    error: '未找到该单词',
    word: word,
    tried: ['kv-cache', 'database'] //, 'api'
  };
}

// =============================================
// 路由处理
// =============================================

/**
 * 处理查词请求（支持D1数据库）
 */
async function handleLookup(request, env) {
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

    // 使用智能查词
    const result = await smartLookup(word, env, request);

    return jsonResponse(result);

  } catch (error) {
    console.error('Lookup error:', error);
    return jsonResponse({
      success: false,
      error: '查询失败，请稍后重试'
    }, 500);
  }
}

/**
 * 处理批量查词请求
 */
async function handleBatchLookup(request, env) {
  try {
    const url = new URL(request.url);
    const wordsParam = url.searchParams.get('words');

    if (!wordsParam) {
      return jsonResponse({
        success: false,
        error: '请提供要查询的单词列表'
      }, 400);
    }

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

    // 批量查词
    const results = [];
    for (const word of words) {
      if (/^[a-zA-Z\s-]+$/.test(word)) {
        const result = await smartLookup(word, env, request);
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
 * 数据库统计信息
 */
async function handleDatabaseStats(request, env) {
  try {
    if (!env || !env.DB) {
      return jsonResponse({
        success: false,
        error: '数据库未配置'
      });
    }

    // 获取总词数
    const countResult = await env.DB.prepare('SELECT COUNT(*) as count FROM mdx').first();
    const totalWords = countResult ? countResult.count : 0;

    // 获取最近查询的单词（从KV）
    let recentWords = [];
    if (env.WORD_CACHE) {
      try {
        const list = await env.WORD_CACHE.list({ limit: 10 });
        recentWords = list.keys.map(key => key.name.replace('word:', ''));
      } catch (error) {
        console.error('KV list error:', error);
      }
    }

    return jsonResponse({
      success: true,
      database: {
        total_words: totalWords,
        type: 'D1 (SQLite)',
        status: 'connected'
      },
      cache: {
        enabled: CONFIG.enableKVCache,
        recent_queries: recentWords
      }
    });

  } catch (error) {
    console.error('Stats error:', error);
    return jsonResponse({
      success: false,
      error: '获取统计信息失败: ' + error.message
    }, 500);
  }
}

// =============================================
// 工具函数（保持与原worker.js相同）
// =============================================

function jsonResponse(data, status = 200) {
  const headers = {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': CONFIG.cors.allowOrigin,
    'Access-Control-Allow-Methods': CONFIG.cors.allowMethods,
    'Access-Control-Allow-Headers': CONFIG.cors.allowHeaders
  };

  if (status === 200 && data.success) {
    headers['Cache-Control'] = `public, max-age=${CONFIG.cacheTTL}`;
  }

  return new Response(JSON.stringify(data, null, 2), {
    status,
    headers
  });
}

function htmlResponse(html) {
  return new Response(html, {
    headers: {
      'Content-Type': 'text/html;charset=UTF-8',
      'Access-Control-Allow-Origin': CONFIG.cors.allowOrigin
    }
  });
}

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
// 主处理函数（支持D1）
// =============================================

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const path = url.pathname;

    // 路由处理
    if (path === '/' || path === '/index.html') {
      return htmlResponse(SMART_LOOKUP_HTML);
    }

    if (path === '/lookup' || path === '/smart-lookup') {
      return htmlResponse(SMART_LOOKUP_HTML);
    }

    if (path === '/test' || path === '/test-optimizations' || path === '/debug') {
      // 返回对应的测试页面
      return htmlResponse(TEST_HTML);
    }

    if (path === '/api/lookup' || path === '/api/word-preview') {
      return handleLookup(request, env);
    }

    if (path === '/api/batch-lookup') {
      return handleBatchLookup(request, env);
    }

    if (path === '/api/health') {
      return jsonResponse({
        success: true,
        service: 'DreamWord Word Lookup',
        version: '2.0.0',
        status: 'healthy',
        features: {
          database: !!(env && env.DB),
          kv_cache: !!(env && env.WORD_CACHE),
          ocr: true,
          smart_lookup: true
        }
      });
    }

    if (path === '/api/stats') {
      return handleDatabaseStats(request, env);
    }

    if (path === '/api/debug') {
      return jsonResponse({
        success: true,
        worker: 'DreamWord Word Lookup',
        version: '2.0.0',
        config: {
          enableKVCache: CONFIG.enableKVCache,
          lookupPriority: CONFIG.lookupPriority,
          cacheTTL: CONFIG.cacheTTL
        },
        bindings: {
          database: !!(env && env.DB),
          kv_cache: !!(env && env.WORD_CACHE)
        }
      });
    }

    // 404
    return jsonResponse({
      success: false,
      error: '未找到请求的端点'
    }, 404);
  }
};
