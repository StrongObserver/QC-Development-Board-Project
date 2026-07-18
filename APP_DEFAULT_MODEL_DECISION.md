# App Default Model Decision

Updated: 2026-07-18

## Decision Scope

Current scope: `mainline_gate`.

Do not change the Android app default live SR model in this loop. This is not a
reason to stop model exploration; it only protects the user-facing default until
real-camera evidence exists.

Keep the current behavior:

```text
The app supports explicit model/backend selection through UI or intent extras.
QuickSRNetSmall is the current engineering route for live ROI.
Real-ESRGAN remains available as the QNN/HTP milestone and optional perceptual path.
```

## Why

The engineering evidence supports Decision C:

```text
QuickSRNetSmall for live ROI.
Real-ESRGAN for QNN/HTP milestone, comparison baseline, and optional
post-capture/offline perceptual enhancement.
```

But changing the app's user-facing default should wait until the real-camera
showcase set is collected and reviewed.

Current blocker:

```text
P9/P10 need new real-camera scenes captured according to REAL_CAMERA_CAPTURE_PLAN.md.
Existing benchmark/fixed-sample images cannot replace that physical evidence.
```

## Trigger To Change Default Later

Change the default live model to QuickSRNetSmall only if:

```text
1. VISUAL_REVIEW_QUEUE.md remains pass/conditional with no fail.
2. The real-camera minimal set supports QuickSRNetSmall as live ROI default.
3. The change is made in a small standalone patch.
4. The app still exposes Real-ESRGAN explicitly for comparison/post-capture use.
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
