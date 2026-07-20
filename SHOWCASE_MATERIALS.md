# Showcase Materials

Updated: 2026-07-19

## Minimum Evidence Package

Use only this small set for the current showcase. Do not collect lots of
near-duplicate screenshots.

Boundary:

```text
This showcase package is the current stable evidence set, not the ceiling for
future exploration. It should preserve what works while leaving room for
bounded experiments such as real-camera validation, YUV ROI, perceptual metrics,
or AIMET if their triggers appear.
```

## 1. QNN Delegate App Milestone

Evidence:

```text
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260718_app_qnn_delegate_fixed_live_rb5
```

Use:

```text
fixed_sample_contact_sheet.png
app_vs_qnn_net_run_contact_sheet.png
SUMMARY.md
```

Message:

```text
The Android app path runs W8A8 TFLite through QNN TFLite Delegate on HTP.
It works for fixed sample and live ROI, and app output aligns with qnn-net-run.
```

## 2. Data-Path Bottleneck And Fix

Before:

```text
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260718_app_qnn_delegate_live_roi_breakdown
```

After:

```text
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260718_app_qnn_delegate_live_roi_1280x960
```

Message:

```text
QNN inference was only about 3ms; the real bottleneck was full-frame
ImageProxy.toBitmap() at about 41/43ms. Reducing live analysis to 1280x960 cut
app e2e from about 63/65ms to about 22/25ms.
```

## 3. Postprocess And Sample-Copy Optimization

Evidence:

```text
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260718_p5_postprocess_samplecopy_w8a8_live_roi
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260718_p5_postprocess_samplecopy_quicksr_live_roi
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260720_app_e2e_schema_output_reuse_120f
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260720_app_e2e_schema_output_reuse_60s
```

Message:

```text
Reusing TFLite buffers and reducing per-frame evidence copying lowered
postprocess/sample-copy overhead. Later live output Bitmap reuse reduced tail
latency without changing the median.
```

Use numbers:

```text
Real-ESRGAN W8A8 postprocess: 14/16ms -> 10/13ms
QuickSRNetSmall postprocess: 15/18ms -> 11/14ms
sampleCopy p50/p95: about 3/4ms -> 0/0ms
default QuickSR live e2e p50/p95 after output reuse: 19.0 / 24.7ms
120s sustained output-reuse QuickSR live e2e first/last 20% p50/p95:
20.0 / 25.0ms -> 21.0 / 26.0ms
latest UINT8 output bulk-copy smoke: postprocess 1 / 1ms, e2e 15 / 19ms
latest 60s sustained smoke: e2e first/last 20% p50/p95 = 15/20ms -> 16/21ms
```

Boundary:

```text
The latest output bulk-copy result is app timing evidence only. It does not
prove visual quality by itself and it is not true zero-copy.
```

## 4. Model Tradeoff

Evidence:

```text
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260718_145028_quicksrnet_small_vs_realesrgan_w8a8_full_host
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260718_app_strategy_three_case_fixed_compare
```

Use:

```text
contact_sheet.png
category_summary.csv
metrics.csv
```

Message:

```text
Real-ESRGAN and QuickSRNet are not a simple winner/loser pair.
Real-ESRGAN is sharper and more perceptual; QuickSRNetSmall is tiny and
conservative, and is safer for selected structure-sensitive cases.
```

Boundary:

```text
Do not claim QuickSRNet is globally better only from PSNR.
Do not claim Real-ESRGAN is obsolete.
```

## 5. Resource And Route Decision

Evidence:

```text
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260718_app_qnn_resource_probe
MODEL_ROUTE_DECISION.md
ROUTE_DECISION.md
```

Use numbers:

```text
Real-ESRGAN -> QuickSRNet switch total: about 369ms
Real-ESRGAN QNN init: about 781ms first init, 679ms later init
QuickSRNet init after switching: about 293ms
```

Message:

```text
Automatic live dual-model routing is not the default because switching and
runtime memory behavior are not free. The current engineering route is
QuickSRNetSmall for live ROI, Real-ESRGAN for QNN/HTP milestone and optional
post-capture/offline perceptual enhancement.
```

## 6. Short Sustained Stability

Evidence:

```text
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260718_p4_sustained_w8a8_live_roi_5min
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260718_p4_sustained_quicksr_live_roi_5min
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20251110_output_reuse_quicksr_live_roi_120s
```

Use numbers:

```text
Real-ESRGAN W8A8: 300s, e2e first/last 20% p50/p95 = 22/25ms -> 22/25ms
QuickSRNetSmall: 300s, e2e first/last 20% p50/p95 = 21/26ms -> 22/27ms
Current output-reuse QuickSR default: 120s, e2e first/last 20% p50/p95 = 20/25ms -> 21/26ms
battery temperature coarse signal: 24.0C -> 24.0C
```

Boundary:

```text
This is short-run stability, not full power/perf-watt proof.
```

## 6.5 Every-N Temporal Smoke

Evidence:

```text
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260720_every_n3_live_roi_60s_final
```

Use numbers:

```text
everyN=3
enhanced frames=85
skipped frames=169
effective enhanced FPS p50/p95=9.9/9.9
per-enhanced-frame e2e p50/p95=22/25ms
```

Message:

```text
The every-N ImageAnalysis route is technically valid as a temporal/cadence
probe. It reduces enhancement frequency, not the latency of each enhanced frame.
Full CameraX VideoCapture remains a separate product/demo decision.
```

## 7. Real-Camera Showcase Set

Evidence:

```text
C:\Users\Admin\Videos\RB5 gen2\real_camera_showcase\20251110_045328_minimal_real_camera_set
```

Use:

```text
contact_sheet.png
review_template.csv
ROUTE_REVIEW.md
SUMMARY.md
```

Result:

```text
8/8 scenes complete
32/32 standard images valid
status: accepted_with_caveats
no retake required for the current minimum set
```

Message:

```text
The real-camera set supports the route decision rather than replacing the fixed
benchmark. QuickSRNetSmall is now the default live ROI workhorse.
Real-ESRGAN remains useful as a sharper text/edge comparison and optional
post-capture/perceptual path.
```

Boundary:

```text
Do not claim either model is globally better from this 8-scene set.
Do not use it as a training set.
```

## Human Review Still Needed

Human visual review status is now recorded in:

```text
VISUAL_REVIEW_QUEUE.md
```

Current labels:

```text
QNN Delegate fixed sample: pass
App delegate vs qnn-net-run: pass
QuickSRNet vs Real-ESRGAN full host set: conditional
Three structure-sensitive app cases: conditional
Real-camera showcase set: accepted_with_caveats
```

Showcase rule:

```text
Use the first two as direct QNN/HTP app milestone evidence.
Use the last two as model-tradeoff evidence with caveats, not as a global
QuickSRNet-wins claim.
Use the real-camera set as final showcase credibility evidence with caveats.
```

## Suggested Slide / Resume Order

1. Problem and platform: RB5 Gen2 / QCS8550 / Android edge AI image enhancement.
2. QNN/HTP deployment path: W8A8 TFLite -> QNN Delegate -> HTP.
3. Profiling finding: inference was not the live bottleneck.
4. Data-path optimization: 63/65ms -> 22/25ms.
5. Model tradeoff: Real-ESRGAN vs QuickSRNetSmall.
6. Resource-aware route decision: no default automatic dual-model routing.
7. Real-camera showcase evidence and remaining boundaries.
8. Short sustained validation and remaining boundaries.
