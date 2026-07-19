# App Default Model Decision

Updated: 2026-07-19

## Decision Scope

Current scope: `mainline_gate`.

The Android app default live SR model is now `QuickSRNetSmall W8A8` on the
`QNN` backend.

Keep the current boundary:

```text
The app still supports explicit model/backend selection through UI or intent extras.
QuickSRNetSmall is the default live ROI workhorse.
Real-ESRGAN remains available as the QNN/HTP milestone and optional perceptual path.
Automatic scene/model routing is still not enabled.
```

## Why

The engineering evidence supports Decision C:

```text
QuickSRNetSmall for live ROI.
Real-ESRGAN for QNN/HTP milestone, comparison baseline, and optional
post-capture/offline perceptual enhancement.
```

The minimum real-camera showcase set is now collected and reviewed:

```text
C:\Users\Admin\Videos\RB5 gen2\real_camera_showcase\20251110_045328_minimal_real_camera_set
```

Review result:

```text
accepted_with_caveats
8/8 scenes complete
32/32 standard images valid
no retake required for the current minimum set
```

## Default Change Record

Change made:

```text
srBackend default: CPU -> QNN
srModelVariant default: FLOAT -> QUICKSR_W8A8
```

Verification:

```text
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20251110_app_default_quicksr_live_roi_smoke
```

Result:

```text
started with --ez start_live_sr true only
resolved frame model: QUICKSR_W8A8
QNN inference p50/p95: 1.0 / 1.0 ms
app e2e p50/p95: 19.0 / 26.3 ms
```

Why this is allowed:

```text
The real-camera blocker is cleared.
The app still exposes Real-ESRGAN through explicit switching/intent controls.
The default change does not introduce automatic dual-model routing.
```

## Current Intent Commands

Keep using explicit intents for automation:

```bat
adb shell am start -n com.cyf.rb5visionlab/.MainActivity --ez start_live_sr true --es sr_backend QNN --es sr_model W8A8
adb shell am start -n com.cyf.rb5visionlab/.MainActivity --ez start_live_sr true --es sr_backend QNN --es sr_model QUICKSR_W8A8
```

## Boundary

Do not implement automatic scene routing as the default path yet. A bounded
routing experiment is still allowed later if it defines a hypothesis, success
metric, budget, rollback, and baseline. Do not hide Real-ESRGAN from the app
because it is still useful for comparison and perceptual enhancement evidence.
