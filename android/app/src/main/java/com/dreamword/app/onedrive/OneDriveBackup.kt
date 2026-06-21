package com.dreamword.app.onedrive

import android.content.Context
import com.dreamword.app.data.KnownWordsDao
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.FormBody
import org.json.JSONArray
import org.json.JSONObject
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.concurrent.TimeUnit

/**
 * OneDrive 备份/恢复（移植自 PC 版 src/modules/onedrive_backup.py）
 *
 * 使用 Microsoft Graph API + OAuth2 Device Code 流（无需公网回调，适合移动端）。
 * 词库备份到 OneDrive 的 App Root（special/approot），这是微软为应用提供的
 * 隔离文件夹，不会污染用户主目录。
 *
 * 与 PC 版的差异：
 *  - requests → OkHttp
 *  - token 缓存：明文 json 文件 → 应用私有 SharedPreferences（MODE_PRIVATE，
 *    其他应用无法读取；如需更强加密可换 androidx.security 的 EncryptedSharedPreferences）
 *  - SQLite 直接读写 → KnownWordsDao（已封装）
 *  - backup_meta.json 同步到云端（与 PC 一致），本地版本号也存 SharedPreferences
 *
 * Device Code 流说明：
 *  1. getDeviceCode() → 拿到 user_code + device_code + verification_url
 *  2. 用户在浏览器打开 verification_url，输入 user_code 完成授权
 *  3. 前端轮询 pollToken(device_code) → 授权完成后返回 token，否则返回 null
 */
