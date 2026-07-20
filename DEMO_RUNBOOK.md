# RB5 Gen2 Demo Runbook

Updated: 2026-07-19

## Goal

Run the current default RB5 live ROI SR demo and collect a small, reproducible
timing record.

Current default:

```text
QNN backend + QuickSRNetSmall W8A8
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
RB5_SR: ... model=QUICKSR_W8A8
```

## Collect Default Live Timing

```bat
cd /d C:\Users\Admin\Desktop\QC-Development-Board-Project
RB5_SR_lab\.venv-eval\Scripts\python.exe RB5_SR_lab\run_app_live_roi_benchmark.py --use-app-default --min-frames 120 --timeout-s 90
```

Reference result:

```text
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260720_app_e2e_schema_output_reuse_120f
```

Current reference numbers:

```text
app e2e p50/p95: 15.0 / 19.0 ms
analyzer p50/p95: 16.0 / 21.0 ms
QNN inference p50/p95: 1.0 / 2.0 ms
postprocess p50/p95: 1.0 / 1.0 ms
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
mainline_not_justified_yet
```

Reason:

```text
tensor-ready e2e p50/p95: 20.0 / 25.7 ms
Bitmap default after output reuse: 19.0 / 24.7 ms
Bitmap default after UINT8 output bulk-copy smoke: 15.0 / 19.0 ms
```

## What Not To Do

- Do not use tensor-ready live as the default path.
- Do not enable automatic dual-model routing.
- Do not claim true zero-copy.
- Do not use raw benchmark outputs as real-camera evidence.
- Do not commit generated images, logs, APKs, or build outputs.
