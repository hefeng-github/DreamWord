package com.dreamword.app.ocr

import android.content.Context
import android.graphics.Bitmap
import com.dreamword.app.data.OcrWord

/**
 * 基于 RapidOcrAndroidOnnx 的 OCR 实现（PP-OCRv3，离线，APK 自带模型）
 *
 * 库的 aar 由 GitHub Actions 编译前从 RapidOcrAndroidOnnx release 自动下载到
 * app/libs/（见 .github/workflows/build-android.yml）。aar 内部打包了模型文件
 * （ch_PP-OCRv3_det/cls/rec + ppocr_keys_v1.txt），OcrEngine 构造时自动从 assets 加载。
 *
 * API（来自 com.benjaminwan.ocrlibrary）：
 *   val engine = OcrEngine(context)          // 自动加载模型
 *   val result = engine.detect(input, output, maxSideLen)
 *   result.textBlocks: List<TextBlock>
 *     - textBlock.boxPoint: List<Point{x,y}>  (4 个角点)
 *     - textBlock.text: String
 *     - textBlock.boxScore: Float
 *
 * 注意：com.benjaminwan.ocrlibrary.OcrEngine 在 init 块里 System.loadLibrary
 * 并加载 assets 模型，若 aar 未放置会抛 UnsatisfiedLinkError，故延迟到首次
 * recognize 时初始化并兜底。
 */
class RapidOcrEngineImpl(
    context: Context
) : OcrEngine {

    private val appContext = context.applicationContext
    private var engine: com.benjaminwan.ocrlibrary.OcrEngine? = null
    @Volatile private var triedInit = false

    private fun ensureEngine(): com.benjaminwan.ocrlibrary.OcrEngine? {
        if (triedInit) return engine
        synchronized(this) {
            if (triedInit) return engine
            triedInit = true
            try {
                engine = com.benjaminwan.ocrlibrary.OcrEngine(appContext)
            } catch (e: Throwable) {
                // aar 未就绪 / 模型缺失 / native 库加载失败 → engine 保持 null
            }
            return engine
        }
    }

    override fun isReady(): Boolean = ensureEngine() != null

    override fun recognize(bitmap: Bitmap): List<OcrWord> {
        val eng = ensureEngine() ?: return emptyList()
        return try {
            // detect 需要一个可变的 output bitmap（库会在上面画检测框）
            val output = Bitmap.createBitmap(
                bitmap.width, bitmap.height, Bitmap.Config.ARGB_8888
            )
            // maxSideLen：长边缩放到此值（加速），0 表示不缩放。
            // 试卷图通常较大，限制到 1024 平衡速度与精度。
            val maxSideLen = if (maxOf(bitmap.width, bitmap.height) > 1024) 1024 else 0
            val result = eng.detect(bitmap, output, maxSideLen)

            result.textBlocks.mapNotNull { block ->
                val text = block.text.trim()
                if (!isEnglishWord(text)) return@mapNotNull null
                val box = block.boxPoint
                if (box.size < 4) return@mapNotNull null
                // 4 个角点 → [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]，与 PC 版 bbox 格式一致
                val bbox = box.take(4).map { listOf(it.x, it.y) }
                OcrWord(
                    text = text,
                    bbox = bbox,
                    confidence = block.boxScore,
                    center = centerOf(box)
                )
            }
        } catch (e: Throwable) {
            emptyList()
        }
    }

    override fun release() {
        engine = null
        triedInit = false
    }

    /** 取角点的中心点 */
    private fun centerOf(box: List<com.benjaminwan.ocrlibrary.Point>): Pair<Float, Float> {
        if (box.isEmpty()) return 0f to 0f
        val xs = box.map { it.x.toFloat() }
        val ys = box.map { it.y.toFloat() }
        return ((xs.min() + xs.max()) / 2f) to ((ys.min() + ys.max()) / 2f)
    }

    /** 与 PC 版 filter_english_words 一致：只保留英文单词（长度 >= 2） */
    private fun isEnglishWord(text: String): Boolean {
        val t = text.trim()
        if (t.length < 2) return false
        return t.matches(Regex("""[a-zA-Z]+"""))
    }
}
