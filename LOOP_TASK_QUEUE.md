# RB5 Runtime Loop Task Queue

Updated: 2026-07-23

## Purpose

This queue turns the accepted QCS8550 Runtime project plan into a long-running
loop. The current project is not primarily a CameraX image-enhancement app; it
is an on-device AI Runtime / model deployment / quantization / heterogeneous
performance optimization project. SR models are representative workloads.

The loop should continue until every task below is `done`,
`blocked_needs_user`, `blocked_technical`, or `not_viable_with_evidence`.
Do not exit only because one milestone is stable or showcase-ready.

The user's current oral template can override this queue for the current turn.

## Current Framing

The current accepted design is:

```text
QCS8550 端侧 AI 推理 Runtime 与异构性能优化
```

Harness/Loop work should therefore prioritize:

```text
QNN/HTP deployment evidence
CPU/GPU/NNAPI/QNN backend comparison
runtime init, skel loading, transport, and profile boundaries
data-path profiling and direct-YUV/native tensor evidence
cold/warm init, memory, sustained latency, and board-level power boundaries
benchmark/result tables and interview-ready explanation
```

Tile, real-camera showcase, and visual review remain useful evidence, but they
are supporting workload/evaluation material rather than the project center.

## Exit Conditions

The loop may stop only when:

```text
1. all queued tasks have reached a terminal state;
2. a task needs a concrete user action or device action;
3. a task is technically blocked with evidence;
4. the user redirects or pauses the loop.
```

If stopped for condition 2 or 3, report in chat:

```text
- what happened;
- what was already tried;
- why it is not solvable locally right now;
- exactly what the user should do next.
```

## Problem-Solving Order

When a task hits a blocker:

```text
1. Try to solve it locally using existing project code and docs.
2. Search the local external research layer:
   knowledge_base/external_research
3. If needed, use targeted web/official/open-source research.
4. If still blocked, prepare a focused prompt for company-internal AI or
   Qualcomm AI. Use English for Qualcomm AI prompts.
```

Technical route choices must follow evidence. Prefer the route closest to the
original project design unless there is concrete evidence that it cannot work.

## Closed Historical Queue

| order | id | state | task | success metric | stop trigger |
| --- | --- | --- | --- | --- | --- |
| 1 | token-disclosure | done | Reduce onboarding token cost with progressive disclosure | entrypoint and loop docs tell future agents what to read lazily | docs updated and checked |
| 2 | tile-mvp | done | Post-capture whole-image tile enhancement MVP | one still image can be tiled, SR processed, stitched, and saved with no obvious seam/geometry error | implementation blocked or evidence complete |
| 3 | tile-eval | done | Tile quality/performance evaluation | input/bicubic/SR/contact sheet plus timing and memory notes | human review needed or result accepted |
| 4 | tile-app | done | Minimal Android app tile entry | app can trigger post-capture tile path without regressing live ROI | device/manual action needed or app evidence complete |
| 5 | d8-config | done | Quantization configuration comparison | at least two quantization/calibration variants compared on fixed inputs | toolchain blocked or comparison complete |
| 6 | aimet-trigger | done | AIMET CLE/Bias Correction trigger check | exact W8A8-vs-float failure crop found, or AIMET remains deferred_with_trigger | recovery feasibility complete or toolchain blocked with evidence |
| 7 | eval-diagnostic | done | LPIPS/NIQE/OCR diagnostic metrics | TextZoom OCR mini diagnostic script and sample run exist; metric remains diagnostic-only | calibrated enough for diagnostic use or deferred |
| 8 | zero-copy-probe | done | True zero-copy feasibility research/probe | Phase 2 normal tensor vs shared custom allocation compare passed with matching checksum | timing comparison complete or blocked with evidence |
| 9 | video-temporal-plan | done | Video/every-N-frame enhancement protocol | every-N ImageAnalysis smoke is classified as cadence evidence; low-cost screenrecord demo path exists | full VideoCapture needs explicit demo/product need |
| 10 | power-perf-watt | done | Real power/perf-watt characterization | current/power evidence exists if making an efficiency claim | hardware/tooling blocked or evidence complete |
| 11 | diff-audit | done | Audit current uncommitted changes and artifact boundaries | explicit source/doc/script files vs generated artifacts are separated | audit complete |
| 12 | commit-boundary-plan | done | Split current work into logical commits | staging paths are explicit and generated artifacts excluded | plan complete |
| 13 | milestone-commit | done | Commit current milestone | oral template authorizes commit/push after closeout assessment | commit complete |

