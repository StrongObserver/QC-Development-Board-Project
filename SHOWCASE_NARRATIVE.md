# RB5 Gen2 Showcase Narrative

Updated: 2026-07-23

## One-Line Positioning

```text
An Android/QCS8550 on-device AI Runtime project that deploys W8A8 workloads
through QNN TFLite Delegate on HTP, profiles the real app path, and makes
backend, model, and data-path decisions from latency, quality, memory, and risk.
```

## Core Story

This project is not just "running a super-resolution model" or "building a
CameraX image-enhancement app".

The engineering story is:

```text
1. Built the Android CameraX -> TFLite workload -> display path.
2. Compared CPU / NNAPI / GPU / QNN paths and moved the main deployment path to QNN/HTP.
3. Verified three Runtime evidence layers:
   AI Hub QNN profile, local qnn-net-run profile, and Android QNN Delegate app e2e.
4. Verified the stable Android app path as:
   W8A8 TFLite -> QNN TFLite Delegate -> HTP -> fixed sample and live ROI.
5. Profiled the actual app path and found inference was not the live bottleneck.
6. Reduced the dominant CameraX/ImageAnalysis conversion cost by changing live analysis from 4000x3000 to 1280x960.
7. Compared Real-ESRGAN and QuickSRNetSmall as different workload tradeoffs instead of ranking them by PSNR alone.
8. Measured init, memory, and switch cost before rejecting automatic live dual-model routing as the default path.
9. Optimized the UINT8 output conversion path and added EvalHub-compatible app e2e rows for live runs.
10. Collected a minimal real-camera showcase set and used visual review to keep the route decision caveated.
11. Tested native/tensor-ready ROI variants, promoted direct-YUV native ROI/RGB after same-frame MAD 0.0, then added native RGB staging to reach 8/9/9ms p50/p95/p99 over 20 minutes.
```

## Evidence Chain

| Claim | Evidence | Result |
| --- | --- | --- |
| AI Hub QNN context route works | `real_esrgan_general_x4v3-qnn-w8a8-qcs8550-20260715` | W8A8 QNN p50 about 1.778ms, NPU 72 |
| Local qnn-net-run route works | `dryrun_full_preflight_check` | QNN accelerator p50/p95 about 9.75/10.39ms |
| QNN/HTP app path works | `20260718_app_qnn_delegate_fixed_live_rb5` | fixed sample and live ROI pass |
| Data path was the real live bottleneck | `20260718_app_qnn_delegate_live_roi_breakdown` | full-frame `ImageProxy.toBitmap()` p50/p95 41/43ms |
| Data-path optimization mattered | `20260718_app_qnn_delegate_live_roi_1280x960` | app e2e 63/65ms -> 22/25ms |
| QuickSRNet can run as live candidate | `20260718_app_quicksrnet_live_roi_1280x960` | e2e p50/p95 22/25ms, inference 2/2ms |
| Output conversion was further reduced | `20260720_app_e2e_schema_output_reuse_120f` | postprocess p50/p95 1/1ms, e2e 15/19ms |
| App e2e schema is now emitted | `20260720_app_e2e_schema_output_reuse_60s` | 60s sustained row under EvalHub app e2e shape |
| Direct-YUV became the default data path | `20260722_app_default_direct_yuv_live_roi_120f` | default app e2e p50/p95 10/12ms |
| Native staging improved the current default | `20260723_native_staging_default_live_roi_20min` | current app e2e p50/p95/p99 8/9/9ms |
| Automatic switching is not free | `20260718_app_qnn_resource_probe` | Real-ESRGAN -> QuickSRNet switch about 369ms |
| PSNR is not the only quality judge | `EVAL_METRIC_POLICY.md` and contact sheets | visual veto remains required |
| Real-camera showcase is available | `20251110_045328_minimal_real_camera_set` | 8/8 scenes complete, accepted with caveats |
| Tensor-ready live is bounded | `20251110_tensor_ready_live_roi_1280x960` | old tensor-ready path stayed a probe; later direct-YUV became default |

