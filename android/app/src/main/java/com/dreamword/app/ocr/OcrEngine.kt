package com.dreamword.app.ocr

import android.content.Context
import android.graphics.Bitmap
import com.dreamword.app.data.OcrWord

/**
 * OCR 引擎封装
 *
 * PC 版用 PaddleOCR（Python）。安卓本地 OCR 采用 RapidOCR PP-OCRv4 onnx 方案，
 * 模型取自 MaaCommonAssets（det/rec/cls + 字典），推理用 onnxruntime-android。
 *
 * 由于 RapidOCR 的集成方式有两种（见 app/build.gradle.kts 注释），此处抽象出接口，
 * 并提供两套实现切换点：
 *   - RapidOcrEngineImpl：基于 RapidOcrAndroidOnnx 源码模块
 *   - MavenOcrEngineImpl：基于 io.github.mymonstercat:rapidocr-onnx-platform
 *
 * 阶段1的验证目标：让 create() 返回的实例能对一张试卷图返回单词+坐标。
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
         * 创建引擎实例。
         *
         * ★ 阶段1 集成指引 ★
         * 这里默认返回 RapidOcrEngineImpl。请按以下步骤接入模型：
         *
         * 【第 1 步：放置模型】
         *   从 https://github.com/MaaXYZ/MaaCommonAssets/tree/main/OCR/ppocr_v6/small
         *   下载 3 个文件，放到 app/src/main/assets/models/：
         *     - det.onnx   (PP-OCRv6 small 文字检测)
         *     - rec.onnx   (PP-OCRv6 small 文字识别)
         *     - keys.txt   (字符表)
         *   （用 small 档：总 30MB，适合安卓；medium 档 138MB 太重）
         *
         * 【第 2 步：接入 RapidOCR 库（二选一）】
         *
         * 【方式 A：源码模块（推荐，体积可控）】
         *   1. git clone https://github.com/RapidAI/RapidOcrAndroidOnnx
         *      放到 android/RapidOcrAndroidOnnx/
         *   2. settings.gradle.kts 加 include(":RapidOcrAndroidOnnx")
         *   3. app/build.gradle.kts 加 implementation(project(":RapidOcrAndroidOnnx"))
         *   4. RapidOcrEngineImpl 里 new RapidOCR() 即自动加载 assets/models
         *
         * 【方式 B：Maven 依赖（开箱即用）】
         *   1. app/build.gradle.kts 取消注释：
         *      implementation("io.github.mymonstercat:rapidocr-onnx-platform:<latest>")
         *   2. 注意：Maven 包默认自带 PP-OCRv4 模型；若要用上面的 v6 模型，
         *      需把 RapidOCR 升级到支持 v6 的版本，或用方式 A 自带 v6 assets。
         *
         * 模型兼容性：MaaCommonAssets 的 ppocr_v6 与 RapidOCR 同源（均来自
         * PaddleOCR 官方），字典格式一致，可互换。v6 比 v4 准确率更高。
         */
        fun create(context: Context): OcrEngine {
            return try {
                RapidOcrEngineImpl(context)
            } catch (e: Throwable) {
                // 模型未就绪时返回 NoOp，前端会提示
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
