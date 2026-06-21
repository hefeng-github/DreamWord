package com.dreamword.app.dict

import android.content.Context
import android.database.sqlite.SQLiteDatabase
import com.dreamword.app.data.WordEntry
import java.io.File

/**
 * 词典数据访问（移植自 PC 版 word_lookup.py 的 DB 部分）
 *
 * PC 版直接用 sqlite3 读 databases/word_details.db，表结构：mdx(entry TEXT, paraphrase TEXT)
 * 安卓上策略：
 *  - 完整词典（441MB）从外部存储 / 下载目录打开（避免打进 APK）
 *  - 若外部没有，回退到 assets 里内置的精简词表（assets/dict/word_details_mini.db）
 *  - 只读打开（SQLiteDatabase.OPEN_READONLY）
 *
 * 所有查询都在 try/finally 关闭游标和连接，避免在大量并发查词时锁库。
 */
class DictRepository private constructor(
    private val dbFile: File
) {

    fun isOpenable(): Boolean = dbFile.exists() && dbFile.canRead()

    /** 对应 Python word_exists：精确匹配 entry */
    fun wordExists(word: String): Boolean = withDb { db ->
        db.rawQuery(
            "SELECT entry FROM mdx WHERE entry = ? LIMIT 1",
            arrayOf(word)
        ).use { it.moveToFirst() } ?: false
    }

    /** 对应 Python get_entry_html：取第一条 paraphrase */
    fun getEntryHtml(word: String): String? = withDb { db ->
        db.rawQuery(
            "SELECT paraphrase FROM mdx WHERE entry = ? LIMIT 1",
            arrayOf(word)
        ).use { c ->
            if (c.moveToFirst()) c.getString(0) else null
        }
    }

    /** 对应 Python get_all_entries_html：取该词所有 paraphrase（一词多义） */
    fun getAllEntriesHtml(word: String): List<String> = withDb { db ->
        db.rawQuery(
            "SELECT paraphrase FROM mdx WHERE entry = ?",
            arrayOf(word)
        ).use { c ->
            val out = ArrayList<String>(c.count)
            while (c.moveToNext()) out.add(c.getString(0))
            out
        }
    }

    /** 对应 Python get_word_entries：HTML → List<WordEntry>（一词多义展开为多个 entry） */
    fun getWordEntries(word: String): List<WordEntry> {
        val htmls = getAllEntriesHtml(word)
        if (htmls.isEmpty()) return emptyList()
        val out = ArrayList<WordEntry>(htmls.size)
        for (html in htmls) out.addAll(MdxParser.parse(html))
        return out
    }

    private inline fun <T> withDb(block: (SQLiteDatabase) -> T): T {
        // 完整词典 441MB，每次查词都打开会慢；调用方应持有 DictRepository 单例，
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
     */
    fun openCached(): CachedDict = CachedDict(SQLiteDatabase.openDatabase(
        dbFile.absolutePath, null,
        SQLiteDatabase.OPEN_READONLY or SQLiteDatabase.NO_LOCALIZED_COLLATORS
    ))

    /** 带缓存的连接包装 */
    class CachedDict internal constructor(internal val db: SQLiteDatabase) : AutoCloseable {
        fun wordExists(word: String): Boolean = db
            .rawQuery("SELECT entry FROM mdx WHERE entry = ? LIMIT 1", arrayOf(word))
            .use { it.moveToFirst() }
        fun getAllEntriesHtml(word: String): List<String> = db
            .rawQuery("SELECT paraphrase FROM mdx WHERE entry = ?", arrayOf(word))
            .use { c -> ArrayList<String>(c.count).apply { while (c.moveToNext()) add(c.getString(0)) } }
        fun getWordEntries(word: String): List<WordEntry> {
            val out = ArrayList<WordEntry>()
            for (html in getAllEntriesHtml(word)) out.addAll(MdxParser.parse(html))
            return out
        }
        override fun close() = db.close()
    }

    companion object {
        @Volatile private var instance: DictRepository? = null

        /**
         * 解析词典位置：
         *  1) 外部下载的完整词典（用户通过设置下载的 441MB）
         *  2) 内置精简词表（assets 解包到 filesDir）
         * 都没有则返回 null（前端会提示去下载）
         */
        fun resolve(context: Context): DictRepository? {
            instance?.let { return it }

            // 外部完整词典：filesDir/dict/word_details.db
            val external = File(context.filesDir, "dict/word_details.db")
            val target = when {
                external.exists() && external.canRead() -> external
                else -> {
                    // 内置精简词表：首次启动从 assets 拷贝到 filesDir
                    val mini = File(context.filesDir, "dict/word_details_mini.db")
                    if (!mini.exists()) {
                        tryCopyAsset(context, "dict/word_details_mini.db", mini)
                    }
                    if (mini.exists() && mini.canRead()) mini else return null
                }
            }
            return DictRepository(target).also { instance = it }
        }

        /** 当用户下载完完整词典后，重置单例使其重新解析 */
        fun reset() { instance = null }

        /**
         * 导入用户从本地选择的词典文件（.db）。
         * 把 Uri 指向的 SQLite 拷贝到 filesDir/dict/word_details.db，
         * 拷贝成功后 reset()，下次查询自动用新词典。
         *
         * @return 导入结果：成功返回文件大小，失败抛异常
         */
        fun importDictionary(context: Context, uri: android.net.Uri): Long {
            val dest = File(context.filesDir, "dict/word_details.db")
            dest.parentFile?.mkdirs()
            // 先写临时文件，校验通过后替换，避免拷贝中途崩溃导致词典损坏
            val tmp = File(context.filesDir, "dict/word_details.db.tmp")
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
                // 替换正式文件
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