## Model Roles

| Model / path | Current role |
| --- | --- |
| Real-ESRGAN W8A8 + QNN Delegate | QNN/HTP deployment milestone, perceptual enhancement candidate, comparison baseline |
| QuickSRNetSmall W8A8 + QNN Delegate | default live ROI workhorse |
| Automatic dual-model live routing | not default; switch cost, route risk, and power/thermal data do not justify it yet |

## Numbers Worth Remembering

```text
AI Hub QCS8550 profile, float model: 5.9ms, 74 ops on HTP, 0 fallback
AI Hub QCS8550 W8A8 QNN profile: about 1.778ms p50, NPU 72
Local qnn-net-run QNN accelerator: about 9.75/10.39ms p50/p95
Android TFLite CPU 128->512 baseline: about 579-610ms inference
Android TFLite GPU 128->512: about 126-148ms inference
QNN Delegate fixed sample W8A8: about 4-5ms inference, about 53-61ms total
Old live ROI full 4000x3000 path: e2e about 63/65ms
New live ROI 1280x960 path: e2e about 22/25ms
QuickSRNet live ROI: inference about 2/2ms, e2e about 22/25ms
Current default after output reuse: e2e about 19.0/24.7ms
Current direct-YUV native staging default: e2e about 8/9/9ms over 20 minutes
Historical output-bulk-copy sustained smoke: e2e first/last 20% 15/20ms -> 16/21ms
120s sustained default run: e2e first/last 20% 20/25ms -> 21/26ms
Real-ESRGAN -> QuickSRNet dynamic switch: about 369ms
Real-camera showcase set: 8 scenes / 32 standard images, accepted with caveats
```

## What Not To Claim

- Do not claim QuickSRNet is globally better than Real-ESRGAN just because PSNR is higher.
- Do not claim Real-ESRGAN is worse just because it is more perceptual/GAN-style.
- Do not claim automatic dual-model live routing is product-ready.
- Do not claim external-meter power or product-grade battery life from battery-node estimates.
- Do not claim true zero-copy or promote tensor-ready live as the default path.
- Do not collapse AI Hub profile, local qnn-net-run profile, and Android app e2e
  timing into a single latency number.

## Interview Answer

```text
I first made the workload run in the Android app, then moved from CPU/GPU
experiments to the QNN TFLite Delegate path on HTP. I also kept AI Hub profile,
local qnn-net-run, and app e2e as separate evidence layers. After the model was
running, I profiled the actual live app path. The important finding was that NPU
inference was already only a few milliseconds; the real bottleneck was full-frame
CameraX to Bitmap conversion and later output postprocessing. So I reduced the
live analysis size from 4000x3000 to 1280x960 and cut app e2e latency from about
63ms to about 22ms. Later output-path work removed per-channel direct buffer
reads in the UINT8 postprocess loop. The later native staging path reuses the RGB staging buffer and reaches about 8/9/9ms p50/p95/p99 over 20 minutes.

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
default path, so I kept the simpler route and optimized the output conversion
path instead.
```

## Current Showcase Boundary

The minimum showcase should use:

```text
1. AI Hub / qnn-net-run / Android app evidence separation.
2. QNN Delegate fixed-sample evidence.
3. Live ROI 63ms -> 22ms -> 10/12ms -> 8/9/9ms data-path optimization table.
4. QuickSRNet vs Real-ESRGAN workload tradeoff table.
5. Three structure-sensitive app cases.
6. Real-camera showcase contact sheet.
7. Route decision explaining why automatic dual-model routing is not default.
```

Before making stronger claims, complete:

```text
1. External power-meter measurement if making product-grade perf/watt claims.
2. Deeper tensor-ready or YUV ROI work only if more live-path latency reduction is needed.
```
