package com.titan.v80

import android.annotation.SuppressLint
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.View
import android.webkit.WebChromeClient
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform
import java.util.concurrent.Executors

class MainActivity : AppCompatActivity() {

    private lateinit var webView: WebView
    private lateinit var loadingPanel: LinearLayout
    private lateinit var loadingText: TextView
    private val io = Executors.newSingleThreadExecutor()
    private val ui = Handler(Looper.getMainLooper())
    private var started = false

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        // Chaquopy requires AndroidPlatform before any Python use
        if (!Python.isStarted()) {
            Python.start(AndroidPlatform(this))
        }

        webView = findViewById(R.id.webview)
        loadingPanel = findViewById(R.id.loadingPanel)
        loadingText = findViewById(R.id.loadingText)

        val s = webView.settings
        s.javaScriptEnabled = true
        s.domStorageEnabled = true
        s.databaseEnabled = true
        s.mixedContentMode = WebSettings.MIXED_CONTENT_ALWAYS_ALLOW
        s.useWideViewPort = true
        s.loadWithOverviewMode = true
        s.cacheMode = WebSettings.LOAD_DEFAULT
        s.userAgentString = s.userAgentString + " TITAN-V80-Full"

        webView.webChromeClient = WebChromeClient()
        webView.webViewClient = object : WebViewClient() {
            override fun onPageFinished(view: WebView?, url: String?) {
                if (url != null && (url.contains("127.0.0.1") || url.contains("localhost"))) {
                    loadingPanel.visibility = View.GONE
                }
            }
        }

        bootEngine()
    }

    private fun bootEngine() {
        loadingPanel.visibility = View.VISIBLE
        loadingText.text = "در حال راه‌اندازی موتور TITAN V80…"
        io.execute {
            try {
                val py = Python.getInstance()
                val boot = py.getModule("titan_bootstrap")
                if (!started) {
                    val result = boot.callAttr("start_titan", filesDir.absolutePath).toString()
                    started = true
                    ui.post { loadingText.text = "وضعیت: $result\nمنتظر داشبورد… (حداکثر ۲ دقیقه)" }
                }
                // Wait up to 120 seconds
                val ready = boot.callAttr("wait_ready", "http://127.0.0.1:8080/", 120.0).toBoolean()
                ui.post {
                    val err = try {
                        boot.callAttr("last_error").toString()
                    } catch (_: Exception) {
                        ""
                    }
                    if (ready) {
                        loadingText.text = "آماده شد"
                    } else {
                        loadingText.text = "موتور کامل بالا نیامد.\n$err\nدر حال باز کردن صفحه…"
                        if (err.isNotBlank()) {
                            Toast.makeText(this, err.take(200), Toast.LENGTH_LONG).show()
                        }
                    }
                    // Always try to open the page (fallback server will answer if full engine failed)
                    webView.loadUrl("http://127.0.0.1:8080/")
                    // Hide spinner after a short delay even if page is slow
                    ui.postDelayed({
                        loadingPanel.visibility = View.GONE
                    }, 3000)
                }
            } catch (e: Exception) {
                ui.post {
                    loadingText.text = "خطای موتور:\n${e.message}"
                    Toast.makeText(this, e.message ?: "error", Toast.LENGTH_LONG).show()
                    // Still try to load something
                    webView.loadUrl("http://127.0.0.1:8080/")
                    ui.postDelayed({
                        loadingPanel.visibility = View.GONE
                    }, 4000)
                }
            }
        }
    }

    @Deprecated("Deprecated in Java")
    override fun onBackPressed() {
        if (webView.canGoBack()) webView.goBack() else super.onBackPressed()
    }
}
