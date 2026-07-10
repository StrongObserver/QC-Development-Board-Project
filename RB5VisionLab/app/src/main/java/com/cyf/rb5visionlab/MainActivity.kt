package com.cyf.rb5visionlab

import android.Manifest
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.graphics.Matrix
import android.os.Bundle
import android.util.Log
import android.util.Size
import android.view.View
import android.widget.Button
import android.widget.ImageView
import android.widget.TextView
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.enableEdgeToEdge
import androidx.appcompat.app.AppCompatActivity
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.ImageProxy
import androidx.camera.core.Preview
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.core.resolutionselector.ResolutionSelector
import androidx.camera.core.resolutionselector.ResolutionStrategy
import androidx.camera.view.PreviewView
import androidx.core.content.ContextCompat
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors

class MainActivity : AppCompatActivity() {

    companion object {
        private const val TAG = "RB5"
        private const val CAMERA_TAG = "RB5_CAMERA"

        init {
            System.loadLibrary("opencv_java4")
            System.loadLibrary("rb5visionlab")
        }
    }

    private lateinit var cameraExecutor: ExecutorService
    private lateinit var statusTextView: TextView
    private lateinit var nativeMessage: String
    private var frameCount = 0
    private var resolver: SuperResolver? = null
    @Volatile private var liveSr = false
    private lateinit var srResultView: ImageView

