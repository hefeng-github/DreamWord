package com.dreamword.app.dict

/**
 * 英语形态规则推断（移植自 PC 版 word_lookup.py:448-972）
 *
 * 两套逻辑：
 *  1) getWordBaseFormSimple(word, wordExists)：原词不存在时，用规则找基本形式
 *     —— 用于查不到词时的兜底（如 looked → look）
 *  2) inferInflectionBase(word, wordExists)：不要求原词不存在，专门处理
 *     "原词本身是合法词条、但语境中其实是变形"的情况（found→find, left→leave 等）
 *     —— 这是"变形词语境选错释义"修复的关键
 *
 * 与 PC 版保持完全一致的特殊词表。只返回「词典中确实存在、且与原词不同」的候选。
 */
object InflectionResolver {

    // 不规则动词过去式 + "既是独立词又是变形"的高频词
    // 合并自 word_lookup.py 的 get_word_base_form_simple 和 _infer_inflection_base
    private val SPECIAL_CASES: Map<String, String> = mapOf(
        "ran" to "run", "bit" to "bite", "ate" to "eat", "drove" to "drive",
        "saw" to "see", "fell" to "fall", "gave" to "give", "knew" to "know",
        "thought" to "think", "threw" to "throw", "came" to "come", "went" to "go",
        "bought" to "buy", "brought" to "bring", "caught" to "catch",
        "fought" to "fight", "taught" to "teach", "sought" to "seek",
        "bent" to "bend", "bound" to "bind", "built" to "build",
        "dealt" to "deal", "felt" to "feel", "held" to "hold",
        "kept" to "keep", "led" to "lead", "lost" to "lose",
        "meant" to "mean", "paid" to "pay", "sold" to "sell",
        "sent" to "send", "spent" to "spend", "stood" to "stand",
        "understood" to "understand", "won" to "win", "wound" to "wind",
        // 既是独立词又是变形的高频词（_infer_inflection_base 独有）
        "found" to "find", "left" to "leave", "lay" to "lie",
        "bore" to "bear", "tore" to "tear", "wore" to "wear",
        "spoke" to "speak", "broke" to "break", "stole" to "steal",
        "chose" to "choose", "froze" to "freeze", "rose" to "rise",
        "woke" to "wake", "drew" to "draw", "flew" to "fly",
        "slid" to "slide", "hid" to "hide", "rode" to "ride"
    )

    interface ExistenceChecker {
        fun exists(word: String): Boolean
    }

    /**
     * 简单规则还原（原词【不存在】时用）——对应 Python get_word_base_form_simple
     */
    fun getWordBaseFormSimple(word: String, checker: ExistenceChecker): String? {
        val wordExists = checker.exists(word)
        val wordLower = word.lower()

        // 1. 特殊不规则
        SPECIAL_CASES[wordLower]?.let { base ->
            if (!wordExists && checker.exists(base)) return base
        }

        // 2. 过去式 -ed
        if (wordLower.endsWith("ed") && wordLower.length > 3) {
            var base = wordLower.dropLast(2)
            base = collapseDoubleOrIe(base)
            if (!wordExists && checker.exists(base)) return base
        }
        // 3. 复数 -es / -s
        when {
            wordLower.endsWith("es") && wordLower.length > 3 -> {
                val base = wordLower.dropLast(2)
                if (!wordExists && checker.exists(base)) return base
            }
            wordLower.endsWith("s") && wordLower.length > 2 && !wordLower.endsWith("ss") -> {
                val base = wordLower.dropLast(1)
                if (!wordExists && checker.exists(base)) return base
            }
        }
        // 4. 现在分词 -ing
        if (wordLower.endsWith("ing") && wordLower.length > 4) {
            var base = wordLower.dropLast(3)
            base = collapseDoubleOrIe(base)
            if (!wordExists && checker.exists(base)) return base
            if (!wordExists && checker.exists(base + "e")) return base + "e"
        }
        // 5. 比较级 -er
        if (wordLower.endsWith("er") && wordLower.length > 3) {
            val base = wordLower.dropLast(2)
            if (!wordExists && checker.exists(base)) return base
        }
        return null
    }

    /**
     * 形态规则推断（不要求原词不存在）——对应 Python _infer_inflection_base
     * 用于"原词本身合法但在语境中其实是变形"。返回第一个词典中存在的候选。
     */
    fun inferInflectionBase(word: String, checker: ExistenceChecker): String? {
        val wordLower = word.lower()
        val candidates = mutableListOf<String>()

        SPECIAL_CASES[wordLower]?.let { candidates.add(it) }

        // -ed
        if (wordLower.endsWith("ed") && wordLower.length > 3) {
            var base = wordLower.dropLast(2)
            base = collapseDoubleOrIe(base)
            candidates.add(base)
            candidates.add(base + "e")
        }
        // -ing
        if (wordLower.endsWith("ing") && wordLower.length > 4) {
            var base = wordLower.dropLast(3)
            base = collapseDoubleOrIe(base)
            candidates.add(base)
            candidates.add(base + "e")
        }
        // -es / -s
        when {
            wordLower.endsWith("es") && wordLower.length > 3 -> candidates.add(wordLower.dropLast(2))
            wordLower.endsWith("s") && wordLower.length > 2 && !wordLower.endsWith("ss") ->
                candidates.add(wordLower.dropLast(1))
        }

        // 只保留词典中存在、且与原词不同的
        for (cand in candidates) {
            if (cand.isNotBlank() && cand.lower() != wordLower && checker.exists(cand)) {
                return cand
            }
        }
        return null
    }

    /** 处理 -ed / -ing 去尾后的拼写：planned→plan、tried→try */
    private fun collapseDoubleOrIe(base: String): String {
        if (base.length <= 1) return base
        // 双写辅音尾：planned -> plan（去掉末尾重复字母）
        if (base[base.length - 1] == base[base.length - 2]) {
            return base.dropLast(1)
        }
        // ie -> y：tried -> try（去 i 加 y）
        if (base.endsWith("i")) {
            return base.dropLast(1) + "y"
        }
        return base
    }
}