## Current Runtime Reframe Queue

| order | id | state | task | success metric | stop trigger |
| --- | --- | --- | --- | --- | --- |
| 1 | runtime-harness-reframe | in_progress | Reframe Harness/Loop text around QCS8550 Runtime and heterogeneous optimization | entrypoint, queue, ledger, route/showcase/interview docs no longer center the project as only image enhancement | text sweep complete |
| 2 | final-benchmark-table | done | Consolidate final benchmark/result table | one compact table separates AI Hub profile, qnn-net-run accelerator, app e2e, cold/warm init, memory, and power boundaries | `FINAL_BENCHMARK_TABLE.md` generated |
| 3 | sustained-p99-thermal | done | Optional sustained app runtime run | current native-staging 20-minute direct-YUV run has 35719 frames, e2e p50/p95/p99 `8/9/9ms`, and board-level battery-node power mean about `4.96W` with temp `24.0C -> 24.0C` | maintain as app timing plus board-level estimate only |
| 4 | init-memory-table | done | Cold/warm init, model switching, and sticky memory summary | Resource probes record Real/Quick init, switch cost, PSS deltas, and sticky memory boundary | evidence complete |
| 5 | perfetto-qnn-timeline | done | Optional Perfetto/QNN timing timeline | app data path timeline can explain CameraX/native/tensor/QNN/display costs | `20260723_perfetto_direct_yuv_trace_smoke_v4` collected a non-empty trace with live frame coverage |
| 6 | aimet-remote-decision | done | Decide whether to submit remote AI Hub CLE W8A8 export/profile jobs | user approved; remote AI Hub export/profile succeeded and local RB5 full 24-case comparison is complete | keep as evidence; do not replace app model |
| 7 | true-zerocopy-scope | done | Scope larger CameraX-to-QNN buffer registration experiment | `ZERO_COPY_SCOPE_PLAN.md` defines staged goals, metrics, budget, rollback, and ROI beyond the 8/9/9ms native-staging baseline | reopen only for a larger data-path project |
| 8 | videocapture-scope | done | Decide whether full CameraX VideoCapture/Recorder is needed | `DEMO_RUNBOOK.md` records screenrecord Demo Mode as the current high-ROI demo; full VideoCapture remains non-mainline | reopen only if a real product/video pipeline is required |

## Current Closeout Task

Current active task: `runtime-harness-reframe`.

Current open work is no longer tile, D8-config, output postprocess, app e2e
schema bring-up, every-N smoke, invoke-level shared-memory probing, or
direct-YUV default promotion. Those lanes have evidence and should be treated as
closed unless a regression appears. The new open work is to make the Harness and
Loop system match the refined project design: Runtime / deployment / profiling /
heterogeneous optimization.

Direct PlaneProxy ByteBuffer -> native ROI/RGB is now the compiled default
QNN/QuickSR live path. QNN shared-memory Phase 2 has validated normal-vs-shared
tensor comparison with matching output checksum. AIMET-Torch CLE is locally
feasible, but a deployable CLE W8A8 TFLite/QNN artifact still requires an
explicit remote AI Hub export decision. TextZoom/OCR and RealSR are diagnostic
or lifecycle evidence, not the project center. Demo Mode wide-FoV video capture
is validated through `adb screenrecord` on the live ROI UI; it is not a true
VideoCapture SR pipeline.

After the RKNN-inspired Runtime loop and follow-up review, the default live path
remains unchanged, but the useful evidence-tooling changes are restored:
stream-log live collection, P99 live runner metrics, and slim live QNN profile
logging. These are collection/log-volume fixes, not model/runtime acceleration
claims. The current remaining Runtime lanes are the Runtime text sweep, optional
Perfetto/QNN timing, a larger CameraX-to-QNN buffer-registration experiment, or
full CameraX VideoCapture/Recorder product work.

RKNN-inspired evidence preserved as ignored/local artifacts:

```text
RKNN idea transfer assessment:
C:\Users\Admin\Desktop\QC-Development-Board-Project\RB5_SR_lab\results\runtime_exploration\20260723_rknn_idea_transfer_assessment

5-minute default direct-YUV stream-log run:
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260723_loop_p2_default_streamlog_5min

5-minute board-level direct-YUV power run:
C:\Users\Admin\Desktop\QC-Development-Board-Project\RB5_SR_lab\results\power_probe\20260723_loop_p3_power_live_direct_yuv_5min

Current APK resource probe:
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260723_loop_p5_resource_probe_current_apk

100-run fixed-sample steady resource probe:
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260723_loop_p6_resource_probe_steady100

Runtime loop summary:
C:\Users\Admin\Desktop\QC-Development-Board-Project\RB5_SR_lab\results\runtime_exploration\20260723_runtime_loop_p0_p16_summary
```

