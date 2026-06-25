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
| 拍照点词（标记已会词）| ✅ | PP-OCRv6 onnx |
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

### 步骤 1：OCR（CI 全自动；本地编译需手动放模型）

OCR 用 **PP-OCRv6 small onnx**（det+rec 两段式，离线），推理用 [onnxruntime-android](https://github.com/microsoft/onnxruntime)，预处理/后处理在 `OnnxOcrEngineImpl` 自实现（DB 检测后处理 + CTC 识别解码）。

模型（det.onnx ~9.4MB / rec.onnx ~20MB / keys.txt ~73KB）取自 [MaaCommonAssets](https://github.com/MaaXYZ/MaaCommonAssets/tree/main/OCR/ppocr_v6/small)，**不入仓库**。

- **CI 编译时**：GitHub Actions 自动用 `curl` 从 MaaCommonAssets 下载这 3 个文件到 `app/src/main/assets/models/`，APK 自带 OCR，**开箱即用**。
- **本地编译时**：手动执行（在仓库根目录）：
  ```bash
  mkdir -p android/app/src/main/assets/models
  BASE="https://raw.githubusercontent.com/MaaXYZ/MaaCommonAssets/main/OCR/ppocr_v6/small"
  curl -fSL -o android/app/src/main/assets/models/det.onnx  "$BASE/det.onnx"
  curl -fSL -o android/app/src/main/assets/models/rec.onnx  "$BASE/rec.onnx"
  curl -fSL -o android/app/src/main/assets/models/keys.txt  "$BASE/keys.txt"
  ```
  （这 3 个文件已被 `.gitignore` 排除，不会误提交。）

### 步骤 2：词典（App 内手动导入）

词典（441MB）不打包进 APK。把 PC 版的 `databases/word_details.db` 放到手机指定目录，App 自动检测加载：

**方式 A：adb 推送（推荐）**

把 .db 推到应用专属外部存储目录（adb 可直接访问，无需 root）：
```
adb push databases/word_details.db /sdcard/Android/data/com.dreamword.app/files/dict/word_details.db
```
> 若目录不存在，先建：`adb shell mkdir -p /sdcard/Android/data/com.dreamword.app/files/dict`

**方式 B：文件管理器**

用手机文件管理器，把 `word_details.db` 放到：
```
内部存储/Android/data/com.dreamword.app/files/dict/
```
> 精确路径以 App 内「📚 词库」Tab →「📖 词典」卡片显示的「导入路径」为准（不同机型外部存储根路径可能不同）。

**放好后**：打开 App → 词库 Tab → 词典卡片 → 点「🔄 重新加载词典」，提示"词典加载成功"即可查词。

> 未导入词典时 App 仍可启动，查词提示"词典未就绪"，其他功能（OCR 点词标记、词库管理、OneDrive 备份）不受影响。

### 步骤 3：运行

**用 GitHub Actions（推荐，无需本地环境）**

push 到 `main` 分支即自动编译，或到 Actions 页面手动触发。编译成功后下载 `DreamWord-debug` artifact，解压得到 APK，传手机安装。详见下方「用 GitHub Actions 在线编译」。

**用 Android Studio 本地编译**

```
用 Android Studio 打开 android/ 目录，等 Gradle 同步完成，点 Run。
```

> 命令行编译（需装好 SDK）：
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
3. 下载 `DreamWord-debug`（调试版）或 `DreamWord-release`（发布版，已签名）

下载下来是 zip，解压得到 `.apk`，传到手机安装即可。

> **关于 wrapper jar**：仓库只提交了 `gradlew`、`gradlew.bat` 和 `gradle-wrapper.properties`，没有提交二进制的 `gradle-wrapper.jar`。workflow 会在编译前用 `gradle wrapper` 命令自动补全它，本地用 Android Studio 打开时也会自动处理。如果你本地要直接跑 `./gradlew`，可执行一次 `gradle wrapper`（需本机装 gradle）生成 jar。

## 签名配置

**默认行为**：CI 编译出的 release APK 自动用 **debug 签名**（能直接安装，但每次构建签名可能变化，覆盖安装时安卓会提示"签名不一致需先卸载"）。

**正式签名（推荐，让每次 CI 出的 APK 签名固定）**：在 GitHub 仓库 Settings → Secrets and variables → Actions 添加 4 个 Secret：

| Secret 名 | 值 |
|---|---|
| `SIGNING_KEYSTORE_BASE64` | keystore 文件的 base64（见下方生成方法） |
| `SIGNING_STORE_PASSWORD` | keystore 密码 |
| `SIGNING_KEY_ALIAS` | key 别名 |
| `SIGNING_KEY_PASSWORD` | key 密码 |

生成 base64（在项目根目录执行，用本地已生成的 `android/app/release.keystore`）：
```bash
# Linux/Mac/Git Bash
base64 -w 0 android/app/release.keystore
# Windows PowerShell
[Convert]::ToBase64String([IO.File]::ReadAllBytes("android\app\release.keystore"))
```
把输出的整串 base64 填入 `SIGNING_KEYSTORE_BASE64` Secret。

> 生成自己的 keystore（有效 10000 天）：
> ```
> keytool -genkeypair -v -keystore release.keystore -alias dreamword \
>   -keyalg RSA -keysize 2048 -validity 10000
> ```
> keystore 文件和密码不要提交到仓库（`.gitignore` 已排除 `app/release.keystore` 和 `keystore.properties`）。

**本地编译签名**：把 keystore 放到 `android/app/release.keystore`，在 `android/keystore.properties` 填写：
```properties
storeFile=app/release.keystore
storePassword=<你的密码>
keyAlias=<你的别名>
keyPassword=<你的密码>
```
`build.gradle.kts` 会自动读取。

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
        ├── build.gradle.kts          # 依赖（含 onnxruntime-android 接入说明）
        ├── proguard-rules.pro
        └── src/main/
            ├── AndroidManifest.xml
            ├── assets/
            │   ├── web/              # ★ 前端（改造自 PC 版 static/）
            │   │   ├── index.html
            │   │   ├── app.js
            │   │   └── style.css
            │   ├── models/           # ★ 放 PP-OCRv6 onnx 模型（det/rec/keys，CI 下载）
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
            │   │   ├── WordLookup.kt         # 查词主流程（大小写兜底 + cached 长连接）
            │   │   ├── OcrLookupPipeline.kt  # 拍照查词管线（OCR→生词→标注）
            │   │   └── Disambiguator.kt      # 在线 LLM 消歧
            │   ├── ocr/
            │   │   ├── OcrEngine.kt          # OCR 接口 + 工厂
            │   │   └── OnnxOcrEngineImpl.kt  # PP-OCRv6 onnxruntime 实现（★ 核心管线）
            │   ├── bridge/
            │   │   ├── NativeBridge.kt       # @JavascriptInterface 桥
            │   │   └── AnnotationRenderer.kt # 标注图绘制
            │   └── ui/settings/SettingsActivity.kt
            └── res/                          # 资源（图标/主题/设置页）
```

## 许可证

继承主项目 GPLv3。
