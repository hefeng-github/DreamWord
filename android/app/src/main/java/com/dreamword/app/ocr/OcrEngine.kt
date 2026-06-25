package com.dreamword.app.ocr

import android.content.Context
import android.graphics.Bitmap
import com.dreamword.app.data.OcrWord

/**
 * OCR 引擎抽象。
 *
 * PC 版用 PaddleOCR（Python，PP-OCRv6）。安卓本地 OCR 采用 PP-OCRv6 small onnx 方案：
 *   - 模型取自 MaaCommonAssets（det.onnx / rec.onnx / keys.txt），由 CI 编译时下载到
 *     app/src/main/assets/models/（不入仓库，本地开发手动 curl 放入）。
 *   - 推理用 onnxruntime-android；DB 检测后处理 + CTC 识别解码在 OnnxOcrEngineImpl 自实现。
 *
 * 抽象出接口便于在引擎未就绪（模型缺失/native 加载失败）时返回 NoOp，保证 app 不崩溃。
 */
interface OcrEngine {
    /** 是否已加载模型，可以识别 */
    fun isReady(): Boolean

    /**
     * 识别图片中的所有单词，返回带坐标的结果
     * @param bitmap 输入图
     * @return 识别出的词（含 bbox 和 confidence）
     */
    fun recognize(bitmap: Bitmap): List<OcrWord>

    /** 释放 native 资源 */
    fun release()

    companion object {
        /**
         * 创建引擎实例。返回 OnnxOcrEngineImpl；模型/native 加载失败时返回 NoOpOcrEngine，
         * 前端通过 isReady()/errorMessage() 提示用户。
         */
        fun create(context: Context): OcrEngine {
            return try {
                OnnxOcrEngineImpl(context)
            } catch (e: Throwable) {
                // 构造异常兜底（真正的模型/native 加载错误在首次 ensureEngine 时捕获）
                NoOpOcrEngine(e)
            }
        }
    }
}

/** 未加载模型时的占位实现——保证 app 不崩溃，前端会显示提示 */
class NoOpOcrEngine(private val error: Throwable) : OcrEngine {
    override fun isReady() = false
    override fun recognize(bitmap: Bitmap): List<OcrWord> = emptyList()
    override fun release() {}
    fun errorMessage(): String = "OCR 引擎未就绪：${error.message ?: error.javaClass.simpleName}"
}