Current evidence to preserve:

```text
Optimized default live ROI with UINT8 bulk input and shadow metrics:
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260721_loop_p4_strategy_shadow_live

Direct-YUV default live ROI:
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260722_app_default_direct_yuv_live_roi_120f

Direct-YUV sustained live ROI:
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260722_direct_yuv_live_roi_120s_sustained

Direct-YUV same-frame correctness probe:
C:\Users\Admin\Desktop\QC-Development-Board-Project\RB5_SR_lab\results\direct_yuv_roi_probe\20260722_direct_yuv_roi_probe

Bulk input comparison:
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260721_loop_p2_bulk_input_compare

QNN Delegate profile fixed sample:
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260721_loop_p3_qnn_profile_fixed_sample_v2

AIMET-Torch CLE probe:
C:\Users\Admin\Desktop\QC-Development-Board-Project\RB5_SR_lab\results\aimet_torch_cle_probe\20260721_realesrgan128_flower

AIMET-Torch QuantSim compare:
C:\Users\Admin\Desktop\QC-Development-Board-Project\RB5_SR_lab\results\aimet_torch_quantsim_compare\20260721_realesrgan128_fixed_slice

AIMET CLE QAI Hub Models local export checkpoint:
C:\Users\Admin\Desktop\QC-Development-Board-Project\RB5_SR_lab\results\aimet_deployability\20260722_aimet_cle_export_checkpoint

Mixed-precision support probe:
C:\Users\Admin\Desktop\QC-Development-Board-Project\RB5_SR_lab\results\mixed_precision_probe\20260722_realesrgan_w8a16_support

QuickSRNet size/latency/quality curve:
C:\Users\Admin\Desktop\QC-Development-Board-Project\RB5_SR_lab\results\quicksrnet_curve\20260721_quicksrnet_sml_curve

Model route decision:
C:\Users\Admin\Desktop\QC-Development-Board-Project\MODEL_ROUTE_DECISION.md

Direct ImageProxy ByteBuffer probe:
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260721_loop_p3_direct_buffer_probe_v2

QNN Delegate profile decode attempt:
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260721_loop_p4_qnn_profile_decode_attempt

Default live ROI recheck:
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260720_loop_p0_1_default_live_roi_recheck

YUV ROI correctness recheck:
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260720_loop_p0_2_yuv_roi_recheck

Native-rotated tensor correctness:
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260720_loop_p0_3_tensor_correctness_rotated_native

Native-rotated tensor live timing:
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260720_loop_p0_3_tensor_rotated_native_v2

App path comparison:
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260720_loop_p0_4_app_path_compare

Latest app e2e output-path smoke:
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260720_app_e2e_schema_output_reuse_120f

Latest app e2e 60s sustained smoke:
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260720_app_e2e_schema_output_reuse_60s

Every-N temporal smoke:
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260720_every_n3_live_roi_60s_final

QNN shared-memory Phase 0:
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260720_qnn_shared_memory_phase0

QNN shared-memory Phase 1:
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260720_qnn_shared_memory_phase1

QNN shared-memory Phase 2:
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260720_qnn_shared_memory_phase2_compare

AIMET trigger crop search:
C:\Users\Admin\Desktop\QC-Development-Board-Project\RB5_SR_lab\results\aimet_trigger_search\20260720_full_v2_patch96

TextZoom OCR mini diagnostic:
C:\Users\Admin\Desktop\QC-Development-Board-Project\RB5_SR_lab\results\textzoom_ocr\20260720_textzoom_ocr_mini_v2

RealSR mini lifecycle sanity:
C:\Users\Admin\Desktop\QC-Development-Board-Project\evalhub_data\derived_runs\evalhub_realsr_mini_10cases_20260720_v2

Demo Mode video demo:
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260720_demo_mode_wide_clear_20s

Demo Mode relation evidence:
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260720_demo_relation_aligned_v3\demo_relation

App fixed-sample replay:
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260720_app_fixed_replay_quicksr_3assets

AIMET toolchain decision:
C:\Users\Admin\Desktop\QC-Development-Board-Project\RB5_SR_lab\results\p1_aimet_toolchain_decision_20260720
```

