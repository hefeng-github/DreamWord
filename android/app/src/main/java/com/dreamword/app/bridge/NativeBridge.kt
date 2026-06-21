package com.dreamword.app.bridge

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.util.Base64
import com.dreamword.app.data.KnownWordsDao
import com.dreamword.app.data.OcrWord
import com.dreamword.app.dict.DictRepository
import com.dreamword.app.dict.Disambiguator
import com.dreamword.app.dict.WordLookup
import com.dreamword.app.ocr.OcrEngine
import com.dreamword.app.onedrive.OneDriveBackup
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject

/**
 * 原生能力桥——暴露给 WebView 前端调用。
 *
 * 前端约定（见 assets/web/app.js 的 apiRequest 改造）：
 *   const resp = await window.NativeBridge.<method>(jsonString);
 *   // resp 是 JSON 字符串，解析后形如 { success, ... }
 *
 * 每个方法对应 PC 版的一个 /api 路由：
 *   ocrWords          ← /api/ocr-words        （拍照点词）
 *   wordPreview       ← /api/word-preview     （手动查词）
 *   autoLookup        ← /api/auto-lookup      （拍照查词书写，去 Gcode）
 *   addKnownWords     ← /api/add-known-words
 *   getKnownWords     ← /api/get-known-words
 *   removeKnownWord   ← /api/remove-known-word
 *
 * 注意：@JavascriptInterface 方法由 WebView 的 JavaBridge 线程调用，
 * 不能直接更新 UI；耗时操作（OCR / 网络）走协程到 IO 线程，runBlocking 取结果。
 */
