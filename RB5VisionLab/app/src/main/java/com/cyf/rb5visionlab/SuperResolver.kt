package com.cyf.rb5visionlab

import android.content.Context
import android.graphics.Bitmap
import android.graphics.Color
import com.qualcomm.qti.QnnDelegate
import org.tensorflow.lite.DataType
import org.tensorflow.lite.Interpreter
import org.tensorflow.lite.Delegate
import org.tensorflow.lite.gpu.GpuDelegate
import java.nio.ByteBuffer
import java.nio.ByteOrder

/** TFLite backend used for one SR experiment run (D7). */
enum class SrBackend(val label: String) {
    CPU("CPU"),
    NNAPI("NNAPI"),
    GPU("GPU"),
    QNN("QNN"),
}

/** Model precision variant used for D8 quantization baseline. */
enum class SrModelVariant(val label: String, val assetName: String) {
    FLOAT("FLOAT", "real_esrgan_general_x4v3.tflite"),
    W8A8("W8A8", "real_esrgan_general_x4v3_w8a8.tflite"),
    QUICKSR_W8A8("QUICKSR_W8A8", "quicksrnetsmall_w8a8.tflite"),
}

/** Input tensor memory layout used by the exported TFLite model. */
enum class SrInputLayout {
    NHWC,
    NHCW,
    NCHW,
}

/** Per-stage timing (ms) for one super-resolution call (B5). */
data class SrTiming(
    val preprocessMs: Long,
    val inferenceMs: Long,
    val postprocessMs: Long,
) {
    val totalMs: Long get() = preprocessMs + inferenceMs + postprocessMs
}

/**
 * B3/D7: runs the float Real-ESRGAN TFLite model (realesr-general-x4v3).
 *
 * Model I/O (must match the exported tflite exactly):
 *   default input  "image"          [1,128,128,3] float32  NHWC, RGB, values in [0,1]
 *   default output "upscaled_image" [1,512,512,3] float32  NHWC, RGB, values in [0,1]
 *
 * Note: TFLite is NHWC (channel-last); the original PyTorch model was NCHW.
 */
