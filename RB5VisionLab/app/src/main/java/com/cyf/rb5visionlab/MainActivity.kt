package com.cyf.rb5visionlab

import android.Manifest
import android.content.ContentValues
import android.content.pm.PackageManager
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
    @Volatile private var srBackend = SrBackend.CPU
    @Volatile private var srModelVariant = SrModelVariant.FLOAT
    @Volatile private var liveSr = false
    @Volatile private var offlineEvalActive = false
    private lateinit var srResultView: ImageView
    private val srSampleLock = Any()
    private var latestSrSample: SrSample? = null
    private var highResResolver: SuperResolver? = null
    @Volatile private var pendingHighResSample = false
    @Volatile private var pendingAutoLiveSr = false

    private data class OfflineEvalAsset(
        val label: String,
        val assetName: String,
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
    external fun processYPlane(yData: ByteArray, width: Int, height: Int, rowStride: Int): String

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

        cameraExecutor = Executors.newSingleThreadExecutor()
        srExecutor = Executors.newSingleThreadExecutor()
        applyIntentSrOverrides()
        setupSuperResolution()
        val autoRunQnnFixed = intent.getBooleanExtra("run_qnn_fixed", false)
        val autoStartLiveSr = intent.getBooleanExtra("start_live_sr", false)
        val autoRunResourceProbe = intent.getBooleanExtra("run_resource_probe", false)
        Log.d("RB5_QNN", "onCreate run_qnn_fixed=$autoRunQnnFixed run_resource_probe=$autoRunResourceProbe extras=${intent.extras?.keySet()?.joinToString()}")
        if (autoRunResourceProbe) {
            srExecutor.execute {
                Thread.sleep(500)
                runResourceProbeOnWorker()
            }
        } else if (autoRunQnnFixed) {
            srExecutor.execute {
                Thread.sleep(500)
                runOnUiThread { runQnnFixedSample() }
            }
        } else if (autoStartLiveSr) {
            pendingAutoLiveSr = true
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

    private fun setupSuperResolution() {
        val srButton = findViewById<Button>(R.id.sr_button)
        val saveSampleButton = findViewById<Button>(R.id.save_sample_button)
        val offlineEvalButton = findViewById<Button>(R.id.offline_eval_button)
        val qnnFixedButton = findViewById<Button>(R.id.qnn_fixed_button)
        srResultView = findViewById(R.id.sr_result)
        val previewView = findViewById<PreviewView>(R.id.previewView)
        srButton.text = startButtonText()
        offlineEvalButton.text = offlineButtonText()
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
                offlineEvalActive = false
                previewView.visibility = View.GONE
                srResultView.visibility = View.VISIBLE
                srButton.text = "停止实时超分"
                statusTextView.text = "Live ROI SR starting with ${srBackend.label} backend..."
            } else {
                offlineEvalActive = false
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
        Log.d("RB5_SR", "intent SR overrides backend=${srBackend.label} model=${srModelVariant.label}")
    }

    private inline fun <reified T : Enum<T>> parseEnum(value: String): T? {
        val normalized = value.trim().uppercase(Locale.US)
        return enumValues<T>().firstOrNull {
            it.name.uppercase(Locale.US) == normalized
        }
    }

    private fun startLiveSrFromIntent() {
        liveSr = true
        offlineEvalActive = false
        findViewById<PreviewView>(R.id.previewView).visibility = View.GONE
        srResultView.visibility = View.VISIBLE
        findViewById<Button>(R.id.sr_button).text = "停止实时超分"
        statusTextView.text = "Live ROI SR starting with ${srBackend.label}/${srModelVariant.label} from intent..."
        Log.d("RB5_SR", "auto live SR from intent backend=${srBackend.label} model=${srModelVariant.label}")
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
            val (croppedRoi, cropSide) = cropCenterRoiKeepingLegacyFov(full, side)
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
            val (out, t) = resolver!!.enhance(roi)
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
            Log.d(
                srTag,
                "backend=${srBackend.label} live ROI crop=${cropSide}->128->512 frame=${full.width}x${full.height} cap=$captureMs frameBitmap=$frameBitmapMs roi=$roiCropScaleMs rotate=$rotateMs pre=${t.preprocessMs} inf=${t.inferenceMs} post=${t.postprocessMs} enhanceWall=$enhanceWallMs sampleCopy=$sampleCopyMs analyzer=$analyzerWallMs e2e=${e2eMs}ms"
            )
            runOnUiThread {
                srResultView.setImageBitmap(out)
                statusTextView.text =
                    "Live ROI SR (TFLite ${srBackend.label}/${srModelVariant.label})\n" +
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
                if (pendingAutoLiveSr) {
                    pendingAutoLiveSr = false
                    previewView.postDelayed({ startLiveSrFromIntent() }, 500)
                }
            } catch (exc: Exception) {
                Log.e(CAMERA_TAG, "CameraX bind failed", exc)
            }
        }, ContextCompat.getMainExecutor(this))
    }

    override fun onDestroy() {
        super.onDestroy()
        liveSr = false
        offlineEvalActive = false
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
