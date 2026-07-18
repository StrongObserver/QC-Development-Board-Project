# RB5 Gen2 Route Decision

Updated: 2026-07-18

## Decision

The current project route should not default to an automatic dual-model live
strategy.

Use this framing instead:

```text
Decision C: QuickSRNetSmall for live ROI; Real-ESRGAN for QNN/HTP milestone,
comparison baseline, and optional post-capture/offline perceptual enhancement.
```

Detailed model route decision:

```text
C:\Users\Admin\Desktop\QC-Development-Board-Project\MODEL_ROUTE_DECISION.md
```

Current roles:

| Role | Model / Path | Decision |
| --- | --- | --- |
| Deployment milestone | Real-ESRGAN W8A8 + QNN TFLite Delegate / HTP | Keep as the proven QNN/HTP app milestone and optional perceptual enhancement path |
| Live ROI workhorse candidate | QuickSRNetSmall W8A8 | Keep as the strongest current live ROI candidate after P5/P6 timing and resource probes |
| Current top optimization target | App postprocess/output path | Data-path optimization already cut frame conversion; postprocess is now the largest live stage |
| Not current default | Automatic Real-ESRGAN vs QuickSRNet live routing | Do not enable; measured switch cost is not free and power/thermal evidence is still missing |

## Why

The current data says the largest live ROI bottleneck is not model inference:

```text
QNN inference p50/p95: 3/3ms
ImageProxy.toBitmap full 4000x3000 p50/p95: 41/43ms
Live ROI e2e p50/p95: about 63/65-66ms
```

Changing or routing models acts mostly on the 3ms inference part. The dominant
cost is the camera frame conversion path. For an industrial-style project,
optimizing the data pipeline has higher priority than adding model-routing
complexity.

## Model Comparison Interpretation

Real-ESRGAN and QuickSRNet should not be judged by PSNR alone.

```text
Real-ESRGAN: perceptual/GAN-style enhancement, sharper, more visually aggressive, can hallucinate or merge structure.
QuickSRNetSmall: conservative reconstruction, smaller, faster, safer on structure-sensitive cases, less visually aggressive.
```

The host full benchmark showed:

```text
QuickSRNetSmall W8A8 model size: 43,672 bytes
Real-ESRGAN W8A8 model size: 1,308,432 bytes
QuickSRNetSmall host p50 avg: 8.512ms
Real-ESRGAN host p50 avg: 344.932ms
QuickSRNetSmall average PSNR delta vs Real-ESRGAN: +2.31dB
```

This supports QuickSRNetSmall as a serious lightweight candidate. It does not
prove that QuickSRNet is globally better, because Real-ESRGAN optimizes a
different perceptual tradeoff.

## Structure-Sensitive Evidence

On three human-identified app fixed-sample cases:

| Case | QuickSR PSNR Delta vs Real-ESRGAN | Interpretation |
| --- | ---: | --- |
| `low_light_div2k0852` | +1.62dB | QuickSR is safer for low-light branch-like structure |
| `people_scene_div2k0832` | +3.60dB | QuickSR is safer for people/face-like structure |
| `text_signage_urban076` | +1.09dB | QuickSR is safer for text/signage-like structure |

This supports keeping QuickSRNetSmall as a conservative candidate. It does not
yet justify keeping two models live and switching automatically.

## Dual-Model Strategy Gate

The following P6 resource measurements are now available:

```text
Interpreter + QNN Delegate initialization time per model
single-model resident memory
two-model resident memory
model switch time
first-frame jank after switching
```

Still missing before product-style claims or automatic routing:

```text
power or current over 5-10 minute sustained runs
thermal drift and throttling
route failure risk on non-cherry-picked scenes
```

## Near-Term Execution Order

1. Preserve the QNN Delegate Real-ESRGAN milestone.
2. Keep QuickSRNetSmall fixed-sample evidence as candidate-model proof.
3. Correct the evaluation language: PSNR/SSIM are fidelity metrics, not final perceptual judgment.
4. Keep the 1280x960 live ROI data-path optimization as the current app milestone.
5. Treat QuickSRNetSmall as the likely default live ROI workhorse candidate, pending human visual review and sustained power/thermal checks.
6. Keep Real-ESRGAN as QNN/HTP deployment milestone, perceptual/post-capture enhancement candidate, and comparison baseline.
7. Do not implement automatic live model switching unless a later product need justifies the 369ms switch path and routing risk.

## Updated Data-Path Result

The first data-path optimization was validated by changing live `ImageAnalysis`
from highest available 4000x3000 to a 1280x960 target.

Result folder:

```text
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260718_app_qnn_delegate_live_roi_1280x960
```

Key result:

```text
ImageProxy.toBitmap p50/p95: 41/43ms -> 4/5ms
app e2e p50/p95: 63/65ms -> 22/25ms
QNN inference p50/p95: about 3/4ms
```

This validates the current route decision: the largest near-term gain came from
the camera/data path, not from changing SR models.

## QuickSRNet Live ROI Result

QuickSRNetSmall was validated in the same 1280x960 app live ROI path:

```text
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260718_app_quicksrnet_live_roi_1280x960
```

Key result:

```text
parsed frames: 166
ImageProxy.toBitmap p50/p95: 4 / 5ms
QuickSRNet QNN inference p50/p95: 2 / 2ms
app e2e p50/p95: 22 / 25ms
analyzer wall p50/p95: 25 / 29ms
```