class SuperResolver(
    context: Context,
    val modelAsset: String = "real_esrgan_general_x4v3.tflite",
    val backend: SrBackend = SrBackend.CPU,
    private val inputSize: Int = 128,
    private val outputSize: Int = inputSize * 4,
    private val inputLayout: SrInputLayout = SrInputLayout.NHWC,
) {
    private val interpreter: Interpreter
    private var gpuDelegate: GpuDelegate? = null
    private var qnnDelegate: Delegate? = null
    private val inputType: DataType
    private val outputType: DataType
    private val inputScale: Float
    private val inputZeroPoint: Int
    private val outputScale: Float
    private val outputZeroPoint: Int
    private val inputBuffer: ByteBuffer
    private val outputBuffer: ByteBuffer
    private val inputPixels = IntArray(inputSize * inputSize)
    private val outputPixels = IntArray(outputSize * outputSize)
    private val outputUint8Lookup: IntArray?

    init {
        // Read the whole .tflite from assets into a direct ByteBuffer (works whether
        // or not the asset is compressed in the APK).
        val modelBytes = context.assets.open(modelAsset).use { it.readBytes() }
        val modelBuffer = ByteBuffer.allocateDirect(modelBytes.size).order(ByteOrder.nativeOrder())
        modelBuffer.put(modelBytes)
        modelBuffer.rewind()
        val options = Interpreter.Options().apply {
            when (backend) {
                SrBackend.CPU -> numThreads = 4
                SrBackend.NNAPI -> {
                    numThreads = 4
                    setUseNNAPI(true)
                }
                SrBackend.GPU -> {
                    gpuDelegate = GpuDelegate()
                    addDelegate(gpuDelegate)
                }
                SrBackend.QNN -> {
                    val qnnOptions = QnnDelegate.Options().apply {
                        setBackendType(QnnDelegate.Options.BackendType.HTP_BACKEND)
                        setSkelLibraryDir(context.applicationInfo.nativeLibraryDir)
                        setHtpPerformanceMode(QnnDelegate.Options.HtpPerformanceMode.HTP_PERFORMANCE_HIGH_PERFORMANCE)
                        setHtpPdSession(QnnDelegate.Options.HtpPdSession.HTP_PD_SESSION_UNSIGNED)
                        setLogLevel(QnnDelegate.Options.LogLevel.LOG_LEVEL_INFO)
                    }
                    qnnDelegate = QnnDelegate(qnnOptions)
                    addDelegate(qnnDelegate)
                }
            }
        }
        interpreter = Interpreter(modelBuffer, options)
        val inputQuant = interpreter.getInputTensor(0).quantizationParams()
        val outputQuant = interpreter.getOutputTensor(0).quantizationParams()
        inputType = interpreter.getInputTensor(0).dataType()
        outputType = interpreter.getOutputTensor(0).dataType()
        inputScale = inputQuant.scale
        inputZeroPoint = inputQuant.zeroPoint
        outputScale = outputQuant.scale
        outputZeroPoint = outputQuant.zeroPoint
        inputBuffer = ByteBuffer
            .allocateDirect(inputSize * inputSize * 3 * bytesPerElement(inputType))
            .order(ByteOrder.nativeOrder())
        outputBuffer = ByteBuffer
            .allocateDirect(outputSize * outputSize * 3 * bytesPerElement(outputType))
            .order(ByteOrder.nativeOrder())
        outputUint8Lookup = if (outputType == DataType.UINT8) {
            IntArray(256) { raw ->
                (((raw - outputZeroPoint) * outputScale).coerceIn(0f, 1f) * 255f).toInt()
            }
        } else {
            null
        }
    }

    /**
     * Enhance a low-res bitmap. Input is forced to inputSize; output is outputSize.
     * @return the enhanced bitmap and per-stage timing (B5).
     */
    fun enhance(input: Bitmap): Pair<Bitmap, SrTiming> {
        return enhanceInto(input, null)
    }

    fun enhanceInto(input: Bitmap, reusableOutput: Bitmap?): Pair<Bitmap, SrTiming> {
        val src = if (input.width != inputSize || input.height != inputSize) {
            Bitmap.createScaledBitmap(input, inputSize, inputSize, true)
        } else {
            input
        }

        // --- preprocess: ARGB pixels -> RGB tensor in the model's input layout ---
        val tPre0 = System.nanoTime()
        inputBuffer.clear()
        src.getPixels(inputPixels, 0, inputSize, 0, 0, inputSize, inputSize)
        when (inputLayout) {
            SrInputLayout.NHWC -> {
                for (y in 0 until inputSize) {
                    for (x in 0 until inputSize) {
                        putRgb(inputBuffer, inputPixels[y * inputSize + x])
                    }
                }
            }
            SrInputLayout.NHCW -> {
                for (y in 0 until inputSize) {
                    for (c in 0 until 3) {
                        for (x in 0 until inputSize) {
                            putChannel(inputBuffer, inputPixels[y * inputSize + x], c)
                        }
                    }
                }
            }
            SrInputLayout.NCHW -> {
                for (c in 0 until 3) {
                    for (y in 0 until inputSize) {
                        for (x in 0 until inputSize) {
                            putChannel(inputBuffer, inputPixels[y * inputSize + x], c)
                        }
                    }
                }
            }
        }
        inputBuffer.rewind()
        outputBuffer.clear()
        val tPre1 = System.nanoTime()

        // --- inference ---
        interpreter.run(inputBuffer, outputBuffer)
        val tInf = System.nanoTime()

        // --- postprocess: [1,H,W,3] float/uint8 -> ARGB bitmap ---
        outputBuffer.rewind()
        when (outputType) {
            DataType.UINT8 -> fillOutputPixelsFromUint8(outputBuffer)
            DataType.FLOAT32 -> fillOutputPixelsFromFloat(outputBuffer)
            else -> error("Unsupported SR output tensor type: $outputType")
        }
        val out = reusableOutput?.takeIf {
            it.width == outputSize && it.height == outputSize && it.config == Bitmap.Config.ARGB_8888
        } ?: Bitmap.createBitmap(outputSize, outputSize, Bitmap.Config.ARGB_8888)
        out.setPixels(outputPixels, 0, outputSize, 0, 0, outputSize, outputSize)
        val tPost = System.nanoTime()

        val timing = SrTiming(
            preprocessMs = (tPre1 - tPre0) / 1_000_000,
            inferenceMs = (tInf - tPre1) / 1_000_000,
            postprocessMs = (tPost - tInf) / 1_000_000,
        )
        return Pair(out, timing)
    }

    fun enhanceRgbBytes(inputRgb: ByteArray): Pair<Bitmap, SrTiming> {
        return enhanceRgbBytesInto(inputRgb, null)
    }

    fun enhanceRgbBytesInto(inputRgb: ByteArray, reusableOutput: Bitmap?): Pair<Bitmap, SrTiming> {
        require(inputRgb.size == inputSize * inputSize * 3) {
            "Expected ${inputSize * inputSize * 3} RGB bytes, got ${inputRgb.size}"
        }

        val tPre0 = System.nanoTime()
        inputBuffer.clear()
        when (inputLayout) {
            SrInputLayout.NHWC -> {
                for (i in inputRgb.indices) {
                    putUnitByte(inputBuffer, inputRgb[i].toInt() and 0xFF)
                }
            }
            SrInputLayout.NHCW -> {
                for (y in 0 until inputSize) {
                    for (c in 0 until 3) {
                        for (x in 0 until inputSize) {
                            putUnitByte(inputBuffer, inputRgb[(y * inputSize + x) * 3 + c].toInt() and 0xFF)
                        }
                    }
                }
            }
            SrInputLayout.NCHW -> {
                for (c in 0 until 3) {
                    for (y in 0 until inputSize) {
                        for (x in 0 until inputSize) {
                            putUnitByte(inputBuffer, inputRgb[(y * inputSize + x) * 3 + c].toInt() and 0xFF)
                        }
                    }
                }
            }
        }
        inputBuffer.rewind()
        outputBuffer.clear()
        val tPre1 = System.nanoTime()

        interpreter.run(inputBuffer, outputBuffer)
        val tInf = System.nanoTime()

        outputBuffer.rewind()
        when (outputType) {
            DataType.UINT8 -> fillOutputPixelsFromUint8(outputBuffer)
            DataType.FLOAT32 -> fillOutputPixelsFromFloat(outputBuffer)
            else -> error("Unsupported SR output tensor type: $outputType")
        }
        val out = reusableOutput?.takeIf {
            it.width == outputSize && it.height == outputSize && it.config == Bitmap.Config.ARGB_8888
        } ?: Bitmap.createBitmap(outputSize, outputSize, Bitmap.Config.ARGB_8888)
        out.setPixels(outputPixels, 0, outputSize, 0, 0, outputSize, outputSize)
        val tPost = System.nanoTime()

        val timing = SrTiming(
            preprocessMs = (tPre1 - tPre0) / 1_000_000,
            inferenceMs = (tInf - tPre1) / 1_000_000,
            postprocessMs = (tPost - tInf) / 1_000_000,
        )
        return Pair(out, timing)
    }

    fun close() {
        interpreter.close()
        gpuDelegate?.close()
        gpuDelegate = null
        qnnDelegate?.close()
        qnnDelegate = null
    }

    private fun putRgb(buffer: ByteBuffer, pixel: Int) {
        putUnitFloat(buffer, Color.red(pixel) / 255.0f)
        putUnitFloat(buffer, Color.green(pixel) / 255.0f)
        putUnitFloat(buffer, Color.blue(pixel) / 255.0f)
    }

    private fun putChannel(buffer: ByteBuffer, pixel: Int, channel: Int) {
        val value = when (channel) {
            0 -> Color.red(pixel)
            1 -> Color.green(pixel)
            else -> Color.blue(pixel)
        }
        putUnitFloat(buffer, value / 255.0f)
    }

    private fun putUnitFloat(buffer: ByteBuffer, value: Float) {
        when (inputType) {
            DataType.FLOAT32 -> buffer.putFloat(value)
            DataType.UINT8 -> {
                val quantized = ((value / inputScale) + inputZeroPoint).toInt().coerceIn(0, 255)
                buffer.put(quantized.toByte())
            }
            else -> error("Unsupported SR input tensor type: $inputType")
        }
    }

    private fun putUnitByte(buffer: ByteBuffer, value: Int) {
        when (inputType) {
            DataType.FLOAT32 -> buffer.putFloat(value / 255.0f)
            DataType.UINT8 -> {
                val quantized = (((value / 255.0f) / inputScale) + inputZeroPoint).toInt().coerceIn(0, 255)
                buffer.put(quantized.toByte())
            }
            else -> error("Unsupported SR input tensor type: $inputType")
        }
    }

    private fun readUnitFloat(buffer: ByteBuffer, type: DataType): Float = when (type) {
        DataType.FLOAT32 -> buffer.float
        DataType.UINT8 -> ((buffer.get().toInt() and 0xFF) - outputZeroPoint) * outputScale
        else -> error("Unsupported SR output tensor type: $type")
    }

    private fun fillOutputPixelsFromUint8(buffer: ByteBuffer) {
        val lookup = outputUint8Lookup ?: error("Missing UINT8 output lookup table")
        for (i in outputPixels.indices) {
            val r = lookup[buffer.get().toInt() and 0xFF]
            val g = lookup[buffer.get().toInt() and 0xFF]
            val b = lookup[buffer.get().toInt() and 0xFF]
            outputPixels[i] = ARGB_ALPHA or (r shl 16) or (g shl 8) or b
        }
    }

    private fun fillOutputPixelsFromFloat(buffer: ByteBuffer) {
        for (i in outputPixels.indices) {
            val r = (buffer.float.coerceIn(0f, 1f) * 255f).toInt()
            val g = (buffer.float.coerceIn(0f, 1f) * 255f).toInt()
            val b = (buffer.float.coerceIn(0f, 1f) * 255f).toInt()
            outputPixels[i] = ARGB_ALPHA or (r shl 16) or (g shl 8) or b
        }
    }

    companion object {
        private const val FLOAT_BYTES = 4
        private const val ARGB_ALPHA = -0x1000000

        private fun bytesPerElement(type: DataType): Int = when (type) {
            DataType.FLOAT32 -> FLOAT_BYTES
            DataType.UINT8 -> 1
            else -> error("Unsupported SR tensor type: $type")
        }
    }
}
