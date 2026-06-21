package com.dreamword.app.dict

import com.dreamword.app.data.LookupResult
import com.dreamword.app.data.WordEntry

/**
 * 单词查询（移植自 PC 版 word_lookup.py 的 WordLookup.lookup 主流程）
 *
 * 安卓版裁剪掉 semantic 分支（torch/sentence-transformers 不可用），
 * 保留完整的：词形还原 → 条目择优 → 释义排序 逻辑。
 * 「变形词语境选错释义」的修复（_infer_inflection_base + merged_entries 择优）
 * 在这里被完整保留——这是该模块的核心价值。
 *
 * 在线 LLM 消歧不在本类，由 Disambiguator 在 Bridge 层对结果做后处理增强。
 */
class WordLookup(private val repo: DictRepository) {

    private val checker = object : InflectionResolver.ExistenceChecker {
        override fun exists(word: String) = repo.wordExists(word)
    }

    /** 对应 Python WordLookup.lookup */
    fun lookup(word: String, context: String = ""): LookupResult {
        val w = word.trim()
        val ctx = context.trim()
        if (w.isEmpty()) {
            return LookupResult(false, "", message = "请输入要查询的单词")
        }

        // 1. 解析词形（有 context 时额外推断变形基本形式）
        val (lookupWord, baseForm) = resolveWordForm(w, ctx)

        if (!repo.wordExists(lookupWord)) {
            return LookupResult(false, w, message = "数据库中未找到单词 \"$w\"")
        }

        var entries = repo.getWordEntries(lookupWord)
        if (entries.isEmpty()) {
            return LookupResult(false, w, message = "未找到单词 \"$w\" 的释义")
        }

        // 2. 按语境选最佳条目
        var bestEntry = SimilarityScorer.findBestMatch(entries, ctx)!!

        // 3. 获取基本形式条目（用于音标/释义复用 + 变形词合并择优）
        var baseEntry: WordEntry? = null
        if (baseForm != null && baseForm != lookupWord) {
            val baseEntries = repo.getWordEntries(baseForm)
            if (baseEntries.isNotEmpty()) {
                // 关键修复（word_lookup.py:1038-1045）：当 baseForm 是规则推断出的
                // （即原词本身也合法，如 found），把原词和基本形式条目合并后按语境择优
                if (ctx.isNotEmpty() && repo.wordExists(lookupWord)) {
                    val merged = ArrayList(entries).apply { addAll(baseEntries) }
                    bestEntry = SimilarityScorer.findBestMatch(merged, ctx)!!
                    if (bestEntry in baseEntries) baseEntry = bestEntry
                } else {
                    baseEntry = SimilarityScorer.findBestMatch(baseEntries, "")!!
                }
            }
        }

        // 4. bestEntry 为空时回退 baseEntry
        val bestIsEmpty = bestEntry.chineseDefinitions.isEmpty()
            && bestEntry.definitions.isEmpty()
            && bestEntry.examples.isEmpty()
        if (bestIsEmpty && baseEntry != null) bestEntry = baseEntry

        // 5. 音标：优先用基本形式
        val phonetics = getPhonetics(bestEntry, baseEntry)

        // 6. 释义：优先中文，没有则英文；空则回退 baseEntry
        var allDefinitions = if (bestEntry.chineseDefinitions.isNotEmpty())
            bestEntry.chineseDefinitions else bestEntry.definitions
        if (allDefinitions.isEmpty() && baseEntry != null) {
            allDefinitions = if (baseEntry.chineseDefinitions.isNotEmpty())
                baseEntry.chineseDefinitions else baseEntry.definitions
        }

        // 7. 有语境且多义项 → 按语境排序
        if (ctx.isNotEmpty() && allDefinitions.size > 1) {
            var sortDefs = bestEntry.definitions
            var sortExs = bestEntry.examples
            if (sortDefs.isEmpty() && baseEntry != null) sortDefs = baseEntry.definitions
            if (sortExs.isEmpty() && baseEntry != null) sortExs = baseEntry.examples
            allDefinitions = SimilarityScorer.rankDefinitionsByContext(
                ctx, allDefinitions, sortExs, sortDefs
            )
        }

        // 8. 例句：空则回退 baseEntry
        var examples = bestEntry.examples
        if (examples.isEmpty() && baseEntry != null) examples = baseEntry.examples

        return LookupResult(
            success = true,
            word = lookupWord,
            phonetic = formatPhonetic(phonetics),
            definitions = allDefinitions,
            baseForm = baseForm ?: lookupWord,
            pos = bestEntry.pos,
            examples = examples
        )
    }

    /** 对应 Python _resolve_word_form —— 返回 (查找词, 基本形式) */
    private fun resolveWordForm(word: String, context: String): Pair<String, String?> {
        if (repo.wordExists(word)) {
            var baseForm = getBaseFormFromDb(word)
            // 有 context 时，即使原词存在也推断变形（found→find 等）
            if (context.isNotEmpty() && baseForm == null) {
                baseForm = InflectionResolver.inferInflectionBase(word, checker)
            }
            return word to baseForm
        }
        // 原词不存在 → 用规则找基本形式
        val base = getWordBaseForm(word)
        return if (base != null) base to base else word to null
    }

    /** 对应 Python get_base_form_from_db —— 从词典 HTML 的 xref 提取 */
    private fun getBaseFormFromDb(word: String): String? {
        val html = repo.getEntryHtml(word) ?: return null
        val entries = MdxParser.parse(html)
        return entries.firstOrNull()?.baseForm
    }

    /** 对应 Python get_word_base_form —— DB 链接优先，否则规则推断 */
    private fun getWordBaseForm(word: String): String? =
        getBaseFormFromDb(word) ?: InflectionResolver.getWordBaseFormSimple(word, checker)

    private fun getPhonetics(entry: WordEntry, baseEntry: WordEntry?): List<String> =
        if (baseEntry != null && baseEntry.phonetics.isNotEmpty()) baseEntry.phonetics
        else entry.phonetics

    private fun formatPhonetic(phonetics: List<String>, maxCount: Int = 2): String =
        if (phonetics.isEmpty()) "N/A" else phonetics.take(maxCount).joinToString(", ")
}
