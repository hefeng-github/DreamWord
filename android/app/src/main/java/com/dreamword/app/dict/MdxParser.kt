package com.dreamword.app.dict

import com.dreamword.app.data.WordEntry
import org.jsoup.Jsoup
import org.jsoup.nodes.Element
import org.jsoup.nodes.TextNode

/**
 * MDX 格式 HTML 解析器（移植自 PC 版 word_lookup.py:34-233 的 MDXParser）
 *
 * PC 版用 Python html.parser 的状态机逐标签解析；这里改用 Jsoup 构建 DOM 后遍历，
 * 等价但更稳健。解析规则：
 *  - div.entry        → 一个独立条目（一个词可能有多个 entry）
 *  - h1.headword      → 词头
 *  - span.phon        → 音标
 *  - span.pos         → 词性
 *  - span.def         → 英文释义（其后紧跟的 <chn> 为对应中文）
 *  - chn（def 之后）    → 中文释义
 *  - span.x           → 例句
 *  - @@@LINK=xxx       → MDX 重定向，返回带 baseForm 的占位条目
 *
 * MDX 常见的 class 写法是多个 class 空格连接，匹配用 contains。
 */
object MdxParser {

    fun parse(htmlContent: String): List<WordEntry> {
        if (htmlContent.isBlank()) return emptyList()

        // MDX 重定向：@@@LINK=realword
        val trimmed = htmlContent.trimStart()
        if (trimmed.startsWith("@@@LINK=")) {
            val target = trimmed.removePrefix("@@@LINK=").trim()
            return listOf(WordEntry(headword = target, baseForm = target))
        }

        val doc = Jsoup.parse(htmlContent)
        val entries = mutableListOf<WordEntry>()

        // MDX 里每个 div.entry 是一个词性条目；若没有 entry 包裹，则把整个文档当作单条目
        val entryDivs = doc.select("div.entry")
        if (entryDivs.isNotEmpty()) {
            for (div in entryDivs) {
                val e = parseOneEntry(div) ?: continue
                entries.add(e)
            }
        } else {
            parseOneEntry(doc.body())?.let { entries.add(it) }
        }
        return entries
    }

    private fun parseOneEntry(root: Element): WordEntry? {
        val headword = selectText(root, "h1.headword")
            ?: root.selectFirst("[class~=\\bheadword\\b]")?.text()
            ?: return null

        val entry = WordEntry(headword = headword.trim())

        // 音标：所有 span.phon
        for (phon in root.select("[class~=\\bphon\\b]")) {
            val p = phon.text().trim()
            if (p.isNotEmpty() && p !in entry.phonetics) entry.phonetics.add(p)
        }

        // 词性：span.pos（class 含 pos，但排除 phon / def 等已匹配的）
        root.select("[class~=\\bpos\\b]").firstOrNull()?.let { posEl ->
            val pos = posEl.text().trim()
            if (pos.isNotEmpty()) entry.pos = pos
        }

        // 英文释义 span.def + 紧邻的中文 <chn>
        // MDX 结构通常是 <span class="def">english</span><chn>中文</chn>
        val defSpans = root.select("span.def")
        for (defSpan in defSpans) {
            val enDef = defSpan.text().trim()
            if (enDef.isNotEmpty()) entry.definitions.add(enDef)
            // 紧邻兄弟 <chn>
            var sib: Element? = defSpan.nextElementSibling()
            if (sib != null && sib.tagName() == "chn") {
                val cnDef = sib.text().trim()
                if (cnDef.isNotEmpty()) entry.chineseDefinitions.add(cnDef)
            }
        }

        // 若没有配对 <chn>，回退：收集所有独立的 chn
        if (entry.chineseDefinitions.isEmpty()) {
            for (chn in root.select("chn")) {
                val cnDef = chn.text().trim()
                if (cnDef.isNotEmpty()) entry.chineseDefinitions.add(cnDef)
            }
        }

        // 例句 span.x（class 恰好为 "x"，避免误中 xref/xh）
        for (ex in root.select("span.x")) {
            val cls = ex.className()
            if (cls == "x" || cls.split(' ').any { it == "x" }) {
                val txt = collectExampleText(ex).trim()
                if (txt.isNotEmpty()) entry.examples.add(txt)
            }
        }

        // 基本形式：xrefs > xh
        root.selectFirst("span.xrefs span.xh")?.let { xh ->
            val bf = xh.text().trim()
            if (bf.isNotEmpty()) entry.baseForm = bf
        }

        return entry
    }

    /** 取首个匹配元素的可见文本（合并其下所有文本节点，等价于 Python 的 data 累积） */
    private fun selectText(root: Element, css: String): String? {
        val el = root.selectFirst(css) ?: return null
        return collectText(el)
    }

    private fun collectText(el: Element): String {
        val sb = StringBuilder()
        for (node in el.textNodes()) {
            sb.append((node as TextNode).text())
        }
        // 若纯文本节点为空，回退到 .text()（含子元素文本）
        return if (sb.isNotEmpty()) sb.toString() else el.text()
    }

    /** 例句可能含嵌套标签（如 <b>...</b> 高亮），需把嵌套文本也取出 */
    private fun collectExampleText(el: Element): String =
        el.text()
}