    private val requestCameraPermission =
        registerForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
            if (granted) {
                startCamera()
            } else {
                Log.e(CAMERA_TAG, "Camera permission denied")
            }
        }

    external fun stringFromJNI(): String
    external fun processYPlane(yData: ByteArray, width: Int, height: Int, rowStride: Int): String

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        Log.d(TAG, "Hello RB5 from MainActivity onCreate")

        enableEdgeToEdge()
        setContentView(R.layout.activity_main)

        nativeMessage = stringFromJNI()
        Log.d(TAG, nativeMessage)

        statusTextView = findViewById(R.id.textView)
        statusTextView.text = nativeMessage

        cameraExecutor = Executors.newSingleThreadExecutor()
        setupSuperResolution()
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED) {
            startCamera()
        } else {
            requestCameraPermission.launch(Manifest.permission.CAMERA)
        }

        ViewCompat.setOnApplyWindowInsetsListener(findViewById(R.id.main)) { v, insets ->
            val systemBars = insets.getInsets(WindowInsetsCompat.Type.systemBars())
            v.setPadding(systemBars.left, systemBars.top, systemBars.right, systemBars.bottom)
            insets
        }
    }

    private fun setupSuperResolution() {
        val srButton = findViewById<Button>(R.id.sr_button)
        srResultView = findViewById(R.id.sr_result)
        val previewView = findViewById<PreviewView>(R.id.previewView)
        srButton.text = "实时超分 ROI (CPU)"
        // Toggle live super-resolution on the camera's center ROI.
        srButton.setOnClickListener {
            liveSr = !liveSr
            if (liveSr) {
                previewView.visibility = View.GONE
                srResultView.visibility = View.VISIBLE
                srButton.text = "停止实时超分"
                statusTextView.text = "Live ROI super-resolution starting..."
            } else {
                srResultView.visibility = View.GONE
                previewView.visibility = View.VISIBLE
                srButton.text = "实时超分 ROI (CPU)"
            }
        }
    }

    /**
     * C6 + B5: take the center 128x128 ROI of the current camera frame, run
     * super-resolution, show the 512x512 result, and report per-stage timing.
     * Runs on cameraExecutor (the analyzer thread); with KEEP_ONLY_LATEST, frames
     * are dropped while one is being processed, giving near-real-time output.
     */
    private fun runLiveSr(imageProxy: ImageProxy) {
        val srTag = "RB5_SR"
        try {
            if (resolver == null) resolver = SuperResolver(this)
            val tCap0 = System.nanoTime()
            val full = imageProxy.toBitmap()
            val side = 128
            if (full.width < side || full.height < side) return
            val left = (full.width - side) / 2
            val top = (full.height - side) / 2
            var roi = Bitmap.createBitmap(full, left, top, side, side)
            val degrees = imageProxy.imageInfo.rotationDegrees
            if (degrees != 0) {
                val matrix = Matrix().apply { postRotate(degrees.toFloat()) }
                roi = Bitmap.createBitmap(roi, 0, 0, side, side, matrix, true)
            }
            val captureMs = (System.nanoTime() - tCap0) / 1_000_000
            val (out, t) = resolver!!.enhance(roi)
            val e2eMs = captureMs + t.totalMs
            Log.d(
                srTag,
                "live ROI 128->512 cap=$captureMs pre=${t.preprocessMs} inf=${t.inferenceMs} post=${t.postprocessMs} e2e=${e2eMs}ms"
            )
            runOnUiThread {
                srResultView.setImageBitmap(out)
                statusTextView.text =
                    "Live ROI SR (TFLite CPU)\n" +
                        "capture+crop ${captureMs} ms | preprocess ${t.preprocessMs} ms\n" +
                        "inference ${t.inferenceMs} ms | postprocess ${t.poprocessMs} ms\n" +
                        "end-to-end ~${e2eMs} ms"
            }
        } catch (e: Exception) {
            Log.e(srTag, "live SR failed", e)
        }
    }

    private fun startCamera() {
        val previewView = findViewById<PreviewView>(R.id.previewView)
        val cameraProviderFuture = ProcessCameraProvider.getInstance(this)

        cameraProviderFuture.addListener({
            val cameraProvider = cameraProviderFuture.get()
            val preview = Preview.Builder().build().also {
                it.surfaceProvider = previewView.surfaceProvider
            }
            val imageAnalysis = ImageAnalysis.Builder()
                .setResolutionSelector(
                    ResolutionSelector.Builder()
                        .setResolutionStrategy(
                            ResolutionStrategy(
                                Size(640, 480),
                                ResolutionStrategy.FALLBACK_RULE_CLOSEST_LOWER_THEN_HIGHER
                            )
                        )
                        .build()
                )
                .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                .build()
                .also {
                    it.setAnalyzer(cameraExecutor) { imageProxy ->
                        try {
                            frameCount++
                            if (liveSr) {
                                runLiveSr(imageProxy)
                            } else if (frameCount == 1 || frameCount % 30 == 0) {
                                val yPlane = imageProxy.planes[0]
                                val yBuffer = yPlane.buffer
                                val yData = ByteArray(yBuffer.remaining())
                                yBuffer.get(yData)
                                val nativeResult = processYPlane(
                                    yData,
                                    imageProxy.width,
                                    imageProxy.height,
                                    yPlane.rowStride
                                )
                                val frameStatus =
                                    "frame=$frameCount\nwidth=${imageProxy.width}\nheight=${imageProxy.height}\nformat=${imageProxy.format}\n$nativeResult"
                                Log.d(
                                    CAMERA_TAG,
                                    "$frameStatus timestamp=${imageProxy.imageInfo.timestamp}"
                                )
                                runOnUiThread {
                                    statusTextView.text = "$nativeMessage\n\n$frameStatus"
                                }
                            }
                        } finally {
                            // Always release the frame, even on error, or ImageAnalysis stalls.
                            imageProxy.close()
                        }
                    }
                }

            try {
                cameraProvider.unbindAll()
                cameraProvider.bindToLifecycle(
                    this,
                    CameraSelector.DEFAULT_BACK_CAMERA,
                    preview,
                    imageAnalysis
                )
                Log.d(CAMERA_TAG, "CameraX preview and ImageAnalysis started")
            } catch (exc: Exception) {
                Log.e(CAMERA_TAG, "CameraX bind failed", exc)
            }
        }, ContextCompat.getMainExecutor(this))
    }

    override fun onDestroy() {
        super.onDestroy()
        liveSr = false
        // Close the interpreter on the same single-thread executor so it cannot run
        // concurrently with an in-flight enhance() (closing during run() can crash).
        // Submitting before shutdown() queues it after any pending SR task (FIFO).
        cameraExecutor.execute { resolver?.close() }
        cameraExecutor.shutdown()
    }
}
