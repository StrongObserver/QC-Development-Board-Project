package com.cyf.rb5visionlab

import android.Manifest
import android.content.ContentValues
import android.content.Intent
import android.content.pm.ActivityInfo
import android.content.pm.PackageManager
import android.content.res.AssetManager
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Matrix
import android.os.Bundle
import android.os.Debug
import android.os.Environment
import android.provider.MediaStore
import android.util.Size
import android.util.Log
import android.view.View
import android.widget.Button
import android.widget.ImageView
import android.widget.TextView
import android.widget.Toast
import androidx.constraintlayout.widget.ConstraintLayout
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
import androidx.core.view.WindowInsetsControllerCompat
import com.qualcomm.qti.QnnDelegate
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
        private const val LIVE_SAMPLE_CAPTURE_INTERVAL = 30
        private val LIVE_ANALYSIS_TARGET_SIZE = Size(1280, 960)

        init {
            System.loadLibrary("opencv_java4")
            System.loadLibrary("rb5visionlab")
        }
    }

    private lateinit var cameraExecutor: ExecutorService
    private lateinit var srExecutor: ExecutorService
    private lateinit var statusTextView: TextView
    private lateinit var nativeMessage: String
    private var frameCount = 0
    private var resolver: SuperResolver? = null
    private var offlineResolver: SuperResolver? = null
    @Volatile private var srBackend = SrBackend.QNN
    @Volatile private var srModelVariant = SrModelVariant.QUICKSR_W8A8
    @Volatile private var tileModelVariant = SrModelVariant.W8A8
    @Volatile private var liveSr = false
    @Volatile private var liveSrTensorReady = false
    @Volatile private var liveSrEveryN = 1
    @Volatile private var liveSrSessionId = "manual"
    @Volatile private var offlineEvalActive = false
    @Volatile private var liveSrSeenFrames = 0
    @Volatile private var liveSrEnhancedFrames = 0
    @Volatile private var liveSrStartNs = 0L
    private lateinit var srResultView: ImageView
    private lateinit var demoOverlayView: TextView
    private lateinit var controlBarView: View
    private var demoMode = false
    private var demoControlsVisible = false
    private val srSampleLock = Any()
    private var latestSrSample: SrSample? = null
    private var liveOutputBitmap: Bitmap? = null
    private var tensorLiveOutputBitmap: Bitmap? = null
    private var highResResolver: SuperResolver? = null
    @Volatile private var pendingHighResSample = false
    @Volatile private var pendingAutoLiveSr = false
    @Volatile private var pendingRealCameraCapture = false
    @Volatile private var pendingTileStillCapture = false
    @Volatile private var pendingAutoTileStill = false
    @Volatile private var pendingTileCompareCapture = false
    @Volatile private var pendingAutoTileCompare = false
    @Volatile private var pendingProbeMode: String = ""
    private val realCameraSessionId = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.US).format(Date())
    private var realCameraSceneIndex = 0

    private data class OfflineEvalAsset(
        val label: String,
        val assetName: String,
    )

    private data class RealCameraScene(
        val id: String,
        val title: String,
        val prompt: String,
    )

    private data class SrSample(
        val backend: SrBackend,
        val label: String,
        val input: Bitmap,
        val baseline: Bitmap,
        val sr: Bitmap,
        val inferenceMs: Long,
        val e2eMs: Long,
    )

    private data class ResourceMemorySnapshot(
        val label: String,
        val totalPssKb: Int,
        val dalvikPssKb: Int,
        val nativePssKb: Int,
        val otherPssKb: Int,
        val runtimeUsedKb: Long,
        val runtimeFreeKb: Long,
        val runtimeMaxKb: Long,
    )

    private data class ProbeResolverInit(
        val resolver: SuperResolver,
        val initMs: Long,
    )

    private val realCameraScenes = listOf(
        RealCameraScene(
            "text_signage_01",
            "文字/招牌 1",
            "拍 1 个清晰文字或屏幕文字区域，字尽量占中心 ROI，距离保持稳定。",
        ),
        RealCameraScene(
            "text_signage_02",
            "文字/招牌 2",
            "换一组更小或更密的文字，不要和第 1 张重复。",
        ),
        RealCameraScene(
            "fine_structure_01",
            "细结构 1",
            "拍树枝、电线、网格、织物或密集边缘，细节放在画面中心。",
        ),
        RealCameraScene(
            "fine_structure_02",
            "细结构 2",
            "再拍 1 个不同细结构，优先选容易出现假纹理或振铃的场景。",
        ),
        RealCameraScene(
            "low_light_noise_01",
            "低光/噪声",
            "拍 1 个偏暗区域，最好有小亮点或暗部纹理，用来检查噪声放大。",
        ),
        RealCameraScene(
            "people_object_01",
            "人物/人像替代",
            "拍人脸、照片上的脸、手办或人物画面，重点看皮肤和边缘是否自然。",
        ),
        RealCameraScene(
            "object_texture_01",
            "日常物体纹理",
            "拍纸张、布料、包装、键盘或桌面纹理，检查过锐和自然质感。",
        ),
        RealCameraScene(
            "optional_failure_01",
            "可选失败样张",
            "只在你看到明显异常时拍；没有异常就拍任意一个你认为有代表性的难场景。",
        ),
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
    external fun qnnRuntimePreflight(): String
    external fun qnnSharedMemoryProbe(inputBytes: Int, outputBytes: Int): String
    external fun qnnSharedMemoryTensorProbe(assetManager: AssetManager, modelAsset: String, delegateHandle: Long, repeats: Int): String
    external fun qnnSharedMemoryTensorCompareProbe(assetManager: AssetManager, modelAsset: String, normalDelegateHandle: Long, sharedDelegateHandle: Long, repeats: Int): String
    external fun processYPlane(yData: ByteArray, width: Int, height: Int, rowStride: Int): String
    external fun nativeYuvToRgbRoi(
        yData: ByteArray,
        uData: ByteArray,
        vData: ByteArray,
        width: Int,
        height: Int,
        yRowStride: Int,
        yPixelStride: Int,
        uRowStride: Int,
        uPixelStride: Int,
        vRowStride: Int,
        vPixelStride: Int,
        outputSide: Int,
    ): IntArray
    external fun nativeYuvToRgbRoiBytes(
        yData: ByteArray,
        uData: ByteArray,
        vData: ByteArray,
        width: Int,
        height: Int,
        yRowStride: Int,
        yPixelStride: Int,
        uRowStride: Int,
        uPixelStride: Int,
        vRowStride: Int,
        vPixelStride: Int,
        outputSide: Int,
    ): ByteArray

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        Log.d(TAG, "Hello RB5 from MainActivity onCreate")

        enableEdgeToEdge()
        setContentView(R.layout.activity_main)

        nativeMessage = stringFromJNI()
        Log.d(TAG, nativeMessage)
        val qnnPreflightMessage = qnnRuntimePreflight()
        Log.d("RB5_QNN", qnnPreflightMessage)

        statusTextView = findViewById(R.id.textView)
        statusTextView.text = "$nativeMessage\n\n$qnnPreflightMessage"
        demoOverlayView = findViewById(R.id.demo_overlay)
        controlBarView = findViewById(R.id.control_bar)
        demoMode = boolIntentExtra("demo_mode")

        cameraExecutor = Executors.newSingleThreadExecutor()
        srExecutor = Executors.newSingleThreadExecutor()
        applyIntentSrOverrides()
        setupSuperResolution()
        val autoRunQnnFixed = boolIntentExtra("run_qnn_fixed")
        val autoStartLiveSr = boolIntentExtra("start_live_sr")
        val autoStartTensorReadyLiveSr = boolIntentExtra("start_live_sr_tensor_ready")
        val autoRunResourceProbe = boolIntentExtra("run_resource_probe")
        val autoRunQnnSharedMemoryProbe = boolIntentExtra("run_qnn_shared_memory_probe")
        val autoRunQnnSharedTensorProbe = boolIntentExtra("run_qnn_shared_tensor_probe")
        val autoRunQnnSharedTensorCompareProbe = boolIntentExtra("run_qnn_shared_tensor_compare_probe")
        val autoRunYuvRoiProbe = boolIntentExtra("run_yuv_roi_probe")
        val autoRunTensorReadyProbe = boolIntentExtra("run_tensor_ready_probe")
        val autoRunTileStill = boolIntentExtra("run_tile_still")
        val autoRunTileCompare = boolIntentExtra("run_tile_compare")
        val requestedProbeMode = intent.getStringExtra("probe_mode")?.trim()?.lowercase(Locale.US).orEmpty()
        liveSrEveryN = intIntentExtra("sr_every_n", 1).coerceAtLeast(1)
        liveSrSessionId = intent.getStringExtra("sr_session_id")?.trim().orEmpty().ifEmpty { "manual" }
        Log.d(
            "RB5_QNN",
            "onCreate run_qnn_fixed=$autoRunQnnFixed run_resource_probe=$autoRunResourceProbe " +
                "run_qnn_shared_memory_probe=$autoRunQnnSharedMemoryProbe " +
                "run_qnn_shared_tensor_probe=$autoRunQnnSharedTensorProbe " +
                "run_qnn_shared_tensor_compare_probe=$autoRunQnnSharedTensorCompareProbe " +
                "run_yuv_roi_probe=$autoRunYuvRoiProbe run_tensor_ready_probe=$autoRunTensorReadyProbe " +
                "probe_mode=$requestedProbeMode extras=${intent.extras?.keySet()?.joinToString()}"
        )
        Log.d(
            "RB5_SR",
            "intent probes run_qnn_fixed=$autoRunQnnFixed start_live_sr=$autoStartLiveSr " +
                "start_live_sr_tensor_ready=$autoStartTensorReadyLiveSr " +
                "run_tile_still=$autoRunTileStill tile_model=${tileModelVariant.label} " +
                "run_tile_compare=$autoRunTileCompare " +
                "run_yuv_roi_probe=$autoRunYuvRoiProbe run_tensor_ready_probe=$autoRunTensorReadyProbe demo_mode=$demoMode " +
                "probe_mode=$requestedProbeMode sr_every_n=$liveSrEveryN sr_session_id=$liveSrSessionId"
        )
        if (autoRunResourceProbe) {
            srExecutor.execute {
                Thread.sleep(500)
                runResourceProbeOnWorker()
            }
        } else if (autoRunQnnSharedMemoryProbe || requestedProbeMode == "qnn_shared_memory") {
            srExecutor.execute {
                Thread.sleep(500)
                runQnnSharedMemoryProbeOnWorker()
            }
        } else if (autoRunQnnSharedTensorProbe || requestedProbeMode == "qnn_shared_tensor") {
            srExecutor.execute {
                Thread.sleep(500)
                runQnnSharedMemoryTensorProbeOnWorker()
            }
        } else if (autoRunQnnSharedTensorCompareProbe || requestedProbeMode == "qnn_shared_tensor_compare") {
            srExecutor.execute {
                Thread.sleep(500)
                runQnnSharedMemoryTensorCompareProbeOnWorker()
            }
        } else if (autoRunQnnFixed) {
            srExecutor.execute {
                Thread.sleep(500)
                runOnUiThread { runQnnFixedSample() }
            }
        } else if (autoStartLiveSr) {
            pendingAutoLiveSr = true
        } else if (autoRunTileStill) {
            pendingAutoTileStill = true
        } else if (autoRunTileCompare) {
            pendingAutoTileCompare = true
        } else if (autoStartTensorReadyLiveSr) {
            pendingProbeMode = "tensor_live"
        } else if (requestedProbeMode == "yuv_roi" || autoRunYuvRoiProbe) {
            pendingProbeMode = "yuv_roi"
        } else if (requestedProbeMode == "tensor_ready" || autoRunTensorReadyProbe) {
            pendingProbeMode = "tensor_ready"
        }
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

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        applyIntentSrOverrides()
        demoMode = boolIntentExtra("demo_mode")
        applyDemoModeUi()
        liveSrEveryN = intIntentExtra("sr_every_n", 1).coerceAtLeast(1)
        liveSrSessionId = intent.getStringExtra("sr_session_id")?.trim().orEmpty().ifEmpty { "manual" }
        if (boolIntentExtra("start_live_sr")) {
            startLiveSrFromIntent()
        }
        Log.d("RB5_SR", "onNewIntent start_live_sr=${boolIntentExtra("start_live_sr")} sr_every_n=$liveSrEveryN sr_session_id=$liveSrSessionId")
    }

    private fun setupSuperResolution() {
        val srButton = findViewById<Button>(R.id.sr_button)
        val saveSampleButton = findViewById<Button>(R.id.save_sample_button)
        val offlineEvalButton = findViewById<Button>(R.id.offline_eval_button)
        val qnnFixedButton = findViewById<Button>(R.id.qnn_fixed_button)
        val realCameraButton = findViewById<Button>(R.id.real_camera_button)
        val tileStillButton = findViewById<Button>(R.id.tile_still_button)
        srResultView = findViewById(R.id.sr_result)
        val previewView = findViewById<PreviewView>(R.id.previewView)
        applyDemoModeUi()
        srButton.text = startButtonText()
        offlineEvalButton.text = offlineButtonText()
        realCameraButton.text = realCameraButtonText()
        tileStillButton.text = tileButtonText()
        saveSampleButton.setOnClickListener { saveLatestSrSample() }
        saveSampleButton.setOnLongClickListener {
            requestHighResSrSample()
            true
        }
        offlineEvalButton.setOnClickListener { runOfflineEvalSamples() }
        qnnFixedButton.setOnClickListener {
            Log.d("RB5_QNN", "QNN fixed button clicked")
            runQnnFixedSample()
        }
        tileStillButton.setOnClickListener { requestTileStillCapture() }
        tileStillButton.setOnLongClickListener {
            cycleTileModelVariant()
            tileStillButton.text = tileButtonText()
            statusTextView.text = "Tile model switched to ${tileModelVariant.label}. Tap tile button to run still tile."
            true
        }
        realCameraButton.setOnClickListener { requestRealCameraCapture() }
        realCameraButton.setOnLongClickListener {
            realCameraSceneIndex = 0
            realCameraButton.text = realCameraButtonText()
            statusTextView.text = realCameraPromptText()
            true
        }
        offlineEvalButton.setOnLongClickListener {
            if (liveSr) {
                statusTextView.text = "Stop live SR before switching model precision."
                return@setOnLongClickListener true
            }
            cycleSrModelVariant()
            srButton.text = startButtonText()
            offlineEvalButton.text = offlineButtonText()
            statusTextView.text = "SR model switched to ${srModelVariant.label}. Tap offline eval to run fixed samples."
            true
        }
        // Toggle live super-resolution on the camera's center ROI.
        srButton.setOnClickListener {
            liveSr = !liveSr
            if (liveSr) {
                liveSrTensorReady = false
                offlineEvalActive = false
                liveSrEveryN = 1
                resetLiveSrCadenceCounters()
                showLiveSrOutput()
                srButton.text = "停止实时超分"
                if (demoMode) {
                    demoOverlayView.text = "RB5 Gen2 Live SR\n${srBackend.label} / ${srModelVariant.label}\nStarting..."
                } else {
                    statusTextView.text = "Live ROI SR starting with ${srBackend.label} backend..."
                }
            } else {
                offlineEvalActive = false
                hideLiveSrOutput()
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

    private fun resetLiveSrCadenceCounters() {
        liveSrSeenFrames = 0
        liveSrEnhancedFrames = 0
        liveSrStartNs = System.nanoTime()
    }

    private fun applyDemoModeUi() {
        if (!::srResultView.isInitialized || !::demoOverlayView.isInitialized || !::controlBarView.isInitialized) {
            return
        }
        if (demoMode) {
            requestedOrientation = ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE
            WindowInsetsControllerCompat(window, window.decorView).hide(WindowInsetsCompat.Type.systemBars())
            controlBarView.visibility = if (demoControlsVisible) View.VISIBLE else View.GONE
            statusTextView.visibility = if (demoControlsVisible) View.VISIBLE else View.GONE
            demoOverlayView.visibility = View.VISIBLE
            demoOverlayView.text = "RB5 VisionLab\nQNN / HTP\nLive ROI demo"
            demoOverlayView.setOnClickListener {
                demoControlsVisible = !demoControlsVisible
                applyDemoModeUi()
            }
            srResultView.scaleType = ImageView.ScaleType.CENTER_CROP
            (srResultView.layoutParams as? ConstraintLayout.LayoutParams)?.let { params ->
                params.topToTop = ConstraintLayout.LayoutParams.PARENT_ID
                params.bottomToBottom = ConstraintLayout.LayoutParams.PARENT_ID
                params.bottomToTop = ConstraintLayout.LayoutParams.UNSET
                srResultView.layoutParams = params
            }
        } else {
            demoControlsVisible = false
            WindowInsetsControllerCompat(window, window.decorView).show(WindowInsetsCompat.Type.systemBars())
            controlBarView.visibility = View.VISIBLE
            statusTextView.visibility = View.VISIBLE
            demoOverlayView.visibility = View.GONE
            demoOverlayView.setOnClickListener(null)
            srResultView.scaleType = ImageView.ScaleType.FIT_CENTER
            (srResultView.layoutParams as? ConstraintLayout.LayoutParams)?.let { params ->
                params.topToTop = ConstraintLayout.LayoutParams.PARENT_ID
                params.bottomToBottom = ConstraintLayout.LayoutParams.UNSET
                params.bottomToTop = R.id.control_bar
                srResultView.layoutParams = params
            }
        }
    }

    private fun showLiveSrOutput() {
        findViewById<PreviewView>(R.id.previewView).visibility = View.GONE
        srResultView.visibility = View.VISIBLE
        if (demoMode) {
            statusTextView.visibility = View.GONE
            demoOverlayView.visibility = View.VISIBLE
        }
    }

    private fun hideLiveSrOutput() {
        srResultView.visibility = View.GONE
        findViewById<PreviewView>(R.id.previewView).visibility = View.VISIBLE
        if (demoMode) {
            demoOverlayView.visibility = View.GONE
        }
    }

    private fun liveDemoOverlayText(
        timing: SrTiming,
        e2eMs: Long,
        effectiveEnhancedFps: Double,
        frameWidth: Int,
        frameHeight: Int,
        cropSide: Int,
        everyN: Int,
    ): String {
        return "RB5 Gen2 Live SR\n" +
            "${srBackend.label} / ${srModelVariant.label}\n" +
            "E2E ${e2eMs} ms  |  NPU ${timing.inferenceMs} ms\n" +
            "FPS ${"%.1f".format(Locale.US, effectiveEnhancedFps)}  |  everyN $everyN\n" +
            "Frame ${frameWidth}x${frameHeight}  |  crop ${cropSide}->128"
    }

    private fun applyIntentSrOverrides() {
        intent.getStringExtra("sr_backend")?.let { requested ->
            parseEnum<SrBackend>(requested)?.let { srBackend = it }
        }
        intent.getStringExtra("sr_model")?.let { requested ->
            parseEnum<SrModelVariant>(requested)?.let { srModelVariant = it }
        }
        intent.getStringExtra("sr_model_variant")?.let { requested ->
            parseEnum<SrModelVariant>(requested)?.let { srModelVariant = it }
        }
        if (intent.getBooleanExtra("run_qnn_fixed", false) && srModelVariant == SrModelVariant.FLOAT) {
            srModelVariant = SrModelVariant.W8A8
        }
        parseTileModelExtra(intent.getStringExtra("tile_model"))?.let { tileModelVariant = it }
        parseTileModelExtra(intent.getStringExtra("tile_model_variant"))?.let { tileModelVariant = it }
        Log.d("RB5_SR", "intent SR overrides backend=${srBackend.label} model=${srModelVariant.label}")
    }

    private fun boolIntentExtra(name: String): Boolean {
        if (intent.getBooleanExtra(name, false)) return true
        val value = intent.extras?.get(name) ?: return false
        return when (value) {
            is Boolean -> value
            is String -> value.equals("true", ignoreCase = true) || value == "1"
            else -> value.toString().equals("true", ignoreCase = true)
        }
    }

    private fun intIntentExtra(name: String, default: Int): Int {
        val value = intent.extras?.get(name) ?: return default
        return when (value) {
            is Int -> value
            is Long -> value.toInt()
            is String -> value.trim().toIntOrNull() ?: default
            else -> value.toString().trim().toIntOrNull() ?: default
        }
    }

    private inline fun <reified T : Enum<T>> parseEnum(value: String): T? {
        val normalized = value.trim().uppercase(Locale.US)
        return enumValues<T>().firstOrNull {
            it.name.uppercase(Locale.US) == normalized
        }
    }

    private fun parseTileModelExtra(value: String?): SrModelVariant? {
        val normalized = value?.trim()?.uppercase(Locale.US) ?: return null
        return when (normalized) {
            "REAL", "REALESRGAN", "REAL_ESRGAN", "W8A8" -> SrModelVariant.W8A8
            "QUICK", "QUICKSR", "QUICKSRNET", "QUICKSR_W8A8" -> SrModelVariant.QUICKSR_W8A8
            else -> parseEnum<SrModelVariant>(normalized)
        }
    }

    private fun startLiveSrFromIntent() {
        liveSr = true
        liveSrTensorReady = false
        offlineEvalActive = false
        showLiveSrOutput()
        findViewById<Button>(R.id.sr_button).text = "停止实时超分"
        if (demoMode) {
            demoOverlayView.text = "RB5 Gen2 Live SR\n${srBackend.label} / ${srModelVariant.label}\nStarting..."
        } else {
            statusTextView.text = "Live ROI SR starting with ${srBackend.label}/${srModelVariant.label} from intent..."
        }
        resetLiveSrCadenceCounters()
        Log.d("RB5_SR", "auto live SR from intent backend=${srBackend.label} model=${srModelVariant.label} session=$liveSrSessionId everyN=$liveSrEveryN")
    }

    private fun startTensorReadyLiveSrFromIntent() {
        liveSr = false
        liveSrTensorReady = true
        offlineEvalActive = false
        showLiveSrOutput()
        findViewById<Button>(R.id.sr_button).text = "停止 Tensor Live"
        if (demoMode) {
            demoOverlayView.text = "RB5 Gen2 Tensor Live\nQNN / QUICKSR_W8A8\nStarting..."
        } else {
            statusTextView.text = "Tensor-ready live ROI SR starting with QNN/QUICKSR_W8A8..."
        }
        Log.d("RB5_SR_TENSOR", "auto tensor-ready live SR from intent backend=QNN model=QUICKSR_W8A8")
    }

    private fun tileButtonText(): String = "整图 Tile (${tileModelVariant.label})"

    private fun cycleTileModelVariant() {
        tileModelVariant = when (tileModelVariant) {
            SrModelVariant.QUICKSR_W8A8 -> SrModelVariant.W8A8
            else -> SrModelVariant.QUICKSR_W8A8
        }
    }

    private fun runQnnFixedSample() {
        if (liveSr) {
            statusTextView.text = "Stop live SR before running QNN fixed sample."
            Toast.makeText(this, "请先停止实时超分", Toast.LENGTH_SHORT).show()
            return
        }
        val previewView = findViewById<PreviewView>(R.id.previewView)
        offlineEvalActive = true
        previewView.visibility = View.GONE
        srResultView.visibility = View.VISIBLE
        val fixedVariant = if (srModelVariant == SrModelVariant.FLOAT) SrModelVariant.W8A8 else srModelVariant
        statusTextView.text = "QNN fixed sample running with ${fixedVariant.label}..."
        srExecutor.execute {
            try {
                val fixedAsset = intent.getStringExtra("sr_asset") ?: "offline_text_edge_128.png"
                val inputBitmap = assets.open(fixedAsset).use { input ->
                    BitmapFactory.decodeStream(input)
                } ?: error("Cannot decode $fixedAsset")
                val modelInput = if (inputBitmap.width == 128 && inputBitmap.height == 128) {
                    inputBitmap.copy(Bitmap.Config.ARGB_8888, false)
                } else {
                    Bitmap.createScaledBitmap(inputBitmap, 128, 128, true)
                }
                val qnnResolver = SuperResolver(
                    this,
                    modelAsset = fixedVariant.assetName,
                    backend = SrBackend.QNN,
                )
                val (qnnBitmap, timing) = try {
                    qnnResolver.enhance(modelInput)
                } finally {
                    qnnResolver.close()
                }
                val baseline = Bitmap.createScaledBitmap(modelInput, 512, 512, true)
                val timestamp = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.US).format(Date())
                val assetLabel = fixedAsset.substringBeforeLast(".").replace(Regex("[^A-Za-z0-9_]+"), "_")
                val prefix = "QNN_FIXED_${fixedVariant.label}_${assetLabel}_$timestamp"
                val saved = listOf(
                    savePngToPictures(modelInput, "${prefix}_input_128.png"),
                    savePngToPictures(baseline, "${prefix}_baseline_resize_512.png"),
                    savePngToPictures(qnnBitmap, "${prefix}_sr_512.png"),
                )
                synchronized(srSampleLock) {
                    latestSrSample = SrSample(
                        backend = SrBackend.QNN,
                        label = "QNN_FIXED_${fixedVariant.label}",
                        input = modelInput,
                        baseline = baseline,
                        sr = qnnBitmap,
                        inferenceMs = timing.inferenceMs,
                        e2eMs = timing.totalMs,
                    )
                }
                Log.d("RB5_QNN", "fixed sample QNN Delegate OK model=${fixedVariant.label} asset=$fixedAsset pre=${timing.preprocessMs} inf=${timing.inferenceMs} post=${timing.postprocessMs} total=${timing.totalMs} saved=${saved.joinToString()}")
                runOnUiThread {
                    offlineEvalActive = false
                    srResultView.setImageBitmap(qnnBitmap)
                    statusTextView.text =
                        "QNN fixed sample OK (${fixedVariant.label}, $fixedAsset)\n" +
                            "pre ${timing.preprocessMs} ms | inference ${timing.inferenceMs} ms | post ${timing.postprocessMs} ms | total ${timing.totalMs} ms\n" +
                            saved.joinToString("\n")
                    Toast.makeText(this, "QNN 固定样张已保存", Toast.LENGTH_LONG).show()
                }
            } catch (e: Throwable) {
                Log.e("RB5_QNN", "fixed sample failed", e)
                runOnUiThread {
                    offlineEvalActive = false
                    statusTextView.text = "QNN fixed sample failed: ${e.message}"
                    Toast.makeText(this, "QNN 固定样张失败", Toast.LENGTH_SHORT).show()
                }
            }
        }
    }

    private fun createQnnDelegateForProbe(): QnnDelegate {
        val options = QnnDelegate.Options().apply {
            setBackendType(QnnDelegate.Options.BackendType.HTP_BACKEND)
            setSkelLibraryDir(applicationInfo.nativeLibraryDir)
            setHtpPerformanceMode(QnnDelegate.Options.HtpPerformanceMode.HTP_PERFORMANCE_HIGH_PERFORMANCE)
            setHtpPdSession(QnnDelegate.Options.HtpPdSession.HTP_PD_SESSION_UNSIGNED)
            setLogLevel(QnnDelegate.Options.LogLevel.LOG_LEVEL_INFO)
        }
        return QnnDelegate(options)
    }

    private fun runQnnSharedMemoryTensorProbeOnWorker() {
        val tag = "RB5_QNN_SHARED"
        val modelAsset = SrModelVariant.QUICKSR_W8A8.assetName
        val repeats = intIntentExtra("shared_tensor_repeats", 20).coerceAtLeast(1)
        runOnUiThread {
            offlineEvalActive = true
            statusTextView.text = "QNN shared-memory tensor probe running..."
        }
        var delegate: QnnDelegate? = null
        try {
            delegate = createQnnDelegateForProbe()
            val result = qnnSharedMemoryTensorProbe(assets, modelAsset, delegate.getNativeHandle(), repeats)
            Log.d(tag, "tensor probe result $result")
            runOnUiThread {
                offlineEvalActive = false
                statusTextView.text = "QNN shared-memory tensor probe\n$result"
            }
        } catch (e: Throwable) {
            Log.e(tag, "tensor probe failed", e)
            runOnUiThread {
                offlineEvalActive = false
                statusTextView.text = "QNN shared-memory tensor probe failed: ${e.message}"
            }
        } finally {
            delegate?.close()
        }
    }

    private fun runQnnSharedMemoryTensorCompareProbeOnWorker() {
        val tag = "RB5_QNN_SHARED"
        val modelAsset = SrModelVariant.QUICKSR_W8A8.assetName
        val repeats = intIntentExtra("shared_tensor_repeats", 20).coerceAtLeast(1)
        runOnUiThread {
            offlineEvalActive = true
            statusTextView.text = "QNN shared-memory tensor compare probe running..."
        }
        var normalDelegate: QnnDelegate? = null
        var sharedDelegate: QnnDelegate? = null
        try {
            normalDelegate = createQnnDelegateForProbe()
            sharedDelegate = createQnnDelegateForProbe()
            val result = qnnSharedMemoryTensorCompareProbe(
                assets,
                modelAsset,
                normalDelegate.getNativeHandle(),
                sharedDelegate.getNativeHandle(),
                repeats,
            )
            Log.d(tag, "tensor compare probe result $result")
            runOnUiThread {
                offlineEvalActive = false
                statusTextView.text = "QNN shared-memory tensor compare probe\n$result"
            }
        } catch (e: Throwable) {
            Log.e(tag, "tensor compare probe failed", e)
            runOnUiThread {
                offlineEvalActive = false
                statusTextView.text = "QNN shared-memory tensor compare probe failed: ${e.message}"
            }
        } finally {
            normalDelegate?.close()
            sharedDelegate?.close()
        }
    }

    private fun runQnnSharedMemoryProbeOnWorker() {
        val tag = "RB5_QNN_SHARED"
        val inputBytes = 128 * 128 * 3
        val outputBytes = 512 * 512 * 3
        runOnUiThread {
            offlineEvalActive = true
            statusTextView.text = "QNN shared-memory probe running..."
        }
        try {
            val result = qnnSharedMemoryProbe(inputBytes, outputBytes)
            Log.d(tag, "probe result $result")
            runOnUiThread {
                offlineEvalActive = false
                statusTextView.text = "QNN shared-memory probe\n$result"
            }
        } catch (e: Throwable) {
            Log.e(tag, "probe failed", e)
            runOnUiThread {
                offlineEvalActive = false
                statusTextView.text = "QNN shared-memory probe failed: ${e.message}"
            }
        }
    }

    private fun runResourceProbeOnWorker() {
        val tag = "RB5_RESOURCE"
        if (liveSr) {
            Log.e(tag, "probe skipped because live SR is active")
            return
        }
        val fixedAsset = intent.getStringExtra("sr_asset") ?: "offline_text_edge_128.png"
        val steadyRuns = intent.getIntExtra("resource_probe_runs", 5).coerceAtLeast(2)
        runOnUiThread {
            offlineEvalActive = true
            findViewById<PreviewView>(R.id.previewView).visibility = View.GONE
            srResultView.visibility = View.VISIBLE
            statusTextView.text = "QNN resource probe running..."
        }

        var real: SuperResolver? = null
        var quick: SuperResolver? = null
        var modelInput: Bitmap? = null
        try {
            Log.d(tag, "probe start asset=$fixedAsset steady_runs=$steadyRuns")
            logResourceMemory("start")
            val tLoad0 = System.nanoTime()
            val inputBitmap = assets.open(fixedAsset).use { input ->
                BitmapFactory.decodeStream(input)
            } ?: error("Cannot decode $fixedAsset")
            modelInput = if (inputBitmap.width == 128 && inputBitmap.height == 128) {
                inputBitmap.copy(Bitmap.Config.ARGB_8888, false)
            } else {
                Bitmap.createScaledBitmap(inputBitmap, 128, 128, true)
            }
            val loadMs = (System.nanoTime() - tLoad0) / 1_000_000
            Log.d(tag, "asset asset=$fixedAsset load=$loadMs bitmap=${modelInput.width}x${modelInput.height}")
            logResourceMemory("after_asset_load")

            val realInit = createProbeResolver(SrModelVariant.W8A8)
            real = realInit.resolver
            logResourceMemory("after_real_init")
            runProbeEnhance("real_first", real, modelInput, 1)
            runProbeEnhance("real_steady", real, modelInput, steadyRuns)
            logResourceMemory("after_real_runs")

            val quickInit = createProbeResolver(SrModelVariant.QUICKSR_W8A8)
            quick = quickInit.resolver
            logResourceMemory("after_both_init")
            runProbeEnhance("quick_first_with_real_resident", quick, modelInput, 1)
            runProbeEnhance("quick_steady_with_real_resident", quick, modelInput, steadyRuns)
            logResourceMemory("after_both_runs")

            val closeRealMs = closeProbeResolver("close_real_keep_quick", real)
            real = null
            Log.d(tag, "close model=${SrModelVariant.W8A8.label} close=$closeRealMs")
            logResourceMemory("after_close_real")
            val closeQuickMs = closeProbeResolver("close_quick", quick)
            quick = null
            Log.d(tag, "close model=${SrModelVariant.QUICKSR_W8A8.label} close=$closeQuickMs")
            logResourceMemory("after_close_both")

            val realForSwitch = createProbeResolver(SrModelVariant.W8A8)
            real = realForSwitch.resolver
            runProbeEnhance("switch_source_real_warm", real, modelInput, 1)
            val tSwitch0 = System.nanoTime()
            val switchCloseMs = closeProbeResolver("switch_close_real", real)
            real = null
            val switchQuickInit = createProbeResolver(SrModelVariant.QUICKSR_W8A8)
            quick = switchQuickInit.resolver
            val switchTiming = runProbeEnhance("switch_target_quick_first", quick, modelInput, 1).first()
            val switchTotalMs = (System.nanoTime() - tSwitch0) / 1_000_000
            Log.d(
                tag,
                "switch from=${SrModelVariant.W8A8.label} to=${SrModelVariant.QUICKSR_W8A8.label} close=$switchCloseMs init=${switchQuickInit.initMs} first_total=${switchTiming.totalMs} total=$switchTotalMs"
            )
            closeProbeResolver("switch_close_quick", quick)
            quick = null
            logResourceMemory("end")
            Log.d(tag, "probe done status=pass")
            runOnUiThread {
                offlineEvalActive = false
                statusTextView.text = "QNN resource probe done. Pull RB5_RESOURCE logcat for results."
            }
        } catch (e: Throwable) {
            Log.e(tag, "probe failed", e)
            runOnUiThread {
                offlineEvalActive = false
                statusTextView.text = "QNN resource probe failed: ${e.message}"
            }
        } finally {
            real?.close()
            quick?.close()
            modelInput?.recycle()
        }
    }

    private fun createProbeResolver(variant: SrModelVariant): ProbeResolverInit {
        val t0 = System.nanoTime()
        val resolver = SuperResolver(
            this,
            modelAsset = variant.assetName,
            backend = SrBackend.QNN,
        )
        val initMs = (System.nanoTime() - t0) / 1_000_000
        Log.d("RB5_RESOURCE", "init model=${variant.label} backend=QNN asset=${variant.assetName} init=$initMs")
        return ProbeResolverInit(resolver, initMs)
    }

    private fun runProbeEnhance(
        phase: String,
        resolver: SuperResolver,
        input: Bitmap,
        runs: Int,
    ): List<SrTiming> {
        val timings = mutableListOf<SrTiming>()
        repeat(runs) { index ->
            val (out, timing) = resolver.enhance(input)
            out.recycle()
            timings += timing
            Log.d(
                "RB5_RESOURCE",
                "enhance phase=$phase run=${index + 1} pre=${timing.preprocessMs} inf=${timing.inferenceMs} post=${timing.postprocessMs} total=${timing.totalMs}"
            )
        }
        return timings
    }

    private fun closeProbeResolver(label: String, resolver: SuperResolver?): Long {
        if (resolver == null) return 0
        val t0 = System.nanoTime()
        resolver.close()
        val closeMs = (System.nanoTime() - t0) / 1_000_000
        Log.d("RB5_RESOURCE", "close label=$label close=$closeMs")
        return closeMs
    }

    private fun logResourceMemory(label: String) {
        val snapshot = resourceMemorySnapshot(label)
        Log.d(
            "RB5_RESOURCE",
            "mem label=${snapshot.label} totalPssKb=${snapshot.totalPssKb} dalvikPssKb=${snapshot.dalvikPssKb} nativePssKb=${snapshot.nativePssKb} otherPssKb=${snapshot.otherPssKb} runtimeUsedKb=${snapshot.runtimeUsedKb} runtimeFreeKb=${snapshot.runtimeFreeKb} runtimeMaxKb=${snapshot.runtimeMaxKb}"
        )
    }

    private fun resourceMemorySnapshot(label: String): ResourceMemorySnapshot {
        System.gc()
        Thread.sleep(80)
        val memoryInfo = Debug.MemoryInfo()
        Debug.getMemoryInfo(memoryInfo)
        val runtime = Runtime.getRuntime()
        val totalKb = runtime.totalMemory() / 1024
        val freeKb = runtime.freeMemory() / 1024
        return ResourceMemorySnapshot(
            label = label,
            totalPssKb = memoryInfo.totalPss,
            dalvikPssKb = memoryInfo.dalvikPss,
            nativePssKb = memoryInfo.nativePss,
            otherPssKb = memoryInfo.otherPss,
            runtimeUsedKb = totalKb - freeKb,
            runtimeFreeKb = freeKb,
            runtimeMaxKb = runtime.maxMemory() / 1024,
        )
    }

    private fun startButtonText(): String = "实时超分 ROI (${srBackend.label}/${srModelVariant.label})"

    private fun offlineButtonText(): String = "离线评测样张 (${srModelVariant.label})"

    private fun realCameraButtonText(): String {
        val scene = realCameraScenes[realCameraSceneIndex.coerceIn(0, realCameraScenes.lastIndex)]
        return "真实采集 ${realCameraSceneIndex + 1}/${realCameraScenes.size} ${scene.title}"
    }

    private fun realCameraPromptText(): String {
        val scene = realCameraScenes[realCameraSceneIndex.coerceIn(0, realCameraScenes.lastIndex)]
        return "Real camera capture ${realCameraSceneIndex + 1}/${realCameraScenes.size}\n" +
            "${scene.title}\n${scene.prompt}\n" +
            "Tap the real-camera button when the center ROI is framed. Long press resets to 1/8.\n" +
            "Session: $realCameraSessionId"
    }

    private fun cycleSrModelVariant() {
        srModelVariant = when (srModelVariant) {
            SrModelVariant.FLOAT -> SrModelVariant.W8A8
            SrModelVariant.W8A8 -> SrModelVariant.QUICKSR_W8A8
            SrModelVariant.QUICKSR_W8A8 -> SrModelVariant.FLOAT
        }
        val oldResolver = resolver
        val oldOfflineResolver = offlineResolver
        resolver = null
        offlineResolver = null
        liveOutputBitmap = null
        tensorLiveOutputBitmap = null
        cameraExecutor.execute { oldResolver?.close() }
        srExecutor.execute { oldOfflineResolver?.close() }
        Log.d("RB5_SR", "SR model switched to ${srModelVariant.label}")
    }

    private fun cycleSrBackend() {
        srBackend = when (srBackend) {
            SrBackend.CPU -> SrBackend.NNAPI
            SrBackend.NNAPI -> SrBackend.GPU
            SrBackend.GPU -> SrBackend.QNN
            SrBackend.QNN -> SrBackend.CPU
        }
        val oldResolver = resolver
        val oldOfflineResolver = offlineResolver
        resolver = null
        offlineResolver = null
        liveOutputBitmap = null
        tensorLiveOutputBitmap = null
        cameraExecutor.execute {
            oldResolver?.close()
        }
        srExecutor.execute {
            oldOfflineResolver?.close()
        }
        Log.d("RB5_SR", "SR backend switched to ${srBackend.label}")
    }

    private fun runOfflineEvalSamples() {
        if (liveSr) {
            statusTextView.text = "Stop live SR before running offline eval samples."
            Toast.makeText(this, "请先停止实时超分", Toast.LENGTH_SHORT).show()
            return
        }
        val previewView = findViewById<PreviewView>(R.id.previewView)
        offlineEvalActive = true
        previewView.visibility = View.GONE
        srResultView.visibility = View.VISIBLE
        statusTextView.text = "Offline SR eval running with ${srBackend.label}/${srModelVariant.label}..."
        val assetsToRun = listOf(
            OfflineEvalAsset("OFFLINE_TEXT_EDGE", "offline_text_edge_128.png"),
            OfflineEvalAsset("OFFLINE_LOWLIGHT_NOISE", "offline_lowlight_noise_128.png"),
        )
        srExecutor.execute {
            try {
                if (offlineResolver?.backend != srBackend || offlineResolver?.modelAsset != srModelVariant.assetName) {
                    offlineResolver?.close()
                    offlineResolver = null
                }
                if (offlineResolver == null) {
                    offlineResolver = SuperResolver(this, modelAsset = srModelVariant.assetName, backend = srBackend)
                }
                val timestamp = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.US).format(Date())
                val savedPaths = mutableListOf<String>()
                var lastOutput: Bitmap? = null
                var lastStatus = ""
                for (asset in assetsToRun) {
                    val t0 = System.nanoTime()
                    val source = assets.open(asset.assetName).use { input ->
                        BitmapFactory.decodeStream(input)
                    } ?: error("Cannot decode ${asset.assetName}")
                    val modelInput = if (source.width == 128 && source.height == 128) {
                        source.copy(Bitmap.Config.ARGB_8888, false)
                    } else {
                        Bitmap.createScaledBitmap(source, 128, 128, true)
                    }
                    val loadMs = (System.nanoTime() - t0) / 1_000_000
                    val (out, timing) = offlineResolver!!.enhance(modelInput)
                    val baseline = Bitmap.createScaledBitmap(modelInput, 512, 512, true)
                    val e2eMs = loadMs + timing.totalMs
                    val sample = SrSample(
                        backend = srBackend,
                        label = asset.label,
                        input = modelInput,
                        baseline = baseline,
                        sr = out,
                        inferenceMs = timing.inferenceMs,
                        e2eMs = e2eMs,
                    )
                    synchronized(srSampleLock) { latestSrSample = sample }
                    savedPaths += savePngToPictures(modelInput, "${asset.label}_${timestamp}_${srBackend.label}_${srModelVariant.label}_input_128.png")
                    savedPaths += savePngToPictures(baseline, "${asset.label}_${timestamp}_${srBackend.label}_${srModelVariant.label}_baseline_resize_512.png")
                    savedPaths += savePngToPictures(out, "${asset.label}_${timestamp}_${srBackend.label}_${srModelVariant.label}_sr_512.png")
                    lastOutput = out
                    lastStatus =
                        "${asset.label} (${srBackend.label}/${srModelVariant.label}) load ${loadMs} ms | pre ${timing.preprocessMs} ms | " +
                            "inf ${timing.inferenceMs} ms | post ${timing.postprocessMs} ms | e2e ~${e2eMs} ms"
                    Log.d("RB5_SR", "offline eval ${asset.label} backend=${srBackend.label} model=${srModelVariant.label} load=$loadMs pre=${timing.preprocessMs} inf=${timing.inferenceMs} post=${timing.postprocessMs} e2e=${e2eMs}ms saved=${savedPaths.takeLast(3).joinToString()}")
                }
                runOnUiThread {
                    offlineEvalActive = false
                    lastOutput?.let { srResultView.setImageBitmap(it) }
                    statusTextView.text = "Offline SR eval saved\n$lastStatus\n" + savedPaths.joinToString("\n")
                    Toast.makeText(this, "离线评测样张已保存", Toast.LENGTH_LONG).show()
                }
            } catch (e: Throwable) {
                Log.e("RB5_SR", "offline eval failed", e)
                runOnUiThread {
                    offlineEvalActive = false
                    statusTextView.text = "Offline eval failed: ${e.message}"
                    Toast.makeText(this, "离线评测失败", Toast.LENGTH_SHORT).show()
                }
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
        liveSrSeenFrames += 1
        val everyN = liveSrEveryN.coerceAtLeast(1)
        if (everyN > 1 && ((liveSrSeenFrames - 1) % everyN != 0)) {
            Log.d(
                srTag,
                "backend=${srBackend.label} live ROI skip everyN=$everyN frameIndex=$liveSrSeenFrames " +
                    "enhancedIndex=$liveSrEnhancedFrames model=${srModelVariant.label} session=$liveSrSessionId"
            )
            return
        }
        liveSrEnhancedFrames += 1
        try {
            if (resolver?.backend != srBackend || resolver?.modelAsset != srModelVariant.assetName) {
                resolver?.close()
                resolver = null
            }
            if (resolver == null) resolver = SuperResolver(this, modelAsset = srModelVariant.assetName, backend = srBackend)
            val tFrameStart = System.nanoTime()
            val full = imageProxy.toBitmap()
            val frameBitmapMs = (System.nanoTime() - tFrameStart) / 1_000_000
            val side = 128
            if (full.width < side || full.height < side) return
            val tRoiStart = System.nanoTime()
            val (croppedRoi, cropSide) = cropLiveDemoAwareCenterRoi(full, side)
            val demoDisplayBitmap = if (demoMode) cropLiveDemoDisplayBitmap(full, cropSide) else null
            val roiCropScaleMs = (System.nanoTime() - tRoiStart) / 1_000_000
            var roi = croppedRoi
            val degrees = imageProxy.imageInfo.rotationDegrees
            val tRotateStart = System.nanoTime()
            if (degrees != 0) {
                val matrix = Matrix().apply { postRotate(degrees.toFloat()) }
                roi = Bitmap.createBitmap(roi, 0, 0, side, side, matrix, true)
            }
            val rotateMs = (System.nanoTime() - tRotateStart) / 1_000_000
            val captureMs = frameBitmapMs + roiCropScaleMs + rotateMs
            val tEnhanceStart = System.nanoTime()
            val (out, t) = resolver!!.enhanceInto(roi, liveOutputBitmap)
            liveOutputBitmap = out
            val enhanceWallMs = (System.nanoTime() - tEnhanceStart) / 1_000_000
            val e2eMs = captureMs + t.totalMs
            val tSampleStart = System.nanoTime()
            if (frameCount % LIVE_SAMPLE_CAPTURE_INTERVAL == 0) {
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
            }
            val sampleCopyMs = (System.nanoTime() - tSampleStart) / 1_000_000
            val analyzerWallMs = frameBitmapMs + roiCropScaleMs + rotateMs + enhanceWallMs + sampleCopyMs
            val elapsedNs = (System.nanoTime() - liveSrStartNs).coerceAtLeast(1L)
            val effectiveEnhancedFps = liveSrEnhancedFrames * 1_000_000_000.0 / elapsedNs.toDouble()
            Log.d(
                srTag,
                "backend=${srBackend.label} live ROI crop=${cropSide}->128->512 frame=${full.width}x${full.height} cap=$captureMs frameBitmap=$frameBitmapMs roi=$roiCropScaleMs rotate=$rotateMs pre=${t.preprocessMs} inf=${t.inferenceMs} post=${t.postprocessMs} enhanceWall=$enhanceWallMs sampleCopy=$sampleCopyMs analyzer=$analyzerWallMs e2e=${e2eMs}ms"
                    + " model=${srModelVariant.label} session=$liveSrSessionId everyN=$everyN frameIndex=$liveSrSeenFrames enhancedIndex=$liveSrEnhancedFrames effectiveEnhancedFps=${"%.2f".format(Locale.US, effectiveEnhancedFps)}"
                    + if (demoMode) " display=wide_preview" else ""
            )
            runOnUiThread {
                srResultView.setImageBitmap(demoDisplayBitmap ?: out)
                if (demoMode) {
                    demoOverlayView.text = liveDemoOverlayText(
                        t,
                        e2eMs,
                        effectiveEnhancedFps,
                        full.width,
                        full.height,
                        cropSide,
                        everyN,
                    )
                } else {
                    statusTextView.text =
                        "Live ROI SR (TFLite ${srBackend.label}/${srModelVariant.label})\n" +
                            "frame ${full.width}x${full.height} | ROI ${cropSide}->128\n" +
                            "everyN $everyN | enhanced $liveSrEnhancedFrames/$liveSrSeenFrames\n" +
                            "capture+crop ${captureMs} ms | preprocess ${t.preprocessMs} ms\n" +
                            "inference ${t.inferenceMs} ms | postprocess ${t.postprocessMs} ms\n" +
                            "end-to-end ~${e2eMs} ms"
                }
            }
        } catch (e: Throwable) {
            Log.e(srTag, "live SR failed", e)
            liveSr = false
            liveOutputBitmap = null
            runOnUiThread {
                hideLiveSrOutput()
                findViewById<Button>(R.id.sr_button).text = startButtonText()
                statusTextView.text = "Live SR failed on ${srBackend.label}. Long press to choose another backend."
            }
        }
    }

    private fun runTensorReadyLiveSr(imageProxy: ImageProxy) {
        val tag = "RB5_SR_TENSOR"
        try {
            if (resolver?.backend != SrBackend.QNN || resolver?.modelAsset != SrModelVariant.QUICKSR_W8A8.assetName) {
                resolver?.close()
                resolver = null
            }
            if (resolver == null) {
                resolver = SuperResolver(
                    this,
                    modelAsset = SrModelVariant.QUICKSR_W8A8.assetName,
                    backend = SrBackend.QNN,
                )
            }
            val side = 128
            val degrees = imageProxy.imageInfo.rotationDegrees
            val tRgbStart = System.nanoTime()
            var rgbBytes = nativeYuv420ToRgbCenterRoiBytes(imageProxy, side)
            if (degrees != 0) {
                val nativeBitmap = rgbBytesToBitmap(rgbBytes, side)
                val matrix = Matrix().apply { postRotate(degrees.toFloat()) }
                val rotated = Bitmap.createBitmap(nativeBitmap, 0, 0, side, side, matrix, true)
                rgbBytes = bitmapToRgbBytes(rotated)
            }
            val nativeRgbMs = (System.nanoTime() - tRgbStart) / 1_000_000
            val tEnhanceStart = System.nanoTime()
            val (out, timing) = resolver!!.enhanceRgbBytesInto(rgbBytes, tensorLiveOutputBitmap)
            tensorLiveOutputBitmap = out
            val enhanceWallMs = (System.nanoTime() - tEnhanceStart) / 1_000_000
            val e2eMs = nativeRgbMs + timing.totalMs
            val analyzerWallMs = nativeRgbMs + enhanceWallMs
            Log.d(
                tag,
                "backend=QNN model=QUICKSR_W8A8 tensorLive crop=256->128->512 " +
                    "frame=${imageProxy.width}x${imageProxy.height} nativeRgb=$nativeRgbMs rotate=$degrees " +
                    "pre=${timing.preprocessMs} inf=${timing.inferenceMs} post=${timing.postprocessMs} " +
                    "enhanceWall=$enhanceWallMs analyzer=$analyzerWallMs e2e=${e2eMs}ms"
            )
            runOnUiThread {
                srResultView.setImageBitmap(out)
                statusTextView.text =
                    "Tensor-ready live ROI SR (QNN/QUICKSR_W8A8)\n" +
                        "frame ${imageProxy.width}x${imageProxy.height} | ROI 128\n" +
                        "native RGB ${nativeRgbMs} ms | preprocess ${timing.preprocessMs} ms\n" +
                        "inference ${timing.inferenceMs} ms | postprocess ${timing.postprocessMs} ms\n" +
                        "end-to-end ~${e2eMs} ms"
            }
        } catch (e: Throwable) {
            Log.e(tag, "tensor-ready live SR failed", e)
            liveSrTensorReady = false
            tensorLiveOutputBitmap = null
            runOnUiThread {
                srResultView.visibility = View.GONE
                findViewById<PreviewView>(R.id.previewView).visibility = View.VISIBLE
                findViewById<Button>(R.id.sr_button).text = startButtonText()
                statusTextView.text = "Tensor-ready live SR failed: ${e.message}"
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

    private fun requestTileStillCapture() {
        if (liveSr || liveSrTensorReady) {
            statusTextView.text = "Stop live SR before running tile still capture."
            Toast.makeText(this, "请先停止实时超分，再运行整图 Tile", Toast.LENGTH_SHORT).show()
            return
        }
        if (pendingTileStillCapture) {
            statusTextView.text = "Tile still capture is already pending. Keep the camera steady."
            return
        }
        pendingTileStillCapture = true
        statusTextView.text = "Tile still capture armed. Keep the camera steady."
        Toast.makeText(this, "保持画面稳定，正在采集整图 Tile", Toast.LENGTH_SHORT).show()
    }

    private fun requestRealCameraCapture() {
        if (liveSr) {
            statusTextView.text = "Stop live SR before capturing real-camera evidence."
            Toast.makeText(this, "请先停止实时超分，再采集真实相机证据", Toast.LENGTH_SHORT).show()
            return
        }
        if (pendingRealCameraCapture) {
            statusTextView.text = "Real-camera capture is already pending. Keep the scene steady."
            return
        }
        pendingRealCameraCapture = true
        offlineEvalActive = true
        statusTextView.text = realCameraPromptText() + "\n\nCapturing next camera frame..."
        Toast.makeText(this, "保持画面稳定，正在采集当前场景", Toast.LENGTH_SHORT).show()
    }

    private fun runRealCameraCapture(imageProxy: ImageProxy) {
        val scene = realCameraScenes[realCameraSceneIndex.coerceIn(0, realCameraScenes.lastIndex)]
        try {
            val side = 128
            val full = imageProxy.toBitmap()
            if (full.width < side || full.height < side) error("Camera frame too small for real-camera ROI")
            val (croppedRoi, cropSide) = cropCenterRoiKeepingLegacyFov(full, side)
            var roi = croppedRoi
            val degrees = imageProxy.imageInfo.rotationDegrees
            if (degrees != 0) {
                val matrix = Matrix().apply { postRotate(degrees.toFloat()) }
                roi = Bitmap.createBitmap(roi, 0, 0, side, side, matrix, true)
            }

            val baseline = Bitmap.createScaledBitmap(roi, 512, 512, true)
            val quickResolver = SuperResolver(
                this,
                modelAsset = SrModelVariant.QUICKSR_W8A8.assetName,
                backend = SrBackend.QNN,
            )
            val realResolver = SuperResolver(
                this,
                modelAsset = SrModelVariant.W8A8.assetName,
                backend = SrBackend.QNN,
            )
            val quickResult = try {
                quickResolver.enhance(roi)
            } finally {
                quickResolver.close()
            }
            val realResult = try {
                realResolver.enhance(roi)
            } finally {
                realResolver.close()
            }

            val prefix = "REALCAM_${realCameraSessionId}_${scene.id}"
            val saved = listOf(
                savePngToPictures(roi, "${prefix}_input_128.png"),
                savePngToPictures(baseline, "${prefix}_bicubic_512.png"),
                savePngToPictures(quickResult.first, "${prefix}_quicksr_qnn_512.png"),
                savePngToPictures(realResult.first, "${prefix}_realesrgan_qnn_512.png"),
            )
            synchronized(srSampleLock) {
                latestSrSample = SrSample(
                    backend = SrBackend.QNN,
                    label = "REALCAM_${scene.id}_QUICKSR",
                    input = roi.copy(Bitmap.Config.ARGB_8888, false),
                    baseline = baseline,
                    sr = quickResult.first.copy(Bitmap.Config.ARGB_8888, false),
                    inferenceMs = quickResult.second.inferenceMs,
                    e2eMs = quickResult.second.totalMs,
                )
            }
            Log.d(
                "RB5_REALCAM",
                "capture scene=${scene.id} session=$realCameraSessionId frame=${full.width}x${full.height} crop=${cropSide}->128 " +
                    "quick_pre=${quickResult.second.preprocessMs} quick_inf=${quickResult.second.inferenceMs} quick_post=${quickResult.second.postprocessMs} " +
                    "real_pre=${realResult.second.preprocessMs} real_inf=${realResult.second.inferenceMs} real_post=${realResult.second.postprocessMs} " +
                    "saved=${saved.joinToString()}"
            )
            val completedIndex = realCameraSceneIndex + 1
            if (realCameraSceneIndex < realCameraScenes.lastIndex) {
                realCameraSceneIndex += 1
            }
            runOnUiThread {
                offlineEvalActive = false
                srResultView.visibility = View.GONE
                findViewById<PreviewView>(R.id.previewView).visibility = View.VISIBLE
                val button = findViewById<Button>(R.id.real_camera_button)
                button.text = realCameraButtonText()
                val nextText = if (completedIndex >= realCameraScenes.size) {
                    "All 8 planned scenes are captured. Long press the real-camera button to restart if you need a retake."
                } else {
                    "Next:\n" + realCameraPromptText()
                }
                statusTextView.text =
                    "Saved real-camera scene $completedIndex/${realCameraScenes.size}: ${scene.title}\n" +
                        "QuickSR inf ${quickResult.second.inferenceMs} ms | Real-ESRGAN inf ${realResult.second.inferenceMs} ms\n" +
                        saved.joinToString("\n") + "\n\n" + nextText
                Toast.makeText(this, "真实相机证据已保存", Toast.LENGTH_LONG).show()
            }
        } catch (e: Throwable) {
            Log.e("RB5_REALCAM", "capture failed scene=${scene.id}", e)
            runOnUiThread {
                offlineEvalActive = false
                srResultView.visibility = View.GONE
                findViewById<PreviewView>(R.id.previewView).visibility = View.VISIBLE
                statusTextView.text = "Real-camera capture failed: ${e.message}\nTap again after reframing."
                Toast.makeText(this, "真实相机证据保存失败", Toast.LENGTH_SHORT).show()
            }
        }
    }

    private fun runTileStillCapture(imageProxy: ImageProxy) {
        try {
            offlineEvalActive = true
            val stillSide = 512
            val tileSide = 128
            val full = imageProxy.toBitmap()
            if (full.width < stillSide || full.height < stillSide) error("Camera frame too small for tile still")
            val (croppedStill, cropSide) = cropCenterRoiKeepingLegacyFov(full, stillSide)
            var still = croppedStill
            val degrees = imageProxy.imageInfo.rotationDegrees
            if (degrees != 0) {
                val matrix = Matrix().apply { postRotate(degrees.toFloat()) }
                still = Bitmap.createBitmap(still, 0, 0, stillSide, stillSide, matrix, true)
            }

            val selectedTileModel = tileModelVariant
            val totalStart = System.nanoTime()
            val (tileSr, tileTimings) = runTileModelOnStill(still, selectedTileModel)
            val totalMs = (System.nanoTime() - totalStart) / 1_000_000
            val baseline = Bitmap.createScaledBitmap(still, stillSide * 4, stillSide * 4, true)
            val sheet = makeTileComparisonSheet(still, baseline, tileSr)
            val timestamp = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.US).format(Date())
            val tileModelLabel = when (selectedTileModel) {
                SrModelVariant.W8A8 -> "REALESRGAN"
                SrModelVariant.QUICKSR_W8A8 -> "QUICKSR"
                SrModelVariant.FLOAT -> "FLOAT"
            }
            val prefix = "TILE_STILL_${timestamp}_${tileModelLabel}_QNN"
            val saved = listOf(
                savePngToPictures(still, "${prefix}_input_512.png"),
                savePngToPictures(baseline, "${prefix}_bicubic_2048.png"),
                savePngToPictures(tileSr, "${prefix}_tile_sr_2048.png"),
                savePngToPictures(sheet, "${prefix}_comparison.png"),
            )
            val p50 = percentileLong(tileTimings, 0.50)
            val p95 = percentileLong(tileTimings, 0.95)
            synchronized(srSampleLock) {
                latestSrSample = SrSample(
                    backend = SrBackend.QNN,
                    label = "TILE_STILL_${tileModelLabel}",
                    input = still.copy(Bitmap.Config.ARGB_8888, false),
                    baseline = baseline,
                    sr = tileSr.copy(Bitmap.Config.ARGB_8888, false),
                    inferenceMs = p50,
                    e2eMs = totalMs,
                )
            }
            Log.d(
                "RB5_TILE",
                "tile still model=${selectedTileModel.label} frame=${full.width}x${full.height} crop=${cropSide}->512 tiles=${tileTimings.size} " +
                    "tileP50=$p50 tileP95=$p95 total=$totalMs saved=${saved.joinToString()}"
            )
            runOnUiThread {
                offlineEvalActive = false
                srResultView.visibility = View.VISIBLE
                findViewById<PreviewView>(R.id.previewView).visibility = View.GONE
                srResultView.setImageBitmap(tileSr)
                statusTextView.text =
                    "Tile still SR saved (${selectedTileModel.label}/QNN)\n" +
                        "frame ${full.width}x${full.height} | crop ${cropSide}->512 | output 2048\n" +
                        "tiles ${tileTimings.size} | tile p50/p95 ${p50}/${p95} ms | total ${totalMs} ms\n" +
                        saved.joinToString("\n")
                Toast.makeText(this, "整图 Tile 结果已保存", Toast.LENGTH_LONG).show()
            }
        } catch (e: Throwable) {
            Log.e("RB5_TILE", "tile still capture failed", e)
            runOnUiThread {
                offlineEvalActive = false
                srResultView.visibility = View.GONE
                findViewById<PreviewView>(R.id.previewView).visibility = View.VISIBLE
                statusTextView.text = "Tile still capture failed: ${e.message}"
                Toast.makeText(this, "整图 Tile 失败", Toast.LENGTH_SHORT).show()
            }
        }
    }

    private fun runTileCompareCapture(imageProxy: ImageProxy) {
        try {
            offlineEvalActive = true
            val stillSide = 512
            val full = imageProxy.toBitmap()
            if (full.width < stillSide || full.height < stillSide) error("Camera frame too small for tile compare")
            val (croppedStill, cropSide) = cropCenterRoiKeepingLegacyFov(full, stillSide)
            var still = croppedStill
            val degrees = imageProxy.imageInfo.rotationDegrees
            if (degrees != 0) {
                val matrix = Matrix().apply { postRotate(degrees.toFloat()) }
                still = Bitmap.createBitmap(still, 0, 0, stillSide, stillSide, matrix, true)
            }

            val totalStart = System.nanoTime()
            val (quickSr, quickTimings) = runTileModelOnStill(still, SrModelVariant.QUICKSR_W8A8)
            val (realSr, realTimings) = runTileModelOnStill(still, SrModelVariant.W8A8)
            val totalMs = (System.nanoTime() - totalStart) / 1_000_000
            val baseline = Bitmap.createScaledBitmap(still, stillSide * 4, stillSide * 4, true)
            val sheet = makeTileComparisonSheet(still, baseline, quickSr, realSr)
            val timestamp = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.US).format(Date())
            val prefix = "TILE_COMPARE_${timestamp}_QNN"
            val saved = listOf(
                savePngToPictures(still, "${prefix}_input_512.png"),
                savePngToPictures(baseline, "${prefix}_bicubic_2048.png"),
                savePngToPictures(quickSr, "${prefix}_quicksr_2048.png"),
                savePngToPictures(realSr, "${prefix}_realesrgan_2048.png"),
                savePngToPictures(sheet, "${prefix}_comparison.png"),
            )
            val quickP50 = percentileLong(quickTimings, 0.50)
            val quickP95 = percentileLong(quickTimings, 0.95)
            val realP50 = percentileLong(realTimings, 0.50)
            val realP95 = percentileLong(realTimings, 0.95)
            synchronized(srSampleLock) {
                latestSrSample = SrSample(
                    backend = SrBackend.QNN,
                    label = "TILE_COMPARE_REALESRGAN",
                    input = still.copy(Bitmap.Config.ARGB_8888, false),
                    baseline = baseline,
                    sr = realSr.copy(Bitmap.Config.ARGB_8888, false),
                    inferenceMs = realP50,
                    e2eMs = totalMs,
                )
            }
            Log.d(
                "RB5_TILE",
                "tile compare frame=${full.width}x${full.height} crop=${cropSide}->512 " +
                    "quickTiles=${quickTimings.size} quickP50=$quickP50 quickP95=$quickP95 " +
                    "realTiles=${realTimings.size} realP50=$realP50 realP95=$realP95 total=$totalMs saved=${saved.joinToString()}"
            )
            runOnUiThread {
                offlineEvalActive = false
                srResultView.visibility = View.VISIBLE
                findViewById<PreviewView>(R.id.previewView).visibility = View.GONE
                srResultView.setImageBitmap(realSr)
                statusTextView.text =
                    "Tile compare saved (QuickSR vs Real-ESRGAN, same frame)\n" +
                        "frame ${full.width}x${full.height} | crop ${cropSide}->512 | output 2048\n" +
                        "Quick p50/p95 ${quickP50}/${quickP95} ms | Real p50/p95 ${realP50}/${realP95} ms | total ${totalMs} ms\n" +
                        saved.joinToString("\n")
                Toast.makeText(this, "同帧 Tile 对比已保存", Toast.LENGTH_LONG).show()
            }
        } catch (e: Throwable) {
            Log.e("RB5_TILE", "tile compare capture failed", e)
            runOnUiThread {
                offlineEvalActive = false
                srResultView.visibility = View.GONE
                findViewById<PreviewView>(R.id.previewView).visibility = View.VISIBLE
                statusTextView.text = "Tile compare failed: ${e.message}"
                Toast.makeText(this, "同帧 Tile 对比失败", Toast.LENGTH_SHORT).show()
            }
        }
    }

    private fun runTileModelOnStill(still: Bitmap, modelVariant: SrModelVariant): Pair<Bitmap, List<Long>> {
        val stillSide = 512
        val tileSide = 128
        val resolver = SuperResolver(
            this,
            modelAsset = modelVariant.assetName,
            backend = SrBackend.QNN,
        )
        val tileSr = Bitmap.createBitmap(stillSide * 4, stillSide * 4, Bitmap.Config.ARGB_8888)
        val canvas = android.graphics.Canvas(tileSr)
        val tileTimings = mutableListOf<Long>()
        try {
            for (tileY in 0 until stillSide step tileSide) {
                for (tileX in 0 until stillSide step tileSide) {
                    val tile = Bitmap.createBitmap(still, tileX, tileY, tileSide, tileSide)
                    val (srTile, timing) = resolver.enhance(tile)
                    tileTimings += timing.totalMs
                    canvas.drawBitmap(srTile, (tileX * 4).toFloat(), (tileY * 4).toFloat(), null)
                }
            }
        } finally {
            resolver.close()
        }
        return Pair(tileSr, tileTimings)
    }

    private fun runYuvRoiProbe(imageProxy: ImageProxy) {
        try {
            val side = 128
            val tBitmap0 = System.nanoTime()
            val full = imageProxy.toBitmap()
            val bitmapMs = (System.nanoTime() - tBitmap0) / 1_000_000
            val tCrop0 = System.nanoTime()
            var bitmapRoi = cropCenterRoiKeepingLegacyFov(full, side).first
            val degrees = imageProxy.imageInfo.rotationDegrees
            if (degrees != 0) {
                val matrix = Matrix().apply { postRotate(degrees.toFloat()) }
                bitmapRoi = Bitmap.createBitmap(bitmapRoi, 0, 0, side, side, matrix, true)
            }
            val bitmapCropMs = (System.nanoTime() - tCrop0) / 1_000_000

            val tYuv0 = System.nanoTime()
            var yuvRoi = yuv420ToRgbCenterRoiKeepingLegacyFov(imageProxy, side)
            if (degrees != 0) {
                val matrix = Matrix().apply { postRotate(degrees.toFloat()) }
                yuvRoi = Bitmap.createBitmap(yuvRoi, 0, 0, side, side, matrix, true)
            }
            val yuvRoiMs = (System.nanoTime() - tYuv0) / 1_000_000
            val tNative0 = System.nanoTime()
            var nativeRoi = nativeYuv420ToRgbCenterRoiKeepingLegacyFov(imageProxy, side)
            if (degrees != 0) {
                val matrix = Matrix().apply { postRotate(degrees.toFloat()) }
                nativeRoi = Bitmap.createBitmap(nativeRoi, 0, 0, side, side, matrix, true)
            }
            val nativeRoiMs = (System.nanoTime() - tNative0) / 1_000_000
            val yuvMad = meanAbsDiff(bitmapRoi, yuvRoi)
            val nativeMad = meanAbsDiff(bitmapRoi, nativeRoi)
            val timestamp = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.US).format(Date())
            val prefix = "YUV_ROI_PROBE_${timestamp}"
            val saved = listOf(
                savePngToPictures(bitmapRoi, "${prefix}_bitmap_roi_128.png"),
                savePngToPictures(yuvRoi, "${prefix}_yuv_roi_128.png"),
                savePngToPictures(nativeRoi, "${prefix}_native_roi_128.png"),
                savePngToPictures(makeHorizontalSheet(listOf(bitmapRoi, yuvRoi, nativeRoi)), "${prefix}_side_by_side.png"),
            )
            Log.d(
                "RB5_YUV_ROI",
                "probe frame=${imageProxy.width}x${imageProxy.height} rotation=$degrees " +
                    "bitmapMs=$bitmapMs bitmapCropMs=$bitmapCropMs yuvRoiMs=$yuvRoiMs nativeRoiMs=$nativeRoiMs " +
                    "yuvMad=${"%.2f".format(Locale.US, yuvMad)} nativeMad=${"%.2f".format(Locale.US, nativeMad)} " +
                    "yRow=${imageProxy.planes[0].rowStride} uRow=${imageProxy.planes[1].rowStride} vRow=${imageProxy.planes[2].rowStride} " +
                    "uPixel=${imageProxy.planes[1].pixelStride} vPixel=${imageProxy.planes[2].pixelStride} saved=${saved.joinToString()}"
            )
            runOnUiThread {
                offlineEvalActive = false
                statusTextView.text =
                    "YUV ROI probe saved\n" +
                        "bitmap $bitmapMs+$bitmapCropMs ms | kotlin $yuvRoiMs ms | native $nativeRoiMs ms\n" +
                        "MAD kotlin ${"%.2f".format(Locale.US, yuvMad)} | native ${"%.2f".format(Locale.US, nativeMad)}\n" +
                        saved.joinToString("\n")
                Toast.makeText(this, "YUV ROI probe saved", Toast.LENGTH_LONG).show()
            }
        } catch (e: Throwable) {
            Log.e("RB5_YUV_ROI", "probe failed", e)
            runOnUiThread {
                offlineEvalActive = false
                statusTextView.text = "YUV ROI probe failed: ${e.message}"
                Toast.makeText(this, "YUV ROI probe failed", Toast.LENGTH_SHORT).show()
            }
        }
    }

    private fun runTensorReadyProbe(imageProxy: ImageProxy) {
        var resolver: SuperResolver? = null
        try {
            Log.d("RB5_TENSOR_READY", "probe begin")
            val side = 128
            val degrees = imageProxy.imageInfo.rotationDegrees
            val tBitmap0 = System.nanoTime()
            val full = imageProxy.toBitmap()
            val bitmapMs = (System.nanoTime() - tBitmap0) / 1_000_000
            Log.d("RB5_TENSOR_READY", "after toBitmap bitmapMs=$bitmapMs frame=${full.width}x${full.height}")
            val tBitmapCrop0 = System.nanoTime()
            var bitmapRoi = cropCenterRoiKeepingLegacyFov(full, side).first
            if (degrees != 0) {
                val matrix = Matrix().apply { postRotate(degrees.toFloat()) }
                bitmapRoi = Bitmap.createBitmap(bitmapRoi, 0, 0, side, side, matrix, true)
            }
            val bitmapCropMs = (System.nanoTime() - tBitmapCrop0) / 1_000_000
            Log.d("RB5_TENSOR_READY", "after bitmap crop bitmapCropMs=$bitmapCropMs rotation=$degrees")

            val tRgb0 = System.nanoTime()
            var rgbBytes = nativeYuv420ToRgbCenterRoiBytes(imageProxy, side)
            if (degrees != 0) {
                val nativeBitmap = rgbBytesToBitmap(rgbBytes, side)
                val matrix = Matrix().apply { postRotate(degrees.toFloat()) }
                val rotated = Bitmap.createBitmap(nativeBitmap, 0, 0, side, side, matrix, true)
                rgbBytes = bitmapToRgbBytes(rotated)
            }
            val nativeRgbMs = (System.nanoTime() - tRgb0) / 1_000_000
            Log.d("RB5_TENSOR_READY", "after native rgb nativeRgbMs=$nativeRgbMs bytes=${rgbBytes.size}")

            Log.d("RB5_TENSOR_READY", "creating resolver")
            resolver = SuperResolver(
                this,
                modelAsset = SrModelVariant.QUICKSR_W8A8.assetName,
                backend = SrBackend.QNN,
            )
            Log.d("RB5_TENSOR_READY", "resolver created")
            val tBitmapEnhance0 = System.nanoTime()
            val bitmapResult = resolver.enhance(bitmapRoi)
            val bitmapEnhanceWallMs = (System.nanoTime() - tBitmapEnhance0) / 1_000_000
            Log.d("RB5_TENSOR_READY", "after bitmap enhance wall=$bitmapEnhanceWallMs")
            val tRgbEnhance0 = System.nanoTime()
            val rgbResult = resolver.enhanceRgbBytes(rgbBytes)
            val rgbEnhanceWallMs = (System.nanoTime() - tRgbEnhance0) / 1_000_000
            Log.d("RB5_TENSOR_READY", "after rgb enhance wall=$rgbEnhanceWallMs")
            val outputMad = meanAbsDiff(bitmapResult.first, rgbResult.first)
            val inputMad = meanAbsDiff(bitmapRoi, rgbBytesToBitmap(rgbBytes, side))
            val timestamp = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.US).format(Date())
            val prefix = "TENSOR_READY_PROBE_${timestamp}"
            val saved = listOf(
                savePngToPictures(bitmapRoi, "${prefix}_bitmap_input_128.png"),
                savePngToPictures(rgbBytesToBitmap(rgbBytes, side), "${prefix}_native_rgb_input_128.png"),
                savePngToPictures(bitmapResult.first, "${prefix}_bitmap_sr_512.png"),
                savePngToPictures(rgbResult.first, "${prefix}_rgbbytes_sr_512.png"),
                savePngToPictures(makeHorizontalSheet(listOf(bitmapResult.first, rgbResult.first)), "${prefix}_sr_side_by_side.png"),
            )
            val bitmapPathMs = bitmapMs + bitmapCropMs + bitmapEnhanceWallMs
            val rgbPathMs = nativeRgbMs + rgbEnhanceWallMs
            Log.d(
                "RB5_TENSOR_READY",
                "probe frame=${imageProxy.width}x${imageProxy.height} rotation=$degrees " +
                    "bitmapMs=$bitmapMs bitmapCropMs=$bitmapCropMs nativeRgbMs=$nativeRgbMs " +
                    "bitmapPre=${bitmapResult.second.preprocessMs} bitmapInf=${bitmapResult.second.inferenceMs} bitmapPost=${bitmapResult.second.postprocessMs} bitmapEnhanceWall=$bitmapEnhanceWallMs bitmapPath=$bitmapPathMs " +
                    "rgbPre=${rgbResult.second.preprocessMs} rgbInf=${rgbResult.second.inferenceMs} rgbPost=${rgbResult.second.postprocessMs} rgbEnhanceWall=$rgbEnhanceWallMs rgbPath=$rgbPathMs " +
                    "inputMad=${"%.2f".format(Locale.US, inputMad)} outputMad=${"%.2f".format(Locale.US, outputMad)} saved=${saved.joinToString()}"
            )
            runOnUiThread {
                offlineEvalActive = false
                statusTextView.text =
                    "Tensor-ready probe saved\n" +
                        "bitmap path $bitmapPathMs ms | rgb path $rgbPathMs ms\n" +
                        "input MAD ${"%.2f".format(Locale.US, inputMad)} | output MAD ${"%.2f".format(Locale.US, outputMad)}\n" +
                        saved.joinToString("\n")
                Toast.makeText(this, "Tensor-ready probe saved", Toast.LENGTH_LONG).show()
            }
        } catch (e: Throwable) {
            Log.e("RB5_TENSOR_READY", "probe failed", e)
            runOnUiThread {
                offlineEvalActive = false
                statusTextView.text = "Tensor-ready probe failed: ${e.message}"
                Toast.makeText(this, "Tensor-ready probe failed", Toast.LENGTH_SHORT).show()
            }
        } finally {
            resolver?.close()
        }
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

    private fun cropLiveDemoAwareCenterRoi(full: Bitmap, modelInputSide: Int): Pair<Bitmap, Int> {
        if (!demoMode) {
            return cropCenterRoiKeepingLegacyFov(full, modelInputSide)
        }
        val cropSide = minOf(full.width, full.height).coerceAtLeast(modelInputSide)
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

    private fun cropLiveDemoDisplayBitmap(full: Bitmap, cropSide: Int): Bitmap {
        val left = (full.width - cropSide) / 2
        val top = (full.height - cropSide) / 2
        return Bitmap.createBitmap(full, left, top, cropSide, cropSide)
    }

    private fun yuv420ToRgbCenterRoiKeepingLegacyFov(imageProxy: ImageProxy, outputSide: Int): Bitmap {
        val cropSide = minOf(
            imageProxy.width * outputSide / LEGACY_ANALYSIS_WIDTH,
            imageProxy.width,
            imageProxy.height,
        ).coerceAtLeast(outputSide)
        val left = (imageProxy.width - cropSide) / 2
        val top = (imageProxy.height - cropSide) / 2
        val pixels = IntArray(outputSide * outputSide)
        val yPlane = imageProxy.planes[0]
        val uPlane = imageProxy.planes[1]
        val vPlane = imageProxy.planes[2]
        val yBuffer = yPlane.buffer
        val uBuffer = uPlane.buffer
        val vBuffer = vPlane.buffer
        for (oy in 0 until outputSide) {
            val srcY = top + (oy * cropSide + cropSide / (outputSide * 2)) / outputSide
            val yBase = srcY * yPlane.rowStride
            val uvY = srcY / 2
            val uBase = uvY * uPlane.rowStride
            val vBase = uvY * vPlane.rowStride
            for (ox in 0 until outputSide) {
                val srcX = left + (ox * cropSide + cropSide / (outputSide * 2)) / outputSide
                val yValue = yBuffer.get(yBase + srcX * yPlane.pixelStride).toInt() and 0xFF
                val uvX = srcX / 2
                val uValue = uBuffer.get(uBase + uvX * uPlane.pixelStride).toInt() and 0xFF
                val vValue = vBuffer.get(vBase + uvX * vPlane.pixelStride).toInt() and 0xFF
                pixels[oy * outputSide + ox] = yuvToArgb(yValue, uValue, vValue)
            }
        }
        return Bitmap.createBitmap(pixels, outputSide, outputSide, Bitmap.Config.ARGB_8888)
    }

    private fun nativeYuv420ToRgbCenterRoiKeepingLegacyFov(imageProxy: ImageProxy, outputSide: Int): Bitmap {
        val y = imageProxy.planes[0]
        val u = imageProxy.planes[1]
        val v = imageProxy.planes[2]
        val yBytes = ByteArray(y.buffer.remaining())
        val uBytes = ByteArray(u.buffer.remaining())
        val vBytes = ByteArray(v.buffer.remaining())
        y.buffer.duplicate().get(yBytes)
        u.buffer.duplicate().get(uBytes)
        v.buffer.duplicate().get(vBytes)
        val pixels = nativeYuvToRgbRoi(
            yBytes,
            uBytes,
            vBytes,
            imageProxy.width,
            imageProxy.height,
            y.rowStride,
            y.pixelStride,
            u.rowStride,
            u.pixelStride,
            v.rowStride,
            v.pixelStride,
            outputSide,
        )
        return Bitmap.createBitmap(pixels, outputSide, outputSide, Bitmap.Config.ARGB_8888)
    }

    private fun nativeYuv420ToRgbCenterRoiBytes(imageProxy: ImageProxy, outputSide: Int): ByteArray {
        val y = imageProxy.planes[0]
        val u = imageProxy.planes[1]
        val v = imageProxy.planes[2]
        val yBytes = ByteArray(y.buffer.remaining())
        val uBytes = ByteArray(u.buffer.remaining())
        val vBytes = ByteArray(v.buffer.remaining())
        y.buffer.duplicate().get(yBytes)
        u.buffer.duplicate().get(uBytes)
        v.buffer.duplicate().get(vBytes)
        return nativeYuvToRgbRoiBytes(
            yBytes,
            uBytes,
            vBytes,
            imageProxy.width,
            imageProxy.height,
            y.rowStride,
            y.pixelStride,
            u.rowStride,
            u.pixelStride,
            v.rowStride,
            v.pixelStride,
            outputSide,
        )
    }

    private fun rgbBytesToBitmap(rgb: ByteArray, side: Int): Bitmap {
        val pixels = IntArray(side * side)
        for (i in pixels.indices) {
            val base = i * 3
            val r = rgb[base].toInt() and 0xFF
            val g = rgb[base + 1].toInt() and 0xFF
            val b = rgb[base + 2].toInt() and 0xFF
            pixels[i] = -0x1000000 or (r shl 16) or (g shl 8) or b
        }
        return Bitmap.createBitmap(pixels, side, side, Bitmap.Config.ARGB_8888)
    }

    private fun bitmapToRgbBytes(bitmap: Bitmap): ByteArray {
        val pixels = IntArray(bitmap.width * bitmap.height)
        bitmap.getPixels(pixels, 0, bitmap.width, 0, 0, bitmap.width, bitmap.height)
        val rgb = ByteArray(pixels.size * 3)
        for (i in pixels.indices) {
            val pixel = pixels[i]
            val base = i * 3
            rgb[base] = ((pixel shr 16) and 0xFF).toByte()
            rgb[base + 1] = ((pixel shr 8) and 0xFF).toByte()
            rgb[base + 2] = (pixel and 0xFF).toByte()
        }
        return rgb
    }

    private fun yuvToArgb(y: Int, u: Int, v: Int): Int {
        val yf = y.toFloat()
        val uf = u.toFloat() - 128f
        val vf = v.toFloat() - 128f
        val r = (yf + 1.402f * vf).toInt().coerceIn(0, 255)
        val g = (yf - 0.344136f * uf - 0.714136f * vf).toInt().coerceIn(0, 255)
        val b = (yf + 1.772f * uf).toInt().coerceIn(0, 255)
        return -0x1000000 or (r shl 16) or (g shl 8) or b
    }

    private fun meanAbsDiff(a: Bitmap, b: Bitmap): Double {
        val width = minOf(a.width, b.width)
        val height = minOf(a.height, b.height)
        val aPixels = IntArray(width * height)
        val bPixels = IntArray(width * height)
        a.getPixels(aPixels, 0, width, 0, 0, width, height)
        b.getPixels(bPixels, 0, width, 0, 0, width, height)
        var sum = 0L
        for (i in aPixels.indices) {
            val ap = aPixels[i]
            val bp = bPixels[i]
            sum += kotlin.math.abs(((ap shr 16) and 0xFF) - ((bp shr 16) and 0xFF))
            sum += kotlin.math.abs(((ap shr 8) and 0xFF) - ((bp shr 8) and 0xFF))
            sum += kotlin.math.abs((ap and 0xFF) - (bp and 0xFF))
        }
        return sum.toDouble() / (aPixels.size * 3)
    }

    private fun makeHorizontalSheet(bitmaps: List<Bitmap>): Bitmap {
        val width = bitmaps.sumOf { it.width }
        val height = bitmaps.maxOf { it.height }
        val out = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888)
        val canvas = android.graphics.Canvas(out)
        var x = 0f
        for (bitmap in bitmaps) {
            canvas.drawBitmap(bitmap, x, 0f, null)
            x += bitmap.width
        }
        return out
    }

    private fun makeTileComparisonSheet(input: Bitmap, bicubic: Bitmap, tileSr: Bitmap): Bitmap {
        val inputPreview = Bitmap.createScaledBitmap(input, 512, 512, true)
        val bicubicPreview = Bitmap.createScaledBitmap(bicubic, 512, 512, true)
        val tilePreview = Bitmap.createScaledBitmap(tileSr, 512, 512, true)
        return makeHorizontalSheet(listOf(inputPreview, bicubicPreview, tilePreview))
    }

    private fun makeTileComparisonSheet(input: Bitmap, bicubic: Bitmap, quickSr: Bitmap, realSr: Bitmap): Bitmap {
        val inputPreview = Bitmap.createScaledBitmap(input, 512, 512, true)
        val bicubicPreview = Bitmap.createScaledBitmap(bicubic, 512, 512, true)
        val quickPreview = Bitmap.createScaledBitmap(quickSr, 512, 512, true)
        val realPreview = Bitmap.createScaledBitmap(realSr, 512, 512, true)
        return makeHorizontalSheet(listOf(inputPreview, bicubicPreview, quickPreview, realPreview))
    }

    private fun percentileLong(values: List<Long>, q: Double): Long {
        if (values.isEmpty()) return 0L
        val sorted = values.sorted()
        val index = ((sorted.size - 1) * q).toInt().coerceIn(0, sorted.lastIndex)
        return sorted[index]
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
                        .setResolutionStrategy(
                            ResolutionStrategy(
                                LIVE_ANALYSIS_TARGET_SIZE,
                                ResolutionStrategy.FALLBACK_RULE_CLOSEST_HIGHER_THEN_LOWER,
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
                            if (pendingHighResSample) {
                                pendingHighResSample = false
                                runHighResSrSample(imageProxy)
                            } else if (pendingProbeMode == "yuv_roi") {
                                pendingProbeMode = ""
                                Log.d("RB5_SR", "pending probe consumed: yuv_roi")
                                runYuvRoiProbe(imageProxy)
                            } else if (pendingProbeMode == "tensor_ready") {
                                pendingProbeMode = ""
                                Log.d("RB5_SR", "pending probe consumed: tensor_ready")
                                runTensorReadyProbe(imageProxy)
                            } else if (pendingRealCameraCapture) {
                                pendingRealCameraCapture = false
                                runRealCameraCapture(imageProxy)
                            } else if (pendingTileStillCapture) {
                                pendingTileStillCapture = false
                                Log.d("RB5_TILE", "pending tile still consumed model=${tileModelVariant.label}")
                                runTileStillCapture(imageProxy)
                            } else if (pendingTileCompareCapture) {
                                pendingTileCompareCapture = false
                                Log.d("RB5_TILE", "pending tile compare consumed")
                                runTileCompareCapture(imageProxy)
                            } else if (liveSrTensorReady) {
                                runTensorReadyLiveSr(imageProxy)
                            } else if (liveSr) {
                                runLiveSr(imageProxy)
                            } else if (!offlineEvalActive && (frameCount == 1 || frameCount % 30 == 0)) {
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
                                if (!demoMode) {
                                    runOnUiThread {
                                        statusTextView.text = "$nativeMessage\n\n$frameStatus"
                                    }
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
                when (pendingProbeMode) {
                    "yuv_roi", "tensor_ready" -> Log.d("RB5_SR", "pending probe armed: $pendingProbeMode")
                    "tensor_live" -> {
                        pendingProbeMode = ""
                        previewView.postDelayed({ startTensorReadyLiveSrFromIntent() }, 500)
                        Log.d("RB5_SR_TENSOR", "pending tensor-ready live armed")
                    }
                }
                if (pendingAutoLiveSr) {
                    pendingAutoLiveSr = false
                    previewView.postDelayed({ startLiveSrFromIntent() }, 500)
                }
                if (pendingAutoTileStill) {
                    pendingAutoTileStill = false
                    previewView.postDelayed({
                        pendingTileStillCapture = true
                        statusTextView.text = "Tile still auto capture armed (${tileModelVariant.label}/QNN)."
                        Log.d("RB5_TILE", "auto tile still armed model=${tileModelVariant.label}")
                    }, 500)
                }
                if (pendingAutoTileCompare) {
                    pendingAutoTileCompare = false
                    previewView.postDelayed({
                        pendingTileCompareCapture = true
                        statusTextView.text = "Tile compare auto capture armed (QuickSR vs Real-ESRGAN/QNN)."
                        Log.d("RB5_TILE", "auto tile compare armed")
                    }, 500)
                }
            } catch (exc: Exception) {
                Log.e(CAMERA_TAG, "CameraX bind failed", exc)
            }
        }, ContextCompat.getMainExecutor(this))
    }

    override fun onDestroy() {
        super.onDestroy()
        liveSr = false
        liveSrTensorReady = false
        offlineEvalActive = false
        liveOutputBitmap = null
        tensorLiveOutputBitmap = null
        // Close the interpreter on the same single-thread executor so it cannot run
        // concurrently with an in-flight enhance() (closing during run() can crash).
        // Submitting before shutdown() queues it after any pending SR task (FIFO).
        cameraExecutor.execute { resolver?.close() }
        cameraExecutor.execute { highResResolver?.close() }
        srExecutor.execute { offlineResolver?.close() }
        cameraExecutor.shutdown()
        srExecutor.shutdown()
    }
}
