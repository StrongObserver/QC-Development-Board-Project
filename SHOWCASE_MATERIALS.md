# Showcase Materials

Updated: 2026-07-18

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
```

Message:

```text
Reusing TFLite buffers and reducing per-frame evidence copying lowered
postprocess/sample-copy overhead. The total e2e improvement is modest but real.
```

Use numbers:

```text
Real-ESRGAN W8A8 postprocess: 14/16ms -> 10/13ms
QuickSRNetSmall postprocess: 15/18ms -> 11/14ms
sampleCopy p50/p95: about 3/4ms -> 0/0ms
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
```

Use numbers:

```text
Real-ESRGAN W8A8: 300s, e2e first/last 20% p50/p95 = 22/25ms -> 22/25ms
QuickSRNetSmall: 300s, e2e first/last 20% p50/p95 = 21/26ms -> 22/27ms
battery temperature coarse signal: 24.0C -> 24.0C
```

Boundary:

```text
This is short-run stability, not full power/perf-watt proof.
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
```

Showcase rule:

```text
Use the first two as direct QNN/HTP app milestone evidence.
Use the last two as model-tradeoff evidence with caveats, not as a global
QuickSRNet-wins claim.
```

## Suggested Slide / Resume Order

1. Problem and platform: RB5 Gen2 / QCS8550 / Android edge AI image enhancement.
2. QNN/HTP deployment path: W8A8 TFLite -> QNN Delegate -> HTP.
3. Profiling finding: inference was not the live bottleneck.
4. Data-path optimization: 63/65ms -> 22/25ms.
5. Model tradeoff: Real-ESRGAN vs QuickSRNetSmall.
6. Resource-aware route decision: no default automatic dual-model routing.
7. Short sustained validation and remaining boundaries.
