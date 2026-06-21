plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

// ---- 签名配置 ----
// 三种来源，按优先级读取：
//   1) GitHub Actions Secrets（CI 用）：SIGNING_KEYSTORE_BASE64 / SIGNING_KEY_ALIAS /
//      SIGNING_KEY_PASSWORD / SIGNING_STORE_PASSWORD（环境变量）
//   2) 本地 keystore.properties（本地开发用，已 gitignore）：
//      storeFile / storePassword / keyAlias / keyPassword
//   3) 都没有时使用 debug 签名（release APK 仍能安装，但每次构建签名可能变化）
val keystorePropsFile = rootProject.file("keystore.properties")
val hasEnvSigning = System.getenv("SIGNING_KEYSTORE_BASE64") != null
val hasPropsSigning = keystorePropsFile.exists()

android {
    namespace = "com.dreamword.app"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.dreamword.app"
        minSdk = 24
        targetSdk = 34
        versionCode = 1
        versionName = "1.0.0"
    }

    // 签名配置：优先环境变量（CI），其次本地 keystore.properties
    signingConfigs {
        create("release") {
            if (hasEnvSigning) {
                // CI 场景：keystore 由 workflow 从 Secret 还原到 app/release.keystore
                storeFile = file("release.keystore")
                storePassword = System.getenv("SIGNING_STORE_PASSWORD")
                keyAlias = System.getenv("SIGNING_KEY_ALIAS")
                keyPassword = System.getenv("SIGNING_KEY_PASSWORD")
            } else if (hasPropsSigning) {
                // 本地场景：读 keystore.properties
                val props = java.util.Properties()
                keystorePropsFile.inputStream().use { props.load(it) }
                storeFile = file(props.getProperty("storeFile"))
                storePassword = props.getProperty("storePassword")
                keyAlias = props.getProperty("keyAlias")
                keyPassword = props.getProperty("keyPassword")
            }
            // 都没有时：不配置，release 用默认 debug 签名（能安装，适合测试）
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
            // 有正式签名配置则用，否则用 debug 签名（保证 release APK 也能安装）
            if (hasEnvSigning || hasPropsSigning) {
                signingConfig = signingConfigs.getByName("release")
            } else {
                signingConfig = signingConfigs.getByName("debug")
            }
        }
    }

    // 不对 assets 里的 441MB 词典压缩（SQLite 已是压缩格式，再压缩无收益且拖慢首次读取）
    androidResources {
        noCompress += listOf("db", "onnx", "txt")
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }

    // RapidOcrAndroidOnnx 内部带 native so，需放开打包
    packaging {
        jniLibs {
            useLegacyPackaging = true
        }
        resources {
            excludes += listOf(
                "META-INF/AL2.0",
                "META-INF/LGPL2.1",
                "META-INF/DEPENDENCIES",
                "META-INF/*.kotlin_module"
            )
        }
    }

    buildFeatures {
        viewBinding = true
    }
}

dependencies {
    // ---- AndroidX 基础 ----
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.appcompat:appcompat:1.7.0")
    implementation("androidx.activity:activity-ktx:1.9.0")
    implementation("androidx.constraintlayout:constraintlayout:2.1.4")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.8.3")
    implementation("androidx.preference:preference-ktx:1.2.1")
    implementation("androidx.security:security-crypto:1.1.0-alpha06")

    // ---- WebView + Material ----
    implementation("com.google.android.material:material:1.12.0")

    // ---- JSON ----
    implementation("com.google.code.gson:gson:2.11.0")

    // ---- HTML 解析（移植 MDXParser 用）----
    implementation("org.jsoup:jsoup:1.18.1")

    // ---- 网络（消歧在线 API / OneDrive OAuth / 词典下载）----
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("com.squareup.okhttp3:logging-interceptor:4.12.0")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.8.1")

    // ---- OCR：RapidOcrAndroidOnnx（PP-OCRv4，离线，APK 自带模型）----
    // aar 由 GitHub Actions 编译前从 RapidOcrAndroidOnnx release 自动下载到 app/libs/。
    // 库主页：https://github.com/RapidAI/RapidOcrAndroidOnnx
    // 本地开发时，手动从该 release 下载 OcrLibrary-x.x.x-release.aar 放到 app/libs/。
    implementation(fileTree(mapOf("dir" to "libs", "include" to listOf("*.aar", "*.jar"))))
}
