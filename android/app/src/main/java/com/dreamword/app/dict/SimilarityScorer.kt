package com.dreamword.app.dict

import com.dreamword.app.data.WordEntry

/**
 * 语境相似度打分（移植自 PC 版 word_lookup.py 的统计部分）
 *
 * PC 版 calculate_similarity 用 5 种相似度加权：语义(0.35) + 例句(0.30) +
 * TF-IDF(0.15) + 中文Jaccard(0.15) + N-gram(0.05)。
 *
 * 安卓版去掉语义模型（依赖 torch/sentence-transformers，不可行），
 * 其余 4 种权重按 PC 版「无语义时」的分配自动调整：
 *   例句 0.20 + TF-IDF 0.40 + 中文Jaccard 0.30 + N-gram 0.10
 * （与 word_lookup.py:800-828 中 use_semantic_search=False 分支完全一致）
 *
 * 这些纯统计打分构成「离线消歧」；在线 LLM 裁决见 Disambiguator，作为增强。
 */
object SimilarityScorer {

    private val STOPWORDS = setOf(
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "by", "from", "as", "is", "was", "are", "were", "be",
        "been", "being", "have", "has", "had", "do", "does", "did", "will",
        "would", "should", "could", "may", "might", "must", "can", "this",
        "that", "these", "those", "i", "you", "he", "she", "it", "we", "they",
        "的", "了", "是", "在", "我", "有", "和", "就", "不", "人", "都", "一",
        "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会", "着", "没有",
        "看", "好", "自己", "这"
    )

    private val WORD_RE = Regex("""\b\w+\b""")

    fun tokenize(text: String): List<String> =
        WORD_RE.findAll(text.lower()).map { it.value }.toList()

    private fun jaccard(a: Set<String>, b: Set<String>): Float {
        if (a.isEmpty() || b.isEmpty()) return 0f
        val inter = a.intersect(b).size.toFloat()
        val union = a.union(b).size.toFloat()
        return if (union > 0) inter / union else 0f
    }

    /** TF-IDF 简化版的关键词提取（去停用词，按词频取前 topN） */
    private fun extractKeywords(text: String, topN: Int = 10): List<String> {
        val tokens = tokenize(text)
        if (tokens.isEmpty()) return emptyList()
        val freq = HashMap<String, Int>()
        for (t in tokens) {
            if (t in STOPWORDS || t.length <= 1) continue
            freq[t] = (freq[t] ?: 0) + 1
        }
        return freq.entries.sortedByDescending { it.value }
            .take(topN).map { it.key }
    }

    /** 例句相似度：取所有例句 Jaccard 的最大值 */
    fun exampleSimilarity(context: String, entry: WordEntry): Float {
        if (entry.examples.isEmpty()) return 0f
        val ctx = tokenize(context).toSet()
        if (ctx.isEmpty()) return 0f
        var best = 0f
        for (ex in entry.examples) {
            val exTok = tokenize(ex).toSet()
            if (exTok.isEmpty()) continue
            best = maxOf(best, jaccard(ctx, exTok))
        }
        return best
    }

    /** TF-IDF 加权相似度：关键词重叠，靠前的词权重高 */
    fun tfidfSimilarity(context: String, entry: WordEntry): Float {
        val ctxKw = extractKeywords(context)
        val defText = (entry.chineseDefinitions + entry.examples).joinToString(" ")
        val defKw = extractKeywords(defText).toHashSet()
        if (ctxKw.isEmpty() || defKw.isEmpty()) return 0f
        var score = 0f
        ctxKw.forEachIndexed { i, w ->
            if (w in defKw) score += 1f / (i + 1)
        }
        var maxScore = 0f
        for (i in ctxKw.indices) maxScore += 1f / (i + 1)
        return if (maxScore > 0) score / maxScore else 0f
    }

    /** 中文释义 Jaccard */
    fun chineseJaccard(context: String, entry: WordEntry): Float {
        val ctx = tokenize(context).toSet()
        val defTok = tokenize(entry.chineseDefinitions.joinToString(" ")).toSet()
        return jaccard(ctx, defTok)
    }

