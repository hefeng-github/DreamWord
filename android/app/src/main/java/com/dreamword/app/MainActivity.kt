package com.dreamword.app

import android.Manifest
import android.annotation.SuppressLint
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Bundle
import android.webkit.PermissionRequest
import android.webkit.ValueCallback
import android.webkit.WebChromeClient
import android.webkit.WebSettings
import android.webkit.WebView
import androidx.activity.OnBackPressedCallback
import androidx.activity.result.ActivityResultLauncher
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import com.dreamword.app.bridge.NativeBridge
import com.dreamword.app.databinding.ActivityMainBinding
import com.dreamword.app.dict.DictRepository
import com.dreamword.app.ocr.OcrEngine

class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    private lateinit var bridge: NativeBridge
    private var ocrEngine: OcrEngine? = null

    /** WebView file input 回调（用于网页里的拍照/上传）*/
    private var filePathCallback: ValueCallback<Array<Uri>>? = null
    private lateinit var fileChooserLauncher: ActivityResultLauncher<Intent>

    private val cameraPermissionLauncher =
        registerForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
            // 由 WebView 的 onPermissionRequest 触发；这里仅记录，权限提示由系统展示
        }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)
        setSupportActionBar(binding.toolbar)
        binding.toolbar.title = "DreamWord"

        // 返回键：WebView 能后退则后退，否则退出
        onBackPressedDispatcher.addCallback(this, object : OnBackPressedCallback(true) {
            override fun handleOnBackPressed() {
                if (binding.webView.canGoBack()) binding.webView.goBack()
                else { isEnabled = false; onBackPressed() }
            }
        })

        // file input 选择器
        fileChooserLauncher = registerForActivityResult(
            ActivityResultContracts.StartActivityForResult()
        ) { result ->
            val uris = if (result.resultCode == RESULT_OK) {
                result.data?.data?.let { arrayOf(it) }
                    ?: result.data?.clipData?.let { cd ->
                        Array(cd.itemCount) { i -> cd.getItemAt(i).uri }
                    }
            } else null
            filePathCallback?.onReceiveValue(uris)
            filePathCallback = null
        }

        setupWebView()
        ensureCameraPermission()
    }

    @SuppressLint("SetJavaScriptEnabled")
    private fun setupWebView() {
        // 初始化原生能力（懒加载）
        val dict = DictRepository.resolve(this)
        ocrEngine = OcrEngine.create(this)

        bridge = NativeBridge(
            context = this,
            dict = dict,
            ocr = ocrEngine!!,
            coroutineScope = lifecycleScope  // 来自 androidx.lifecycle
        )

        with(binding.webView) {
            // 关键设置
            settings.javaScriptEnabled = true
            settings.domStorageEnabled = true
            settings.databaseEnabled = true
            settings.allowFileAccess = true
            settings.allowContentAccess = true
            settings.mediaPlaybackRequiresUserGesture = false
            settings.cacheMode = WebSettings.LOAD_DEFAULT
            // 视口适配（触屏）
            settings.useWideViewPort = true
            settings.loadWithOverviewMode = true
            settings.builtInZoomControls = false

            // 注入 NativeBridge：前端通过 window.NativeBridge.xxx() 调用
            addJavascriptInterface(bridge, "NativeBridge")

            // 相机权限 + file input 回调
            webChromeClient = object : WebChromeClient() {
                override fun onPermissionRequest(request: PermissionRequest) {
                    // 摄像头权限：检查并自动授予
                    val needed = request.resources.filter { res ->
                        res == PermissionRequest.RESOURCE_VIDEO_CAPTURE
                    }.toTypedArray()
                    if (needed.isEmpty()) { request.deny(); return }
                    if (hasCameraPermission()) {
                        runOnUiThread { request.grant(needed) }
                    } else {
                        cameraPermissionLauncher.launch(Manifest.permission.CAMERA)
                        // 授权完成后再尝试授予（延迟一点）
                        binding.webView.postDelayed({
                            if (hasCameraPermission()) request.grant(needed) else request.deny()
                        }, 800)
                    }
                }

                override fun onShowFileChooser(
                    webView: WebView?,
                    cb: ValueCallback<Array<Uri>>?,
                    params: FileChooserParams?
                ): Boolean {
                    filePathCallback?.onReceiveValue(null)
                    filePathCallback = cb
                    val intent = params?.createIntent()?.apply {
                        // 允许相机 + 图库
                        putExtra(Intent.EXTRA_MIME_TYPES, arrayOf("image/*"))
                    } ?: Intent(Intent.ACTION_GET_CONTENT).apply { type = "image/*" }
                    return try {
                        fileChooserLauncher.launch(intent)
                        true
                    } catch (e: Exception) {
                        filePathCallback = null
                        false
                    }
                }
            }

            // 加载本地前端（assets/web/index.html）
            loadUrl("file:///android_asset/web/index.html")
        }
    }

    private fun ensureCameraPermission() {
        if (!hasCameraPermission()) {
            cameraPermissionLauncher.launch(Manifest.permission.CAMERA)
        }
    }

    private fun hasCameraPermission(): Boolean =
        ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA) ==
            PackageManager.PERMISSION_GRANTED

    /** 工具栏菜单 */
    override fun onCreateOptionsMenu(menu: android.view.Menu): Boolean {
        menuInflater.inflate(R.menu.menu_main, menu)
        return true
    }

    override fun onOptionsItemSelected(item: android.view.MenuItem): Boolean {
        return when (item.itemId) {
            R.id.action_settings -> {
                startActivity(Intent(this, com.dreamword.app.ui.settings.SettingsActivity::class.java))
                true
            }
            else -> super.onOptionsItemSelected(item)
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        ocrEngine?.release()
        binding.webView.destroy()
    }
}
