# QC Development Board Project

Android / Qualcomm RB5 Gen2 edge-AI image enhancement project.

## Current Project

**RB5 Gen2 / QCS8550 on-device super-resolution pipeline with QNN deployment.**

The current milestone is an Android CameraX live ROI enhancement path:

```text
CameraX ImageAnalysis
-> center ROI crop
-> QuickSRNetSmall W8A8 TFLite
-> QNN TFLite Delegate / HTP
-> display
```

Real-ESRGAN W8A8 remains in the app as the QNN/HTP deployment milestone,
perceptual comparison path, and optional post-capture/offline enhancement route.
Automatic dual-model live routing is intentionally not the default.

## Key Results

| Result | Evidence |
| --- | --- |
| QNN/HTP app path works | `20260718_app_qnn_delegate_fixed_live_rb5` |
| Full-frame Bitmap conversion was the live bottleneck | `ImageProxy.toBitmap()` p50/p95 was about `41/43ms` before the 1280x960 live analysis fix |
| Default live ROI route | `QNN + QuickSRNetSmall W8A8` |
| Default live ROI after output reuse | `19.0 / 24.7ms` e2e p50/p95 |
| Latest live ROI after UINT8 output bulk-copy | `15 / 19ms` e2e p50/p95 in 120-frame app e2e smoke |
| Latest app e2e schema output | `20260720_app_e2e_schema_output_reuse_120f/app_e2e_log.csv` |
| 120s default live run | 3551 frames, e2e first/last 20% p50/p95 `20.0/25.0ms -> 21.0/26.0ms` |
| 60s latest live run | 1763 frames, e2e first/last 20% p50/p95 `15.0/20.0ms -> 16.0/21.0ms` |
| Every-N temporal smoke | `everyN=3`, effective enhanced FPS `9.9`, enhanced-frame e2e `22 / 25ms` |
| Demo Mode wide-clear live ROI video | `20260720_demo_mode_wide_clear_20s`, 20s MP4, wide preview display with QNN/SR timing, e2e p50/p95 `23 / 28ms` |
| Demo Mode relation evidence | `20260720_demo_relation_smoke/demo_relation`, shows wide preview, model input 128, and QNN SR output 512 |
| App fixed-sample replay | `20260720_app_fixed_replay_quicksr_3assets`, 3 fixed assets through Android QNN path, p50 total about `17-18ms` |
| Shared-memory feasibility | Phase 2 normal-vs-shared tensor compare passed; checksum matched and shared invoke avg was `1.056ms` vs normal `1.104ms`, but this is still not CameraX true zero-copy |
| Real-camera showcase | 8 scenes / 32 standard images, `accepted_with_caveats` |
| Tensor-ready live experiment | valid, but not promoted: p50 e2e `20.0ms` vs Bitmap default `19.0ms` |

Large generated evidence lives outside Git under:

```text
C:\Users\Admin\Videos\RB5 gen2\
```

Raw benchmark images, generated outputs, APKs, and build products are not
tracked by default.

## Repository Layout

- `RB5VisionLab/`: Android app for CameraX, TFLite, QNN Delegate, live ROI SR,
  fixed samples, real-camera capture, and probe modes.
- `RB5_SR_lab/`: host-side evaluation, benchmark, log parsing, and evidence
  collection scripts.
- `eval_hub/`: evaluation registry, lifecycle layers, and metric-role policy.
- `knowledge_base/`: external research cards and reference index.
- `SHOWCASE_MATERIALS.md`: current minimum evidence package.
- `SHOWCASE_INDEX.md`: one-page navigation for presentation materials.
- `SHOWCASE_NARRATIVE.md`: interview-ready project story.
- `FINAL_INTERVIEW_PACKAGE.md`: compact pre-interview review sheet.
- `INTERVIEW_ORAL_SCRIPT.md`: spoken 30-second / 2-minute / deep-dive answers.
- `RESUME_PROJECT_DRAFT.md`: Chinese and English resume bullets.
- `NEXT_ACTION.md`: current handoff.

## Useful Commands

Build the Android app on Windows:

```bat
cd /d C:\Users\Admin\Desktop\QC-Development-Board-Project\RB5VisionLab
set "JAVA_HOME=C:\Program Files\Android\Android Studio\jbr"
set "ANDROID_HOME=C:\Users\Admin\AppData\Local\Android\Sdk"
set "ANDROID_SDK_ROOT=C:\Users\Admin\AppData\Local\Android\Sdk"
gradlew.bat --no-daemon :app:assembleDebug
```

Install and start default live ROI:

```bat
adb install -r app\build\outputs\apk\debug\app-debug.apk
adb shell am start -n com.cyf.rb5visionlab/.MainActivity --ez start_live_sr true
```

Collect default live ROI timing:

```bat
cd /d C:\Users\Admin\Desktop\QC-Development-Board-Project
RB5_SR_lab\.venv-eval\Scripts\python.exe RB5_SR_lab\run_app_live_roi_benchmark.py --use-app-default --min-frames 120 --timeout-s 90
```

## Boundaries

Do not claim:

```text
true zero-copy
full power/perf-watt characterization
automatic dual-model routing product readiness
QuickSRNet globally better than Real-ESRGAN
the screenrecord demo as a true VideoCapture/Recorder SR pipeline
```

The supported claim is narrower and stronger:

```text
The project deploys SR models through QNN/HTP, profiles the real Android app
path, identifies data movement and output processing as dominant costs, and
makes a route decision from latency, quality, memory, and visual-review evidence.
```

See `push_readme.txt` for commit and push conventions.
