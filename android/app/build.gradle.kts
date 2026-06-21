plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

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

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
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
