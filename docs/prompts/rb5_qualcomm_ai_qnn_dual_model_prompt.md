# RB5 Gen2 Runtime / Dual-Model QNN Delegate Review Prompt - Qualcomm AI

I am working on an RB5 Gen2 / QCS8550 / Android 13 on-device AI Runtime,
quantization, and heterogeneous performance optimization project. Real-ESRGAN
and QuickSRNet are representative W8A8 workloads used to evaluate QNN/HTP
deployment, data-path cost, memory, initialization, and model-route tradeoffs.

## Current Project Status

1. The Android app uses CameraX ROI input and runs W8A8 TFLite workloads through Qualcomm QNN TFLite Delegate on HTP.
2. The main model is Real-ESRGAN general x4v3 W8A8 TFLite. It is already working in the Android app through QNN Delegate.
3. The key fix for QNN Delegate was packaging `libQnnHtpV73Skel.so` into app `jniLibs` and calling `QnnDelegate.Options.setSkelLibraryDir(nativeLibraryDir)`.
4. Real-ESRGAN W8A8 fixed sample runs successfully:
   - approximately `pre=8ms / inf=4ms / post=47ms / total=59ms`
5. Real-ESRGAN live ROI repeated app e2e is approximately:
   - `e2e p50/p95=63/66ms`
   - `QNN inference p50/p95=3/3ms`
6. A detailed live ROI breakdown shows the dominant bottleneck is not QNN:
   - `ImageProxy.toBitmap()` full 4000x3000 conversion: `p50/p95=41/43ms`
   - ROI crop/scale: about `4ms`
   - QNN inference: about `3ms`
   - output bitmap/postprocess: about `14ms`
7. I added QuickSRNetSmall W8A8 as a candidate model.
8. QuickSRNetSmall W8A8 also runs successfully in the same Android app fixed-sample path through QNN TFLite Delegate:
   - approximately `pre=7ms / inf=3ms / post=39ms / total=49ms`
9. App QuickSRNet output aligns with host LiteRT output on the same input:
   - `PSNR=46.92dB`
   - `MAD=0.939`
   - `max abs diff=6`
10. On host full 24-case benchmark:
    - QuickSRNetSmall W8A8 model size: `43,672 bytes`
    - Real-ESRGAN W8A8 model size: `1,308,432 bytes`
    - QuickSRNetSmall host LiteRT average p50: `8.512ms`
    - Real-ESRGAN W8A8 host LiteRT average p50: `344.932ms`
    - QuickSRNetSmall average PSNR delta vs Real-ESRGAN: `+2.31dB`
11. On three structure-sensitive app fixed-sample cases, QuickSRNetSmall is objectively closer to HR:
    - `low_light_div2k0852`: QuickSRNet `+1.62dB PSNR` over Real-ESRGAN
    - `people_scene_div2k0832`: QuickSRNet `+3.60dB PSNR` over Real-ESRGAN
    - `text_signage_urban076`: QuickSRNet `+1.09dB PSNR` over Real-ESRGAN

## Current Engineering Question

I am deciding whether it is reasonable to keep both models in the same Android app:

- Real-ESRGAN W8A8 as the main perceptual enhancement model.
- QuickSRNetSmall W8A8 as a lightweight conservative model for structure-sensitive cases such as text, face/person, low-light tree branches, and natural textures.

The quality benefit is real, but I am concerned about real product costs:

- model residency memory
- QNN Delegate graph/context memory
- initialization time
- model switching cost
- HTP resource usage
- power and thermal impact
- whether two TFLite/QNN Delegate models should be preloaded or created on demand

## Questions

From the perspective of Qualcomm QNN / HTP runtime and Android deployment, how should I evaluate whether using two TFLite SR models in the same app is reasonable?

Please focus on:

1. QNN TFLite Delegate behavior when two TFLite models are used in one Android app.
2. Whether two `Interpreter + QnnDelegate` instances should be kept alive, or whether the second model should be created on demand.
3. Expected memory overhead:
   - model file
   - tensor buffers
   - QNN graph/context
   - HTP resources
4. Initialization and graph prepare cost when switching models.
5. How to measure:
   - QNN Delegate initialization time
   - HTP graph loading/preparation time
   - per-model memory usage
   - possible CPU fallback
   - HTP/NPU execution time
6. Whether QNN Delegate provides practical profiling hooks or recommended logs for this use case.
7. Whether keeping both models in one APK has any issue with:
   - `libQnnHtpV73Skel.so`
   - `nativeLibraryDir`
   - unsigned PD session
   - HTP backend resource management
8. Best practice for deciding between:
   - single main model only
   - two models but one active at a time
   - both models preloaded
   - dynamic model switching based on scene type
9. For an RB5/QCS8550 Android demo project, what is the most practical engineering recommendation?

## Desired Answer Format

Please answer in this structure:

- Overall recommendation
- What data I must measure before choosing a dual-model strategy
- How to measure memory / initialization / switching / profiling
- Risks or pitfalls specific to QNN TFLite Delegate on QCS8550
- Recommended deployment pattern for this project
- What not to do