    /** N-gram（n=2）相似度 */
    fun ngramSimilarity(text1: String, text2: String, n: Int = 2): Float {
        val t1 = tokenize(text1); val t2 = tokenize(text2)
        if (t1.size < n || t2.size < n) return 0f
        val g1 = (0..t1.size - n).map { t1.subList(it, it + n).joinToString(" ") }.toSet()
        val g2 = (0..t2.size - n).map { t2.subList(it, it + n).joinToString(" ") }.toSet()
        return jaccard(g1, g2)
    }

    /**
     * 综合相似度——对应 Python calculate_similarity（无语义分支）
     * 权重与 word_lookup.py:798-828 完全一致
     */
    fun calculateSimilarity(context: String, entry: WordEntry): Float {
        if (context.isBlank()) return 0f
        val scores = mutableListOf<Pair<Float, Float>>() // (score, weight)

        if (entry.examples.isNotEmpty()) {
            scores.add(exampleSimilarity(context, entry) to 0.20f)
        }
        scores.add(tfidfSimilarity(context, entry) to 0.40f)
        scores.add(chineseJaccard(context, entry) to 0.30f)
        scores.add(ngramSimilarity(
            context,
            if (entry.definitions.isNotEmpty()) entry.definitions.joinToString(" ")
            else entry.chineseDefinitions.joinToString(" ")
        ) to 0.10f)

        if (scores.isEmpty()) return 0f
        val totalScore = scores.sumOf { (it.first * it.second).toDouble() }.toFloat()
        val totalWeight = scores.sumOf { it.second.toDouble() }.toFloat()
        return if (totalWeight > 0) totalScore / totalWeight else 0f
    }

    /**
     * 在多个条目中找最佳匹配——对应 Python find_best_match
     */
    fun findBestMatch(entries: List<WordEntry>, context: String): WordEntry? {
        if (entries.isEmpty()) return null
        if (context.isBlank() || entries.size == 1) {
            // 返回第一个有释义的
            for (e in entries) {
                if (e.chineseDefinitions.isNotEmpty() || e.definitions.isNotEmpty()) return e
            }
            return entries[0]
        }
        return entries.maxByOrNull { calculateSimilarity(context, it) }
    }

    /**
     * 按语境对多义项释义排序——对应 Python _rank_definitions_by_context（无语义分支）
     * 权重：例句 0.3 + 中文释义 Jaccard 0.3 + TF-IDF 占满剩余（这里按 Python 调整为 0.4）
     * 注意：Python 里无语义时直接退回 example(0.3) + chinese(0.3) + 顺序，
     * 为贴近效果，这里对多义项采用相同策略
     */
    fun rankDefinitionsByContext(
        context: String,
        definitions: List<String>,
        examples: List<String>,
        englishDefinitions: List<String>
    ): List<String> {
        if (context.isBlank() || definitions.isEmpty()) return definitions
        val ctxTokens = tokenize(context).toSet()

        // 例句相似度（所有释义共享）
        var exampleScore = 0f
        if (examples.isNotEmpty()) {
            for (ex in examples) {
                val exTok = tokenize(ex).toSet()
                if (exTok.isNotEmpty()) {
                    exampleScore = maxOf(exampleScore, jaccard(ctxTokens, exTok))
                }
            }
        }

        val scored = definitions.mapIndexed { i, def ->
            var score = 0f
            score += exampleScore * 0.3f
            val defTokens = tokenize(def).toSet()
            if (ctxTokens.isNotEmpty() && defTokens.isNotEmpty()) {
                score += jaccard(ctxTokens, defTokens) * 0.3f
            }
            // TF-IDF 兜底：context 关键词与该释义的重叠
            score += tfidfKwOverlap(context, def) * 0.4f
            i to score
        }
        return scored.sortedByDescending { it.second }.map { definitions[it.first] }
    }

    private fun tfidfKwOverlap(context: String, definition: String): Float {
        val ctxKw = extractKeywords(context).toHashSet()
        val defKw = extractKeywords(definition).toHashSet()
        if (ctxKw.isEmpty() || defKw.isEmpty()) return 0f
        return ctxKw.intersect(defKw).size.toFloat() / ctxKw.size.toFloat()
    }
}
