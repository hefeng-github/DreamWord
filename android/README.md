# DreamWord 安卓版

DreamWord 的安卓客户端。**完全离线**（本地 OCR + 本地词典），仅"多义词语境消歧"为可配置的在线 API（默认智谱 GLM-4-Flash，断网自动降级）。去掉整个硬件链路（写字机串口/抄写/书写/Gcode/校准），聚焦"查词学词"。

## 架构

```
原生 Kotlin 层（OCR 推理 + 词典查询 + 词库管理）
       ↕ JSBridge（@JavascriptInterface）
WebView 层（assets/web 里的 index.html + app.js + style.css）
```

前端复用并改造自 PC 版 `static/`（把 `fetch('/api/*')` 改为 `window.NativeBridge.xxx()`，鼠标事件改为 Pointer Events 以适配触屏）。

## 功能对照

| 功能 | 状态 | 说明 |
|---|---|---|
| 拍照点词（标记已会词）| ✅ | RapidOCR onnx |
| 手动查词 | ✅ | 本地词典 + 离线/在线消歧 |
| 拍照查词（生成标注图）| ✅ | 只返回标注图，无 Gcode |
| 批量导入词库 | ✅ | 兼容 JSON / JSON Lines |
| 已会词库管理 | ✅ | 本地 SQLite |
| 变形词语境消歧 | ✅ | 离线统计 + 在线 LLM 增强 |
| OneDrive 备份 | 🔧 | 接口预留，OAuth 流待完善 |
| 自动抄写/写字机/校准/Gcode | ❌ | 已移除（硬件链路） |

---

## 编译运行（3 步）

### 前置要求
- Android Studio (Hedgehog 2023.1.1 或更新)
- JDK 17（Android Studio 自带）
- Android SDK Platform 34 + Build-Tools 34.x

### 步骤 1：放置 OCR 模型（★ 关键 ★）

OCR 引擎需要 PaddleOCR PP-OCRv6 的 onnx 模型。**这是项目能否跑起来的前提**。

