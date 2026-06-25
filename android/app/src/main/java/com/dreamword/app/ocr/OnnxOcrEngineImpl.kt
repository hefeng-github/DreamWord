package com.dreamword.app.ocr

import android.content.Context
import android.graphics.Bitmap
import ai.onnxruntime.OnnxTensor
import ai.onnxruntime.OrtEnvironment
import ai.onnxruntime.OrtSession
import com.dreamword.app.data.OcrWord
import java.io.File
import java.util.Locale

/**
 * 基于 onnxruntime-android 的 PP-OCRv6 自研 OCR 管线（离线，APK 自带模型）。
 *
 * 模型（det.onnx / rec.onnx / keys.txt）位于 assets/models/，由 CI 编译时从
 * MaaCommonAssets 下载（不入仓库，本地开发手动 curl 放入，见 assets/models/README.txt）。
 * PP-OCRv6 small 是 det+rec 两段式（无 cls，试卷文字基本正向，省略方向分类）。
 *
 * 管线：
 *  1. 检测（det，DB-based）：
 *     - 预处理：长边缩放到 ≤1024（保持比例），pad 到 32 的倍数，
 *       归一化 (x/255 - mean)/std，mean=[.485,.456,.406] std=[.229,.224,.225]
 *     - 推理 → 概率图
 *     - DB 后处理：阈值 0.3 二值化 → 找轮廓 → unclip（膨胀）→ minAreaRect → 4 角点；
 *       按 score>0.6 过滤
 *  2. 识别（rec，CRNN/CTC）：
 *     - 每框裁剪 → 缩放高度到 48（v6 关键！v3 是 32）保持比例 → pad 到等宽批次 → 归一化
 *     - 推理 → CTC greedy 解码 → keys.txt 映射去 blank/重复
 *  3. 英文过滤（与 PC 版 filter_english_words 一致）：
 *     对每个文本块用 \b[a-zA-Z]+\b 逐词提取，长度>1 且非停用词，复用该块 bbox/center。
 *
 * 移植参考：RapidOCR C++ core（v6 默认）+ PaddleOCR C++ deploy。
 * 关键常量：det maxSideLen 1024、DB thresh 0.3 boxThresh 0.6 unclip ratio 1.6、rec height 48。
 *
 * 延迟初始化：首次 recognize/isReady 时从 assets 拷模型到 filesDir + 建 OrtSession；
 * 失败则 engine 保持 null，isReady() 返回 false，前端提示（不崩溃）。
 */
