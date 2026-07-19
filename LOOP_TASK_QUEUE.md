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
| 8 | zero-copy-probe | blocked_needs_user | True zero-copy feasibility research/probe | AHardwareBuffer/DMA-BUF/QNN tensor-memory path classified with evidence | not viable, blocked, or bounded probe complete |
| 9 | video-temporal-plan | blocked_needs_user | Video/every-N-frame enhancement protocol | evaluation protocol exists before video implementation starts | protocol complete or user input needed |
| 10 | power-perf-watt | done | Real power/perf-watt characterization | current/power evidence exists if making an efficiency claim | hardware/tooling blocked or evidence complete |
| 11 | diff-audit | done | Audit current uncommitted changes and artifact boundaries | explicit source/doc/script files vs generated artifacts are separated | audit complete |
| 12 | commit-boundary-plan | done | Split current work into logical commits | staging paths are explicit and generated artifacts excluded | plan complete |
| 13 | milestone-commit | done | Commit current milestone | oral template authorizes commit/push after closeout assessment | commit complete |

## Current Closeout Task

Current active task: `post-closeout-handoff`.

Host-side tile technical gates are complete. Multi-scene tile evaluation has
been generated and now needs user visual review before promoting one tile model
as the post-capture quality default. Minimal Android app tile entry has been
implemented, build-verified, installed on RB5, and validated with saved output.

Current evidence:

