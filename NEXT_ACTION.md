# Next Action

## Current Conclusion

The QNN Delegate app path is ready to be treated as a milestone:

```text
W8A8 TFLite -> QNN TFLite Delegate -> HTP -> fixed sample and CameraX live ROI
```

The current RB5 app evidence shows fixed sample success and repeated live ROI timing. QuickSRNetSmall has completed host-side full 24-case comparison, Android fixed-sample validation, Android live ROI validation, and a short app resource-cost probe through QNN Delegate.

## Highest Priority

Next priority:

```text
Proceed to P9/P10 only after the user provides or captures the minimal
real-camera showcase set described in REAL_CAMERA_CAPTURE_PLAN.md.

Do not use benchmark or fixed-sample images as a substitute for real-camera
evidence. If no real-camera set exists, pause product/showcase claims there and
continue only with explicitly scoped exploration lanes.
```

## Current Checkpoint

The current stable checkpoint has been committed and pushed through:

```text
e30141c docs(loop): scope negative evidence gates
```

The worktree was clean after the push. GitHub warned that
`libQnnHtpPrepare.so` is about 83.67MB, above the recommended 50MB limit but
below the hard 100MB limit. If repository size becomes a problem, evaluate Git
LFS or a runtime SDK dependency strategy.

## Verified Evidence

QNN Delegate app evidence:

```text
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260718_app_qnn_delegate_fixed_live_rb5
```

Key numbers:

```text
fixed sample final smoke: pre=8ms, inf=4ms, post=47ms, total=59ms
live ROI repeated app e2e: 133 frames, inf p50/p95=3/3ms, e2e p50/p95=63/66ms
```

Live ROI bottleneck breakdown:

```text
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260718_app_qnn_delegate_live_roi_breakdown
```

Key finding:

```text
ImageProxy.toBitmap full 4000x3000 conversion p50/p95=41/43ms.
QNN inference p50/p95=3/3ms.
```

QuickSRNetSmall comparison:

```text
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260718_145028_quicksrnet_small_vs_realesrgan_w8a8_full_host
```

Key numbers:

```text
QuickSRNetSmall W8A8: 43,672 bytes, host p50 avg 8.512ms.
Real-ESRGAN W8A8: 1,308,432 bytes, host p50 avg 344.932ms.
QuickSRNetSmall average PSNR delta vs Real-ESRGAN: +2.31dB.
```

QuickSRNetSmall app fixed-sample validation:

```text
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260718_app_quicksrnet_fixed_validation
```

Key numbers:

```text
QuickSRNet app fixed sample: pre=7ms, inf=3ms, post=39ms, total=49ms.
App-vs-host same input: PSNR=46.92dB, MAD=0.939.
```

Three-case app strategy validation:

```text
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260718_app_strategy_three_case_fixed_compare
```

Key numbers:

```text
low_light_div2k0852: QuickSR +1.62dB PSNR vs RealESRGAN.
people_scene_div2k0832: QuickSR +3.60dB PSNR vs RealESRGAN.
text_signage_urban076: QuickSR +1.09dB PSNR vs RealESRGAN.
```

QuickSRNetSmall live ROI validation:

```text
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260718_app_quicksrnet_live_roi_1280x960
```

Key numbers:

```text
parsed frames: 166
QuickSRNet QNN inference p50/p95: 2/2ms
app e2e p50/p95: 22/25ms
analyzer wall p50/p95: 25/29ms
```

QNN app resource probe:

```text
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260718_app_qnn_resource_probe
```

Key numbers:

```text
Real-ESRGAN W8A8 QNN init: 781ms first init, 679ms later init
QuickSRNetSmall QNN init: 38ms when added after Real-ESRGAN, 293ms after switching
QuickSRNet steady fixed-sample total: p50/p95 15/16.8ms
Real-ESRGAN -> QuickSRNet switch total: 369ms
single Real-ESRGAN load PSS delta: about +98,991KB
add QuickSRNet while Real-ESRGAN resident: about +1,600KB in this short probe
```

External alignment prompts:

```text
C:\Users\Admin\Desktop\QC-Development-Board-Project\docs\prompts\rb5_internal_ai_route_review_prompt.md
C:\Users\Admin\Desktop\QC-Development-Board-Project\docs\prompts\rb5_qualcomm_ai_qnn_dual_model_prompt.md
```

Route and metric decisions:

```text
C:\Users\Admin\Desktop\QC-Development-Board-Project\ROUTE_DECISION.md
C:\Users\Admin\Desktop\QC-Development-Board-Project\EVAL_METRIC_POLICY.md
C:\Users\Admin\Desktop\QC-Development-Board-Project\ROADMAP_NEXT.md
C:\Users\Admin\Desktop\QC-Development-Board-Project\COMMIT_PLAN.md
```

## Verification Already Run