class OneDriveBackup(
    private val context: Context,
    private val clientId: String,
    private val knownWords: KnownWordsDao
) {
    private val client = OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(60, TimeUnit.SECONDS)
        .build()

    private val prefs by lazy {
        context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
    }

    // ============ Token 管理（加密存储）============

    private fun loadTokens(): JSONObject? {
        val json = prefs.getString(KEY_TOKENS, null) ?: return null
        return try { JSONObject(json) } catch (e: Exception) { null }
    }

    private fun saveTokens(tokens: JSONObject) {
        prefs.edit().putString(KEY_TOKENS, tokens.toString()).apply()
    }

    private fun clearTokens() {
        prefs.edit().remove(KEY_TOKENS).remove(KEY_LOCAL_VERSION).apply()
    }

    /**
     * 获取设备码（Device Code 流第一步）
     * 返回：{ user_code, device_code, verification_uri, expires_in, interval, message }
     */
    fun getDeviceCode(): JSONObject {
        val form = FormBody.Builder()
            .add("client_id", clientId)
            .add("scope", "Files.ReadWrite.AppFolder offline_access")
            .build()
        val req = Request.Builder()
            .url("https://login.microsoftonline.com/common/oauth2/v2.0/devicecode")
            .post(form)
            .build()
        client.newCall(req).execute().use { resp ->
            val body = resp.body?.string().orEmpty()
            if (!resp.isSuccessful) {
                throw Exception("获取设备码失败: ${resp.code} $body")
            }
            return JSONObject(body)
        }
    }

    /**
     * 轮询 token（Device Code 流第二步）
     * @return 授权完成返回 token JSON（已保存），未完成返回 null，错误抛异常
     */
    fun pollToken(deviceCode: String): JSONObject? {
        val form = FormBody.Builder()
            .add("grant_type", "urn:ietf:params:oauth:grant-type:device_code")
            .add("client_id", clientId)
            .add("device_code", deviceCode)
            .build()
        val req = Request.Builder()
            .url("https://login.microsoftonline.com/common/oauth2/v2.0/token")
            .post(form)
            .build()
        client.newCall(req).execute().use { resp ->
            val body = resp.body?.string().orEmpty()
            val json = JSONObject(body)
            if (resp.isSuccessful) {
                // 记录过期时间戳（提前 60 秒）
                val expiresAt = System.currentTimeMillis() / 1000 +
                    json.optLong("expires_in", 3600) - 60
                json.put("expires_at", expiresAt)
                saveTokens(json)
                return json
            }
            // 授权中 / 慢一点：返回 null，让前端继续轮询
            val err = json.optString("error", "")
            if (err == "authorization_pending" || err == "slow_down") return null
            throw Exception("获取token失败: $body")
        }
    }

    private fun ensureToken(): String {
        val tokens = loadTokens() ?: throw Exception("未授权，请先完成 OneDrive 授权")
        val now = System.currentTimeMillis() / 1000
        if (now > tokens.optLong("expires_at", 0)) {
            refreshToken()
            return loadTokens()!!.optString("access_token")
        }
        return tokens.optString("access_token")
    }

    private fun refreshToken() {
        val tokens = loadTokens() ?: throw Exception("无 refresh_token，请重新授权")
        val rt = tokens.optString("refresh_token").orEmpty()
        if (rt.isEmpty()) throw Exception("无 refresh_token，请重新授权")
        val form = FormBody.Builder()
            .add("grant_type", "refresh_token")
            .add("client_id", clientId)
            .add("refresh_token", rt)
            .build()
        val req = Request.Builder()
            .url("https://login.microsoftonline.com/common/oauth2/v2.0/token")
            .post(form)
            .build()
        client.newCall(req).execute().use { resp ->
            val body = resp.body?.string().orEmpty()
            if (!resp.isSuccessful) throw Exception("刷新token失败: $body")
            val newTokens = JSONObject(body)
            newTokens.put("expires_at", System.currentTimeMillis() / 1000 +
                newTokens.optLong("expires_in", 3600) - 60)
            saveTokens(newTokens)
        }
    }

    // ============ Graph API 封装 ============

    private fun graphGet(path: String): JSONObject = graphRequest("GET", path, null)
    private fun graphPut(path: String, content: String): JSONObject =
        graphRequest("PUT", path, content)

    private fun graphRequest(method: String, path: String, content: String?): JSONObject {
        var token = ensureToken()
        var resp = doGraph(method, path, content, token)
        // 401 → 刷新 token 后重试一次
        if (resp.first == 401) {
            refreshToken()
            token = ensureToken()
            resp = doGraph(method, path, content, token)
        }
        val (code, body) = resp
        if (code !in 200..299) {
            throw Exception("Graph API 错误: $code $body")
        }
        return if (body.isNotBlank()) JSONObject(body) else JSONObject()
    }

    private fun doGraph(method: String, path: String, content: String?, token: String): Pair<Int, String> {
        val builder = Request.Builder()
            .url("$GRAPH_BASE$path")
            .header("Authorization", "Bearer $token")
        if (content != null) {
            builder.header("Content-Type", "application/json")
            builder.method(method, content.toRequestBody("application/json".toMediaType()))
        } else {
            builder.method(method, null)
        }
        client.newCall(builder.build()).execute().use { r ->
            return r.code to (r.body?.string().orEmpty())
        }
    }

    // ============ 业务方法 ============

    fun isAuthorized(): Boolean = try { ensureToken(); true } catch (e: Exception) { false }

    private fun getLocalVersion(): Int = prefs.getInt(KEY_LOCAL_VERSION, 0)
    private fun setLocalVersion(v: Int) = prefs.edit().putInt(KEY_LOCAL_VERSION, v).apply()

    /**
     * 备份已会词到 OneDrive（对应 Python backup）
     * @return { version, word_count, timestamp }
     */
    fun backup(): JSONObject {
        val words = knownWords.getAllWords()
        val newVersion = getLocalVersion() + 1
        val timestamp = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss", Locale.getDefault())
            .format(Date())

        val backupData = JSONObject()
            .put("version", newVersion)
            .put("timestamp", timestamp)
            .put("word_count", words.size)
            .put("words", JSONArray(words))

        // 触发 approot 创建（忽略错误）
        try { graphGet("/me/drive/special/approot") } catch (e: Exception) {}

        val filename = "known_words_v$newVersion.json"
        graphPut("/me/drive/special/approot:/$filename:/content", backupData.toString())

        // 写 meta（忽略错误，与 PC 版一致）
        try {
            val meta = JSONObject()
                .put("last_backup_version", newVersion)
                .put("last_backup_time", timestamp)
                .put("last_backup_count", words.size)
            graphPut("/me/drive/special/approot:/backup_meta.json:/content", meta.toString())
        } catch (e: Exception) {}

        setLocalVersion(newVersion)

        return JSONObject()
            .put("version", newVersion)
            .put("word_count", words.size)
            .put("timestamp", timestamp)
    }

    /**
     * 列出云端备份（对应 Python list_backups）
     * @return [{ name, size, last_modified }, ...] 按版本号倒序
     */
    fun listBackups(): JSONArray {
        val result = try {
            graphGet("/me/drive/special/approot/children")
        } catch (e: Exception) { return JSONArray() }

        val backups = mutableListOf<JSONObject>()
        val items = result.optJSONArray("value") ?: return JSONArray()
        for (i in 0 until items.length()) {
            val item = items.optJSONObject(i) ?: continue
            val name = item.optString("name")
            if (name.startsWith("known_words_v") && name.endsWith(".json")) {
                backups.add(JSONObject()
                    .put("name", name)
                    .put("size", item.optLong("size"))
                    .put("last_modified", item.optString("lastModifiedDateTime"))
                )
            }
        }
        // 按文件名（含版本号）倒序
        backups.sortByDescending { it.optString("name") }
        val out = JSONArray()
        backups.forEach { out.put(it) }
        return out
    }

    /**
     * 从 OneDrive 恢复（对应 Python restore）
     * @param backupName 指定备份文件名；null 则取 meta 里记录的最新版本
     * @param merge true=合并（并集），false=替换
     */
    fun restore(backupName: String?, merge: Boolean): JSONObject {
        val path = if (backupName != null) {
            "/me/drive/special/approot:/$backupName:/content"
        } else {
            val meta = graphGet("/me/drive/special/approot:/backup_meta.json:/content")
            val v = meta.optInt("last_backup_version", 0)
            if (v <= 0) throw Exception("云端无备份元数据")
            "/me/drive/special/approot:/known_words_v$v.json:/content"
        }

        // 下载备份内容（GET，可能返回大文件，单独走 ensureToken）
        val token = ensureToken()
        val req = Request.Builder()
            .url("$GRAPH_BASE$path")
            .header("Authorization", "Bearer $token")
            .get()
            .build()
        val backupData = client.newCall(req).execute().use { r ->
            if (!r.isSuccessful) throw Exception("下载备份失败: ${r.code}")
            JSONObject(r.body?.string().orEmpty())
        }

        val cloudWords = mutableSetOf<String>()
        val arr = backupData.optJSONArray("words")
        if (arr != null) for (i in 0 until arr.length()) {
            cloudWords.add(arr.getString(i).lowercase())
        }

        return if (merge) {
            val localWords = knownWords.getAllWords().map { it.lowercase() }.toMutableSet()
            val merged = (localWords + cloudWords).toList()
            knownWords.addWords(merged)
            JSONObject()
                .put("action", "merged")
                .put("local_count", localWords.size)
                .put("cloud_count", cloudWords.size)
                .put("merged_count", merged.size)
                .put("new_words", merged.size - localWords.size)
                .put("version", backupData.optInt("version", 0))
        } else {
            // 替换：先清空再写入（KnownWordsDao 无 clear，用删除全部+添加）
            for (w in knownWords.getAllWords()) knownWords.removeWord(w)
            knownWords.addWords(cloudWords.toList())
            JSONObject()
                .put("action", "replaced")
                .put("word_count", cloudWords.size)
                .put("version", backupData.optInt("version", 0))
        }
    }

    fun disconnect() = clearTokens()

    companion object {
        private const val PREFS_NAME = "onedrive_prefs"
        private const val KEY_TOKENS = "tokens"
        private const val KEY_LOCAL_VERSION = "last_backup_version"
        private const val GRAPH_BASE = "https://graph.microsoft.com/v1.0"
    }
}
