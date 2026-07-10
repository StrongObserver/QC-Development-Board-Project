package com.cyf.rb5visionlab

import android.content.Context
import android.graphics.Bitmap
import android.graphics.Color
import org.tensorflow.lite.Interpreter
import java.nio.ByteBuffer
import java.nio.ByteOrder

/** Per-stage timing (ms) for one super-resolution call (B5). */
data class SrTiming(
    val preprocessMs: Long,
    val inferenceMs: Long,
    val postprocessMs: Long,
) {
    val totalMs: Long get() = preprocessMs + inferenceMs + postprocessMs
}

/**
 * B3: runs the float Real-ESRGAN TFLite model (realesr-general-x4v3) on CPU.
 *
 * Model I/O (must match the exported tflite exactly):
 *   input  "image"          [1,128,128,3] float32  NHWC, RGB, values in [0,1]
 *   output "upscaled_image" [1,512,512,3] float32  NHWC, RGB, values in [0,1]
 *
 * Note: TFLite is NHWC (channel-last); the original PyTorch model was NCHW.
 */
class SuperResolver(
    context: Context,
    modelAsset: String = "real_esrgan_general_x4v3.tflite",
) {
    private val interpreter: Interpreter

    init {
        // Read the whole .tflite from assets into a direct ByteBuffer (works whether
        // or not the asset is compressed in the APK).
        val modelBytes = context.assets.open(modelAsset).use { it.readBytes() }
        val modelBuffer = ByteBuffer.allocateDirect(modelBytes.size).order(ByteOrder.nativeOrder())
        modelBuffer.put(modelBytes)
        modelBuffer.rewind()
        val options = Interpreter.Options().apply { numThreads = 4 }
        interpreter = Interpreter(modelBuffer, options)
    }

    /**
     * Enhance a low-res bitmap. Input is forced to 128x128; output is 512x512.
     * @return the 512x512 enhanced bitmap and per-stage timing (B5).
     */
    fun enhance(input: Bitmap): Pair<Bitmap, SrTiming> {
        val src = if (input.width != IN_SIZE || input.height != IN_SIZE) {
            Bitmap.createScaledBitmap(input, IN_SIZE, IN_SIZE, true)
        } else {
            input
        }

        // --- preprocess: ARGB pixels -> [1,128,128,3] float RGB /255 ---
        val tPre0 = System.nanoTime()
        val inputArr = Array(1) { Array(IN_SIZE) { Array(IN_SIZE) { FloatArray(3) } } }
        val pixels = IntArray(IN_SIZE * IN_SIZE)
        src.getPixels(pixels, 0, IN_SIZE, 0, 0, IN_SIZE, IN_SIZE)
        for (y in 0 until IN_SIZE) {
            for (x in 0 until IN_SIZE) {
                val p = pixels[y * IN_SIZE + x]
                inputArr[0][y][x][0] = Color.red(p) / 255.0f
                inputArr[0][y][x][1] = Color.green(p) / 255.0f
                inputArr[0][y][x][2] = Color.blue(p) / 255.0f
            }
        }
        val outputArr = Array(1) { Array(OUT_SIZE) { Array(OUT_SIZE) { FloatArray(3) } } }
        val tPre1 = System.nanoTime()

        // --- inference ---
        interpreter.run(inputArr, outputArr)
        val tInf = System.nanoTime()

        // --- postprocess: [1,512,512,3] float [0,1] -> ARGB bitmap ---
        val outPixels = IntArray(OUT_SIZE * OUT_SIZE)
        for (y in 0 until OUT_SIZE) {
            for (x in 0 until OUT_SIZE) {
                val r = (outputArr[0][y][x][0].coerceIn(0f, 1f) * 255f).toInt()
                val g = (outputArr[0][y][x][1].coerceIn(0f, 1f) * 255f).toInt()
                val b = (outputArr[0][y][x][2].coerceIn(0f, 1f) * 255f).toInt()
                outPixels[y * OUT_SIZE + x] = Color.rgb(r, g, b)
            }
        }
        val out = Bitmap.createBitmap(OUT_SIZE, OUT_SIZE, Bitmap.Config.ARGB_8888)
        out.setPixels(outPixels, 0, OUT_SIZE, 0, 0, OUT_SIZE, OUT_SIZE)
        val tPost = System.nanoTime()

        val timing = SrTiming(
            preprocessMs = (tPre1 - tPre0) / 1_000_000,
            inferenceMs = (tInf - tPre1) / 1_000_000,
            postprocessMs = (tPost - tInf) / 1_000_000,
        )
        return Pair(out, timing)
    }

    fun close() = interpreter.close()

    companion object {
        private const val IN_SIZE = 128
        private const val OUT_SIZE = 512
    }
}