class NativeBridge(
    private val context: Context,
    private val dict: DictRepository?,
    private val ocr: OcrEngine,
    private val coroutineScope: CoroutineScope
) {
    private val knownWords: KnownWordsDao = KnownWordsDao(context)
    private val lookup: WordLookup? = dict?.let { WordLookup(it) }

    // ---- OCR ----

    /**
     * 拍照点词：识别图片中的单词，返回带 bbox 的列表。
     * 入参 JSON: { "image": "<base64 png/jpg>" }
     * 返回 JSON: { success, words: [{word, bbox, center, confidence}] }
     */
    @android.webkit.JavascriptInterface
    fun ocrWords(payload: String): String = runCatching {
        val args = JSONObject(payload)
        val bitmap = decodeBase64Bitmap(args.optString("image"))
            ?: return error("无效的图片数据")
        if (!ocr.isReady()) return error("OCR 引擎未就绪，请在设置中检查模型")
        val words = runBlocking { withContext(Dispatchers.Default) { ocr.recognize(bitmap) } }
        ok(JSONObject().put("words", wordsToJson(words)))
    }.getOrElse { error("OCR 失败：${it.message}") }

    // ---- 查词 ----

    /**
     * 手动查词预览。
     * 入参 JSON: { "word": "found", "context": "I found it" }
     * 返回 PC 版 LookupResult.to_dict() 同构的 JSON。
     */
    @android.webkit.JavascriptInterface
    fun wordPreview(payload: String): String = runCatching {
        if (lookup == null) return error("词典未就绪，请在设置中下载完整词典")
        val args = JSONObject(payload)
        val word = args.optString("word").trim()
        val contextStr = args.optString("context", "").trim()
        if (word.isEmpty()) return error("请输入要查询的单词")

        var result = lookup.lookup(word, contextStr)

        // 在线语境消歧（增强，失败则沿用离线结果）
        val disamb = buildDisambiguator()
        if (disamb.isUsable() && contextStr.isNotEmpty()) {
            result = runBlocking { disamb.enhance(result, contextStr) }
        }
        ok(lookupResultToJson(result))
    }.getOrElse { error("查词失败：${it.message}") }

    /**
     * 拍照查词书写：识别图片 → 找生词 → 查释义 → 画标注图。
     * 入参 JSON: { "image": "<base64>", "known_words": [...], "crop": {x,y,w,h} }
     * 返回 JSON: { success, annotated_image: "<base64>", words: [...] }
     * 注意：安卓版去掉 Gcode 生成（无硬件链路），只返回标注图。
     */
    @android.webkit.JavascriptInterface
    fun autoLookup(payload: String): String = runCatching {
        if (lookup == null) return error("词典未就绪")
        if (!ocr.isReady()) return error("OCR 引擎未就绪")
        val args = JSONObject(payload)
        var bitmap = decodeBase64Bitmap(args.optString("image"))
            ?: return error("无效的图片数据")

        // 裁剪
        val crop = args.optJSONObject("crop")
        if (crop != null) {
            val x = crop.optInt("x"); val y = crop.optInt("y")
            val w = crop.optInt("w"); val h = crop.optInt("h")
            if (w > 0 && h > 0 && x + w <= bitmap.width && y + h <= bitmap.height) {
                bitmap = Bitmap.createBitmap(bitmap, x, y, w, h)
            }
        }

        val allWords = runBlocking { withContext(Dispatchers.Default) { ocr.recognize(bitmap) } }
        // 已会词集合（入参传入 + 本地库）
        val knownSet = HashSet<String>()
        args.optJSONArray("known_words")?.let { arr ->
            for (i in 0 until arr.length()) knownSet.add(arr.getString(i).lowercase())
        }
        knownWords.getAllWords().forEach { knownSet.add(it.lowercase()) }

        // 找生词（过滤已会）
        val newWords = allWords.filter { it.text.lowercase() !in knownSet }

        // 查释义
        val annotations = JSONArray()
        for (w in newWords) {
            val r = lookup.lookup(w.text, "")
            if (r.success) {
                annotations.put(JSONObject()
                    .put("word", r.word)
                    .put("phonetic", r.phonetic)
                    .put("definition", r.definitions.firstOrNull() ?: "")
                    .put("bbox", JSONArray(w.bbox.map { JSONArray(it) }))
                )
            }
        }

        // 画标注图
        val annotated = AnnotationRenderer.render(bitmap, newWords, annotations)
        ok(JSONObject()
            .put("annotated_image", bitmapToBase64(annotated))
            .put("words", annotations)
        )
    }.getOrElse { error("查词书写失败：${it.message}") }

    // ---- 已会词库 ----

    @android.webkit.JavascriptInterface
    fun addKnownWords(payload: String): String = runCatching {
        val args = JSONObject(payload)
        val arr = args.optJSONArray("words") ?: return error("缺少 words 参数")
        val list = ArrayList<String>(arr.length())
        for (i in 0 until arr.length()) list.add(arr.getString(i))
        knownWords.addWords(list)
        ok(JSONObject().put("added", list.size).put("total", knownWords.count()))
    }.getOrElse { error("添加失败：${it.message}") }

    @android.webkit.JavascriptInterface
    fun getKnownWords(payload: String): String = runCatching {
        val all = knownWords.getAllWords()
        ok(JSONObject().put("words", JSONArray(all)).put("total", all.size))
    }.getOrElse { error("读取失败：${it.message}") }

    @android.webkit.JavascriptInterface
    fun removeKnownWord(payload: String): String = runCatching {
        val args = JSONObject(payload)
        val word = args.optString("word")
        knownWords.removeWord(word)
        ok(JSONObject().put("total", knownWords.count()))
    }.getOrElse { error("删除失败：${it.message}") }

    // ---- 状态查询（供前端启动时自检）----

    @android.webkit.JavascriptInterface
    fun getStatus(): String = ok(JSONObject()
        .put("ocr_ready", ocr.isReady())
        .put("dict_ready", dict?.isOpenable() ?: false)
        .put("known_words_count", knownWords.count())
    )

    // ---- OneDrive 备份/恢复 ----
    // 统一入口 onedrive(payload)，用 action 字段分发，对应 PC 版的多个 /api/onedrive/* 路由：
    //   status    → 是否已授权
    //   auth      → 获取设备码（getDeviceCode）
    //   poll      → 轮询 token（pollToken）
    //   backup    → 备份到云端
    //   list      → 列出云端备份
    //   restore   → 恢复（backup_name 可选，merge 可选）
    //   disconnect → 断开连接

    @android.webkit.JavascriptInterface
    fun onedrive(payload: String): String = runCatching {
        val args = JSONObject(payload)
        val action = args.optString("action")
        when (action) {
            "status" -> {
                val od = buildOneDrive()
                ok(JSONObject().put("authorized", od?.isAuthorized() ?: false))
            }
            "auth" -> {
                val od = buildOneDrive() ?: return error("请先在设置中填写 OneDrive Client ID")
                val code = runBlocking { withContext(Dispatchers.IO) { od.getDeviceCode() } }
                ok(code)  // 含 user_code / device_code / verification_uri
            }
            "poll" -> {
                val od = buildOneDrive() ?: return error("请先在设置中填写 OneDrive Client ID")
                val deviceCode = args.optString("device_code")
                val tokens = runBlocking { withContext(Dispatchers.IO) { od.pollToken(deviceCode) } }
                if (tokens != null) ok(JSONObject().put("authorized", true))
                else ok(JSONObject().put("authorized", false).put("pending", true))
            }
            "backup" -> {
                val od = buildOneDrive() ?: return error("请先在设置中填写 OneDrive Client ID")
                val result = runBlocking { withContext(Dispatchers.IO) { od.backup() } }
                ok(result)
            }
            "list" -> {
                val od = buildOneDrive() ?: return error("请先在设置中填写 OneDrive Client ID")
                val list = runBlocking { withContext(Dispatchers.IO) { od.listBackups() } }
                ok(JSONObject().put("backups", list))
            }
            "restore" -> {
                val od = buildOneDrive() ?: return error("请先在设置中填写 OneDrive Client ID")
                val name = args.optString("backup_name").takeIf { it.isNotBlank() }
                val merge = args.optBoolean("merge", true)
                val result = runBlocking { withContext(Dispatchers.IO) { od.restore(name, merge) } }
                ok(result)
            }
            "disconnect" -> {
                buildOneDrive()?.disconnect()
                ok(JSONObject().put("disconnected", true))
            }
            else -> error("未知的 OneDrive 操作: $action")
        }
    }.getOrElse { error("OneDrive 操作失败：${it.message}") }

    /** 构造 OneDriveBackup；Client ID 未配置时返回 null */
    private fun buildOneDrive(): OneDriveBackup? {
        val prefs = androidx.preference.PreferenceManager.getDefaultSharedPreferences(context)
        val clientId = prefs.getString("onedrive_client_id", "")?.trim().orEmpty()
        if (clientId.isEmpty()) return null
        return OneDriveBackup(context, clientId, knownWords)
    }

    private fun buildDisambiguator(): Disambiguator {
        val prefs = androidx.preference.PreferenceManager.getDefaultSharedPreferences(context)
        val enabled = prefs.getBoolean("disambig_enable", true)
        val baseUrl = prefs.getString("llm_base_url", context.getString(com.dreamword.app.R.string.default_llm_base_url)) ?: ""
        val apiKey = prefs.getString("llm_api_key", "") ?: ""
        val model = prefs.getString("llm_model", context.getString(com.dreamword.app.R.string.default_llm_model)) ?: ""
        return Disambiguator(baseUrl, apiKey, model, enabled)
    }

    private fun wordsToJson(words: List<OcrWord>): JSONArray = JSONArray().apply {
        for (w in words) {
            put(JSONObject()
                .put("word", w.text)
                .put("bbox", JSONArray(w.bbox.map { JSONArray(it) }))
                .put("center", JSONArray().put(w.center.first).put(w.center.second))
                .put("confidence", w.confidence.toDouble())
            )
        }
    }

    private fun lookupResultToJson(r: com.dreamword.app.data.LookupResult): JSONObject = JSONObject().apply {
        put("success", r.success)
        put("word", r.word)
        if (r.success) {
            put("phonetic", r.phonetic)
            put("definitions", JSONArray(r.definitions))
            put("base_form", r.baseForm ?: r.word)
            put("pos", r.pos ?: JSONObject.NULL)
            put("examples", JSONArray(r.examples))
            if (r.allEntries.isNotEmpty()) {
                put("all_entries", JSONArray(r.allEntries.map { JSONObject(it) }))
            }
        } else {
            put("message", r.message ?: "未找到")
        }
    }

    private fun decodeBase64Bitmap(dataUri: String): Bitmap? {
        if (dataUri.isBlank()) return null
        // 兼容 "data:image/png;base64,xxxx" 或纯 base64
        val b64 = if (dataUri.contains(",")) dataUri.substringAfter(",") else dataUri
        return try {
            val bytes = Base64.decode(b64, Base64.DEFAULT)
            BitmapFactory.decodeByteArray(bytes, 0, bytes.size)
        } catch (e: Exception) { null }
    }

    private fun bitmapToBase64(bitmap: Bitmap): String {
        val baos = java.io.ByteArrayOutputStream()
        bitmap.compress(Bitmap.CompressFormat.JPEG, 85, baos)
        return "data:image/jpeg;base64," +
            Base64.encodeToString(baos.toByteArray(), Base64.NO_WRAP)
    }

    private fun ok(data: JSONObject): String =
        JSONObject().put("success", true).put("data", data).toString()

    private fun error(message: String): String =
        JSONObject().put("success", false).put("error", message).toString()
}
