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
| 6 | aimet-trigger | done | AIMET CLE/Bias Correction trigger check | exact W8A8-vs-float failure crop found, or AIMET remains deferred_with_trigger | recovery feasibility complete or toolchain blocked with evidence |
| 7 | eval-diagnostic | done | LPIPS/NIQE/OCR diagnostic metrics | TextZoom OCR mini diagnostic script and sample run exist; metric remains diagnostic-only | calibrated enough for diagnostic use or deferred |
| 8 | zero-copy-probe | done | True zero-copy feasibility research/probe | Phase 2 normal tensor vs shared custom allocation compare passed with matching checksum | timing comparison complete or blocked with evidence |
| 9 | video-temporal-plan | done | Video/every-N-frame enhancement protocol | every-N ImageAnalysis smoke is classified as cadence evidence; low-cost screenrecord demo path exists | full VideoCapture needs explicit demo/product need |
| 10 | power-perf-watt | done | Real power/perf-watt characterization | current/power evidence exists if making an efficiency claim | hardware/tooling blocked or evidence complete |
| 11 | diff-audit | done | Audit current uncommitted changes and artifact boundaries | explicit source/doc/script files vs generated artifacts are separated | audit complete |
| 12 | commit-boundary-plan | done | Split current work into logical commits | staging paths are explicit and generated artifacts excluded | plan complete |
| 13 | milestone-commit | done | Commit current milestone | oral template authorizes commit/push after closeout assessment | commit complete |

## Current Closeout Task

Current active task: `blocked-needs-user-or-new-scope`.

Current open work is no longer tile, D8-config, output postprocess, app e2e
schema bring-up, every-N smoke, or invoke-level shared-memory probing. Those
lanes have evidence and should be treated as closed unless a regression appears.
QNN shared-memory Phase 2 has validated normal-vs-shared tensor comparison with
matching output checksum. AIMET trigger search found
concrete W8A8-vs-float local regression candidates, but native Windows remains
blocked for actual AIMET execution. TextZoom/OCR mini evaluation is now a
diagnostic-only text-fidelity tool, not a hard quality gate. RealSR 10-case
mini review is now a real-degradation lifecycle sanity check, not a replacement
for `RB5_SR_Benchmark_v1`. Demo Mode wide-FoV video capture is now validated
through `adb screenrecord` on the live ROI UI; it is not a true VideoCapture SR
pipeline.

The current loop can stop under exit condition 2/3: remaining progress needs
either user/toolchain input (AIMET on WSL/Linux or supported environment),
human visual review (low-cost MP4 framing/readability), or a new larger scoped
CameraX/native data-path integration experiment.

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
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260720_demo_relation_aligned_v2\demo_relation

App fixed-sample replay:
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260720_app_fixed_replay_quicksr_3assets
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
appears. AIMET trigger search has found candidate crops; the next step is
toolchain feasibility for CLE/Bias Correction. Perceptual metrics only run when
their trigger conditions appear; full VideoCapture only runs when a demo or
product need is explicit.
Prompts for Qualcomm/internal AI must be output directly in chat, not written to
Markdown files, unless the user explicitly asks for a file.
```
