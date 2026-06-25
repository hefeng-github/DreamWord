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
 *
 * 查询后端抽象为 DictBackend（CachedDict 长连接 / DictRepository 每次开关），
 * 默认用 CachedDict，避免对 441MB 词典反复 open/close（见 DictRepository.openCached）。
 * 所有查询走大小写兜底（getEntryHtmlCaseInsensitive / wordExistsCaseInsensitive），
 * 修正 OCR 混合大小写命中失败的问题。
 */
class WordLookup(private val backend: DictBackend) {

    /** 词典查询后端：CachedDict（长连接，推荐）或 DictRepository（每次开关） */
    interface DictBackend {
        fun wordExists(word: String): Boolean
        fun wordExistsCaseInsensitive(word: String): Boolean
        fun getEntryHtml(word: String): String?
        fun getEntryHtmlCaseInsensitive(word: String): String?
        fun getWordEntries(word: String): List<WordEntry>
        /** 返回真正命中的词典 key，未命中 null（用于结果回填正确大小写） */
        fun resolveEntryKey(word: String): String?
    }

    private val checker = object : InflectionResolver.ExistenceChecker {
        override fun exists(word: String) = backend.wordExistsCaseInsensitive(word)
    }

    /** 对应 Python WordLookup.lookup */
    fun lookup(word: String, context: String = ""): LookupResult {
        val w = word.trim()
        val ctx = context.trim()
        if (w.isEmpty()) {
            return LookupResult(false, "", message = "请输入要查询的单词")
        }

        // 1. 解析词形（有 context 时额外推断变形基本形式）
        val (lookupWordRaw, baseForm) = resolveWordForm(w, ctx)

        // 大小写兜底：解析出真正命中的词典 key
        val lookupKey = backend.resolveEntryKey(lookupWordRaw)
            ?: return LookupResult(false, w, message = "数据库中未找到单词 \"$w\"")

        var entries = backend.getWordEntries(lookupKey)
        if (entries.isEmpty()) {
            return LookupResult(false, w, message = "未找到单词 \"$w\" 的释义")
        }

        // 2. 按语境选最佳条目
        var bestEntry = SimilarityScorer.findBestMatch(entries, ctx)!!

        // 3. 获取基本形式条目（用于音标/释义复用 + 变形词合并择优）
        var baseEntry: WordEntry? = null
        if (baseForm != null && baseForm != lookupKey) {
            val baseKey = backend.resolveEntryKey(baseForm)
            if (baseKey != null) {
                val baseEntries = backend.getWordEntries(baseKey)
                if (baseEntries.isNotEmpty()) {
                    // 关键修复（word_lookup.py:1038-1045）：当 baseForm 是规则推断出的
                    // （即原词本身也合法，如 found），把原词和基本形式条目合并后按语境择优
                    if (ctx.isNotEmpty() && backend.wordExistsCaseInsensitive(lookupKey)) {
                        val merged = ArrayList(entries).apply { addAll(baseEntries) }
                        bestEntry = SimilarityScorer.findBestMatch(merged, ctx)!!
                        if (bestEntry in baseEntries) baseEntry = bestEntry
                    } else {
                        baseEntry = SimilarityScorer.findBestMatch(baseEntries, "")!!
                    }
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
        // 显式声明为 List<String>：后续 rankDefinitionsByContext 返回不可变 List
        var allDefinitions: List<String> = if (bestEntry.chineseDefinitions.isNotEmpty())
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
            word = lookupKey,
            phonetic = formatPhonetic(phonetics),
            definitions = allDefinitions,
            baseForm = baseForm ?: lookupKey,
            pos = bestEntry.pos,
            examples = examples
        )
    }

    /** 对应 Python _resolve_word_form —— 返回 (查找词, 基本形式) */
    private fun resolveWordForm(word: String, context: String): Pair<String, String?> {
        if (backend.wordExistsCaseInsensitive(word)) {
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
        val html = backend.getEntryHtmlCaseInsensitive(word) ?: return null
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

    /** 释放底层 CachedDict 连接（dict reload/import 前调用） */
    fun close() {
        (backend as? RepoBackend)?.cached?.close()
    }

    companion object {
        /** 从 DictRepository 构造（用 CachedDict 长连接，推荐） */
        fun fromRepo(repo: DictRepository): WordLookup = WordLookup(RepoBackend(repo.openCached()))

        /** CachedDict 适配器 */
        private class RepoBackend(val cached: DictRepository.CachedDict) : DictBackend {
            override fun wordExists(word: String) = cached.wordExists(word)
            override fun wordExistsCaseInsensitive(word: String) = cached.wordExistsCaseInsensitive(word)
            override fun getEntryHtml(word: String) = cached.getEntryHtml(word)
            override fun getEntryHtmlCaseInsensitive(word: String) = cached.getEntryHtmlCaseInsensitive(word)
            override fun getWordEntries(word: String) = cached.getWordEntries(word)
            override fun resolveEntryKey(word: String) = cached.resolveEntryKey(word)
        }
    }
}
