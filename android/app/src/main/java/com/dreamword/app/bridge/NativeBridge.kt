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
    private val ocr: OcrEngine,
    private val coroutineScope: CoroutineScope
) {
    private val knownWords: KnownWordsDao = KnownWordsDao(context)
    // dict 可被 reloadDict() 刷新：初始从外部存储/内部目录解析，用户放入 .db 后重载生效
    @Volatile private var dict: DictRepository? = DictRepository.resolve(context)
    /**
     * WordLookup 持有一个 CachedDict 长连接（避免对 441MB 词典反复 open/close）。
     * 在 dict 重新解析（reload/import）后由 invalidateLookup() 关闭旧连接、置空，
     * 下次访问时惰性重建。
     */
    @Volatile private var lookupHolder: WordLookup? = null

    /** 取当前 WordLookup（dict 就绪时惰性构建），未就绪返回 null */
    private fun acquireLookup(): WordLookup? {
        val d = dict ?: return null
        if (!d.isOpenable()) return null
        lookupHolder?.let { return it }
        synchronized(this) {
            lookupHolder?.let { return it }
            return try {
                val wl = WordLookup.fromRepo(d)
                lookupHolder = wl
                wl
            } catch (e: Throwable) { null }
        }
    }

    /** dict 重新解析后调用：关闭旧连接，清空 lookupHolder */
    private fun invalidateLookup() {
        synchronized(this) {
            try { lookupHolder?.close() } catch (_: Throwable) {}
            lookupHolder = null
        }
    }

    /**
     * 启动 SAF 文件选择器的回调（由 MainActivity 注入，因为 Launcher 必须在 Activity 上注册）。
     * NativeBridge.pickAndImportDict 调用它触发选择器，结果异步通过 importDictByUri + JS 回调返回。
     */
    var launchDictPicker: (() -> Unit)? = null


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
        // 惰性获取 WordLookup（持 CachedDict 长连接）；未就绪返回错误
        val lookupInstance = acquireLookup() ?: return error("词典未就绪，请在设置中下载完整词典")
        val args = JSONObject(payload)
        val word = args.optString("word").trim()
        val contextStr = args.optString("context", "").trim()
        if (word.isEmpty()) return error("请输入要查询的单词")

        var result = lookupInstance.lookup(word, contextStr)

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
        // 惰性获取 WordLookup（持 CachedDict 长连接）
        val lookupInstance = acquireLookup() ?: return error("词典未就绪")
        if (!ocr.isReady()) return error("OCR 引擎未就绪")
        val args = JSONObject(payload)
        val bitmap = decodeBase64Bitmap(args.optString("image"))
            ?: return error("无效的图片数据")

        // 裁剪框
        val crop = args.optJSONObject("crop")?.let { c ->
            OcrLookupPipeline.Crop(c.optInt("x"), c.optInt("y"), c.optInt("w"), c.optInt("h"))
        }

        // 已会词（入参传入）
        val knownFromCaller = ArrayList<String>()
        args.optJSONArray("known_words")?.let { arr ->
            for (i in 0 until arr.length()) knownFromCaller.add(arr.getString(i))
        }

        // 跑管线（OCR + 查词 + 标注），在后台线程
        val result = runBlocking {
            withContext(Dispatchers.Default) {
                OcrLookupPipeline(ocr, lookupInstance) { knownWords.getAllWords() }
                    .run(bitmap, crop, knownFromCaller)
            }
        }

        // 回传标注图（base64） + 标注列表
        val wordsJson = JSONArray()
        for (a in result.annotations) {
            wordsJson.put(JSONObject()
                .put("word", a.word)
                .put("phonetic", a.phonetic)
                .put("definition", a.definition)
                .put("bbox", JSONArray(a.bbox.map { JSONArray(it) }))
            )
        }
        ok(JSONObject()
            .put("annotated_image", bitmapToBase64(result.annotatedBitmap))
            .put("words", wordsJson)
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

    /**
     * 词典状态 + 导入路径查询。
     * 不再用 base64 传输（441MB 会撑爆内存导致闪退）。
     * 改为：前端调用此方法，拿到推荐导入路径，提示用户把 .db 文件
     * 用文件管理器 / adb 放到该路径，然后调用 reloadDict() 重新加载。
     *
     * 返回 JSON: { dict_ready, import_path, hint }
     */
    /**
     * 触发系统文件选择器（SAF）让用户选 .db 词典文件。
     * 选择结果异步通过 window.__dictImportCallback 回调返回前端。
     * 全程流式拷贝（ContentResolver），441MB 也不会 OOM，且能访问任何位置（微信/文件管理器/U盘）。
     *
     * 前端用法：
     *   window.__dictImportCallback = (result) => { ... };  // 先注册回调
     *   window.NativeBridge.pickAndImportDict('{}');        // 再触发选择器
     */
    @android.webkit.JavascriptInterface
    fun pickAndImportDict(payload: String): String = runCatching {
        val launcher = launchDictPicker
            ?: return error("文件选择器未初始化")
        launcher.invoke()
        ok(JSONObject().put("launched", true))  // 选择器已弹出，结果走异步回调
    }.getOrElse { error("启动文件选择器失败：${it.message}") }

    @android.webkit.JavascriptInterface
    fun dictInfo(): String = runCatching {
        val hintPath = DictRepository.getImportHintPath(context)
        ok(JSONObject()
            .put("dict_ready", dict?.isOpenable() ?: false)
            .put("import_path", hintPath)
            .put("hint", "把 word_details.db 放到上述路径，然后点「重新加载」")
        )
    }.getOrElse { error("查询词典状态失败：${it.message}") }

    /**
     * 重新检测词典文件并加载。用户把 .db 放到公共目录后调用。
     * 返回 JSON: { dict_ready, import_path }
     */
    @android.webkit.JavascriptInterface
    fun reloadDict(): String = runCatching {
        invalidateLookup()  // 关闭旧 CachedDict
        DictRepository.reset()
        // 重新 resolve（触发从外部存储目录查找）并刷新 bridge 持有的引用
        dict = DictRepository.resolve(context)
        ok(JSONObject()
            .put("dict_ready", dict?.isOpenable() ?: false)
            .put("import_path", DictRepository.getImportHintPath(context))
        )
    }.getOrElse { error("重新加载词典失败：${it.message}") }

    /**
     * 通过文件 Uri 导入词典（供 MainActivity 的 file chooser 回调调用，不走 base64）。
     * 用 ContentResolver 流式拷贝，不会撑爆内存。
     */
    fun importDictByUri(uri: android.net.Uri): String = try {
        val size = DictRepository.importDictionary(context, uri)
        invalidateLookup()
        DictRepository.reset()
        dict = DictRepository.resolve(context)
        ok(JSONObject().put("size", size))
    } catch (e: Exception) {
        error("词典导入失败：${e.message}")
    }

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
