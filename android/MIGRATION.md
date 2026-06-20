# PC 版 → 安卓版 代码迁移映射

本文档记录 DreamWord 安卓版每个模块对应的 PC 版源码位置，方便对照维护与回归测试。

## 数据结构

| PC 版 | 安卓版 |
|---|---|
| `src/core/__init__.py:28-37` `WordEntry` | `data/Models.kt` `WordEntry` |
| `src/core/__init__.py:40-73` `LookupResult` + `to_dict()` | `data/Models.kt` `LookupResult`（序列化在 `NativeBridge.lookupResultToJson`） |
| `src/core/__init__.py:76-83` `OCRResult` | `data/Models.kt` `OcrWord` |
| `src/core/__init__.py:85-92` `WordPosition` / `Annotation` | `data/Models.kt` `Annotation`（WordPosition 在安卓端由前端处理） |

## 词典查询（核心移植）

| PC 版 `src/modules/word_lookup.py` | 安卓版 |
|---|---|
| `MDXParser` (34-233) HTML 状态机 | `dict/MdxParser.kt`（改用 Jsoup DOM 遍历，等价逻辑） |
| `word_exists` (395-402) | `dict/DictRepository.kt` `wordExists` |
| `get_entry_html` (404-411) | `DictRepository.kt` `getEntryHtml` |
| `get_all_entries_html` (413-420) | `DictRepository.kt` `getAllEntriesHtml` |
| `get_word_entries` (427-434) | `DictRepository.kt` `getWordEntries` |
| `get_base_form_from_db` (436-446) | `dict/WordLookup.kt` `getBaseFormFromDb` |
| `get_word_base_form_simple` (448-519) | `dict/InflectionResolver.kt` `getWordBaseFormSimple` |
| **`_infer_inflection_base` (909-972)** ★变形词修复★ | `InflectionResolver.kt` `inferInflectionBase`（special_cases 字典 1:1 搬移） |
| `_resolve_word_form` (880-907) | `WordLookup.kt` `resolveWordForm` |
| `find_best_match` (839-878) | `dict/SimilarityScorer.kt` `findBestMatch` |
| `calculate_similarity` (765-837) 无 semantic 分支 | `SimilarityScorer.kt` `calculateSimilarity`（权重 0.40/0.30/0.20/0.10 与 PC 无语义时一致） |
| `_calculate_tfidf_similarity` (563-590) | `SimilarityScorer.kt` `tfidfSimilarity` |
| `_calculate_example_similarity` (592-613) | `SimilarityScorer.kt` `exampleSimilarity` |
| `_calculate_ngram_similarity` (615-633) | `SimilarityScorer.kt` `ngramSimilarity` |
| `tokenize` (529-532) | `SimilarityScorer.kt` `tokenize` |
| `_rank_definitions_by_context` (689-763) 无 semantic 分支 | `SimilarityScorer.kt` `rankDefinitionsByContext` |
| **`lookup` 主流程 (986-1109)** ★含 found→find 合并择优修复(1038-1045)★ | `WordLookup.kt` `lookup`（逻辑分支完全对应） |
| `_calculate_semantic_similarity` (635-687) | ❌ 不移植（依赖 torch）；改由 `dict/Disambiguator.kt` 用在线 LLM 替代 |

## 已知词库

| PC 版 `src/modules/auto_lookup.py` | 安卓版 |
|---|---|
| `KnownWordsDatabase` (62-170) 全部方法 | `data/KnownWordsDao.kt`（表结构一致，PC 的 known_words.db 可直接读） |

## OCR

| PC 版 | 安卓版 |
|---|---|
| `src/modules/auto_lookup.py:172-360` `TextExtractor`（PaddleOCR） | `ocr/OcrEngine.kt` 接口 + `RapidOcrEngineImpl.kt`（RapidOCR onnx） |
| `filter_english_words` (324-351) | `RapidOcrEngineImpl.kt` `isEnglishWord`（正则一致） |

## 拍照查词

| PC 版 | 安卓版 |
|---|---|
| `app.py:262-322` `/api/auto-lookup` | `bridge/NativeBridge.kt` `autoLookup` |
| `auto_lookup.py:564-718` `process_exam_image`（去 Gcode） | `NativeBridge.kt` `autoLookup`（裁剪→OCR→找生词→查释义→画图） |
| `auto_lookup.py:720-749` `_draw_annotation`（cv2.putText） | `bridge/AnnotationRenderer.kt`（Canvas+Paint，绿音标/红释义一致） |
| `_generate_writing_gcode` (751-776) | ❌ 移除（无硬件链路） |

## API 路由 → Bridge 方法

| PC 版 Flask 路由 | 安卓版 NativeBridge 方法 | 前端调用 |
|---|---|---|
| `POST /api/ocr-words` | `ocrWords(payload)` | `callNative('ocrWords', {image})` |
| `GET /api/word-preview` | `wordPreview(payload)` | `callNative('wordPreview', {word, context})` |
| `POST /api/auto-lookup` | `autoLookup(payload)` | `callNative('autoLookup', {image, crop})` |
| `POST /api/add-known-words` | `addKnownWords(payload)` | `callNative('addKnownWords', {words})` |
| `GET /api/get-known-words` | `getKnownWords(payload)` | `callNative('getKnownWords', {})` |
| `POST /api/remove-known-word` | `removeKnownWord(payload)` | `callNative('removeKnownWord', {word})` |
| `POST /api/onedrive/*` | `onedrive(payload)` | （占位，待完善） |

## 前端

| PC 版 | 安卓版 `assets/web/` |
|---|---|
| `static/js/app.js:1` `API_BASE` | 移除（不再 fetch） |
| `static/js/app.js:15-58` `apiRequest`（fetch） | `app.js` `callNative`（调 `window.NativeBridge`） |
| `static/js/app.js:234-269` 点词 `click` | `app.js` `pointerdown`（触屏适配） |
| `static/js/app.js:1016-1048` 裁剪 `mousedown/move/up` | `app.js` `bindCropPointerEvents`（Pointer Events） |
| `static/js/app.js:1186-1264` `getUserMedia` 摄像头 | `app.js` `startCamera/capturePhoto`（一致） |
| `static/js/app.js:298-362` 容错 JSON 解析 | `app.js` `parseWordJson`（逻辑一致） |
| `static/js/app.js:859-896` `displayWordPreview` | `app.js` `displayWordPreview`（一致） |

## 已移除（硬件链路，安卓版不需要）

- `src/modules/writer.py`（Gcode 生成 + 串口控制）
- `src/modules/calibration.py`（ArUco 校准 + 坐标转换）
- `src/modules/auto_copy.py`（自动抄写）
- `app.py` 所有 `/api/serial/*`、`/api/calibrate`、`/api/auto-copy`、`/api/write`、`/api/generate-*`、`/api/draw-markers` 路由
- 前端"工具"Tab 整块

## 回归测试建议

移植后建议对以下词做 PC 版 vs 安卓版输出对比，确保查词一致性：

| 测试词 | 语境 | 预期（PC 版行为） |
|---|---|---|
| `found` | "I found it interesting" | 应取 `find` 释义（变形词修复） |
| `left` | "She left the room" | 应取 `leave` 释义 |
| `looked` | （无语境） | 应回退到 `look` |
| `reading` | "I am reading" | 应识别为 `read` 的现在分词 |
| `bank` | （多义词） | 离线：按 TF-IDF/Jaccard 排序；在线：LLM 选最贴切 |