Current route boundaries:

```text
0a. Current default QNN/QuickSR live ROI now uses the direct-YUV tensor path:
   CameraX PlaneProxy direct ByteBuffer -> native ROI/RGB -> UINT8 NHWC bulk
   input -> QNN Delegate. Latest compiled default e2e p50/p95/p99 is 8/9/9ms.
   This is a measured data-path win, not true CameraX buffer -> QNN input
   zero-copy.
0b. AIMET-CLE is no longer purely blocked: PyTorch FP source and AIMET-Torch CLE
   are locally validated. QuantSim shows small average simulated INT8
   improvement (+0.115dB) but mixed results per case. The CLE state dict can be
   wrapped into the checkpoint shape expected by Qualcomm AI Hub Models and
   serialized to ONNX locally. A deployable CLE W8A8 TFLite/QNN asset still
   needs explicit user approval for remote AI Hub quantize/compile/profile jobs.
0c. QNN Delegate profiling is accessible from the Android app: fixed sample
   replay collected `profileBytes=904`. The profile payload is raw delegate bytes
   and is not decoded per op yet.
0d. Strategy shadow mode is active in logs only. It records luma, simple
   sharpness, motion MAD, and a shadow decision; it does not actually skip frames
   or switch models.
0e. QuickSRNet medium/large host curve exists. Larger models need human visual
   review of contact sheets before any Android packaging or QNN app validation.
0f. Human review found QuickSRNetSmall is at least as good as Medium/Large for
   the checked text/low-light sheets; Medium appears more yellow and has no
   clear visual gain. Keep Small as the live workhorse and do not add
   Medium/Large to Android by default.
0g. Direct ImageProxy ByteBuffer probe shows Y/U/V plane buffers are direct and
   JNI `GetDirectBufferAddress` returns non-null addresses. This supports a
   future JNI direct-plane read experiment, but it is still not QNN input
   zero-copy.
0h. qnn-profile-viewer rejects the raw Java QNN Delegate profile buffer as a
   corrupted flatbuffer stream. A best-effort diagnostic parser extracts 10
   readable events, but this is not official per-op decoding.
0. The default live ROI path remains the mainline after the P0 recheck:
   default Bitmap live ROI e2e p50/p95 is 14/18ms, while native-rotated tensor
   live ROI is 14/20ms. Native YUV ROI correctness is good enough for probes
   (`nativeMad=0.39`), and native rotation correctness passes, but this does not
   justify replacing the default path.
1. Output postprocess is no longer the next target unless a regression appears.
2. every-N ImageAnalysis is a completed cadence/product boundary, not a per-frame
   latency win: everyN=3 gives about 9.9 effective enhanced FPS, while each
   enhanced frame remains about 22/25ms e2e.
3. QNN shared memory is a C++ delegate/native probe lane:
   TfLiteQnnDelegateAllocCustomMem + SetCustomAllocationForTensor, or
   SampleAppSharedBuffer with libcdsprpc/rpcmem/QnnMem_register. The current
   Java/Kotlin QnnDelegate wrapper does not expose the custom allocation API;
   `javap` on `qtld-release.aar` confirms only backend/skel/perf/profile/skip
   options are exposed. Phase 0 passed alloc/free; Phase 1 passed tensor binding;
   Phase 2 passed normal-vs-shared tensor comparison with matching checksum and
   about -48us shared invoke average delta. This is still not CameraX buffer
   binding or true zero-copy.
4. Full CameraX VideoCapture/Recorder remains a separate product/demo decision.
5. Prompts for Qualcomm/internal AI must be output directly in chat, not written
   to Markdown files, unless the user explicitly asks for a file.
6. TextZoom/OCR is diagnostic-only: the mini run showed very low OCR similarity
   even on HR references, so it can flag text-readability questions but cannot
   replace human visual review.
7. RealSR mini review is host LiteRT sanity only: it covers Canon/Nikon 5+5
   cases and shows real-degradation metrics can disagree with sharpness, but it
   is not RB5 QNN/app evidence and cannot replace the 24-case main gate.
8. Demo Mode video is a screenrecorded app demo: it hides the old control-heavy
   UI, shows a wide clear camera preview full-screen in landscape, keeps a
   compact QNN/SR performance overlay, and avoids stretching the 128->512 SR
   output as the main visual. The default debug UI still has all buttons, and
   tapping the overlay in Demo Mode temporarily shows/hides the original control
   bar. The display-aligned relation sheet preserves wide preview / 128 input /
   512 SR output evidence so the display boundary is explainable, while raw
   model input/SR PNGs remain available. It still does not prove temporal
   consistency or true per-frame video SR.
9. App fixed-sample replay is now a small regression layer: it runs fixed assets
   through the Android QNN path, pulls input/baseline/SR outputs, and writes an
   app_e2e row. It supports repeatability but is not live-camera quality proof.
10. AIMET remote export is blocked_needs_user: local CLE deployability is
   proven, but producing a CLE W8A8 TFLite/QNN replacement would submit remote
   Qualcomm AI Hub jobs and needs explicit user approval.
```