```bat
RB5_SR_lab\.venv-eval\Scripts\python.exe RB5_SR_lab\test_loop_policy.py

cd /d C:\Users\Admin\Desktop\QC-Development-Board-Project\RB5VisionLab
set JAVA_HOME=C:\Program Files\Android\Android Studio\jbr
set ANDROID_HOME=C:\Users\Admin\AppData\Local\Android\Sdk
set ANDROID_SDK_ROOT=C:\Users\Admin\AppData\Local\Android\Sdk
gradlew.bat --no-daemon :app:assembleDebug

adb install -r RB5VisionLab\app\build\outputs\apk\debug\app-debug.apk
adb shell am start -n com.cyf.rb5visionlab/.MainActivity --ez run_qnn_fixed true
adb shell am start -n com.cyf.rb5visionlab/.MainActivity --ez start_live_sr true --es sr_backend QNN --es sr_model W8A8

RB5_SR_lab\.venv-eval\Scripts\python.exe RB5_SR_lab\eval_quicksrnet_compare.py --input-set smoke --runs 5 --warmup 1
RB5_SR_lab\.venv-eval\Scripts\python.exe RB5_SR_lab\eval_quicksrnet_compare.py --input-set full --runs 5 --warmup 1

adb shell am start -n com.cyf.rb5visionlab/.MainActivity --ez run_qnn_fixed true --es sr_model QUICKSR_W8A8
adb shell am start -n com.cyf.rb5visionlab/.MainActivity --ez run_qnn_fixed true --es sr_model QUICKSR_W8A8 --es sr_asset case_low_light_div2k0852.png

python RB5_SR_lab\run_app_live_roi_benchmark.py --model QUICKSR_W8A8 --min-frames 120 --timeout-s 120 --run-id 20260718_app_quicksrnet_live_roi_1280x960
python RB5_SR_lab\run_app_resource_probe.py --run-id 20260718_app_qnn_resource_probe --steady-runs 5 --timeout-s 90
```

## Commit Scope Guidance

Likely QNN Delegate milestone paths:

```text
.gitignore
PROJECT_ENTRYPOINTS.md
RB5VisionLab/app/build.gradle.kts
RB5VisionLab/app/libs/qtld-release.aar
RB5VisionLab/app/src/main/AndroidManifest.xml
RB5VisionLab/app/src/main/cpp/rb5visionlab.cpp
RB5VisionLab/app/src/main/java/com/cyf/rb5visionlab/MainActivity.kt
RB5VisionLab/app/src/main/java/com/cyf/rb5visionlab/SuperResolver.kt
RB5VisionLab/app/src/main/res/layout/activity_main.xml
RB5VisionLab/app/src/main/assets/quicksrnetsmall_w8a8.tflite
RB5VisionLab/app/src/main/assets/case_low_light_div2k0852.png
RB5VisionLab/app/src/main/assets/case_people_scene_div2k0832.png
RB5VisionLab/app/src/main/assets/case_text_signage_urban076.png
RB5VisionLab/app/src/main/jniLibs/arm64-v8a/libQnnHtp.so
RB5VisionLab/app/src/main/jniLibs/arm64-v8a/libQnnHtpPrepare.so
RB5VisionLab/app/src/main/jniLibs/arm64-v8a/libQnnHtpV73Skel.so
RB5VisionLab/app/src/main/jniLibs/arm64-v8a/libQnnHtpV73Stub.so
RB5VisionLab/app/src/main/jniLibs/arm64-v8a/libQnnSystem.so
RB5_SR_lab/loop_policy.py
RB5_SR_lab/test_loop_policy.py
RB5_SR_lab/run_qnn_smoke_benchmark.py
RB5_SR_lab/eval_benchmark_v1.py
RB5_SR_lab/eval_quicksrnet_compare.py
RB5_SR_lab/run_app_live_roi_benchmark.py
RB5_SR_lab/run_app_resource_probe.py
eval_hub/
knowledge_base/
```

Do not blindly stage:

```text
RB5VisionLab/app/build/
RB5VisionLab/app/.cxx/
RB5VisionLab/app/libs/qtld_tmp/
RB5VisionLab/app/src/main/jniLibs/**/libqnn_net_run_exec.so
RB5VisionLab/app/src/main/jniLibs/**/libqnn_profile_viewer_exec.so
RB5_SR_lab/results/
RB5_SR_lab/export_assets/
evalhub_data/
project_assets/
APK files
raw/log/generated image artifacts
RB5_SR_lab/qnn_local_run/app_quicksr_fixed_*.png
RB5_SR_lab/qnn_local_run/host_quicksr_fixed_sr_512.png
RB5_SR_lab/qnn_local_run/app_strategy_cases/
```

## Human Review Needed

Open these contact sheets before app integration or final milestone write-up:

```text
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260718_app_qnn_delegate_fixed_live_rb5\fixed_sample_contact_sheet.png
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260718_app_qnn_delegate_fixed_live_rb5\app_vs_qnn_net_run_contact_sheet.png
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260718_145028_quicksrnet_small_vs_realesrgan_w8a8_full_host\contact_sheet.png
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260718_app_strategy_three_case_fixed_compare\contact_sheet.png
```

Decision rule:

```text
QuickSRNetSmall is now integrated into the Android app fixed-sample path and validated in live ROI. Resource probing shows automatic live switching is not free: Real-ESRGAN -> QuickSRNet measured about 369ms. Treat QuickSRNetSmall as the likely live ROI workhorse candidate, not as an automatic routing layer.
```

Harness rule:

```text
`not default yet`, `deferred`, `conditional`, and `no-go for current mainline`
must not be interpreted as `never explore`. Use HARNESS_LOOP_ENGINEERING.md to
classify scope: claim_gate, mainline_gate, implementation_gate, or true
dead_end. Only a true dead_end stops a route.
```

## What Not To Reopen As If Unfinished

```text
QNN Delegate app path
QuickSRNet app/live validation
P5 postprocess/sample-copy optimization
5-minute short sustained runs
route/metric/AIMET/YUV decision docs
commit split and push of the current checkpoint
```

## Next Engineering Choices

Recommended order:

```text
1. Capture the minimal real-camera set from REAL_CAMERA_CAPTURE_PLAN.md.
2. Review that set with pass / conditional / fail labels.
3. Decide whether app default live SR should remain explicit or switch to QuickSRNetSmall.
4. If more latency work is needed, run a bounded YUV ROI Kotlin probe from NATIVE_YUV_ROI_PLAN.md.
5. Add LPIPS/DISTS or AIMET only when their trigger conditions are met.
```
