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
| AIMET-CLE | AIMET CLE or Bias Correction | queued | Trigger check completed; no clear W8A8-vs-float showcase regression was found | Need failure crop before execution |
| AIMET-advanced | AdaRound / QAT | queued | High cost and no current trigger | Keep behind CLE/Bias trigger |
| model-curve | Real-ESRGAN vs QuickSRNet quality/latency/size/power curve | done | Quality/latency/size evidence exists; board-level battery-node power smoke exists for idle, preview, live QuickSR, QuickSR tile, and Real-ESRGAN tile | Treat power as board-level estimate, not external-meter evidence |
| eval-fixed | fixed scenario benchmark | done | `RB5_SR_Benchmark_v1`, full 24-case, real-camera 8-scene set | Maintain only |
| eval-perceptual | LPIPS / NIQE / OCR diagnostic metrics | in_progress | Low-cost tile diagnostics exist; LPIPS/NIQE/OCR remain uncalibrated diagnostic-only tools | Use only when visual and PSNR/SSIM conflict |
| native-preprocess | native YUV ROI / RGB preprocessing | in_progress | Kotlin YUV correct but slow; native ROI faster single-frame; tensor-ready repeated live not default; output UINT8 bulk-copy now reduces postprocess to about 1/1ms in app e2e smoke | Future attempts should target deeper tensor-ready/YUV ROI only as isolated experiments |
| buffer-reuse | buffer / object reuse | done | TFLite buffers, pixel arrays, sample-copy reduction, output Bitmap reuse, and reusable UINT8 output byte buffer | Maintain only |
| zero-copy | true zero-copy CameraX -> NPU | blocked_technical | QAIRT docs confirm QNN TFLite Delegate C API shared memory via `TfLiteQnnDelegateAllocCustomMem` + TFLite C++ `SetCustomAllocationForTensor`; Java/Kotlin wrapper exposes no equivalent API, and this is not direct CameraX buffer binding | Keep Kotlin/TFLite path; only attempt separate C++ delegate shared-memory probe if needed |
| mixed-precision | w8a16 mixed precision | queued | No current W8A8 quality blocker | Needs quantization failure evidence |
| temporal | frame skip / temporal reuse / double buffering | in_progress | `sr_every_n=3` ImageAnalysis smoke is implemented and validated; effective enhanced FPS is about 9.4-9.9, but per-enhanced-frame e2e is about 21/25ms and does not beat every-frame latency | Decide whether this is useful as display cadence/product strategy or just a boundary result |
| tile | post-capture whole-image tile enhancement | done | Host MVP, host multi-scene comparison, and Android app tile entry are implemented; same-frame QuickSR vs Real-ESRGAN app evidence exists | Real-ESRGAN tile is the quality-priority post-capture route; QuickSR tile stays speed/conservative baseline |
| video | video every-N-frame enhancement | blocked_needs_user | No CameraX VideoCapture/Recorder path yet; every-N ImageAnalysis smoke now exists as pre-video evidence | Full VideoCapture waits for explicit demo need |
| power | sustained power/perf-watt | done | Rooted battery-node current/voltage reads work; core smoke estimates exist | Use as board-level estimate only; do not claim external-meter precision |
| showcase | resume / README / demo / interview package | done | README, SHOWCASE_INDEX, DEMO_RUNBOOK, INTERVIEW_TALK_TRACK, resume draft | Maintain only |

## Current Required Next Unfinished Items

The current checkpoint is strong enough for showcase, but the full original
design still has unfinished required lanes:

1. `AIMET-CLE`: precision recovery, triggered by a real quantization failure.
2. `eval-perceptual`: LPIPS / NIQE / OCR diagnostic metrics when visual and
   PSNR/SSIM conflict.
3. `zero-copy`: C++ delegate shared-memory probe only if it is worth leaving the
   current Kotlin/TFLite path.
4. `temporal` / `video`: decide whether every-N is useful enough to become a
   product/display strategy; full VideoCapture still needs explicit demo need.

## Loop Rule

Future agents must choose the next task from this ledger unless the user's live
oral template gives a more specific P0 instruction. A completed showcase package
is not permission to stop the project or avoid the remaining design items.