```text
QuickSR:
C:\Users\Admin\Desktop\QC-Development-Board-Project\RB5_SR_lab\results\tile_mvp\20260720_tile_mvp_quicksr_structure_edges

Real-ESRGAN:
C:\Users\Admin\Desktop\QC-Development-Board-Project\RB5_SR_lab\results\tile_mvp\20260720_tile_eval_realesrgan_structure_edges

Android app tile entry:
RB5VisionLab app has a new `整图 Tile` button. It captures a 512x512 still ROI,
runs 16 QNN tiles, stitches a 2048x2048 result, and saves input, bicubic, tile
SR, and comparison PNGs to `/sdcard/Pictures/RB5VisionLab`. Short press runs
the selected tile model; long press switches QuickSR / Real-ESRGAN. Intent
automation supports `--es tile_model QUICKSR` and `--es tile_model REALESRGAN`.
Verification so far: `:app:assembleDebug` passes; device runs saved
`TILE_STILL_20251110_091057_QUICKSR_QNN_*` and
`TILE_STILL_20251110_100948_REALESRGAN_QNN_*`. Pulled evidence is under
`RB5_SR_lab\results\tile_app\20251110_091057_quicksr_qnn` and
`RB5_SR_lab\results\tile_app\20251110_100948_realesrgan_qnn`.

Same-frame app tile compare:
The old app-side QuickSR/Real-ESRGAN comparison was invalid for quality because
the two modes used different camera inputs. This has been fixed with
`--ez run_tile_compare true`, which runs QuickSR and Real-ESRGAN on the same
512x512 frame. Device evidence was saved as `TILE_COMPARE_20251110_102602_QNN_*`
and pulled to
`RB5_SR_lab\results\tile_app\20251110_102602_same_frame_compare`, including a
`review_pack` with 1x/2x/4x crops and difference heatmaps.

Multi-scene tile eval:
C:\Users\Admin\Desktop\QC-Development-Board-Project\RB5_SR_lab\results\tile_eval\20260720_tile_eval_smoke_quicksr_vs_realesrgan

Zoom-friendly review packs:
C:\Users\Admin\Desktop\QC-Development-Board-Project\RB5_SR_lab\results\tile_eval\20260720_tile_eval_smoke_quicksr_vs_realesrgan\review_packs

Use `center_crop_1x.png`, `center_crop_2x.png`, `detail_patch_4x.png`, and
`difference_heatmaps.png` per case. Low-light color statistics confirm QuickSR
is brighter than Real-ESRGAN on `low_light_div2k0852`; other categories have
small color/luma deltas. Do not decide tile model quality from shrunken overview
thumbnails alone.

User visual review result:
Real-ESRGAN tile is accepted as better than QuickSR tile across the reviewed
six smoke scenes. The user saw higher sharpness without obvious fake texture or
oversharpening. Continue by making Android app tile support Real-ESRGAN mode.

Tile route decision:
Real-ESRGAN tile is the post-capture quality-priority route. QuickSR tile stays
as the speed/conservative baseline. App same-frame comparison evidence confirms
the fair comparison path: `run_tile_compare` saves input, bicubic, QuickSR, and
Real-ESRGAN outputs from the same 512x512 frame.

Next non-visual task:
Start `d8-config` planning and feasibility check while tile visual review is
pending. Do not claim a tile quality winner until the overview images are
reviewed.

D8-config feasibility:
Real-ESRGAN export exposes `--num-calibration-samples` and `--quantize-options`.
Confirmed safe candidate variables are calibration sample count and
`--range_scheme min_max`. No explicit Real-ESRGAN export support was found for
per-channel/per-tensor switching. Running the comparison needs user approval
because it submits Qualcomm AI Hub remote quantize/export jobs using the local
AI Hub configuration.
Prompt policy: do not create prompt Markdown files unless the user asks. Output
Qualcomm/internal-AI prompts directly in chat.
D8-config first run:
AI Hub TFLite W8A8 exports completed for `calib10_default` and
`calib10_minmax`. Host smoke comparison is under
`RB5_SR_lab\results\d8_config_compare\20260720_d8_config_smoke`. `minmax`
performed worse on average; `calib10_default` was very close to current app
W8A8, so there is no evidence-based reason to replace the app model yet.

AIMET trigger:
Current W8A8-vs-float evidence does not show a blocking quantization-only
failure. Keep AIMET as `deferred_with_trigger`; do not start CLE/Bias Correction
until a concrete failure crop shows float preserving detail that W8A8 loses.

Eval diagnostic:
Low-cost tile diagnostics were added for the smoke tile comparison under
`RB5_SR_lab\results\tile_eval\20260720_tile_eval_smoke_quicksr_vs_realesrgan`.
They support the observation that Real-ESRGAN is sharper, but remain diagnostic
only and do not replace visual review.

Zero-copy:
Existing native/tensor-ready probes are valid but repeated live did not beat
the default path on p50. Local and public references did not provide a direct
CameraX AHardwareBuffer/DMA-BUF -> QNN TFLite Delegate input path. This needs
Qualcomm/internal confirmation before deeper implementation.
Prompt policy: output Qualcomm/internal-AI prompts directly in chat.

Video/temporal:
The current app has no CameraX VideoCapture/Recorder path. Adding video changes
product scope; next step needs a concrete choice between recording real video,
processing every N ImageAnalysis frames, or only writing an evaluation protocol.

Power/perf-watt:
`dumpsys battery` exposes voltage/temperature/level, but ordinary adb shell is
denied access to `/sys/class/power_supply/battery/*`, including `current_now`.
Without current or an external power meter, the project cannot claim real
perf/watt. Next step needs user approval for rooted device reads or external
measurement hardware.
User approved root read. `adb root` works; root shell can read
`current_now` and `voltage_now`. `power_now` is 0, so power is computed from
absolute current times voltage. Smoke outputs:
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
The 2026-07-20 oral template asked for project closeout, high-signal context
maintenance, and commit/push if the current progress was suitable. Diff audit
and logical commits are complete: keep generated outputs under `RB5_SR_lab\results` and
`RB5_SR_lab\export_assets` out of git. Candidate tracked files are entrypoint /
loop docs, app code, layout, tools README, token policy, queue, full-scope
ledger, and host scripts.
Diff audit:
Generated outputs under `RB5_SR_lab\results` are ignored. D8 exported model
assets are ignored by `RB5_SR_lab/export_assets/d8_config_*/`. Candidate tracked
paths are `.gitignore`, `PROJECT_ENTRYPOINTS.md`, `HARNESS_LOOP_ENGINEERING.md`,
`PROJECT_FULL_SCOPE_LEDGER.md`, `TOKEN_DISCLOSURE_POLICY.md`,
`LOOP_TASK_QUEUE.md`, `tools/README.md`,
`tools/rb5_progressive_onboarding.ps1`, Android app tile changes, and host
scripts under `RB5_SR_lab`.

Suggested logical commits for this closeout:
1. `docs(loop): add progressive RB5 loop onboarding`
2. `feat(android): add post-capture tile SR comparison`
3. `test(sr): add tile and quantization comparison scripts`
4. `test(power): add RB5 battery power probe`
5. `chore(repo): ignore generated D8 config assets`
```
