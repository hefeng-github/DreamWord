-- DreamWord D1 数据库表结构
-- 与Python版本兼容

-- 词典表（MDX格式）
CREATE TABLE IF NOT EXISTS mdx (
  entry TEXT NOT NULL,
  paraphrase TEXT NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_entry ON mdx(entry);

-- 插入一些常用单词作为示例数据
INSERT OR IGNORE INTO mdx (entry, paraphrase) VALUES
('hello', '<div class="entry"><h1 class="headword">hello</h1><span class="pos">int.</span><span class="phon">/həˈləʊ/</span><span class="def">你好；问候</span><span class="x">Hello, how are you?</span></div>'),

('world', '<div class="entry"><h1 class="headword">world</h1><span class="pos">n.</span><span class="phon">/wɜːld/</span><span class="def">世界；地球</span><span class="def">领域；范围</span><span class="x">The world is round.</span></div>'),

('test', '<div class="entry"><h1 class="headword">test</h1><span class="pos">n./v.</span><span class="phon">/test/</span><span class="def">测试；试验</span><span class="def">检验</span><span class="x">This is a test.</span></div>'),

('computer', '<div class="entry"><h1 class="headword">computer</h1><span class="pos">n.</span><span class="phon">/kəmˈpjuːtər/</span><span class="def">计算机；电脑</span><span class="x">I work on my computer every day.</span></div>'),

('program', '<div class="entry"><h1 class="headword">program</h1><span class="pos">n./v.</span><span class="phon">/ˈproʊɡræm/</span><span class="def">程序；计划</span><span class="def">编程</span><span class="x">This program is written in Python.</span></div>'),

('database', '<div class="entry"><h1 class="headword">database</h1><span class="pos">n.</span><span class="phon">/ˈdeɪtəbeɪs/</span><span class="def">数据库</span><span class="x">The database contains millions of words.</span></div>'),

('cloudflare', '<div class="entry"><h1 class="headword">cloudflare</h1><span class="pos">n.</span><span class="phon">/ˈklaʌdfler/</span><span class="def">Cloudflare（一家网络基础设施公司）</span></div>'),

('worker', '<div class="entry"><h1 class="headword">worker</h1><span class="pos">n.</span><span class="phon">/ˈwɜːrkər/</span><span class="def">工人；工作者</span><span class="def">Worker（Cloudflare Workers）</span></div>'),

('dictionary', '<div class="entry"><h1 class="headword">dictionary</h1><span class="pos">n.</span><span class="phon">/ˈdɪkʃəneri/</span><span class="def">词典；字典</span><span class="x">I use a dictionary to learn new words.</span></div>'),

('lookup', '<div class="entry"><h1 class="headword">lookup</h1><span class="pos">n./v.</span><span class="phon">/ˈlʊkʌp/</span><span class="def">查找</span><span class="def">查阅</span></div>'),

('performance', '<div class="entry"><h1 class="headword">performance</h1><span class="pos">n.</span><span class="phon">/pərˈfɔːrməns/</span><span class="def">性能；表现</span><span class="def">演出；表演</span></div>'),

('optimization', '<div class="entry"><h1 class="headword">optimization</h1><span class="pos">n.</span><span class="phon">/ˌɑːptɪməˈzeɪʃn/</span><span class="def">优化</span><span class="def">最佳化</span></div>'),

('amazing', '<div class="entry"><h1 class="headword">amazing</h1><span class="pos">adj.</span><span class="phon">/əˈmeɪzɪŋ/</span><span class="def">令人惊异的；了不起的</span><span class="x">The performance is amazing!</span></div>'),

('wonderful', '<div class="entry"><h1 class="headword">wonderful</h1><span class="pos">adj.</span><span class="phon">/ˈwʌndərfl/</span><span class="def">精彩的；极好的</span><span class="x">Have a wonderful day!</span></div>'),

('excellent', '<div class="entry"><h1 class="headword">excellent</h1><span class="pos">adj.</span><span class="phon">/ˈeksələnt/</span><span class="def">优秀的；杰出的</span><span class="def">极好的</span></div>');