class OnnxOcrEngineImpl(
    context: Context
) : OcrEngine {

    private val appContext = context.applicationContext
    private val env: OrtEnvironment = OrtEnvironment.getEnvironment()

    @Volatile private var detSession: OrtSession? = null
    @Volatile private var recSession: OrtSession? = null
    @Volatile private var keys: List<String> = emptyList()
    @Volatile private var triedInit = false

    private fun ensureEngine(): Boolean {
        if (triedInit) return detSession != null
        synchronized(this) {
            if (triedInit) return detSession != null
            triedInit = true
            try {
                val detFile = copyAssetToFile("models/det.onnx", "det.onnx")
                val recFile = copyAssetToFile("models/rec.onnx", "rec.onnx")
                keys = copyAssetToFile("models/keys.txt", "keys.txt")
                    .readBytes().toString(Charsets.UTF_8)
                    .split("\n").map { it.trim('\r', ' ') }
                detSession = env.createSession(detFile.absolutePath, OrtSession.SessionOptions())
                recSession = env.createSession(recFile.absolutePath, OrtSession.SessionOptions())
            } catch (e: Throwable) {
                // 模型缺失 / native 库加载失败 → session 保持 null
            }
            return detSession != null
        }
    }

    override fun isReady(): Boolean = ensureEngine()

    override fun recognize(bitmap: Bitmap): List<OcrWord> {
        val det = detSession ?: if (!ensureEngine()) return emptyList() else detSession ?: return emptyList()
        val rec = recSession ?: return emptyList()
        if (keys.isEmpty()) return emptyList()
        return try {
            // 1. 检测：得到文本框（原图坐标，4 角点 + 均值 score）
            val boxes = detect(bitmap, det)
            if (boxes.isEmpty()) return emptyList()

            // 2. 识别：每框裁剪 → rec → 文本
            val results = ArrayList<OcrWord>()
            for (box in boxes) {
                val cropped = warpPerspective(bitmap, box.corners)
                if (cropped == null || cropped.width < 4 || cropped.height < 4) continue
                val text = recognizeText(cropped, rec)
                if (text.isBlank()) continue
                // 3. 英文过滤（与 PC 一致：逐词提取 + 停用词），每个词复用该框 bbox/center
                for (word in extractEnglishWords(text)) {
                    results.add(OcrWord(
                        text = word,
                        bbox = box.corners.map { listOf(it.first, it.second) },
                        confidence = box.score,
                        center = centerOf(box.corners)
                    ))
                }
            }
            // 按 y 再按 x 排序，便于阅读
            results.sortedWith(compareBy({ it.center.second.toInt() / 10 }, { it.center.first }))
        } catch (e: Throwable) {
            emptyList()
        }
    }

    override fun release() {
        synchronized(this) {
            try { detSession?.close() } catch (_: Throwable) {}
            try { recSession?.close() } catch (_: Throwable) {}
            detSession = null
            recSession = null
            triedInit = false
        }
    }

    // ============ 检测（det，DB）============

    private data class TextBox(val corners: List<Pair<Int, Int>>, val score: Float)

    private fun detect(bitmap: Bitmap, session: OrtSession): List<TextBox> {
        val maxSideLen = 1024
        val srcW = bitmap.width
        val srcH = bitmap.height
        val ratio = maxSideLen.toFloat() / maxOf(srcW, srcH).toFloat()
        val rsW = (srcW * ratio).toInt().coerceAtLeast(1)
        val rsH = (srcH * ratio).toInt().coerceAtLeast(1)
        // pad 到 32 的倍数
        val padW = roundUp(rsW, 32)
        val padH = roundUp(rsH, 32)

        // 缩放 + pad 到 [padH, padW, 3]，归一化
        val scaled = Bitmap.createScaledBitmap(bitmap, rsW, rsH, true)
        val inputData = FloatArray(1 * padH * padW * 3)
        val px = IntArray(rsW * rsH)
        scaled.getPixels(px, 0, rsW, 0, 0, rsW, rsH)
        for (y in 0 until padH) {
            for (x in 0 until padW) {
                val inRange = y < rsH && x < rsW
                val (r, g, b) = if (inRange) {
                    val c = px[y * rsW + x]
                    Triple((c shr 16 and 0xFF), (c shr 8 and 0xFF), (c and 0xFF))
                } else Triple(0, 0, 0)
                // CHW 布局：[c][y][x]
                inputData[0 * padH * padW + y * padW + x] = ((r / 255f - 0.485f) / 0.229f)
                inputData[1 * padH * padW + y * padW + x] = ((g / 255f - 0.456f) / 0.224f)
                inputData[2 * padH * padW + y * padW + x] = ((b / 255f - 0.406f) / 0.225f)
            }
        }
        if (scaled !== bitmap) scaled.recycle()

        val shape = longArrayOf(1, 3, padH.toLong(), padW.toLong())
        val input = OnnxTensor.createTensor(env, inputData, shape)
        // 概率图 [1,1,H,W] → 扁平 FloatArray[H*W]（row-major）
        val out = FloatArray(padH * padW)
        session.run(mapOf(inputName(session) to input)).use { run ->
            (run[0] as ai.onnxruntime.OnnxTensor).floatBuffer.get(out)
        }
        input.close()

        // DB 后处理：二值化 → 找轮廓 → unclip → minAreaRect
        val thresh = 0.3f
        val binary = BitMatrix(padW, padH)
        for (i in out.indices) binary.data[i] = out[i] > thresh

        val contours = findContours(binary)
        val boxes = ArrayList<TextBox>()
        for (contour in contours) {
            if (contour.size < 4) continue
            val score = meanScoreOnBox(out, contour, padW, padH)
            if (score < 0.6f) continue
            val rect = minAreaRect(contour)
            // unclip：按长边膨胀 ratio 倍
            val expanded = unclip(rect, ratio = 1.6f)
            if (expanded.size < 4) continue
            // 映射回原图坐标
            val corners = expanded.map {
                val x = (it.first / ratio).coerceIn(0f, srcW - 1f).toInt()
                val y = (it.second / ratio).coerceIn(0f, srcH - 1f).toInt()
                x to y
            }
            // 面积过小丢弃
            val area = polygonArea(corners)
            if (area < 8f) continue
            boxes.add(TextBox(corners.take(4), score))
        }
        return boxes
    }

    // ============ 识别（rec，CTC）============

    private fun recognizeText(cropped: Bitmap, session: OrtSession): String {
        val recHeight = 48  // PP-OCRv6 关键：识别图高度固定 48（v3 是 32）
        val ratio = recHeight.toFloat() / cropped.height
        val recW = (cropped.width * ratio).toInt().coerceAtLeast(1)
        val scaled = Bitmap.createScaledBitmap(cropped, recW, recHeight, true)
        // pad 宽度到 4 的倍数（rec 输入需对齐）
        val imgW = roundUp(recW, 4)
        val inputData = FloatArray(1 * recHeight * imgW * 3)
        val px = IntArray(recW * recHeight)
        scaled.getPixels(px, 0, recW, 0, 0, recW, recHeight)
        for (y in 0 until recHeight) {
            for (x in 0 until imgW) {
                val (r, g, b) = if (x < recW) {
                    val c = px[y * recW + x]
                    Triple((c shr 16 and 0xFF), (c shr 8 and 0xFF), (c and 0xFF))
                } else Triple(0, 0, 0)
                inputData[0 * recHeight * imgW + y * imgW + x] = ((r / 255f - 0.5f) / 0.5f)
                inputData[1 * recHeight * imgW + y * imgW + x] = ((g / 255f - 0.5f) / 0.5f)
                inputData[2 * recHeight * imgW + y * imgW + x] = ((b / 255f - 0.5f) / 0.5f)
            }
        }
        if (scaled !== cropped) scaled.recycle()

        val shape = longArrayOf(1, 3, recHeight.toLong(), imgW.toLong())
        val input = OnnxTensor.createTensor(env, inputData, shape)
        // CTC 输出 [1, T, num_classes] → 扁平 FloatArray[T*C]（row-major: t 行 c 列）
        val tCount: Int
        val cCount: Int
        val flatOut: FloatArray
        session.run(mapOf(inputName(session) to input)).use { run ->
            val tensor = run[0] as ai.onnxruntime.OnnxTensor
            val sh = tensor.info.shape  // [1, T, C]
            tCount = sh[1].toInt()
            cCount = sh[2].toInt()
            flatOut = FloatArray(tCount * cCount)
            tensor.floatBuffer.get(flatOut)
        }
        input.close()

        // CTC greedy：每时间步取 argmax → 合并重复 → 去 blank（index 0）
        val sb = StringBuilder()
        var prev = -1
        for (t in 0 until tCount) {
            val base = t * cCount
            var maxIdx = 0
            var maxVal = flatOut[base]
            for (i in 1 until cCount) {
                val v = flatOut[base + i]
                if (v > maxVal) { maxVal = v; maxIdx = i }
            }
            if (maxIdx != 0 && maxIdx != prev) {
                if (maxIdx - 1 < keys.size) sb.append(keys[maxIdx - 1])
            }
            prev = maxIdx
        }
        return sb.toString().trim()
    }

    // ============ 几何工具 ============

    /** 透视校正：把任意 4 角点框校正为水平裁剪图（简化版：用外接矩形 + 不做透视，
     *  对试卷这类近正向的文字够用；若框倾斜严重可后续补透视变换） */
    private fun warpPerspective(bitmap: Bitmap, corners: List<Pair<Int, Int>>): Bitmap? {
        if (corners.size < 4) return null
        val xs = corners.map { it.first }
        val ys = corners.map { it.second }
        val left = xs.min().coerceAtLeast(0)
        val top = ys.min().coerceAtLeast(0)
        val right = xs.max().coerceAtMost(bitmap.width)
        val bottom = ys.max().coerceAtMost(bitmap.height)
        val w = right - left
        val h = bottom - top
        if (w < 4 || h < 4) return null
        return try {
            Bitmap.createBitmap(bitmap, left, top, w, h)
        } catch (e: Throwable) { null }
    }

    private fun centerOf(corners: List<Pair<Int, Int>>): Pair<Float, Float> {
        if (corners.isEmpty()) return 0f to 0f
        val xs = corners.map { it.first.toFloat() }
        val ys = corners.map { it.second.toFloat() }
        return ((xs.min() + xs.max()) / 2f) to ((ys.min() + ys.max()) / 2f)
    }

    private fun polygonArea(pts: List<Pair<Int, Int>>): Float {
        var s = 0f
        for (i in pts.indices) {
            val j = (i + 1) % pts.size
            s += pts[i].first * pts[j].second - pts[j].first * pts[i].second
        }
        return kotlin.math.abs(s) / 2f
    }

    private fun roundUp(v: Int, m: Int): Int = if (v % m == 0) v else v + (m - v % m)

    // ============ DB 后处理几何 ============

    private fun meanScoreOnBox(prob: FloatArray, contour: List<Pair<Int, Int>>, w: Int, h: Int): Float {
        val xs = contour.map { it.first }
        val ys = contour.map { it.second }
        val x0 = xs.min().coerceIn(0, w - 1); val x1 = xs.max().coerceIn(0, w - 1)
        val y0 = ys.min().coerceIn(0, h - 1); val y1 = ys.max().coerceIn(0, h - 1)
        if (x1 <= x0 || y1 <= y0) return 0f
        var sum = 0f; var n = 0
        for (y in y0..y1) for (x in x0..x1) { sum += prob[y * w + x]; n++ }
        return if (n > 0) sum / n else 0f
    }

    /** 最小外接矩形（4 角点），输入轮廓点 */
    private fun minAreaRect(contour: List<Pair<Int, Int>>): List<Pair<Float, Float>> {
        // 用外接矩形近似（PCA/旋转矩形实现复杂，试卷框近正向，外接矩形足够）
        if (contour.isEmpty()) return emptyList()
        val xs = contour.map { it.first.toFloat() }
        val ys = contour.map { it.second.toFloat() }
        val x0 = xs.min(); val x1 = xs.max()
        val y0 = ys.min(); val y1 = ys.max()
        return listOf(x0 to y0, x1 to y0, x1 to y1, x0 to y1)
    }

    /** unclip：按矩形长边膨胀 ratio 倍（DB 标准 post：扩大检测框） */
    private fun unclip(rect: List<Pair<Float, Float>>, ratio: Float): List<Pair<Float, Float>> {
        if (rect.size < 4) return rect
        val (cx, cy) = centroid(rect)
        return rect.map { p ->
            val nx = cx + (p.first - cx) * ratio
            val ny = cy + (p.second - cy) * ratio
            nx to ny
        }
    }

    private fun centroid(pts: List<Pair<Float, Float>>): Pair<Float, Float> {
        val cx = pts.map { it.first }.average().toFloat()
        val cy = pts.map { it.second }.average().toFloat()
        return cx to cy
    }

    // ============ 连通域轮廓（简化：8 连通 flood fill 找外轮廓点集）============

    private class BitMatrix(val w: Int, val h: Int) {
        val data = BooleanArray(w * h)
    }

    /** 在二值图上找连通域，每个返回其边界点集（用于后续 minAreaRect） */
    private fun findContours(binary: BitMatrix): List<List<Pair<Int, Int>>> {
        val visited = BooleanArray(binary.w * binary.h)
        val contours = ArrayList<List<Pair<Int, Int>>>()
        val dx = intArrayOf(-1, 1, 0, 0, -1, -1, 1, 1)
        val dy = intArrayOf(0, 0, -1, 1, -1, 1, -1, 1)
        for (startY in 0 until binary.h) {
            for (startX in 0 until binary.w) {
                val idx = startY * binary.w + startX
                if (!binary.data[idx] || visited[idx]) continue
                // BFS 该连通域，收集所有点
                val queue = java.util.ArrayDeque<Int>()
                queue.add(idx); visited[idx] = true
                val pts = ArrayList<Pair<Int, Int>>()
                while (queue.isNotEmpty()) {
                    val cur = queue.poll()
                    val cx = cur % binary.w
                    val cy = cur / binary.w
                    pts.add(cx to cy)
                    for (k in 0 until 8) {
                        val nx = cx + dx[k]
                        val ny = cy + dy[k]
                        if (nx < 0 || ny < 0 || nx >= binary.w || ny >= binary.h) continue
                        val ni = ny * binary.w + nx
                        if (!visited[ni] && binary.data[ni]) {
                            visited[ni] = true
                            queue.add(ni)
                        }
                    }
                }
                if (pts.size >= 4) contours.add(pts)
            }
        }
        return contours
    }

    // ============ 英文过滤（与 PC filter_english_words 一致）============

    private val englishWordRegex = Regex("""\b[a-zA-Z]+\b""")

    /** 与 PC 版 auto_lookup.py:324-360 一致：逐词提取，长度>1 且非停用词 */
    private fun extractEnglishWords(text: String): List<String> {
        val out = ArrayList<String>()
        for (m in englishWordRegex.findAll(text)) {
            val w = m.value
            if (w.length > 1 && w.lowercase(Locale.ROOT) !in STOP_WORDS) {
                out.add(w)
            }
        }
        return out
    }

    private val STOP_WORDS = setOf(
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to",
        "of", "for", "with", "by", "from", "as", "is", "was", "are",
        "been", "be", "have", "has", "had", "do", "does", "did"
    )

    // ============ 工具 ============

    private fun inputName(session: OrtSession): String =
        session.inputNames.first()

    private fun copyAssetToFile(assetPath: String, fileName: String): File {
        val outFile = File(appContext.filesDir, "ocr/$fileName")
        if (!outFile.exists() || outFile.length() == 0L) {
            outFile.parentFile?.mkdirs()
            appContext.assets.open(assetPath).use { input ->
                outFile.outputStream().use { input.copyTo(it) }
            }
        }
        return outFile
    }
}
