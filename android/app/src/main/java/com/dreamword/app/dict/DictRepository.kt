package com.dreamword.app.dict

import android.content.Context
import android.database.sqlite.SQLiteDatabase
import com.dreamword.app.data.WordEntry
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken
import java.io.File

/**
 * 词典数据访问（移植自 PC 版 word_lookup.py 的 DB 部分）
 *
 * 支持两种词典格式（自动按表是否存在切换）：
 *  - v2（推荐）：words(entry, data BLOB) + redirects(entry, target) + metadata(key, html)
 *    data 是预解析 JSON，查词时零 HTML 解析、更快；体积从 421MB → ~93MB。
 *  - v1（旧）：mdx(entry, paraphrase TEXT)，paraphrase 是 HTML，运行时用 MdxParser 解析。
 *
 * 安卓上策略：
 *  - 完整词典从外部存储 / 下载目录打开（避免打进 APK）
 *  - 若外部没有，回退到 assets 里内置的精简词表（assets/dict/word_details_mini.db）
 *  - 只读打开（SQLiteDatabase.OPEN_READONLY）
 *
 * 所有查询都在 try/finally 关闭游标和连接，避免在大量并发查词时锁库。
 */
class DictRepository private constructor(
    private val dbFile: File
) {

    /** 探测当前库是 v2（words 表）还是 v1（mdx 表） */
    private val isV2: Boolean by lazy {
        withDb { db ->
            db.rawQuery(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='words' LIMIT 1", null
            ).use { it.moveToFirst() }
        }
    }

    fun isOpenable(): Boolean = dbFile.exists() && dbFile.canRead()

    /** 对应 Python word_exists：精确匹配 entry（v2 含 redirects 兜底） */
    fun wordExists(word: String): Boolean = withDb { db ->
        if (isV2) {
            db.rawQuery(
                "SELECT 1 FROM words WHERE entry = ? " +
                    "UNION ALL SELECT 1 FROM redirects WHERE entry = ? LIMIT 1",
                arrayOf(word, word)
            ).use { it.moveToFirst() }
        } else {
            db.rawQuery(
                "SELECT entry FROM mdx WHERE entry = ? LIMIT 1", arrayOf(word)
            ).use { it.moveToFirst() }
        }
    } ?: false

    /**
     * v2: 取该词（或其跳转目标）的 words.data JSON 字符串；v1: 取第一条 paraphrase HTML。
     * 返回值供 getBaseFormFromDb 使用——v2 下是 JSON，需配合 [wordEntriesFromJson]。
     */
    fun getEntryHtml(word: String): String? = withDb { db ->
        if (isV2) {
            val target = resolveRedirect(db, word) ?: return@withDb null
            db.rawQuery("SELECT data FROM words WHERE entry = ? LIMIT 1", arrayOf(target)).use { c ->
                if (c.moveToFirst()) String(c.getBlob(0), Charsets.UTF_8) else null
            }
        } else {
            db.rawQuery(
                "SELECT paraphrase FROM mdx WHERE entry = ? LIMIT 1", arrayOf(word)
            ).use { c -> if (c.moveToFirst()) c.getString(0) else null }
        }
    }

    /**
     * 大小写兜底版 getEntryHtml：OCR 文本混合大小写时，精确匹配可能 miss。
     * 按 [原样, 全小写, 首字母大写] 顺序尝试，命中即返回。
     */
    fun getEntryHtmlCaseInsensitive(word: String): String? {
        getEntryHtml(word)?.let { return it }
        val lower = word.lowercase()
        if (lower != word) getEntryHtml(lower)?.let { return it }
        val capitalized = lower.replaceFirstChar { it.uppercase() }
        if (capitalized != word && capitalized != lower) getEntryHtml(capitalized)?.let { return it }
        return null
    }

    /** 大小写兜底版 wordExists（与 getEntryHtmlCaseInsensitive 的形态顺序一致） */
    fun wordExistsCaseInsensitive(word: String): Boolean =
        getEntryHtmlCaseInsensitive(word) != null

    /** 解析出真正命中的词典 key（用于 lookup 结果回填），未命中返回 null */
    fun resolveEntryKey(word: String): String? {
        if (wordExists(word)) return word
        val lower = word.lowercase()
        if (lower != word && wordExists(lower)) return lower
        val capitalized = lower.replaceFirstChar { it.uppercase() }
        if (capitalized != word && capitalized != lower && wordExists(capitalized)) return capitalized
        return null
    }

    /** 对应 Python get_word_entries：取该词所有条目（v2 直接反序列化 JSON，零 HTML 解析） */
    fun getWordEntries(word: String): List<WordEntry> {
        val payload = getEntryHtml(word) ?: return emptyList()
        return if (isV2) wordEntriesFromJson(payload) else MdxParser.parse(payload)
    }

    private inline fun <T> withDb(block: (SQLiteDatabase) -> T): T {
        // 完整词典很大，每次查词都打开会慢；调用方应持有 DictRepository 单例，
        // 并在内部缓存一个打开的 SQLiteDatabase（见 openCached）。
        synchronized(dbFile) {
            val db = SQLiteDatabase.openDatabase(
                dbFile.absolutePath, null,
                SQLiteDatabase.OPEN_READONLY or SQLiteDatabase.NO_LOCALIZED_COLLATORS
            )
            return try {
                block(db)
            } finally {
                db.close()
            }
        }
    }


    /**
     * 长连接版：在内存中保持一个打开的 SQLiteDatabase，避免反复 open/close。
     * 适合查询密集场景（如拍照批量查词）。调用方负责 close。
     * 所有方法 synchronized：autoLookup 在 Dispatchers.Default 线程跑，
     * 与手动查词/状态查询可能并发，需保护底层 SQLiteDatabase。
     */
    fun openCached(): CachedDict = CachedDict(SQLiteDatabase.openDatabase(
        dbFile.absolutePath, null,
        SQLiteDatabase.OPEN_READONLY or SQLiteDatabase.NO_LOCALIZED_COLLATORS
    ))

    /** 带缓存的连接包装 */
    class CachedDict internal constructor(internal val db: SQLiteDatabase) : AutoCloseable {
        private val isV2: Boolean = db.rawQuery(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='words' LIMIT 1", null
        ).use { it.moveToFirst() }

        fun wordExists(word: String): Boolean = synchronized(db) {
            if (isV2) {
                db.rawQuery(
                    "SELECT 1 FROM words WHERE entry = ? " +
                        "UNION ALL SELECT 1 FROM redirects WHERE entry = ? LIMIT 1",
                    arrayOf(word, word)
                ).use { it.moveToFirst() }
            } else {
                db.rawQuery("SELECT entry FROM mdx WHERE entry = ? LIMIT 1", arrayOf(word))
                    .use { it.moveToFirst() }
            }
        }

        fun getEntryHtml(word: String): String? = synchronized(db) {
            if (isV2) {
                val target = resolveRedirect(db, word) ?: return@synchronized null
                db.rawQuery("SELECT data FROM words WHERE entry = ? LIMIT 1", arrayOf(target))
                    .use { c -> if (c.moveToFirst()) String(c.getBlob(0), Charsets.UTF_8) else null }
            } else {
                db.rawQuery("SELECT paraphrase FROM mdx WHERE entry = ? LIMIT 1", arrayOf(word))
                    .use { c -> if (c.moveToFirst()) c.getString(0) else null }
            }
        }

        fun getWordEntries(word: String): List<WordEntry> {
            val payload = getEntryHtml(word) ?: return emptyList()
            return if (isV2) wordEntriesFromJson(payload) else MdxParser.parse(payload)
        }

        /** 大小写兜底（与 DictRepository 同语义） */
        fun getEntryHtmlCaseInsensitive(word: String): String? {
            getEntryHtml(word)?.let { return it }
            val lower = word.lowercase()
            if (lower != word) getEntryHtml(lower)?.let { return it }
            val capitalized = lower.replaceFirstChar { it.uppercase() }
            if (capitalized != word && capitalized != lower) getEntryHtml(capitalized)?.let { return it }
            return null
        }
        fun wordExistsCaseInsensitive(word: String): Boolean =
            getEntryHtmlCaseInsensitive(word) != null
        fun resolveEntryKey(word: String): String? {
            if (wordExists(word)) return word
            val lower = word.lowercase()
            if (lower != word && wordExists(lower)) return lower
            val capitalized = lower.replaceFirstChar { it.uppercase() }
            if (capitalized != word && capitalized != lower && wordExists(capitalized)) return capitalized
            return null
        }

        override fun close() = synchronized(db) { db.close() }
    }

    companion object {
        private val gson = Gson()

        /**
         * 解析 redirects 链，返回最终目标 entry（即 words 表里的 key）。
         * 若 word 本身不在 redirects 里（是真实词头或不存在），返回 word 自身。
         * 最多 5 层，防循环。
         */
        private fun resolveRedirect(db: SQLiteDatabase, word: String): String? {
            var current = word
            repeat(5) {
                val target = db.rawQuery(
                    "SELECT target FROM redirects WHERE entry = ? LIMIT 1", arrayOf(current)
                ).use { c -> if (c.moveToFirst()) c.getString(0) else null } ?: return current
                current = target
            }
            return current
        }

        /**
         * v2: 把 words.data 的 JSON（WordEntry 字段数组）反序列化为 List<WordEntry>。
         * 字段与 PC 端 build_dict_db.py 的 entry_to_dict 1:1 对应。
         */
        fun wordEntriesFromJson(json: String): List<WordEntry> {
            return try {
                val type = object : TypeToken<List<Map<String, Any?>>>() {}.type
                val list: List<Map<String, Any?>> = gson.fromJson(json, type)
                list.map { m ->
                    WordEntry(
                        headword = m["headword"] as? String ?: "",
                        phonetics = (m["phonetics"] as? List<*>)?.mapNotNull { it?.toString() }
                            ?.toMutableList() ?: mutableListOf(),
                        definitions = (m["definitions"] as? List<*>)?.mapNotNull { it?.toString() }
                            ?.toMutableList() ?: mutableListOf(),
                        chineseDefinitions = (m["chinese_definitions"] as? List<*>)?.mapNotNull { it?.toString() }
                            ?.toMutableList() ?: mutableListOf(),
                        examples = (m["examples"] as? List<*>)?.mapNotNull { it?.toString() }
                            ?.toMutableList() ?: mutableListOf(),
                        baseForm = m["base_form"] as? String,
                        pos = m["pos"] as? String
                    )
                }
            } catch (e: Exception) {
                emptyList()
            }
        }

        @Volatile private var instance: DictRepository? = null

        /**
         * 解析词典位置（按优先级查找）：
         *  1) 外部应用目录 Android/data/com.dreamword.app/files/dict/word_details_v2.db（新格式）
         *  2) 外部应用目录 .../word_details.db（旧 v1 格式，过渡期兼容）
         *  3) 内部目录 filesDir/dict/word_details(_v2).db（旧版导入或 adb push）
         *  4) 内置精简词表（assets 解包到 filesDir）
         * 都没有则返回 null（前端会提示去导入）
         */
        fun resolve(context: Context): DictRepository? {
            instance?.let { return it }

            val candidates = mutableListOf<File>()
            context.getExternalFilesDir(null)?.let { extBase ->
                candidates.add(File(extBase, "dict/word_details_v2.db"))   // v2 优先
                candidates.add(File(extBase, "dict/word_details.db"))     // v1 兼容
                candidates.add(File(extBase, "dict/word_details_mini.db"))
            }
            candidates.add(File(context.filesDir, "dict/word_details_v2.db"))
            candidates.add(File(context.filesDir, "dict/word_details.db"))
            // 内置精简词表（assets 解包）
            val mini = File(context.filesDir, "dict/word_details_mini.db")
            if (!mini.exists()) {
                tryCopyAsset(context, "dict/word_details_mini.db", mini)
            }
            candidates.add(mini)

            val target = candidates.firstOrNull { it.exists() && it.canRead() }
                ?: return null
            return DictRepository(target).also { instance = it }
        }

        /** 当用户下载完完整词典后，重置单例使其重新解析 */
        fun reset() { instance = null }

        /** 返回推荐的词典导入路径（给前端提示用户把 .db 放这里） */
        fun getImportHintPath(context: Context): String {
            val ext = context.getExternalFilesDir(null)
            return if (ext != null) "${ext.absolutePath}/dict/word_details_v2.db"
            else "${context.filesDir.absolutePath}/dict/word_details_v2.db"
        }

        /**
         * 导入用户从本地选择的词典文件（.db）。
         * 支持 v2（words 表）和 v1（mdx 表）两种格式。
         * 拷贝到外部应用目录 dict/，校验通过后 reset()，下次查询自动用新词典。
         * 用流式拷贝（非 base64），避免大文件撑爆内存。
         *
         * @return 导入结果：成功返回文件大小，失败抛异常
         */
        fun importDictionary(context: Context, uri: android.net.Uri): Long {
            val ext = context.getExternalFilesDir(null)
                ?: throw Exception("无法访问外部存储目录")
            File(ext, "dict").mkdirs()
            // 先写临时文件，校验通过后替换，避免拷贝中途崩溃导致词典损坏
            val tmp = File(ext, "dict/word_details.db.tmp")
            try {
                context.contentResolver.openInputStream(uri).use { input ->
                    if (input == null) throw Exception("无法读取所选文件")
                    tmp.outputStream().use { output -> input.copyTo(output) }
                }
                // 基本校验：SQLite 文件头应为 "SQLite format 3\000"
                tmp.inputStream().use { ins ->
                    val header = ByteArray(16)
                    val n = ins.read(header)
                    if (n < 16 || !String(header, 0, 15).startsWith("SQLite format 3")) {
                        throw Exception("所选文件不是有效的 SQLite 词典（缺少 SQLite 文件头）")
                    }
                }
                // 结构校验：必须有 words（v2）或 mdx（v1）表，否则导入后查询才崩
                val probe = SQLiteDatabase.openDatabase(
                    tmp.absolutePath, null,
                    SQLiteDatabase.OPEN_READONLY or SQLiteDatabase.NO_LOCALIZED_COLLATORS
                )
                val isV2: Boolean
                try {
                    val hasWords = probe.rawQuery(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name='words' LIMIT 1", null
                    ).use { it.moveToFirst() }
                    val hasMdx = probe.rawQuery(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name='mdx' LIMIT 1", null
                    ).use { it.moveToFirst() }
                    if (!hasWords && !hasMdx) {
                        throw Exception("这不是 DreamWord 词典（缺少 words/mdx 表，请选 word_details_v2.db 或 word_details.db）")
                    }
                    isV2 = hasWords
                } finally {
                    probe.close()
                }
                // 替换正式文件：v2 用 word_details_v2.db，v1 用 word_details.db
                val dest = if (isV2) File(ext, "dict/word_details_v2.db")
                else File(ext, "dict/word_details.db")
                if (dest.exists()) dest.delete()
                if (!tmp.renameTo(dest)) throw Exception("写入词典失败")
                reset()
                return dest.length()
            } catch (e: Exception) {
                tmp.delete()
                throw e
            }
        }

        private fun tryCopyAsset(context: Context, assetPath: String, dest: File) {
            try {
                dest.parentFile?.mkdirs()
                context.assets.open(assetPath).use { input ->
                    dest.outputStream().use { input.copyTo(it) }
                }
            } catch (e: Exception) {
                // 精简词表可能不存在（assets 未放置），不致命
            }
        }
    }
}

