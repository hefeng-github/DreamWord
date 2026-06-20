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

    // ---- OCR：RapidOcrAndroidOnnx（PaddleOCR PP-OCRv4 onnx，离线）----
    // 官方推荐通过源码集成；Maven 中央仓也发布了 io.github.mymonstercat 系列。
    // 两种方式任选其一：
    //   方式 A（推荐，体积更小、可控）：从 https://github.com/RapidAI/RapidOcrAndroidOnnx
    //         下载源码作为 module 引入；模型放到本模块 assets/models/（见 README）。
    //   方式 B（Maven 一行依赖，开箱即用）：
    //         implementation("io.github.mymonstercat:rapidocr-onnx-platform:0.0.7")
    // 这里默认走方式 A 的接口约定，OcrEngine 持有 RapidOCR 实例；
    // 若用方式 B，把对应类换成 RapidOCR 即可（API 几乎一致）。
}
