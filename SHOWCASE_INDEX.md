# RB5 Gen2 Showcase Index

Updated: 2026-07-19

## What This Project Proves

```text
Android CameraX live ROI
-> QuickSRNetSmall W8A8
-> QNN TFLite Delegate
-> Qualcomm HTP
-> display at about 19.0 / 24.7ms e2e p50/p95
```

The project is not just a model demo. It shows deployment, profiling,
evaluation, route decisions, and bounded performance exploration on an actual
RB5 Gen2 / QCS8550 Android device.

## Read These First

| Purpose | File |
| --- | --- |
| Repository overview | `README.md` |
| Evidence package | `SHOWCASE_MATERIALS.md` |
| Interview story | `SHOWCASE_NARRATIVE.md` |
| Resume bullets | `RESUME_PROJECT_DRAFT.md` |
| Demo commands | `DEMO_RUNBOOK.md` |
| Interview Q&A | `INTERVIEW_TALK_TRACK.md` |
| Current handoff | `NEXT_ACTION.md` |

## Minimum Evidence Set

| Claim | Evidence path |
| --- | --- |
| QNN Delegate app path works | `C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260718_app_qnn_delegate_fixed_live_rb5` |
| Data path was the bottleneck | `C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260718_app_qnn_delegate_live_roi_breakdown` |
| Default QuickSR live path | `C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20251110_output_reuse_default_live_roi` |
| 120s short sustained run | `C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20251110_output_reuse_quicksr_live_roi_120s` |
| Real-camera showcase | `C:\Users\Admin\Videos\RB5 gen2\real_camera_showcase\20251110_045328_minimal_real_camera_set` |
| Tensor-ready boundary | `C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20251110_tensor_ready_live_roi_1280x960` |

## Numbers To Use

| Topic | Number |
| --- | ---: |
| Old live ROI e2e before data-path fix | about `63 / 65ms` p50/p95 |
| Default QuickSR live e2e after output reuse | `19.0 / 24.7ms` p50/p95 |
| Default QuickSR live inference | `1.0 / 1.0ms` p50/p95 |
| 120s sustained e2e drift | `20.0/25.0ms -> 21.0/26.0ms` |
| Real-ESRGAN -> QuickSRNet switch | about `369ms` |
| QuickSRNetSmall W8A8 model size | about `43.7KB` |
| Real-camera set | `8 scenes / 32 images`, `accepted_with_caveats` |

## Route Decision

| Path | Decision |
| --- | --- |
| `QNN + QuickSRNetSmall W8A8` | default live ROI workhorse |
| `QNN + Real-ESRGAN W8A8` | QNN/HTP milestone, comparison, optional post-capture/perceptual path |
| automatic live dual-model routing | not default |
| tensor-ready live path | valid but not promoted |
| Kotlin-only YUV ROI | correct but slower |

## Boundaries

Do not claim:

```text
QuickSRNet is globally better than Real-ESRGAN
automatic routing is product-ready
true zero-copy is implemented
full power/perf-watt is characterized
```

Use the supported claim:

```text
I built and profiled an Android QNN/HTP SR pipeline, identified the true app
bottlenecks, validated model roles with benchmark and real-camera evidence, and
made route decisions from latency, quality, memory, and implementation risk.
```
