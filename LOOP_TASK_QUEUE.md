# RB5 Loop Task Queue

Updated: 2026-07-20

## Purpose

This queue turns the accepted project plan into a long-running loop.

The loop should continue until every task below is `done`,
`blocked_needs_user`, `blocked_technical`, or `not_viable_with_evidence`.
Do not exit only because one milestone is stable or showcase-ready.

The user's current oral template can override this queue for the current turn.

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

## Queue

| order | id | state | task | success metric | stop trigger |
| --- | --- | --- | --- | --- | --- |
| 1 | token-disclosure | done | Reduce onboarding token cost with progressive disclosure | entrypoint and loop docs tell future agents what to read lazily | docs updated and checked |
| 2 | tile-mvp | done | Post-capture whole-image tile enhancement MVP | one still image can be tiled, SR processed, stitched, and saved with no obvious seam/geometry error | implementation blocked or evidence complete |
| 3 | tile-eval | done | Tile quality/performance evaluation | input/bicubic/SR/contact sheet plus timing and memory notes | human review needed or result accepted |
| 4 | tile-app | done | Minimal Android app tile entry | app can trigger post-capture tile path without regressing live ROI | device/manual action needed or app evidence complete |
| 5 | d8-config | done | Quantization configuration comparison | at least two quantization/calibration variants compared on fixed inputs | toolchain blocked or comparison complete |
| 6 | aimet-trigger | done | AIMET CLE/Bias Correction trigger check | exact W8A8-vs-float failure crop found, or AIMET remains deferred_with_trigger | no trigger, blocked, or recovery evidence complete |
| 7 | eval-diagnostic | done | LPIPS/NIQE/OCR diagnostic metrics | diagnostic metrics added only for a visual/metric conflict or text claim | calibrated enough for diagnostic use or deferred |
| 8 | zero-copy-probe | in_progress | True zero-copy feasibility research/probe | Phase 0 QNN Delegate shared-memory alloc/free validated in app process | Phase 1 C++ TFLite tensor-binding probe complete or blocked with evidence |
| 9 | video-temporal-plan | done | Video/every-N-frame enhancement protocol | every-N ImageAnalysis smoke is classified as cadence evidence, not per-frame latency gain | full VideoCapture needs explicit demo/product need |
| 10 | power-perf-watt | done | Real power/perf-watt characterization | current/power evidence exists if making an efficiency claim | hardware/tooling blocked or evidence complete |
| 11 | diff-audit | done | Audit current uncommitted changes and artifact boundaries | explicit source/doc/script files vs generated artifacts are separated | audit complete |
| 12 | commit-boundary-plan | done | Split current work into logical commits | staging paths are explicit and generated artifacts excluded | plan complete |
| 13 | milestone-commit | done | Commit current milestone | oral template authorizes commit/push after closeout assessment | commit complete |

## Current Closeout Task

Current active task: `qnn-shared-memory-phase1-design`.

Current open work is no longer tile, D8-config, output postprocess, app e2e
schema bring-up, or every-N smoke. Those lanes have evidence and should be
treated as closed unless a regression appears. The active technical exploration
is QNN shared-memory Phase 1 after Phase 0 confirmed that the app process can
access `TfLiteQnnDelegateAllocCustomMem` / `TfLiteQnnDelegateFreeCustomMem`.

Current evidence to preserve:

```text
Latest app e2e output-path smoke:
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260720_app_e2e_schema_output_reuse_120f

Latest app e2e 60s sustained smoke:
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260720_app_e2e_schema_output_reuse_60s

Every-N temporal smoke:
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260720_every_n3_live_roi_60s_final

QNN shared-memory Phase 0:
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260720_qnn_shared_memory_phase0
```

Current route boundaries:

```text
1. Output postprocess is no longer the next target unless a regression appears.
2. every-N ImageAnalysis is a completed cadence/product boundary, not a per-frame
   latency win: everyN=3 gives about 9.9 effective enhanced FPS, while each
   enhanced frame remains about 22/25ms e2e.
3. QNN shared memory is a C++ delegate/native probe lane:
   TfLiteQnnDelegateAllocCustomMem + SetCustomAllocationForTensor, or
   SampleAppSharedBuffer with libcdsprpc/rpcmem/QnnMem_register. The current
   Java/Kotlin QnnDelegate wrapper does not expose the custom allocation API;
   `javap` on `qtld-release.aar` confirms only backend/skel/perf/profile/skip
   options are exposed. Phase 0 passed alloc/free for the current model I/O
   sizes; Phase 1 must prove tensor binding and inference.
4. Full CameraX VideoCapture/Recorder remains a separate product/demo decision.
5. Prompts for Qualcomm/internal AI must be output directly in chat, not written
   to Markdown files, unless the user explicitly asks for a file.
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
shared-memory feasibility classification, and related handoff updates have been
reviewed, verified, and split into logical commits. Keep generated evidence
under `RB5_SR_lab\results` and `evalhub_data` out of git.
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
appears. The current active route is C++ shared-memory Phase 1. AIMET/perceptual
metrics only run when their trigger conditions appear; full VideoCapture only
runs when a demo or product need is explicit.
Prompts for Qualcomm/internal AI must be output directly in chat, not written to
Markdown files, unless the user explicitly asks for a file.
```
