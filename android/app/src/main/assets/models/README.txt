此目录放 PP-OCRv6 small onnx 模型。模型已被 .gitignore 排除，不入仓库。

来源：https://github.com/MaaXYZ/MaaCommonAssets/tree/main/OCR/ppocr_v6/small

需要 3 个文件（CI 编译时自动下载到此处）：
  det.onnx   (9.4MB，PP-OCRv6 small 文字检测)
  rec.onnx   (20MB， PP-OCRv6 small 文字识别)
  keys.txt   (73KB， 识别字符表)

【本地开发】手动下载（在仓库根目录执行）：
  mkdir -p android/app/src/main/assets/models
  BASE="https://raw.githubusercontent.com/MaaXYZ/MaaCommonAssets/main/OCR/ppocr_v6/small"
  curl -fSL -o android/app/src/main/assets/models/det.onnx  "$BASE/det.onnx"
  curl -fSL -o android/app/src/main/assets/models/rec.onnx  "$BASE/rec.onnx"
  curl -fSL -o android/app/src/main/assets/models/keys.txt  "$BASE/keys.txt"

【CI 编译】见 .github/workflows/build-android.yml 的「Download PP-OCRv6 models」步骤。

推理用 onnxruntime-android，DB 检测后处理 + CTC 识别解码在 OnnxOcrEngineImpl 自实现。
详见 android/README.md 的「步骤 1」。
