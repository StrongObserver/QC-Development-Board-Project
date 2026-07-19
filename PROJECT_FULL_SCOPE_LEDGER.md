# RB5 Gen2 Full Scope Ledger

Updated: 2026-07-19

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
| D8-config | per-channel/per-tensor/calibration comparison | queued | W8A8 baseline exists; no multi-config sweep yet | Run only if quantization study becomes next lane |
| AIMET-CLE | AIMET CLE or Bias Correction | queued | Not triggered yet because no clear W8A8-vs-float showcase regression | Need failure crop before execution |
| AIMET-advanced | AdaRound / QAT | queued | High cost and no current trigger | Keep behind CLE/Bias trigger |
| model-curve | Real-ESRGAN vs QuickSRNet quality/latency/size/power curve | in_progress | Quality/latency/size done; power/perf-watt incomplete | Add power/perf-watt only if needed for final claim |
| eval-fixed | fixed scenario benchmark | done | `RB5_SR_Benchmark_v1`, full 24-case, real-camera 8-scene set | Maintain only |
| eval-perceptual | LPIPS / NIQE / OCR diagnostic metrics | queued | Metric policy says diagnostic only; not calibrated | Use only when visual and PSNR/SSIM conflict |
| native-preprocess | native YUV ROI / RGB preprocessing | in_progress | Kotlin YUV correct but slow; native ROI faster single-frame; tensor-ready repeated live not default | Next attempt must target output/postprocess or deeper tensor-ready path |
| buffer-reuse | buffer / object reuse | done | TFLite buffers, pixel arrays, sample-copy reduction, output Bitmap reuse | Maintain only |
| zero-copy | true zero-copy CameraX -> NPU | queued | Not attempted; known high complexity: AHardwareBuffer/DMA-BUF/QNN tensor memory/vendor permissions | Start only after smaller native/tensor-ready lanes are exhausted |
| mixed-precision | w8a16 mixed precision | queued | No current W8A8 quality blocker | Needs quantization failure evidence |
| temporal | frame skip / temporal reuse / double buffering | queued | Current project is single-frame ROI; no video path yet | Start only when video path begins |
| tile | post-capture whole-image tile enhancement | queued | Not implemented | Candidate next feature if product demo needs still-photo enhancement |
| video | video every-N-frame enhancement | queued | Not implemented | Requires video capture/evaluation plan first |
| power | sustained power/perf-watt | in_progress | 120s and 5min coarse thermal signals exist; no current/power | Add real power/current only if making perf-watt claim |
| showcase | resume / README / demo / interview package | done | README, SHOWCASE_INDEX, DEMO_RUNBOOK, INTERVIEW_TALK_TRACK, resume draft | Maintain only |

## Current Required Next Unfinished Items

The current checkpoint is strong enough for showcase, but the full original
design still has unfinished required lanes:

1. `tile`: post-capture whole-image tile enhancement.
2. `D8-config`: quantization configuration comparison.
3. `AIMET-CLE`: precision recovery, triggered by a real quantization failure.
4. `eval-perceptual`: LPIPS / NIQE / OCR diagnostic metrics when visual and
   PSNR/SSIM conflict.
5. `zero-copy`: true zero-copy exploration after smaller copy-reduction lanes.
6. `temporal` / `video`: video or every-N-frame enhancement.
7. `power`: real power/perf-watt if that claim is needed.

## Loop Rule

Future agents must choose the next task from this ledger unless the user's live
oral template gives a more specific P0 instruction. A completed showcase package
is not permission to stop the project or avoid the remaining design items.
