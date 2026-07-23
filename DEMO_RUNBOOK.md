# RB5 Gen2 Demo Runbook

Updated: 2026-07-23

## Goal

Run the current default RB5 live ROI SR demo and collect a small, reproducible
timing record.

Current default:

```text
QNN backend + QuickSRNetSmall W8A8 + direct-YUV native tensor input path
```

Real-ESRGAN remains available for comparison through explicit UI / intent
selection.

## Preconditions

```bat
adb devices
```

Expected:

```text
ff5d3ab4    device
```

Use Android Studio JBR on Windows:

```bat
set "JAVA_HOME=C:\Program Files\Android\Android Studio\jbr"
set "ANDROID_HOME=C:\Users\Admin\AppData\Local\Android\Sdk"
set "ANDROID_SDK_ROOT=C:\Users\Admin\AppData\Local\Android\Sdk"
```

## Build And Install

```bat
cd /d C:\Users\Admin\Desktop\QC-Development-Board-Project\RB5VisionLab
gradlew.bat --no-daemon :app:assembleDebug
adb install -r app\build\outputs\apk\debug\app-debug.apk
```

## Start Default Live ROI

```bat
adb shell am force-stop com.cyf.rb5visionlab
adb shell am start -n com.cyf.rb5visionlab/.MainActivity --ez start_live_sr true
```

Expected log signal:

```text
RB5_SR: auto live SR from intent backend=QNN model=QUICKSR_W8A8
RB5_SR_TENSOR: ... model=QUICKSR_W8A8 ... tensorPath=directYuv optimizedTensor=true
```

## Collect Default Live Timing

```bat
cd /d C:\Users\Admin\Desktop\QC-Development-Board-Project
RB5_SR_lab\.venv-eval\Scripts\python.exe RB5_SR_lab\run_app_live_roi_benchmark.py --use-app-default --min-frames 120 --timeout-s 90
```

Reference result:

```text
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260722_app_default_direct_yuv_live_roi_120f
```

Current reference numbers:

```text
app e2e p50/p95: 10.0 / 12.0 ms
analyzer p50/p95: 10.0 / 13.0 ms
QNN inference p50/p95: 2.0 / 2.0 ms
postprocess p50/p95: 2.0 / 2.0 ms
```

Reference result:

```text
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260722_direct_yuv_live_roi_120s_sustained
```

## Short Sustained Check

Run only when you need sustained-use evidence:

```bat
cd /d C:\Users\Admin\Desktop\QC-Development-Board-Project
RB5_SR_lab\.venv-eval\Scripts\python.exe RB5_SR_lab\run_app_sustained_live_roi.py --model QUICKSR_W8A8 --duration-s 120 --thermal-interval-s 30 --run-id 20251110_output_reuse_quicksr_live_roi_120s
```

Reference result:

```text
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20251110_output_reuse_quicksr_live_roi_120s
```

Reference numbers:

```text
parsed frames: 3551
e2e first/last 20% p50/p95: 20.0 / 25.0 ms -> 21.0 / 26.0 ms
battery temperature: 24.0C -> 24.0C
```

## Real-Camera Showcase

The current minimum real-camera set is already captured and accepted with
caveats:

```text
C:\Users\Admin\Videos\RB5 gen2\real_camera_showcase\20251110_045328_minimal_real_camera_set
```

Use:

```text
contact_sheet.png
ROUTE_REVIEW.md
review_template.csv
```

Do not collect more real-camera images unless a new claim specifically needs
targeted low-light or text evidence.

## Demo Mode Video Capture

Use this when you need a short interview/demo video. This is a screenrecorded
live ROI UI demo, not a true CameraX VideoCapture/Recorder SR pipeline.

Start Demo Mode:

```bat
adb shell am force-stop com.cyf.rb5visionlab
adb shell am start -n com.cyf.rb5visionlab/.MainActivity --ez demo_mode true --ez start_live_sr_direct_yuv true
```

Record a 20-second MP4:

```bat
adb shell screenrecord --time-limit 20 /sdcard/Movies/rb5_demo_mode_direct_yuv_20s.mp4
adb pull /sdcard/Movies/rb5_demo_mode_direct_yuv_20s.mp4 "C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\manual_demo_mode_direct_yuv_20s.mp4"
```

Collect matching timing evidence:

```bat
cd /d C:\Users\Admin\Desktop\QC-Development-Board-Project
RB5_SR_lab\.venv-eval\Scripts\python.exe RB5_SR_lab\run_app_live_roi_benchmark.py --use-app-default --min-frames 120 --timeout-s 90 --run-id manual_demo_mode_timing_recheck
```

Reference evidence:

```text
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260720_demo_mode_wide_clear_20s
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260720_demo_relation_aligned_v3\demo_relation
```

What the demo proves:

```text
QNN/QuickSR live ROI is running.
The displayed overlay reports real app timing.
The wide preview makes the video visually inspectable.
The relation sheet explains preview / model input / SR output correspondence.
```

What it does not prove:

```text
true VideoCapture/Recorder SR
temporal SR quality
full-frame SR
external-meter power
```

## Experimental Paths

Tensor-ready input experiment:

```bat
adb shell am start -n com.cyf.rb5visionlab/.MainActivity --ez start_live_sr_tensor_ready true
```

Reference result:

```text
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20251110_tensor_ready_live_roi_1280x960
```

Decision:

```text
superseded_by_optimized_tensor_default
```

Reason:

```text
old tensor-ready e2e p50/p95: 20.0 / 25.7 ms
old native-rotated tensor e2e p50/p95: 14.0 / 20.0 ms
direct-YUV default e2e p50/p95: 10.0 / 12.0 ms
The current default reads CameraX PlaneProxy direct ByteBuffers in native code
and keeps the existing QNN Delegate tensor path. This is not true QNN input
zero-copy.
```

## What Not To Do

- Do not use the old tensor-ready path as the default path.
- Do not enable automatic dual-model routing.
- Do not claim true zero-copy.
- Do not call screenrecord Demo Mode a true VideoCapture/Recorder SR pipeline.
- Do not use raw benchmark outputs as real-camera evidence.
- Do not commit generated images, logs, APKs, or build outputs.
