# RB5 Gen2 Showcase Index

Updated: 2026-07-23

## What This Project Proves

```text
PyTorch / TFLite / AI Hub / qnn-net-run / Android app
-> W8A8 workloads
-> QNN TFLite Delegate / Qualcomm HTP
-> direct-YUV native tensor input
-> measured app e2e at about 8 / 9 / 9ms p50/p95/p99 in the current native-staging default run
```

The project is not just a model demo or an image-enhancement app. It shows
Runtime deployment, QNN/HTP profiling, app data-path optimization, evaluation,
route decisions, and bounded performance exploration on an actual RB5 Gen2 /
QCS8550 Android device.

## Read These First

| Purpose | File |
| --- | --- |
| Repository overview | `README.md` |
| Final benchmark table | `FINAL_BENCHMARK_TABLE.md` |
| Zero-copy scope plan | `ZERO_COPY_SCOPE_PLAN.md` |
| Perf/watt summary | `PERF_WATT_SUMMARY.md` |
| Final interview package | `FINAL_INTERVIEW_PACKAGE.md` |
| Evidence package | `SHOWCASE_MATERIALS.md` |
| Interview story | `SHOWCASE_NARRATIVE.md` |
| Oral interview script | `INTERVIEW_ORAL_SCRIPT.md` |
| Resume bullets | `RESUME_PROJECT_DRAFT.md` |
| Demo commands | `DEMO_RUNBOOK.md` |
| Interview Q&A | `INTERVIEW_TALK_TRACK.md` |
| Current handoff | `NEXT_ACTION.md` |

## Minimum Evidence Set

| Claim | Evidence path |
| --- | --- |
| AI Hub QNN context profile | `RB5_SR_lab\export_assets\real_esrgan_general_x4v3-qnn-w8a8-qcs8550-20260715` |
| Local qnn-net-run 24-case profile | `C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\dryrun_full_preflight_check` |
| QNN Delegate app path works | `C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260718_app_qnn_delegate_fixed_live_rb5` |
| Data path was the bottleneck | `C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260718_app_qnn_delegate_live_roi_breakdown` |
| Default direct-YUV QuickSR live path | `C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260722_app_default_direct_yuv_live_roi_120f` |
| Native staging default live path | `C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260723_native_staging_default_live_roi_20min` |
| Perfetto timeline smoke | `C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260723_perfetto_direct_yuv_trace_smoke_v4` |
| Stream-log sustained default live path | `C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260723_default_streamlog_20min_current_source` |
| Latest app e2e schema + output bulk-copy smoke | `C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260720_app_e2e_schema_output_reuse_120f` |
| Latest 60s sustained app e2e smoke | `C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260720_app_e2e_schema_output_reuse_60s` |
| Every-N temporal smoke | `C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260720_every_n3_live_roi_60s_final` |
| Demo Mode wide-clear live ROI video | `C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260720_demo_mode_wide_clear_20s` |
| Demo Mode relation evidence | `C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260720_demo_relation_aligned_v3\demo_relation` |
| App fixed-sample replay | `C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260720_app_fixed_replay_quicksr_3assets` |
| Shared-memory Phase 2 compare | `C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260720_qnn_shared_memory_phase2_compare` |
| 120s short sustained run | `C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20251110_output_reuse_quicksr_live_roi_120s` |
| Real-camera showcase | `C:\Users\Admin\Videos\RB5 gen2\real_camera_showcase\20251110_045328_minimal_real_camera_set` |
| Tensor-ready recheck boundary | `C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260720_recheck_tensor_ready_live_roi_120f` |

## Numbers To Use

| Topic | Number |
| --- | ---: |
| AI Hub QCS8550 W8A8 QNN profile | about `1.778ms` p50, NPU 72 |
| Local qnn-net-run QNN accelerator | about `9.75 / 10.39ms` p50/p95 |
| Old live ROI e2e before data-path fix | about `63 / 65ms` p50/p95 |
| Default QuickSR live e2e after output reuse | `19.0 / 24.7ms` p50/p95 |
| Latest QuickSR live e2e after UINT8 output bulk-copy | `15 / 19ms` p50/p95 |
| Current direct-YUV native staging QuickSR live e2e | `8 / 9 / 9ms` p50/p95/p99 over 20 minutes, 35719 frames |
| Default QuickSR live inference | `1.0 / 1.0ms` p50/p95 |
| App QNN inference in 5-minute stream-log run | `2 / 2 / 2ms` p50/p95/p99 |
| Current board-level live native staging power | about `4.96W` mean over 20 minutes, battery-node estimate |
| Latest QuickSR live postprocess | `1 / 1ms` p50/p95 in 120-frame smoke |
| 120s sustained e2e drift | `20.0/25.0ms -> 21.0/26.0ms` |
| Latest 60s sustained e2e drift | `15.0/20.0ms -> 16.0/21.0ms` |
| Every-N temporal smoke | `everyN=3`, effective enhanced FPS `9.9`, enhanced-frame e2e `22 / 25ms` |
| Demo Mode wide-clear video | 20s MP4, 188 parsed live ROI frames, wide preview display, QNN/SR e2e `23 / 28ms` p50/p95 |
| Demo Mode relation evidence | display-aligned wide preview / model input 128 / QNN SR output 512 in one sheet |
| App fixed-sample replay | 3 fixed assets, 9 pulled images, QNN app total `17-18ms` |
| Shared-memory Phase 2 | checksum match, shared invoke avg `1.056ms` vs normal `1.104ms` |
| Shared-memory Phase 2 500 repeats | checksum match, shared invoke avg `1.004ms` vs normal `1.028ms`; only `24us` avg delta |
| Real-ESRGAN -> QuickSRNet switch | about `369ms` |
| Current Real-ESRGAN -> QuickSRNet switch | about `800ms` on current APK resource probe |
| QuickSRNetSmall W8A8 model size | about `43.7KB` |
| Real-camera set | `8 scenes / 32 images`, `accepted_with_caveats` |

## Route Decision

| Path | Decision |
| --- | --- |
| `QNN + QuickSRNetSmall W8A8 + direct-YUV native tensor input` | default live ROI workhorse |
| `QNN + Real-ESRGAN W8A8` | QNN/HTP milestone, comparison, optional post-capture/perceptual path |
| automatic live dual-model routing | not default |
| tensor-ready live path | valid but not promoted after current recheck |
| Kotlin-only YUV ROI | correct but slower |

## Boundaries

Do not claim:

```text
QuickSRNet is globally better than Real-ESRGAN
automatic routing is product-ready
true zero-copy is implemented
full power/perf-watt is characterized
the screenrecord demo is a true VideoCapture/Recorder SR pipeline
AI Hub profile, qnn-net-run profile, and app e2e are one latency number
```

Use the supported claim:

```text
I built and profiled an Android QNN/HTP Runtime path, separated AI Hub,
qnn-net-run, and app-e2e evidence, identified the true app bottlenecks,
validated workload roles with benchmark and real-camera evidence, and made route
decisions from latency, quality, memory, and implementation risk.
```
