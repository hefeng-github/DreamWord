pluginManagement {
    repositories {
        google {
            content {
                includeGroupByRegex("com\\.android.*")
                includeGroupByRegex("com\\.google.*")
                includeGroupByRegex("androidx.*")
            }
        }
        mavenCentral()
        gradlePluginPortal()
    }
}
dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
        // RapidOcrAndroidOnnx / RapidOCR 相关产物发布在 jitpack / maven central
        maven { url = uri("https://jitpack.io") }
    }
}

rootProject.name = "DreamWord"
include(":app")
