# Model Route Decision

Updated: 2026-07-19

## Decision

Use decision **C** as the current engineering route:

```text
QuickSRNetSmall W8A8 for live ROI.
Real-ESRGAN W8A8 for QNN/HTP deployment milestone, comparison baseline, and
optional post-capture/offline perceptual enhancement.
```

Do not make automatic dual-model live routing the default path yet. This is a
mainline gate, not a permanent rejection of routing experiments.

## Why C, Not D

Automatic routing sounds attractive, but the measured system costs do not make
it free:

```text
Real-ESRGAN -> QuickSRNet switch total: about 369ms
Real-ESRGAN QNN init: about 781ms first init, 679ms later init
QuickSRNet init after switching: about 293ms
QNN/runtime memory remains sticky after close()
```

This means dynamic live switching can create visible cold-path jank and resource
complexity. A single live workhorse plus an optional enhancement path is more
defensible for the current mainline. A future routing experiment is still valid
if it has a clear hypothesis, success metric, budget, rollback, and baseline.

## Why QuickSRNet For Live ROI

QuickSRNetSmall now has enough engineering evidence to be the live ROI
workhorse candidate:

| Evidence | Result |
| --- | --- |
| Android fixed sample through QNN Delegate | pass |
| App-vs-host output alignment | PSNR 46.92dB, MAD 0.939 on same input |
| 1280x960 live ROI | p50/p95 e2e about 22/25ms before P5, 19/24ms after P5, 15/19ms after UINT8 output bulk-copy smoke |
| QNN inference | about 1-2ms in recent live runs |
| 5-minute sustained run | no meaningful e2e drift, coarse battery temp 24.0C -> 24.0C |
| Model size | about 43.7KB |
| Structure-sensitive metrics | better PSNR/SSIM than Real-ESRGAN on three selected cases |
| Real-camera showcase set | accepted with caveats; no retake required |

Real-camera evidence:

```text
C:\Users\Admin\Videos\RB5 gen2\real_camera_showcase\20251110_045328_minimal_real_camera_set
```

Summary:

```text
8/8 scenes complete, 32/32 standard images valid.
QuickSRNet remains safer/conservative for live ROI.
Real-ESRGAN is often sharper on text/edges and remains useful as optional
post-capture or comparison evidence.
```

## Why Keep Real-ESRGAN

Real-ESRGAN remains valuable:

```text
It is the proven QNN/HTP deployment milestone.
It represents the perceptual/GAN-style enhancement branch.
It is the main comparison baseline for model tradeoff analysis.
It may be useful for post-capture or offline enhancement where latency is less strict.
```

Do not describe Real-ESRGAN as obsolete or simply worse. It optimizes a
different perceptual tradeoff.

## Real-Camera Gate

The minimum real-camera showcase gate is now complete and accepted with caveats.
The review is stored in:

```text
C:\Users\Admin\Videos\RB5 gen2\real_camera_showcase\20251110_045328_minimal_real_camera_set\ROUTE_REVIEW.md
```

Promotion rule after this review:

```text
Keep decision C.
Do not claim QuickSRNet is globally better.
Do not claim Real-ESRGAN is obsolete.
Do not enable automatic live dual-model routing as the default.
```

## App Default Boundary

The Android app default live SR path has been changed to:

```text
QNN backend + QuickSRNetSmall W8A8
```

This is a default workhorse change, not automatic scene routing. Real-ESRGAN
must remain explicitly reachable for comparison and optional post-capture /
perceptual enhancement evidence.

## Current Route Summary

```text
Default engineering story: QuickSRNet live ROI + Real-ESRGAN optional/post-capture.
Default app implementation: QNN/QuickSRNetSmall live ROI by default, with explicit UI/intent access to Real-ESRGAN.
Do not add automatic scene routing to the default path yet. Keep bounded
experiments open.
```
