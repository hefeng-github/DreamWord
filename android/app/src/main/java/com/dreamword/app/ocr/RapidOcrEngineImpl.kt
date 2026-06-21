package com.dreamword.app.ocr

import android.content.Context
import android.graphics.Bitmap
import com.dreamword.app.data.OcrWord

/**
 * 基于 RapidOcrAndroidOnnx 的 OCR 实现（PP-OCRv6 small 模型）
 *
 * ★ 模型来源 ★：https://github.com/MaaXYZ/MaaCommonAssets/tree/main/OCR/ppocr_v6/small
 *   把这 3 个文件放到 app/src/main/assets/models/ 下：
 *     - det.onnx   (9.4MB，文字检测，PP-OCRv6_small_det)
 *     - rec.onnx   (20MB，文字识别，PP-OCRv6_small_rec)
 *     - keys.txt   (73KB，识别字符表 —— 注意文件名就是 keys.txt，非 ppocr_keys_v1.txt)
 *   该套模型无 cls（方向分类），纯 det+rec 两段式；支持简繁中文/英文/日文。
 *
 * ★ 依赖接入 ★（二选一，详见 app/build.gradle.kts 注释）：
 *   方式 A（推荐）：RapidOcrAndroidOnnx 源码模块
 *   方式 B：io.github.mymonstercat:rapidocr-onnx-platform Maven 依赖
 *
 * ★ 版本注意 ★：RapidOCR 3.x 支持 PP-OCRv6；若用旧版默认带 v4 模型，
 *   替换成 v6 时需确认 RapidOCR 版本支持 v6 的预处理参数（DB 后处理 / CTC 解码）。
 *
 * RapidOCR 的 Java API 通常长这样：
 *   RapidOCR ocr = new RapidOCR(context);          // 自动从 assets/models 加载
 *   OcrResult result = ocr.detect(bitmap);          // 同步识别
 *   for (OcrResult.ResultItem item : result.items) {
 *       item.text;        // 文字
 *       item.box;         // 4 点坐标 [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
 *       item.score;       // 置信度
 *   }
 *
 * 接入后把下方 TODO 处替换为实际调用。
 */
class RapidOcrEngineImpl(
    private val context: Context
) : OcrEngine {

    // TODO: 接入 RapidOCR 后，把下行改为实际引用
    // private val rapid: Any? = null  // RapidOCR 实例
    private var released = false

    override fun isReady(): Boolean = false // TODO: rapid != null && !released

    override fun recognize(bitmap: Bitmap): List<OcrWord> {
        // TODO: 接入 RapidOCR 后实现：
        // val result = rapid.detect(bitmap)
        // return result.items.map { item ->
        //     OcrWord(
        //         text = item.text.trim(),
        //         bbox = item.box.map { p -> listOf(p.x.toInt(), p.y.toInt()) },
        //         confidence = item.score,
        //         center = centerOf(item.box)
        //     )
        // }.filter { isEnglishWord(it.text) }
        return emptyList()
    }

    override fun release() {
        released = true
        // TODO: rapid.release()
    }

    /** 取 bbox 的中心点 */
    private fun centerOf(box: List<List<Int>>): Pair<Float, Float> {
        if (box.size < 4) return 0f to 0f
        val xs = box.map { it[0] }
        val ys = box.map { it[1] }
        return ((xs.min() + xs.max()) / 2f) to ((ys.min() + ys.max()) / 2f)
    }

    /** 与 PC 版 filter_english_words 一致：只保留英文单词 */
    private fun isEnglishWord(text: String): Boolean {
        val t = text.trim()
        if (t.length < 2) return false
        return t.matches(Regex("""[a-zA-Z]+"""))
    }
}