Power/perf-watt:
`dumpsys battery` exposes voltage/temperature/level, but ordinary adb shell is
denied access to `/sys/class/power_supply/battery/*`, including `current_now`.
User approved root read. `adb root` works; root shell can read `current_now`
and `voltage_now`. `power_now` is 0, so power is computed from absolute current
times voltage. This supports board-level power/energy estimates only; it must
not be reported as external-meter perf/watt precision. Smoke outputs:
`RB5_SR_lab\results\power_probe\20260720_power_idle_smoke`
and
`RB5_SR_lab\results\power_probe\20260720_power_live_quicksr_smoke`.
Additional smoke outputs:
`RB5_SR_lab\results\power_probe\20260720_power_camera_preview_smoke`,
`RB5_SR_lab\results\power_probe\20260720_power_tile_realesrgan_once_energy`,
and `RB5_SR_lab\run_power_probe.py`. Real-ESRGAN tile single-run smoke produced
about 9.66 W mean board power over about 3.2 s and about 31.4 J board energy.
This is battery-node board-level evidence, not external power-meter evidence.
Power suite output:
`RB5_SR_lab\results\power_probe\20260720_power_suite_core_smoke\suite_summary.csv`.
Smoke results: idle about 5.07 W; camera preview about 5.92 W; live QuickSR
about 6.98 W; QuickSR tile once about 29.8 J; Real-ESRGAN tile once about
31.1 J. This is battery-node board-level evidence, not external power-meter
evidence.

Current source-control task:
The app e2e schema export, UINT8 output bulk-copy, every-N ImageAnalysis smoke,
shared-memory feasibility classification, Demo Mode relation fix, app fixed
replay, AIMET feasibility evidence, and related handoff updates have been
reviewed, verified, pushed, and sealed. Keep generated evidence under
`RB5_SR_lab\results` and `evalhub_data` out of git.
```

2026-07-20 app e2e / output-path follow-up:

```text
App e2e schema output:
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260720_app_e2e_schema_output_reuse_120f\app_e2e_log.csv
C:\Users\Admin\Desktop\QC-Development-Board-Project\evalhub_data\derived\app_e2e\20260720_app_e2e_schema_output_reuse_120f\app_e2e_log.csv

60s sustained schema output:
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260720_app_e2e_schema_output_reuse_60s\app_e2e_log.csv
C:\Users\Admin\Desktop\QC-Development-Board-Project\evalhub_data\derived\app_e2e\20260720_app_e2e_schema_output_reuse_60s\app_e2e_log.csv
```

Current result:

```text
`RB5_SR_lab\run_app_live_roi_benchmark.py` and
`RB5_SR_lab\run_app_sustained_live_roi.py` now emit EvalHub-compatible
`app_e2e_log.csv` rows and mirror them to ignored `evalhub_data\derived\app_e2e`.
`SuperResolver` now bulk-copies UINT8 TFLite output into a reusable byte array
before ARGB conversion.
120-frame default app live ROI smoke: postprocess 1/1ms, e2e 15/19ms.
60s sustained QuickSR smoke: 1763 frames, e2e first/last 20% 15/20ms -> 16/21ms,
battery temperature coarse signal 24.0C -> 24.0C.
```

Boundary:

```text
This is app timing and schema evidence, not visual quality evidence and not true
zero-copy. Do not reopen output postprocess as the next task unless a regression
appears. AIMET trigger search has found candidate crops; the next step is
toolchain feasibility for CLE/Bias Correction. Perceptual metrics only run when
their trigger conditions appear; full VideoCapture only runs when a demo or
product need is explicit.
Prompts for Qualcomm/internal AI must be output directly in chat, not written to
Markdown files, unless the user explicitly asks for a file.
```
