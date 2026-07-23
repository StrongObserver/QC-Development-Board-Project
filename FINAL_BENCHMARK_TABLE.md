# RB5 Final Benchmark Table

Updated: 2026-07-23

## Purpose

This table is the compact evidence map for the current project frame:

```text
QCS8550 on-device AI inference Runtime and heterogeneous performance optimization
```

Use it to keep AI Hub profile, local `qnn-net-run`, Android app e2e, resource,
power, and quality evidence separate. Do not collapse these numbers into one
latency claim.

## Runtime Evidence Layers

| Layer | Workload / path | Current result | Supports | Does not support | Evidence |
| --- | --- | --- | --- | --- | --- |
| AI Hub hosted profile | Real-ESRGAN float TFLite on QCS8550 Proxy | `5.9ms`, 74 ops on HTP, 0 CPU fallback | HTP feasibility for the float model | Android app e2e latency | `RB5_SR_lab/export_assets/real_esrgan_general_x4v3-tflite-float` |
| AI Hub hosted profile | Real-ESRGAN W8A8 QNN context on QCS8550 Proxy | p50 `1.778ms`, p95 `1.854ms`, NPU 72, first load about `210ms` | W8A8 QNN/HTP compile/profile feasibility | Local RB5 app latency | `RB5_SR_lab/export_assets/real_esrgan_general_x4v3-qnn-w8a8-qcs8550-20260715` |
| Local RB5 runner | Real-ESRGAN W8A8 QNN context via `qnn-net-run --retrieve_context` | QNN accelerator p50/p95 about `9.75/10.39ms`; NetRun p50/p95 about `13.53/14.13ms` | Local QAIRT runner correctness and accelerator timing | Android UI/data-path timing | `C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\dryrun_full_preflight_check` |
| Android QNN Delegate | W8A8 TFLite fixed sample / live ROI | Fixed sample and live ROI run through QNN TFLite Delegate / HTP; app output aligns with `qnn-net-run` | App-side QNN Delegate milestone | Official per-op app profile | `C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260718_app_qnn_delegate_fixed_live_rb5` |
| App e2e before data-path fix | QNN live ROI with 4000x3000 full-frame Bitmap conversion | `ImageProxy.toBitmap()` p50/p95 about `41/43ms`; app e2e about `63/65ms` | Bottleneck was data movement, not QNN inference | Model-only latency claim | `C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260718_app_qnn_delegate_live_roi_breakdown` |
| App e2e after analysis-size fix | QNN live ROI at 1280x960 | app e2e about `22/25ms`; full-frame conversion about `4/5ms` | Data-path optimization win | True zero-copy | `C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260718_app_qnn_delegate_live_roi_1280x960` |
| App e2e after output/bulk-copy work | QuickSR live ROI app e2e schema smoke | postprocess `1/1ms`; app e2e `15/19ms` | Output path and schema evidence | Visual quality or power evidence | `C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260720_app_e2e_schema_output_reuse_120f` |
| Current compiled default app path | `QNN + QuickSRNetSmall W8A8 + direct-YUV native staging input` | 20-minute app e2e p50/p95/p99 `8/9/9ms`; nativeRgb `4/5/5ms`; QNN inference `2/2/2ms`; skipped frames `0` | Current default live ROI timing and native staging win | True QNN input zero-copy | `C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260723_native_staging_default_live_roi_20min` |
| Sustained app wall-time evidence before native staging | Stream-log default direct-YUV run, 20 minutes | 35742 frames; e2e p50/p95/p99 `11/12/12ms`; QNN inference `2/2/2ms`; skipped frames `0` | Previous sustained app timing baseline | Product-grade thermal/power proof | `C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260723_default_streamlog_20min_current_source` |
| Board-level power estimate | 20-minute live native-staging battery-node probe | mean `4.96W`, min/max `4.65/5.96W`, temp `24.0C -> 24.0C`, energy about `5.95kJ`, about `166.5mJ` per enhanced frame | Board-level power boundary | External-meter perf/watt | `RB5_SR_lab/results/power_probe/20260723_power_live_native_staging_20min`; `PERF_WATT_SUMMARY.md` |
| Resource cost | Current APK init/memory/switch probe | Real init `2.4-2.9s`; Quick init `155/624ms`; Real->Quick switch about `800ms`; close-both PSS still about `+83MB` vs start | Blocks automatic live model switching from being treated as free | Long-run memory stability | `C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260723_loop_p5_resource_probe_current_apk` |
| Fixed replay steady state | 100-run fixed-sample resource probe | Quick total p50/p95/p99 `18/19/19ms`; Real total `18/20/25ms` | Warm fixed-sample regression evidence | Live-camera quality | `C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260723_loop_p6_resource_probe_steady100` |
| Shared-memory probe | QNN Delegate custom allocation Phase 2 500 repeats | normal `1028us`, shared `1004us`, delta about `-24us`, checksum match | Invoke-level shared allocation feasibility | CameraX buffer binding or true zero-copy | `C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260723_rknn_shared_memory_phase2_500` |
| AIMET local feasibility | AIMET-Torch CLE + QuantSim slice | average simulated INT8 PSNR delta about `+0.115dB` | Quantization recovery research evidence | Deployed CLE-W8A8 TFLite/QNN model | `RB5_SR_lab/results/aimet_torch_quantsim_compare/20260721_realesrgan128_fixed_slice` |
| AIMET deployable export | CLE checkpoint -> AI Hub W8A8 QNN context -> RB5 qnn-net-run full 24-case | AI Hub profile succeeds, estimated inference `1.7ms`, NPU 72; local RB5 full run passes 23 pass + 1 conditional; average PSNR delta vs current W8A8 `-0.011dB`, SSIM delta `+0.00180`, QNN accel delta `+208us` | End-to-end AIMET deployability proof and quantization-optimization due diligence | Replacing current Android app model | `RB5_SR_lab/export_assets/real_esrgan_general_x4v3-cle-qnn-w8a8-qcs8550-20260723`; `RB5_SR_lab/results/aimet_deployability/20260723_cle_vs_baseline_full_qnn_compare` |

