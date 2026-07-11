package com.cyf.rb5visionlab

import android.content.Context
import android.graphics.Bitmap
import android.graphics.Color
import org.tensorflow.lite.Interpreter
import org.tensorflow.lite.gpu.GpuDelegate
import java.nio.ByteBuffer
import java.nio.ByteOrder

/** TFLite backend used for one SR experiment run (D7). */
enum class SrBackend(val label: String) {
    CPU("CPU"),
    NNAPI("NNAPI"),
    GPU("GPU"),
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
    modelAsset: String = "real_esrgan_general_x4v3.tflite",
    val backend: SrBackend = SrBackend.CPU,
    private val inputSize: Int = 128,
    private val outputSize: Int = inputSize * 4,
    private val inputLayout: SrInputLayout = SrInputLayout.NHWC,
) {
    private val interpreter: Interpreter
    private var gpuDelegate: GpuDelegate? = null

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
            }
        }
        interpreter = Interpreter(modelBuffer, options)
    }

    /**
     * Enhance a low-res bitmap. Input is forced to inputSize; output is outputSize.
     * @return the enhanced bitmap and per-stage timing (B5).
     */
    fun enhance(input: Bitmap): Pair<Bitmap, SrTiming> {
        val src = if (input.width != inputSize || input.height != inputSize) {
            Bitmap.createScaledBitmap(input, inputSize, inputSize, true)
        } else {
            input
        }

        // --- preprocess: ARGB pixels -> float RGB /255 in the model's input layout ---
        val tPre0 = System.nanoTime()
        val inputBuffer = ByteBuffer
            .allocateDirect(inputSize * inputSize * 3 * FLOAT_BYTES)
            .order(ByteOrder.nativeOrder())
        val pixels = IntArray(inputSize * inputSize)
        src.getPixels(pixels, 0, inputSize, 0, 0, inputSize, inputSize)
        when (inputLayout) {
            SrInputLayout.NHWC -> {
                for (y in 0 until inputSize) {
                    for (x in 0 until inputSize) {
                        putRgb(inputBuffer, pixels[y * inputSize + x])
                    }
                }
            }
            SrInputLayout.NHCW -> {
                for (y in 0 until inputSize) {
                    for (c in 0 until 3) {
                        for (x in 0 until inputSize) {
                            putChannel(inputBuffer, pixels[y * inputSize + x], c)
                        }
                    }
                }
            }
            SrInputLayout.NCHW -> {
                for (c in 0 until 3) {
                    for (y in 0 until inputSize) {
                        for (x in 0 until inputSize) {
                            putChannel(inputBuffer, pixels[y * inputSize + x], c)
                        }
                    }
                }
            }
        }
        inputBuffer.rewind()
        val outputBuffer = ByteBuffer
            .allocateDirect(outputSize * outputSize * 3 * FLOAT_BYTES)
            .order(ByteOrder.nativeOrder())
        val tPre1 = System.nanoTime()

        // --- inference ---
        interpreter.run(inputBuffer, outputBuffer)
        val tInf = System.nanoTime()

        // --- postprocess: [1,H,W,3] float [0,1] -> ARGB bitmap ---
        outputBuffer.rewind()
        val outPixels = IntArray(outputSize * outputSize)
        for (y in 0 until outputSize) {
            for (x in 0 until outputSize) {
                val r = (outputBuffer.float.coerceIn(0f, 1f) * 255f).toInt()
                val g = (outputBuffer.float.coerceIn(0f, 1f) * 255f).toInt()
                val b = (outputBuffer.float.coerceIn(0f, 1f) * 255f).toInt()
                outPixels[y * outputSize + x] = Color.rgb(r, g, b)
            }
        }
        val out = Bitmap.createBitmap(outputSize, outputSize, Bitmap.Config.ARGB_8888)
        out.setPixels(outPixels, 0, outputSize, 0, 0, outputSize, outputSize)
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
    }

    companion object {
        private const val FLOAT_BYTES = 4

        private fun putRgb(buffer: ByteBuffer, pixel: Int) {
            buffer.putFloat(Color.red(pixel) / 255.0f)
            buffer.putFloat(Color.green(pixel) / 255.0f)
            buffer.putFloat(Color.blue(pixel) / 255.0f)
        }

        private fun putChannel(buffer: ByteBuffer, pixel: Int, channel: Int) {
            val value = when (channel) {
                0 -> Color.red(pixel)
                1 -> Color.green(pixel)
                else -> Color.blue(pixel)
            }
            buffer.putFloat(value / 255.0f)
        }
    }
}
