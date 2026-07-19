# RB5 Gen2 Showcase Narrative

Updated: 2026-07-19

## One-Line Positioning

```text
An Android/QCS8550 edge-AI image-enhancement pipeline that deploys SR models
through QNN TFLite Delegate on HTP, profiles the real app path, and makes model
and pipeline decisions from latency, quality, memory, and product risk.
```

## Core Story

This project is not just "running a super-resolution model".

The engineering story is:

```text
1. Built the Android CameraX -> TFLite SR -> display pipeline.
2. Compared CPU / NNAPI / GPU / QNN paths and moved the main deployment path to QNN/HTP.
3. Verified the stable Android app path as:
   W8A8 TFLite -> QNN TFLite Delegate -> HTP -> fixed sample and live ROI.
4. Profiled the actual app path and found inference was not the live bottleneck.
5. Reduced the dominant CameraX/ImageAnalysis conversion cost by changing live analysis from 4000x3000 to 1280x960.
6. Compared Real-ESRGAN and QuickSRNetSmall as different quality/latency tradeoffs instead of ranking them by PSNR alone.
7. Measured init, memory, and switch cost before rejecting automatic live dual-model routing as the default path.
8. Collected a minimal real-camera showcase set and used visual review to keep the route decision caveated.
9. Tested native/tensor-ready ROI variants and kept the Bitmap default because repeated live p50 did not improve.
```

## Evidence Chain

| Claim | Evidence | Result |
| --- | --- | --- |
| QNN/HTP app path works | `20260718_app_qnn_delegate_fixed_live_rb5` | fixed sample and live ROI pass |
| Data path was the real live bottleneck | `20260718_app_qnn_delegate_live_roi_breakdown` | full-frame `ImageProxy.toBitmap()` p50/p95 41/43ms |
| Data-path optimization mattered | `20260718_app_qnn_delegate_live_roi_1280x960` | app e2e 63/65ms -> 22/25ms |
| QuickSRNet can run as live candidate | `20260718_app_quicksrnet_live_roi_1280x960` | e2e p50/p95 22/25ms, inference 2/2ms |
| Automatic switching is not free | `20260718_app_qnn_resource_probe` | Real-ESRGAN -> QuickSRNet switch about 369ms |
| PSNR is not the only quality judge | `EVAL_METRIC_POLICY.md` and contact sheets | visual veto remains required |
| Real-camera showcase is available | `20251110_045328_minimal_real_camera_set` | 8/8 scenes complete, accepted with caveats |
| Tensor-ready live is bounded | `20251110_tensor_ready_live_roi_1280x960` | valid but not promoted; p50 e2e did not beat Bitmap default |

## Model Roles

| Model / path | Current role |
| --- | --- |
| Real-ESRGAN W8A8 + QNN Delegate | QNN/HTP deployment milestone, perceptual enhancement candidate, comparison baseline |
| QuickSRNetSmall W8A8 + QNN Delegate | default live ROI workhorse |
| Automatic dual-model live routing | not default; switch cost, route risk, and power/thermal data do not justify it yet |

## Numbers Worth Remembering

```text
AI Hub QCS8550 profile, float model: 5.9ms, 74 ops on HTP, 0 fallback
Android TFLite CPU 128->512 baseline: about 579-610ms inference
Android TFLite GPU 128->512: about 126-148ms inference
QNN Delegate fixed sample W8A8: about 4-5ms inference, about 53-61ms total
Old live ROI full 4000x3000 path: e2e about 63/65ms
New live ROI 1280x960 path: e2e about 22/25ms
QuickSRNet live ROI: inference about 2/2ms, e2e about 22/25ms
Current default after output reuse: e2e about 19.0/24.7ms
120s sustained default run: e2e first/last 20% 20/25ms -> 21/26ms
Real-ESRGAN -> QuickSRNet dynamic switch: about 369ms
Real-camera showcase set: 8 scenes / 32 standard images, accepted with caveats
```

## What Not To Claim

- Do not claim QuickSRNet is globally better than Real-ESRGAN just because PSNR is higher.
- Do not claim Real-ESRGAN is worse just because it is more perceptual/GAN-style.
- Do not claim automatic dual-model live routing is product-ready.
- Do not claim sustained power or thermal stability until P7 is complete.
- Do not claim full power/perf-watt characterization from the current short sustained run.
- Do not claim true zero-copy or promote tensor-ready live as the default path.

## Interview Answer

```text
I first made the SR model run in the Android app, then moved from CPU/GPU
experiments to the QNN TFLite Delegate path on HTP. After the model was running,
I profiled the actual live app path. The important finding was that NPU inference
was already only a few milliseconds; the real bottleneck was full-frame CameraX
to Bitmap conversion and later output postprocessing. So I reduced the live
analysis size from 4000x3000 to 1280x960 and cut app e2e latency from about
63ms to about 22ms.

I also compared Real-ESRGAN and QuickSRNetSmall. Real-ESRGAN is more perceptual
and sharper, while QuickSRNetSmall is much smaller and more conservative on
structure-sensitive cases. I did not turn that into automatic routing directly:
I measured model init, memory, and switch cost first. Since switching costs about
369ms and power/thermal behavior is not yet validated, the current route is
QuickSRNet as the live ROI workhorse candidate and Real-ESRGAN as the QNN/HTP
milestone plus optional perceptual/post-capture enhancement path. I then captured
a small real-camera set to check that this route still makes sense outside fixed
benchmarks; it supports the route with caveats rather than proving either model
is globally better. I also tested native YUV ROI and tensor-ready input; they
were technically valid, but repeated live timing did not justify replacing the
default path, so I kept the simpler route and used output reuse for a small
tail-latency improvement.
```

## Current Showcase Boundary

The minimum showcase should use:

```text
1. QNN Delegate fixed-sample evidence.
2. Live ROI 63ms -> 22ms data-path optimization table.
3. QuickSRNet vs Real-ESRGAN model tradeoff table.
4. Three structure-sensitive app cases.
5. Real-camera showcase contact sheet.
6. Route decision explaining why automatic dual-model routing is not default.
```

Before making stronger claims, complete:

```text
1. Longer power/perf-watt characterization if making sustained-use claims.
2. Deeper output/postprocess work only if more live-path latency reduction is needed.
```
