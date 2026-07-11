package com.cyf.rb5visionlab

import android.Manifest
import android.content.ContentValues
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.graphics.Matrix
import android.os.Bundle
import android.os.Environment
import android.provider.MediaStore
import android.util.Log
import android.view.View
import android.widget.Button
import android.widget.ImageView
import android.widget.TextView
import android.widget.Toast
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
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors

class MainActivity : AppCompatActivity() {

    companion object {
        private const val TAG = "RB5"
        private const val CAMERA_TAG = "RB5_CAMERA"
        private const val LEGACY_ANALYSIS_WIDTH = 640

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
    @Volatile private var srBackend = SrBackend.CPU
    @Volatile private var liveSr = false
    private lateinit var srResultView: ImageView
    private val srSampleLock = Any()
    private var latestSrSample: SrSample? = null
    private var highResResolver: SuperResolver? = null
    @Volatile private var pendingHighResSample = false

    private data class SrSample(
        val backend: SrBackend,
        val label: String,
        val input: Bitmap,
        val baseline: Bitmap,
        val sr: Bitmap,
        val inferenceMs: Long,
        val e2eMs: Long,
    )

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
        val saveSampleButton = findViewById<Button>(R.id.save_sample_button)
        srResultView = findViewById(R.id.sr_result)
        val previewView = findViewById<PreviewView>(R.id.previewView)
        srButton.text = startButtonText()
        saveSampleButton.setOnClickListener { saveLatestSrSample() }
        saveSampleButton.setOnLongClickListener {
            requestHighResSrSample()
            true
        }
        // Toggle live super-resolution on the camera's center ROI.
        srButton.setOnClickListener {
            liveSr = !liveSr
            if (liveSr) {
                previewView.visibility = View.GONE
                srResultView.visibility = View.VISIBLE
                srButton.text = "停止实时超分"
                statusTextView.text = "Live ROI SR starting with ${srBackend.label} backend..."
            } else {
                srResultView.visibility = View.GONE
                previewView.visibility = View.VISIBLE
                srButton.text = startButtonText()
            }
        }
        srButton.setOnLongClickListener {
            if (liveSr) {
                statusTextView.text = "Stop live SR before switching backend."
                return@setOnLongClickListener true
            }
            cycleSrBackend()
            srButton.text = if (liveSr) "停止实时超分" else startButtonText()
            statusTextView.text = "SR backend switched to ${srBackend.label}. Tap to run; long press to switch backend."
            true
        }
    }

    private fun startButtonText(): String = "实时超分 ROI (${srBackend.label})"

