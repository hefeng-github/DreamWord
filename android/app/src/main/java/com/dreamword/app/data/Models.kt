package com.dreamword.app.data

/**
 * 单词数据模型（移植自 PC 版 src/core/__init__.py 的 WordEntry / LookupResult / OCRResult）
 */

/** 单词条目（音标 / 释义 / 例句 / 词形）—— 对应 Python WordEntry */
data class WordEntry(
    val headword: String,
    val phonetics: MutableList<String> = mutableListOf(),
    val definitions: MutableList<String> = mutableListOf(),
    val chineseDefinitions: MutableList<String> = mutableListOf(),
    val examples: MutableList<String> = mutableListOf(),
    val baseForm: String? = null,
    val pos: String? = null
)

/** OCR 识别出的单个词——对应 Python OCRResult */
data class OcrWord(
    val text: String,
    /** 4 个角点 [[x1,y1],[x2,y2],[x3,y3],[x4,y4]] */
    val bbox: List<List<Int>>,
    val confidence: Float,
    val center: Pair<Float, Float>
)

/** 查词结果——对应 Python LookupResult */
data class LookupResult(
    val success: Boolean,
    val word: String,
    val phonetic: String = "N/A",
    val definitions: List<String> = emptyList(),
    val baseForm: String? = null,
    val pos: String? = null,
    val examples: List<String> = emptyList(),
    val message: String? = null,
    val allEntries: List<Map<String, Any?>> = emptyList()
)

/** 标注图上的一个注记（拍照查词书写用）——对应 Python Annotation */
data class Annotation(
    val text: String,
    val x: Float,
    val y: Float,
    val isPhonetic: Boolean
)
