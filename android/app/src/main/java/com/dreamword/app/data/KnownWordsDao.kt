package com.dreamword.app.data

import android.content.ContentValues
import android.content.Context
import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteOpenHelper

/**
 * 已知单词库（移植自 PC 版 auto_lookup.py:62-170 的 KnownWordsDatabase）
 *
 * 表结构与 PC 版完全一致（known_words: id / word / add_time），
 * 因此 PC 版导出的 known_words.db 可以直接拷贝到安卓上读取/合并。
 * 单词统一小写存储（与 PC 版一致，INSERT OR IGNORE 去重）。
 *
 * DB_VERSION=2：表结构未变，仅把版本号机制落实到位（为未来加列迁移预留）。
 * v1→v2 无 schema 变化，onUpgrade 直接落地。
 */
class KnownWordsDao(context: Context) : SQLiteOpenHelper(
    context, DB_NAME, null, DB_VERSION
) {

    init { writableDatabase } // 触发建表

    override fun onCreate(db: SQLiteDatabase) {
        db.execSQL(KNOWN_WORDS_SCHEMA)
    }

    override fun onUpgrade(db: SQLiteDatabase, oldVersion: Int, newVersion: Int) {
        // v1→v2：表结构无变化（仅引入版本号机制），无需迁移
        if (oldVersion <= 1 && newVersion >= 2) {
            // 已由 onCreate 建表，此处 no-op
        }
    }

    fun addWord(word: String) {
        val cv = ContentValues().apply { put("word", word.trim().lowercase()) }
        writableDatabase.insertWithOnConflict(
            "known_words", null, cv, SQLiteDatabase.CONFLICT_IGNORE
        )
    }

    fun addWords(words: List<String>) {
        val db = writableDatabase
        db.beginTransaction()
        try {
            for (w in words) {
                val cv = ContentValues().apply { put("word", w.trim().lowercase()) }
                db.insertWithOnConflict(
                    "known_words", null, cv, SQLiteDatabase.CONFLICT_IGNORE
                )
            }
            db.setTransactionSuccessful()
        } finally {
            db.endTransaction()
        }
    }

    fun isKnown(word: String): Boolean = readableDatabase
        .rawQuery("SELECT 1 FROM known_words WHERE word = ? LIMIT 1", arrayOf(word.trim().lowercase()))
        .use { it.moveToFirst() }

    fun removeWord(word: String) {
        writableDatabase.delete(
            "known_words", "word = ?", arrayOf(word.trim().lowercase())
        )
    }

    fun getAllWords(): List<String> = readableDatabase
        .rawQuery("SELECT word FROM known_words ORDER BY add_time DESC", null)
        .use { c ->
            val out = ArrayList<String>(c.count)
            while (c.moveToNext()) out.add(c.getString(0))
            out
        }

    fun count(): Int = readableDatabase
        .rawQuery("SELECT COUNT(*) FROM known_words", null)
        .use { c -> if (c.moveToFirst()) c.getInt(0) else 0 }

    companion object {
        private const val DB_NAME = "known_words.db"
        private const val DB_VERSION = 2

        // 已会词库表结构（PC/Android 共用同一份定义，见 src/modules/auto_lookup.py 的 KNOWN_WORDS_SCHEMA）
        private const val KNOWN_WORDS_SCHEMA = """
            CREATE TABLE IF NOT EXISTS known_words (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                word TEXT UNIQUE NOT NULL,
                add_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """.trimIndent()
    }
}
