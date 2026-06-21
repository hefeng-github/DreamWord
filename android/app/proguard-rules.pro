# RapidOCR / onnxruntime 反射调用，不要混淆
-keep class ai.djl.** { *; }
-keep class com.onnxruntime.** { *; }
-keep class com.baidu.dcs.** { *; }
-keep class io.github.mymonstercat.** { *; }
-keep class com.dreamword.app.** { *; }
-dontwarn org.slf4j.**