**模型来源**：[MaaCommonAssets/OCR/ppocr_v6/small](https://github.com/MaaXYZ/MaaCommonAssets/tree/main/OCR/ppocr_v6/small)

从该目录下载 **3 个文件**（用 `small` 档，总 30MB，适合安卓；`medium` 档 138MB 太重）：

| 文件 | 大小 | 说明 |
|---|---|---|
| `det.onnx` | 9.4 MB | 文字检测（PP-OCRv6_small_det） |
| `rec.onnx` | 20.1 MB | 文字识别（PP-OCRv6_small_rec，支持简繁中文/英文/日文） |
| `keys.txt` | 73 KB | 识别字符表（注意文件名就是 `keys.txt`） |

放到：
```
android/app/src/main/assets/models/
├── det.onnx
├── rec.onnx
└── keys.txt
```

> 这套是 v6（最新），与 PC 版主项目用的 PP-OCRv6 同源，效果一致。无 cls（方向分类），纯 det+rec 两段式。
> 该目录已被 `.gitignore` 排除（模型文件不入仓库）。

### 步骤 2：接入 RapidOCR 库

在 `android/app/build.gradle.kts` 里二选一：

**方式 A（推荐，体积可控）：源码模块**
```kotlin
// 1. 下载 https://github.com/RapidAI/RapidOcrAndroidOnnx 源码
//    放到 android/RapidOcrAndroidOnnx/
// 2. settings.gradle.kts 加：
include(":RapidOcrAndroidOnnx")
// 3. app/build.gradle.kts dependencies 加：
implementation(project(":RapidOcrAndroidOnnx"))
```

**方式 B：Maven 依赖（开箱即用）**
```kotlin
// 取消 app/build.gradle.kts 里的注释：
implementation("io.github.mymonstercat:rapidocr-onnx-platform:0.0.7")
// 然后把 RapidOcrEngineImpl.kt 的实现切换为 Maven 版（按库的 API 调用）
```

接入后，编辑 `RapidOcrEngineImpl.kt`，把 `recognize()` 里的 TODO 替换为实际调用（文件内有详细注释）。

### 步骤 3：词典 + 运行

**词典（首次可不放，app 仍能启动，只是查词功能提示"词典未就绪"）**

- **精简版（推荐起步）**：准备一个小型 SQLite（表 `mdx(entry, paraphrase)`），放到 `android/app/src/main/assets/dict/word_details_mini.db`。可从 PC 版的 `databases/word_details.db` 中筛取高考/CET 词表生成。
- **完整版（441MB）**：不要打进 APK。运行后在 设置 → 下载完整词典，下载到 `filesDir/dict/word_details.db`。或手动把 PC 版的 `databases/word_details.db` 用 adb push 到：
  ```
  /data/data/com.dreamword.app/files/dict/word_details.db
  ```

**打开运行**
```
用 Android Studio 打开 android/ 目录，等 Gradle 同步完成，点 Run。
```

> 本机无 Android Studio 环境时，可用命令行（需装好 SDK）：
> ```
> cd android
> ./gradlew assembleRelease
> ```
> 产物在 `app/build/outputs/apk/release/app-release-unsigned.apk`

---

## 用 GitHub Actions 在线编译（无需本地环境）

仓库已配好 workflow：`.github/workflows/build-android.yml`。

**用法**：把改动 push 到 `main` 分支（改动 `android/` 目录会自动触发），或在 GitHub 仓库的 **Actions** 页面点 `Build Android APK` → `Run workflow` 手动触发。

编译成功后：
1. 进入对应的 workflow run 页面
2. 拉到底部 **Artifacts** 区
3. 下载 `DreamWord-debug`（调试版，带日志）或 `DreamWord-release-unsigned`（发布版，未签名）

下载下来是 zip，解压得到 `.apk`，传到手机安装即可。

> **关于 wrapper jar**：仓库只提交了 `gradlew`、`gradlew.bat` 和 `gradle-wrapper.properties`，没有提交二进制的 `gradle-wrapper.jar`。workflow 会在编译前用 `gradle wrapper` 命令自动补全它，本地用 Android Studio 打开时也会自动处理。如果你本地要直接跑 `./gradlew`，可执行一次 `gradle wrapper`（需本机装 gradle）生成 jar。

> **关于签名**：release APK 是未签名的（`app-release-unsigned.apk`），安装时安卓会提示"未知来源"。如需正式签名，在 `app/build.gradle.kts` 的 `signingConfigs` 配置 keystore，并把密码存为 GitHub Secrets。

---

## 配置在线消歧

App 内：右上角 ⚙️ 设置

| 项 | 默认 | 说明 |
|---|---|---|
| 启用在线语境消歧 | 开 | 关闭则纯离线 |
| API Base URL | `https://open.bigmodel.cn/api/paas/v4/` | OpenAI 兼容格式 |
| API Key | （空） | 智谱/GLM 去 open.bigmodel.cn 申请 |
| 模型名 | `glm-4-flash` | 智谱免费档；可换 `deepseek-chat` 等 |

**断网行为**：消歧静默失败，沿用离线统计排序结果，不影响查词。

---

## 目录结构

```
android/
├── build.gradle.kts              # 根构建
├── settings.gradle.kts
├── gradle.properties
├── README.md                     # 本文件
├── MIGRATION.md                  # PC 版 → 安卓版 的代码映射
└── app/
    ├── build.gradle.kts          # 依赖（含 RapidOCR 接入说明）
    ├── proguard-rules.pro
    └── src/main/
        ├── AndroidManifest.xml
        ├── assets/
        │   ├── web/              # ★ 前端（改造自 PC 版 static/）
        │   │   ├── index.html
        │   │   ├── app.js
        │   │   └── style.css
        │   ├── models/           # ★ 放 OCR onnx 模型（det/rec/cls + 字典）
        │   └── dict/             # （可选）word_details_mini.db
        ├── java/com/dreamword/app/
        │   ├── MainActivity.kt           # WebView 壳
        │   ├── data/
        │   │   ├── Models.kt             # 数据类（WordEntry/LookupResult/OcrWord）
        │   │   └── KnownWordsDao.kt      # 已知词库 SQLite
        │   ├── dict/
        │   │   ├── MdxParser.kt          # HTML→WordEntry
        │   │   ├── DictRepository.kt     # 词典 SQLite 访问
        │   │   ├── InflectionResolver.kt # 形态规则（found→find）
        │   │   ├── SimilarityScorer.kt   # 离线语境打分
        │   │   ├── WordLookup.kt         # 查词主流程
        │   │   └── Disambiguator.kt      # 在线 LLM 消歧
        │   ├── ocr/
        │   │   ├── OcrEngine.kt          # OCR 接口 + 工厂
        │   │   └── RapidOcrEngineImpl.kt # RapidOCR 实现（★ 接入点）
        │   ├── bridge/
        │   │   ├── NativeBridge.kt       # @JavascriptInterface 桥
        │   │   └── AnnotationRenderer.kt # 标注图绘制
        │   └── ui/settings/SettingsActivity.kt
        └── res/                          # 资源（图标/主题/设置页）
```

## 许可证

继承主项目 GPLv3。
