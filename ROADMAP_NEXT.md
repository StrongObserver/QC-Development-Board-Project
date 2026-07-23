# RB5 Gen2 Next Roadmap

Updated: 2026-07-23

## Current Positioning

The roadmap now follows the refined project design:

```text
QCS8550 端侧 AI 推理 Runtime 与异构性能优化
```

Do not interpret this roadmap as a request to add more image-enhancement UI
features by default. The next high-value work is Runtime evidence: final
benchmark tables, longer sustained P50/P95/P99, cold/warm init and sticky-memory
summaries, Perfetto/QNN timing if useful, and explicit AIMET/zero-copy/video
decisions.

This roadmap starts from the current route decision:

```text
Do not default to automatic dual-model live routing yet.
Prioritize data-path optimization and disciplined model-candidate validation.
Keep bounded exploration lanes open after preserving a stable baseline.
```

## P5: QuickSRNet Live ROI Validation - Done

Goal:

```text
Measure whether QuickSRNetSmall is a viable live ROI workhorse candidate after
the 1280x960 data-path optimization.
```

Tasks:

1. Launch live ROI with:

```bat
adb shell am start -n com.cyf.rb5visionlab/.MainActivity --ez start_live_sr true --es sr_backend QNN --es sr_model QUICKSR_W8A8
```

2. Capture at least 100 frames of `RB5_SR` logs.
3. Parse `frameBitmap`, `pre`, `inf`, `post`, `e2e`.
4. Compare against Real-ESRGAN W8A8 1280x960 live ROI.

Expected output:

```text
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260718_app_quicksrnet_live_roi_1280x960
```

Result:

```text
parsed frames: 166
QuickSRNet QNN inference p50/p95: 2 / 2ms
app e2e p50/p95: 22 / 25ms
analyzer wall p50/p95: 25 / 29ms
```

Decision:

```text
QuickSRNetSmall is validated as a live ROI workhorse candidate, but this does
not justify automatic dual-model live routing.
```

## P6: Resource Cost Measurement - Done

Goal:

```text
Decide whether a second model is cheap enough to keep as a candidate.
```

Measure:

| Metric | Why |
| --- | --- |
| Real-ESRGAN init time | Detect cold-start jank |
| QuickSRNet init time | Detect candidate-model overhead |
| first inference time | Captures graph prepare / delegate startup cost |
| steady inference p50/p95 | Runtime cost |
| memory before/after model load | Resident cost |
| memory with both models loaded | Whether dual residency is realistic |
| switch time | Whether dynamic switching is acceptable |

Boundary:

```text
The table now exists. It supports a scoped route: do not implement automatic
switching by default because switching has a visible cold path. This is not a
dead end for future routing experiments.
```

Result:

```text
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260718_app_qnn_resource_probe

Real-ESRGAN W8A8 QNN init: 781ms first init, 679ms later init
QuickSRNetSmall QNN init: 38ms when added after Real-ESRGAN, 293ms after switching
QuickSRNet steady fixed-sample total: p50/p95 15 / 16.8ms
Real-ESRGAN -> QuickSRNet switch total: 369ms
single Real-ESRGAN load PSS delta: about +98,991KB
add QuickSRNet while Real-ESRGAN resident: about +1,600KB in this short probe
```

## P7: Power And Thermal Plan - Done For Short Sustained Run

Goal:

```text
Avoid claiming product-level viability from short demo runs.
```

Plan:

1. Run Real-ESRGAN live ROI for 5-10 minutes.
2. Run QuickSRNet live ROI for 5-10 minutes.
3. Record e2e p50/p95 drift.
4. Record available temperature and throttling signals.
5. If current/power data is available, record energy per frame.

Boundary:

```text
This is short sustained evidence, not a full power/perf-watt measurement.
Battery temperature is a coarse signal.
```

Result:

```text
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260718_p4_sustained_w8a8_live_roi_5min
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260718_p4_sustained_quicksr_live_roi_5min

Real-ESRGAN W8A8: 300s, 8970 parsed frames, e2e first/last 20% p50/p95 = 22/25ms -> 22/25ms
QuickSRNetSmall: 300s, 8987 parsed frames, e2e first/last 20% p50/p95 = 21/26ms -> 22/27ms
battery temperature coarse signal: 24.0C -> 24.0C for both runs
```

## P8: Route Decision Update

Possible final decisions:

| Decision | Meaning |
| --- | --- |
| A | Keep Real-ESRGAN as deployment milestone, QuickSRNet as evidence only |
| B | QuickSRNet becomes default live ROI workhorse, Real-ESRGAN becomes optional enhancement |
| C | QuickSRNet for live, Real-ESRGAN for post-capture/offline enhancement |
| D | Automatic dual-model live routing |

Current preference:

```text
B or C are now the practical choices.
D is still not justified for the default live path, but can be revisited as a
bounded experiment with a clear hypothesis and rollback.
```

## P5: Postprocess And Sample-Copy Optimization - Done

Goal:

```text
Reduce the remaining live ROI overhead after 1280x960 data-path optimization.
```

Change:

```text
SuperResolver now reuses input/output ByteBuffers and pixel arrays.
UINT8 output postprocess uses a small lookup table.
Live ROI evidence sample copying now happens every 30 frames instead of every frame.
```

Result:

```text
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260718_p5_postprocess_samplecopy_w8a8_live_roi
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260718_p5_postprocess_samplecopy_quicksr_live_roi

Real-ESRGAN W8A8 postprocess p50/p95: 14/16ms -> 10/13ms
Real-ESRGAN W8A8 sampleCopy p50/p95: 3/~4ms -> 0/0ms
Real-ESRGAN W8A8 e2e p50/p95: 22/25ms -> 20/25ms

QuickSRNetSmall postprocess p50/p95: 15/18ms -> 11/14ms
QuickSRNetSmall sampleCopy p50/p95: 3/4ms -> 0/0ms
QuickSRNetSmall e2e p50/p95: 22/25ms -> 19/24ms
```

2026-07-20 follow-up:

```text
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260720_app_e2e_schema_output_reuse_120f
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260720_app_e2e_schema_output_reuse_60s

QuickSRNetSmall UINT8 output bulk-copy smoke: postprocess 1/1ms, e2e 15/19ms
60s sustained smoke: e2e first/last 20% p50/p95 15/20ms -> 16/21ms
```

Boundary:

```text
This is a real but modest app-path optimization. FrameBitmap timing varied in
the P5 runs, so do not claim the whole live path improved by the full
postprocess delta. The strongest supported claim is: postprocess and sample-copy
overhead were reduced, while total e2e improved modestly.

The 2026-07-20 follow-up is stronger for the default QuickSR path: it validates
that UINT8 output bulk-copy reduces postprocess to about 1/1ms in app timing.
This is still not true zero-copy and not visual quality evidence.
```

## P9: Showcase Material

Minimum useful package:

```text
1. QNN Delegate fixed sample evidence.
2. Live ROI before/after table: 63ms -> 22ms.
3. QuickSRNet vs Real-ESRGAN full benchmark contact sheet.
4. Three structure-sensitive app cases.
5. Route decision: why not automatic dual-model routing yet.
```

Interview framing:

```text
The project is not "I ran a model".
It is "I deployed on QNN/HTP, profiled the real app path, found the actual
bottleneck, corrected the evaluation metric, and made an engineering route
decision based on latency, fidelity, perceptual quality, memory, and product
risk."
```
