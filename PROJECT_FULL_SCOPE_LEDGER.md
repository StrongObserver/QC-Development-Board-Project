# RB5 Gen2 Full Scope Ledger

Updated: 2026-07-20

## Purpose

This ledger prevents a recurring loop failure:

```text
Stable milestone != whole project complete.
```

Every original project-design item must stay visible until it is completed or
blocked with concrete evidence. Hard or time-consuming work can be ordered
later, but it must not disappear.

## State Values

| state | meaning |
| --- | --- |
| `done` | implemented and verified with evidence |
| `in_progress` | currently being executed |
| `queued` | required but not the immediate step |
| `blocked_needs_user` | needs a concrete user action/device/access |
| `blocked_technical` | attempted and blocked by a concrete technical issue |
| `not_viable_with_evidence` | proven not viable under current constraints |

## Original Design Coverage

| id | original design item | state | current evidence / blocker | next action |
| --- | --- | --- | --- | --- |
| A1 | Offline image enhancement | done | Android fixed samples and host inference paths work | Maintain only |
| A2 | CameraX center ROI live enhancement | done | Default live path is QNN + QuickSRNetSmall; `20251110_output_reuse_default_live_roi` | Maintain only |
| D7 | App CPU / GPU / NNAPI backend comparison | done | CPU ~600ms, GPU ~126-148ms, NNAPI no gain | Keep as baseline evidence |
| E10-A | QNN/HTP Path A local runner | done | `qnn-net-run --retrieve_context` smoke/full benchmark exists | Maintain only |
| E10-B | QNN/HTP Android app path | done | QNN TFLite Delegate + HTP app path works with skel lib | Maintain only |
| D8 | W8A8 quantized baseline | done | Real-ESRGAN W8A8 TFLite and QNN paths; QuickSRNetSmall W8A8 default live path | Maintain only |
| D8-config | per-channel/per-tensor/calibration comparison | done | First-pass AI Hub comparison completed for current app W8A8, calib10 default, and calib10 minmax; minmax is worse and calib10 default is close to current app W8A8 | Do not replace app model without stronger evidence |
| AIMET-CLE | AIMET CLE or Bias Correction | blocked_needs_user | Trigger check completed; no clear W8A8-vs-float showcase regression was found | Reopen only when human review or a benchmark finds a concrete W8A8-vs-float failure crop |
| AIMET-advanced | AdaRound / QAT | blocked_needs_user | High cost and no current quantization failure trigger | Reopen only after CLE/Bias is insufficient on a real failure crop |
| model-curve | Real-ESRGAN vs QuickSRNet quality/latency/size/power curve | done | Quality/latency/size evidence exists; board-level battery-node power smoke exists for idle, preview, live QuickSR, QuickSR tile, and Real-ESRGAN tile | Treat power as board-level estimate, not external-meter evidence |
| eval-fixed | fixed scenario benchmark | done | `RB5_SR_Benchmark_v1`, full 24-case, real-camera 8-scene set | Maintain only |
| eval-perceptual | LPIPS / NIQE / OCR diagnostic metrics | blocked_needs_user | Low-cost tile diagnostics exist; LPIPS/NIQE/OCR remain uncalibrated diagnostic-only tools; no current visual/metric conflict or text-readability claim requires them | Reopen when visual review conflicts with PSNR/SSIM or a text/OCR claim is needed |
| native-preprocess | native YUV ROI / RGB preprocessing | in_progress | Kotlin YUV correct but slow; native ROI faster single-frame; tensor-ready repeated live not default; output UINT8 bulk-copy now reduces postprocess to about 1/1ms in app e2e smoke | Future attempts should target deeper tensor-ready/YUV ROI only as isolated experiments |
| buffer-reuse | buffer / object reuse | done | TFLite buffers, pixel arrays, sample-copy reduction, output Bitmap reuse, and reusable UINT8 output byte buffer | Maintain only |
| zero-copy | true zero-copy CameraX -> NPU | in_progress | Phase 1 shared-memory tensor probe passed: TFLite C API interpreter uses QNN Delegate, input/output custom allocations are bound to shared buffers, 50 invokes average about 1.05ms; this is still not CameraX buffer binding | Decide whether to integrate a bounded C API e2e comparison path or stop at probe evidence |
| mixed-precision | w8a16 mixed precision | blocked_needs_user | No current W8A8 quality blocker or layer-level sensitivity evidence | Reopen only with quantization failure evidence |
| temporal | frame skip / temporal reuse / double buffering | done | `sr_every_n=3` ImageAnalysis smoke is implemented and validated; effective enhanced FPS is about 9.4-9.9, while each enhanced frame remains about 21/25ms e2e | Treat as a cadence/product boundary; do not claim lower per-frame latency |
| tile | post-capture whole-image tile enhancement | done | Host MVP, host multi-scene comparison, and Android app tile entry are implemented; same-frame QuickSR vs Real-ESRGAN app evidence exists | Real-ESRGAN tile is the quality-priority post-capture route; QuickSR tile stays speed/conservative baseline |
| video | video every-N-frame enhancement | blocked_needs_user | No CameraX VideoCapture/Recorder path yet; every-N ImageAnalysis smoke now exists as pre-video evidence | Full VideoCapture waits for explicit demo need |
| power | sustained power/perf-watt | done | Rooted battery-node current/voltage reads work; core smoke estimates exist | Use as board-level estimate only; do not claim external-meter precision |
| showcase | resume / README / demo / interview package | done | README, SHOWCASE_INDEX, DEMO_RUNBOOK, INTERVIEW_TALK_TRACK, resume draft | Maintain only |

## Current Required Next Unfinished Items

The current checkpoint is strong enough for showcase, but the full original
design still has unfinished required lanes:

1. `AIMET-CLE` / `mixed-precision`: blocked until a concrete W8A8-vs-float
   failure crop appears.
2. `eval-perceptual`: blocked until visual review conflicts with PSNR/SSIM, or a
   text/OCR claim needs calibrated diagnostic evidence.
3. `zero-copy`: Java/Kotlin route remains blocked, but Phase 1 C API tensor
   binding and invoke timing are validated. Next decision is whether to build a
   bounded C API e2e comparison path around CameraX/ROI/output, while keeping
   rollback to `rb5-stable-20260720`.
4. `video`: full CameraX VideoCapture/Recorder still needs explicit demo/product
   need from the user; every-N ImageAnalysis is already classified as cadence
   evidence, not a latency win.

## Loop Rule

Future agents must choose the next task from this ledger unless the user's live
oral template gives a more specific P0 instruction. A completed showcase package
is not permission to stop the project or avoid the remaining design items.
