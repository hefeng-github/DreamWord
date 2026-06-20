package com.dreamword.app.bridge

import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.Typeface
import com.dreamword.app.data.OcrWord
import org.json.JSONArray
import org.json.JSONObject

/**
 * 标注图绘制（移植自 PC 版 auto_lookup.py:720-749 的 _draw_annotation）
 *
 * PC 版用 cv2.putText 在试卷图上画绿色音标 + 红色释义。
 * 安卓版用 Canvas + Paint 实现等价效果。
 */
object AnnotationRenderer {

    fun render(src: Bitmap, newWords: List<OcrWord>, annotations: JSONArray): Bitmap {
        // 复制成可变 bitmap 以便绘制
        val result = src.copy(Bitmap.Config.ARGB_8888, true)
        val canvas = Canvas(result)

        // 字号随图片宽度自适应（PC 版固定，安卓需适配分辨率）
        val fontSize = (result.width * 0.018f).coerceIn(14f, 40f)

        // 绿色音标
        val phoneticPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = Color.parseColor("#2e7d32")
            textSize = fontSize
            typeface = Typeface.create(Typeface.DEFAULT, Typeface.BOLD)
            setShadowLayer(2f, 1f, 1f, Color.WHITE)
        }
        // 红色释义
        val defPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = Color.parseColor("#c62828")
            textSize = fontSize
            setShadowLayer(2f, 1f, 1f, Color.WHITE)
        }
        // 半透明蓝框（生词高亮）
        val boxPaint = Paint().apply {
            color = Color.parseColor("#330000FF")
            style = Paint.Style.FILL
        }
        val boxStroke = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = Color.parseColor("#1976D2")
            style = Paint.Style.STROKE
            strokeWidth = 3f
        }

        // 先画生词框
        for (w in newWords) {
            if (w.bbox.size < 4) continue
            val xs = w.bbox.map { it[0].toFloat() }
            val ys = w.bbox.map { it[1].toFloat() }
            val left = xs.min(); val top = ys.min()
            val right = xs.max(); val bottom = ys.max()
            canvas.drawRect(left, top, right, bottom, boxPaint)
            canvas.drawRect(left, top, right, bottom, boxStroke)
        }

        // 再在生词上方画音标 + 释义
        for (i in 0 until annotations.length()) {
            val ann: JSONObject = annotations.optJSONObject(i) ?: continue
            val bbox = ann.optJSONArray("bbox") ?: continue
            if (bbox.length() < 4) continue
            // bbox 是 [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
            val p0 = bbox.optJSONArray(0)
            val p2 = bbox.optJSONArray(2)
            if (p0 == null || p2 == null) continue
            val left = p0.optDouble(0).toFloat()
            val top = p0.optDouble(1).toFloat()

            val phonetic = ann.optString("phonetic")
            val definition = ann.optString("definition")

            var y = top - fontSize * 0.4f
            if (y < fontSize) y = fontSize // 防止超出顶部
            if (phonetic.isNotEmpty() && phonetic != "N/A") {
                canvas.drawText(phonetic, left, y, phoneticPaint)
                y -= fontSize * 1.3f
            }
            if (definition.isNotEmpty()) {
                // 长释义截断（PC 版每行不换行；这里同理，过长截断）
                val max = definition.take(30)
                canvas.drawText(max, left, y, defPaint)
            }
        }

        return result
    }
}
