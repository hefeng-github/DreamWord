package com.dreamword.app.dict

import com.dreamword.app.data.LookupResult
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import java.util.concurrent.TimeUnit

/**
 * 在线语境消歧（OpenAI 兼容 API，默认智谱 GLM-4-Flash）
 *
 * 使用场景：当查词结果有多个释义、且提供了语境时，用 LLM 在这些释义中
 * 选出最贴切的一个并置顶。这替代了 PC 版的 sentence-transformers 语义消歧
 * （准确率更高，但需要联网）。
 *
 * 设计原则：
 *  - 断网 / 未配置 / 超时 → 静默失败，沿用离线统计排序结果（不阻塞查词）
 *  - 只做"排序增强"：把 LLM 选中的释义挪到第一位，不删除其他释义
 *  - 可配置：Base URL + Key + Model 三参数（OpenAI 兼容）
 */
class Disambiguator(
    private val baseUrl: String,
    private val apiKey: String,
    private val model: String,
    private val enabled: Boolean
) {
    private val client = OkHttpClient.Builder()
        .connectTimeout(8, TimeUnit.SECONDS)
        .readTimeout(15, TimeUnit.SECONDS)
        .build()

    /** 是否实际可用（开关打开 + 配了 Key） */
    fun isUsable(): Boolean = enabled && apiKey.isNotBlank() && baseUrl.isNotBlank()

    /**
     * 对查词结果做语境消歧：把最贴切的释义置顶。
     * 失败时返回原 result（不修改）。
     */
    suspend fun enhance(result: LookupResult, context: String): LookupResult = withContext(Dispatchers.IO) {
        if (!isUsable()) return@withContext result
        if (!result.success || context.isBlank()) return@withContext result
        if (result.definitions.size <= 1) return@withContext result

        try {
            val picked = pickBestDefinition(result.word, context, result.definitions) ?: return@withContext result
            if (picked < 0 || picked >= result.definitions.size) return@withContext result
            // 把选中的释义置顶，其余保持原序
            val reordered = ArrayList<String>(result.definitions.size).apply {
                add(result.definitions[picked])
                for (i in result.definitions.indices) if (i != picked) add(result.definitions[i])
            }
            result.copy(definitions = reordered)
        } catch (e: Exception) {
            // 静默失败，沿用离线结果
            result
        }
    }

    /** 调 LLM，返回最贴切释义的索引（0-based）。失败返回 null。 */
    private fun pickBestDefinition(word: String, context: String, definitions: List<String>): Int? {
        val defsJson = JSONArray()
        definitions.forEachIndexed { i, d -> defsJson.put(JSONObject().put("idx", i).put("def", d)) }

        val prompt = """
            你是英语词典助手。请根据句子语境，从给定释义中选出最符合该语境的一项。
            单词: $word
            语境句子: $context
            候选释义（JSON数组）: $defsJson
            请只返回一个 JSON：{"pick": <候选释义的 idx 整数>,"reason":"简短理由"}
            不要返回任何其他内容。
        """.trimIndent()

        val url = baseUrl.trimEnd('/') + "/chat/completions"
        val body = JSONObject()
            .put("model", model)
            .put("messages", JSONArray().put(JSONObject().put("role", "user").put("content", prompt)))
            .put("temperature", 0.1)
            .toString()

        val request = Request.Builder()
            .url(url)
            .header("Authorization", "Bearer $apiKey")
            .header("Content-Type", "application/json")
            .post(body.toRequestBody("application/json".toMediaType()))
            .build()

        client.newCall(request).execute().use { resp ->
            if (!resp.isSuccessful) return null
            val text = resp.body?.string() ?: return null
            val content = JSONObject(text)
                .optJSONArray("choices")?.optJSONObject(0)
                ?.optJSONObject("message")?.optString("content") ?: return null
            // 提取 JSON（容错：LLM 可能包在 markdown ``` 里）
            val jsonStr = extractJson(content) ?: return null
            val pick = JSONObject(jsonStr).optInt("pick", -1)
            return if (pick in definitions.indices) pick else null
        }
    }

    /** 从可能含 markdown 包裹的文本中提取首个 {...} */
    private fun extractJson(text: String): String? {
        val start = text.indexOf('{')
        val end = text.lastIndexOf('}')
        return if (start in 0 until end) text.substring(start, end + 1) else null
    }
}