Interpretation:

```text
QuickSRNetSmall runs cleanly through QNN Delegate in the current live ROI path.
It reduces the inference slice from about 3-4ms to about 2ms, but total e2e is
still dominated by non-inference work, especially postprocess/output bitmap work.
```

## Resource Cost Result

P6 resource-cost probing was completed here:

```text
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260718_app_qnn_resource_probe
```

Key result:

| Metric | Result | Interpretation |
| --- | ---: | --- |
| Real-ESRGAN W8A8 QNN init | 781ms first init, 679ms later init | visible cold-start cost |
| QuickSRNetSmall QNN init | 38ms when added after Real-ESRGAN, 293ms after switching | cheaper, but not always free |
| Real-ESRGAN steady fixed-sample total | p50/p95 20 / 21.6ms | fixed-sample path after warmup |
| QuickSRNet steady fixed-sample total | p50/p95 15 / 16.8ms | faster, mostly by inference and postprocess |
| Real-ESRGAN -> QuickSRNet switch | 369ms total | too large for seamless live automatic switching |
| Single Real-ESRGAN load PSS delta | about +98,991KB | QNN/TFLite path has meaningful resident cost |
| Add QuickSRNet while Real-ESRGAN resident | about +1,600KB in this short probe | second model asset is small, but runtime cache behavior is sticky |

The memory result has an important caveat: after closing both interpreters, PSS
did not return to the start value. Treat this as QNN/runtime cache and process
memory behavior, not as proof that `close()` fully releases all resources.

## Next Data-Path Work

The next bottleneck is output/postprocess bitmap generation around 14/16ms
p50/p95. If more live ROI speed is needed, investigate in this order:

1. Avoid unnecessary sample-copy work during live preview unless the user is saving evidence.
2. Optimize output conversion from TFLite buffer to `Bitmap`.
3. Consider YUV ROI conversion only for the ROI instead of full-frame `Bitmap`.
4. Keep high-resolution still-sample capture as a separate path if it is still needed.

Do not start AHardwareBuffer, DMA-BUF, or true zero-copy work until the simpler
ROI/data-path options are exhausted.

## Postprocess Optimization Result

P5 reduced the output/postprocess and evidence-copy overhead:

```text
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260718_p5_postprocess_samplecopy_w8a8_live_roi
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260718_p5_postprocess_samplecopy_quicksr_live_roi
```

Key result:

| Model | Postprocess p50/p95 before | Postprocess p50/p95 after | e2e p50/p95 after |
| --- | ---: | ---: | ---: |
| Real-ESRGAN W8A8 | 14 / 16ms | 10 / 13ms | 20 / 25ms |
| QuickSRNetSmall W8A8 | 15 / 18ms | 11 / 14ms | 19 / 24ms |

The change also reduced live evidence `sampleCopy` p50/p95 to `0/0ms` by no
longer copying saveable evidence on every frame. This is a modest but real app
path improvement. Do not over-claim it as a full zero-copy pipeline.

## Short Sustained Run Result

P4 short sustained validation is complete:

```text
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260718_p4_sustained_w8a8_live_roi_5min
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260718_p4_sustained_quicksr_live_roi_5min
```

Key result:

```text
Real-ESRGAN W8A8: 300s, 8970 parsed frames, e2e first/last 20% p50/p95 = 22/25ms -> 22/25ms
QuickSRNetSmall: 300s, 8987 parsed frames, e2e first/last 20% p50/p95 = 21/26ms -> 22/27ms
battery temperature coarse signal: 24.0C -> 24.0C for both runs
```

Boundary:

```text
This supports short-run stability. It is not full perf-per-watt evidence.
```

## QuickSRNet Workhorse Gate

QuickSRNetSmall is a likely live ROI workhorse candidate because these are now
true:

```text
fixed sample app output aligns with host output
live ROI e2e is acceptable after data-path optimization
init and switching cost are measured
short-run memory cost is measured
```

Still required before making it the default product-style story:

```text
structure-sensitive cases pass human visual review
5-10 minute power/thermal drift is acceptable
showcase evidence is cleaned and minimal
```

It is still not an automatic routing strategy.

## Real-ESRGAN Role

Real-ESRGAN should be presented as:

```text
QNN/HTP deployment milestone
perceptual enhancement path
optional post-capture enhancement candidate
comparison baseline for model tradeoff analysis
```

It should not be presented as the universal always-on best model for every
scene.

## What Not To Do

- Do not claim QuickSRNet is globally better only because PSNR is higher.
- Do not claim Real-ESRGAN is worse only because PSNR is lower.
- Do not optimize the 3ms QNN inference before addressing the 41ms frame conversion.
- Do not enable automatic dual-model live routing based only on three favorable cases.
- Do not treat model switching as free; the measured Real-ESRGAN -> QuickSRNet switch path is about 369ms.
- Do not claim dual residency is harmless from one short probe; QNN/runtime memory stays sticky after `close()`.

## Interview Framing

Use this project story:

```text
I first deployed a W8A8 SR model through QNN Delegate on HTP.
Then I profiled the app path and found inference was not the bottleneck.
The actual live ROI bottleneck was full-frame CameraX to Bitmap conversion.
I also compared a perceptual SR model and a lightweight conservative SR model.
That showed a real perceptual-vs-fidelity tradeoff.
I did not blindly add model routing; I used latency, memory, power, maintainability, and artifact risk to decide the next engineering step.
```

