package com.dreamword.app.dict

import android.graphics.Bitmap
import com.dreamword.app.bridge.AnnotationRenderer
import com.dreamword.app.data.OcrWord
import com.dreamword.app.ocr.OcrEngine
import org.json.JSONArray
import org.json.JSONObject

/**
 * 拍照查词书写管线（从 NativeBridge.autoLookup 抽出，便于复用/测试）。
 *
 * 流程：裁剪 → OCR → 已会词合并 → 生词过滤 → 逐词查释义 → 画标注图。
 * OCR 引擎与词典查询均由外部注入；词典查词用 WordLookup（内部 CachedDict 长连接，
 * 避免对 441MB 词典反复 open/close）。
 *
 * 已会词集合统一小写比较；生词查询走大小写兜底（WordLookup 内部已处理）。
 * 与 PC 版 filter_english_words 一致的停用词/长度过滤在 OCR 引擎层完成。
 */
class OcrLookupPipeline(
    private val ocr: OcrEngine,
    private val lookup: WordLookup,
    private val knownWordsSource: () -> List<String>
) {
    /** 单条标注（word + 音标 + 释义 + bbox），用于回传前端 + 渲染 */
    data class Annotation(
        val word: String,
        val phonetic: String,
        val definition: String,
        val bbox: List<List<Int>>
    )

    /** 管线运行结果 */
    data class Result(
        val annotatedBitmap: Bitmap,
        val annotations: List<Annotation>
    )

    /**
     * @param bitmap 原始图（拍照/上传）
     * @param crop 可选裁剪框 {x,y,w,h}，null 表示不裁剪
     * @param knownWordsFromCaller 调用方（前端）传入的已会词列表
     */
    fun run(
        bitmap: Bitmap,
        crop: Crop? = null,
        knownWordsFromCaller: List<String> = emptyList()
    ): Result {
        // 1. 裁剪
        var image = bitmap
        if (crop != null && crop.w > 0 && crop.h > 0 &&
            crop.x + crop.w <= image.width && crop.y + crop.h <= image.height
        ) {
            image = Bitmap.createBitmap(image, crop.x, crop.y, crop.w, crop.h)
        }

        // 2. OCR
        val allWords = ocr.recognize(image)

        // 3. 已会词集合（入参 + 本地库），统一小写
        val knownSet = HashSet<String>()
        knownWordsFromCaller.mapTo(knownSet) { it.trim().lowercase() }
        knownWordsSource().mapTo(knownSet) { it.trim().lowercase() }

        // 4. 生词（过滤已会）
        val newWords = allWords.filter { it.text.trim().lowercase() !in knownSet }

        // 5. 逐词查释义
        val annotations = ArrayList<Annotation>(newWords.size)
        for (w in newWords) {
            val r = lookup.lookup(w.text, "")
            if (r.success) {
                annotations.add(Annotation(
                    word = r.word,
                    phonetic = r.phonetic,
                    definition = r.definitions.firstOrNull() ?: "",
                    bbox = w.bbox
                ))
            }
        }

        // 6. 画标注图
        val annotated = AnnotationRenderer.render(image, newWords, annotationsToJson(annotations))
        return Result(annotatedBitmap = annotated, annotations = annotations)
    }

    /** 裁剪框 */
    data class Crop(val x: Int, val y: Int, val w: Int, val h: Int)

    private fun annotationsToJson(annotations: List<Annotation>): JSONArray = JSONArray().apply {
        for (a in annotations) {
            put(JSONObject()
                .put("word", a.word)
                .put("phonetic", a.phonetic)
                .put("definition", a.definition)
                .put("bbox", JSONArray(a.bbox.map { JSONArray(it) }))
            )
        }
    }
}