    private fun cycleSrBackend() {
        srBackend = when (srBackend) {
            SrBackend.CPU -> SrBackend.NNAPI
            SrBackend.NNAPI -> SrBackend.GPU
            SrBackend.GPU -> SrBackend.CPU
        }
        val oldResolver = resolver
        resolver = null
        cameraExecutor.execute {
            oldResolver?.close()
        }
        Log.d("RB5_SR", "SR backend switched to ${srBackend.label}")
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
            if (resolver?.backend != srBackend) {
                resolver?.close()
                resolver = null
            }
            if (resolver == null) resolver = SuperResolver(this, backend = srBackend)
            val tCap0 = System.nanoTime()
            val full = imageProxy.toBitmap()
            val side = 128
            if (full.width < side || full.height < side) return
            val (croppedRoi, cropSide) = cropCenterRoiKeepingLegacyFov(full, side)
            var roi = croppedRoi
            val degrees = imageProxy.imageInfo.rotationDegrees
            if (degrees != 0) {
                val matrix = Matrix().apply { postRotate(degrees.toFloat()) }
                roi = Bitmap.createBitmap(roi, 0, 0, side, side, matrix, true)
            }
            val captureMs = (System.nanoTime() - tCap0) / 1_000_000
            val (out, t) = resolver!!.enhance(roi)
            val e2eMs = captureMs + t.totalMs
            val baseline = Bitmap.createScaledBitmap(roi, 512, 512, true)
            synchronized(srSampleLock) {
                latestSrSample = SrSample(
                    backend = srBackend,
                    label = "D7",
                    input = roi.copy(Bitmap.Config.ARGB_8888, false),
                    baseline = baseline,
                    sr = out.copy(Bitmap.Config.ARGB_8888, false),
                    inferenceMs = t.inferenceMs,
                    e2eMs = e2eMs,
                )
            }
            Log.d(
                srTag,
                "backend=${srBackend.label} live ROI crop=${cropSide}->128->512 frame=${full.width}x${full.height} cap=$captureMs pre=${t.preprocessMs} inf=${t.inferenceMs} post=${t.postprocessMs} e2e=${e2eMs}ms"
            )
            runOnUiThread {
                srResultView.setImageBitmap(out)
                statusTextView.text =
                    "Live ROI SR (TFLite ${srBackend.label})\n" +
                        "frame ${full.width}x${full.height} | ROI ${cropSide}->128\n" +
                        "capture+crop ${captureMs} ms | preprocess ${t.preprocessMs} ms\n" +
                        "inference ${t.inferenceMs} ms | postprocess ${t.postprocessMs} ms\n" +
                        "end-to-end ~${e2eMs} ms"
            }
        } catch (e: Throwable) {
            Log.e(srTag, "live SR failed", e)
            liveSr = false
            runOnUiThread {
                srResultView.visibility = View.GONE
                findViewById<PreviewView>(R.id.previewView).visibility = View.VISIBLE
                findViewById<Button>(R.id.sr_button).text = startButtonText()
                statusTextView.text = "Live SR failed on ${srBackend.label}. Long press to choose another backend."
            }
        }
    }

    private fun saveLatestSrSample() {
        val sample = synchronized(srSampleLock) { latestSrSample }
        if (sample == null) {
            statusTextView.text = "No SR sample yet. Start live SR first, wait for one result, then tap Save sample."
            Toast.makeText(this, "先运行一次实时超分，再保存样张", Toast.LENGTH_SHORT).show()
            return
        }
        cameraExecutor.execute {
            try {
                val timestamp = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.US).format(Date())
                val saved = listOf(
                    savePngToPictures(sample.input, "${sample.label}_${timestamp}_${sample.backend.label}_input_${sample.input.width}.png"),
                    savePngToPictures(sample.baseline, "${sample.label}_${timestamp}_${sample.backend.label}_baseline_resize_${sample.baseline.width}.png"),
                    savePngToPictures(sample.sr, "${sample.label}_${timestamp}_${sample.backend.label}_sr_${sample.sr.width}.png"),
                )
                Log.d("RB5_SR", "saved SR sample files: ${saved.joinToString()}")
                runOnUiThread {
                    statusTextView.text =
                        "Saved SR sample (${sample.backend.label})\n" +
                            "inference ${sample.inferenceMs} ms | end-to-end ~${sample.e2eMs} ms\n" +
                            saved.joinToString("\n")
                    Toast.makeText(this, "样张已保存到 Pictures/RB5VisionLab", Toast.LENGTH_LONG).show()
                }
            } catch (e: Exception) {
                Log.e("RB5_SR", "save SR sample failed", e)
                runOnUiThread {
                    statusTextView.text = "Save SR sample failed: ${e.message}"
                    Toast.makeText(this, "保存失败", Toast.LENGTH_SHORT).show()
                }
            }
        }
    }

    private fun requestHighResSrSample() {
        pendingHighResSample = true
        statusTextView.text = "High-res SR sample running... Keep the camera steady."
        Toast.makeText(this, "正在保存 256→1024 样张，请保持画面稳定", Toast.LENGTH_LONG).show()
    }

    private fun runHighResSrSample(imageProxy: ImageProxy) {
        try {
            val side = 256
            val full = imageProxy.toBitmap()
            if (full.width < side || full.height < side) error("Camera frame too small for 256 ROI")
            val (croppedRoi, cropSide) = cropCenterRoiKeepingLegacyFov(full, side)
            var roi = croppedRoi
            val degrees = imageProxy.imageInfo.rotationDegrees
            if (degrees != 0) {
                val matrix = Matrix().apply { postRotate(degrees.toFloat()) }
                roi = Bitmap.createBitmap(roi, 0, 0, side, side, matrix, true)
            }
            if (highResResolver == null) {
                highResResolver = SuperResolver(
                    this,
                    modelAsset = "real_esrgan_general_x4v3_256_float32.tflite",
                    backend = SrBackend.CPU,
                    inputSize = side,
                    outputSize = 1024,
                    inputLayout = SrInputLayout.NHCW,
                )
            }
            val (rawOut, timing) = highResResolver!!.enhance(roi)
            var out = rawOut
            // The local ONNX->TFLite 256 model uses an unusual NHCW input layout.
            // On this CameraX stream it returns the SR image before the ROI's
            // display rotation, so rotate the SR output to keep it comparable
            // with the saved 256 ROI and bicubic 1024 baseline.
            if (degrees != 0) {
                val matrix = Matrix().apply { postRotate(degrees.toFloat()) }
                out = Bitmap.createBitmap(out, 0, 0, out.width, out.height, matrix, true)
            }
            val baseline = Bitmap.createScaledBitmap(roi, 1024, 1024, true)
            val sample = SrSample(
                backend = SrBackend.CPU,
                label = "D75_256",
                input = roi,
                baseline = baseline,
                sr = out,
                inferenceMs = timing.inferenceMs,
                e2eMs = timing.totalMs,
            )
            synchronized(srSampleLock) { latestSrSample = sample }
            val timestamp = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.US).format(Date())
            val saved = listOf(
                savePngToPictures(sample.input, "${sample.label}_${timestamp}_input_256.png"),
                savePngToPictures(sample.baseline, "${sample.label}_${timestamp}_baseline_resize_1024.png"),
                savePngToPictures(sample.sr, "${sample.label}_${timestamp}_sr_1024.png"),
            )
            Log.d("RB5_SR", "saved high-res SR sample files: ${saved.joinToString()}")
            runOnUiThread {
                statusTextView.text =
                    "Saved high-res SR sample (${full.width}x${full.height} frame, ROI ${cropSide}->256→1024 CPU)\n" +
                        "inference ${timing.inferenceMs} ms | total ~${timing.totalMs} ms\n" +
                        saved.joinToString("\n")
                Toast.makeText(this, "高分辨率样张已保存", Toast.LENGTH_LONG).show()
            }
        } catch (e: Throwable) {
            Log.e("RB5_SR", "save high-res SR sample failed", e)
            runOnUiThread {
                statusTextView.text = "High-res sample failed: ${e.message}"
                Toast.makeText(this, "高分辨率样张保存失败", Toast.LENGTH_SHORT).show()
            }
        }
    }

    private fun cropCenterRoiKeepingLegacyFov(full: Bitmap, modelInputSide: Int): Pair<Bitmap, Int> {
        val cropSide = minOf(
            full.width * modelInputSide / LEGACY_ANALYSIS_WIDTH,
            full.width,
            full.height,
        ).coerceAtLeast(modelInputSide)
        val left = (full.width - cropSide) / 2
        val top = (full.height - cropSide) / 2
        val crop = Bitmap.createBitmap(full, left, top, cropSide, cropSide)
        val roi = if (cropSide == modelInputSide) {
            crop
        } else {
            Bitmap.createScaledBitmap(crop, modelInputSide, modelInputSide, true)
        }
        return Pair(roi, cropSide)
    }

    private fun savePngToPictures(bitmap: Bitmap, fileName: String): String {
        val relativePath = Environment.DIRECTORY_PICTURES + "/RB5VisionLab"
        val values = ContentValues().apply {
            put(MediaStore.Images.Media.DISPLAY_NAME, fileName)
            put(MediaStore.Images.Media.MIME_TYPE, "image/png")
            put(MediaStore.Images.Media.RELATIVE_PATH, relativePath)
        }
        val uri = contentResolver.insert(MediaStore.Images.Media.EXTERNAL_CONTENT_URI, values)
            ?: error("MediaStore insert returned null")
        contentResolver.openOutputStream(uri)?.use { out ->
            check(bitmap.compress(Bitmap.CompressFormat.PNG, 100, out)) { "PNG compress failed" }
        } ?: error("Cannot open output stream for $fileName")
        return "/sdcard/$relativePath/$fileName"
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
                        .setResolutionStrategy(ResolutionStrategy.HIGHEST_AVAILABLE_STRATEGY)
                        .build()
                )
                .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                .build()
                .also {
                    it.setAnalyzer(cameraExecutor) { imageProxy ->
                        try {
                            frameCount++
                            if (pendingHighResSample) {
                                pendingHighResSample = false
                                runHighResSrSample(imageProxy)
                            } else if (liveSr) {
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
        cameraExecutor.execute { highResResolver?.close() }
        cameraExecutor.shutdown()
    }
}