## Tooling Verification

| Tooling item | Current status | Verification |
| --- | --- | --- |
| Stream-log live runner | restored in `RB5_SR_lab/run_app_live_roi_benchmark.py` | `20260723_streamlog_p99_profileslim_smoke` parsed 80 direct-YUV frames |
| P99 live metrics | restored in `metrics.csv` and `SUMMARY.md` | smoke e2e p50/p95/p99 `10.0/12.0/12.2ms` |
| Live QNN profile log slimming | restored for tensor-live logs | live path emits no full `profileHex=`; fixed-sample diagnostics still can keep full hex |
| 20-minute sustained runner | validated on current source | `20260723_native_staging_default_live_roi_20min` parsed 35719 frames with e2e `8/9/9ms` p50/p95/p99 |
| Perfetto timeline smoke | collected on device | `20260723_perfetto_direct_yuv_trace_smoke_v4` produced a non-empty 222805-byte trace with live frame logcat coverage |
| QNN Delegate profile diagnostic | improved best-effort parser | fixed-sample raw delegate profile is 904 bytes; 10/10 known event strings recognized; `qnn-profile-viewer` still rejects the buffer, so this is diagnostic-only |

## Route Decisions

| Decision | Current state | Evidence reason |
| --- | --- | --- |
| Default live workload | Keep `QuickSRNetSmall W8A8` on QNN Delegate / HTP | small model, conservative quality, app e2e `8/9/9ms` on direct-YUV native staging default path |
| Real-ESRGAN role | Keep as QNN/HTP milestone, comparison baseline, and post-capture route | stronger perceptual path but heavier and more aggressive |
| Automatic dual-model live routing | Not default | switching has visible cold path and sticky memory behavior |
| True CameraX -> QNN input zero-copy | Not implemented; larger experiment only | direct PlaneProxy read and shared allocation probes are not buffer registration |
| True zero-copy staged plan | Scoped, not active mainline | `ZERO_COPY_SCOPE_PLAN.md` defines Stage A-D goals, success metrics, budget, rollback, and ROI |
| Full VideoCapture/Recorder SR | Not current mainline | Demo Mode screenrecord is enough for current showcase; `DEMO_RUNBOOK.md` records reproducible screenrecord workflow and boundaries |
| AIMET CLE deployable export | Done, not promoted | remote AI Hub export/profile and local RB5 full benchmark succeeded, but quality/latency deltas do not justify replacing the current app model |

## Interview-Safe Claims

Use:

```text
Current default direct-YUV native staging Android app live ROI reaches about 8/9/9ms p50/p95/p99 over 20 minutes.
AI Hub, qnn-net-run, and app e2e are separate evidence layers.
The main app win came from data-path work, not from claiming a faster QNN kernel.
```

Do not use:

```text
end-to-end 1.778ms
true zero-copy
full product-grade power/perf-watt
automatic dual-model routing is ready
QuickSRNet is globally better than Real-ESRGAN
app timing proves visual quality
```
