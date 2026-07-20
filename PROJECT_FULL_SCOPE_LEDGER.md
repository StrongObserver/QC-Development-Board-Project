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
| AIMET-CLE | AIMET CLE or Bias Correction | blocked_needs_user | Trigger crops exist; Windows check shows `aimet-onnx` has no matching Win/Python 3.12 distribution and PyPI provides Linux `manylinux` wheel, while `aimet-torch` only helps if a PyTorch FP source path is confirmed | Provide WSL/Linux or another supported AIMET-ONNX toolchain, or confirm a PyTorch FP source model path before trying AIMET-Torch |
| AIMET-advanced | AdaRound / QAT | blocked_needs_user | High cost and no current quantization failure trigger | Reopen only after CLE/Bias is insufficient on a real failure crop |
| model-curve | Real-ESRGAN vs QuickSRNet quality/latency/size/power curve | done | Quality/latency/size evidence exists; board-level battery-node power smoke exists for idle, preview, live QuickSR, QuickSR tile, and Real-ESRGAN tile | Treat power as board-level estimate, not external-meter evidence |
| eval-fixed | fixed scenario benchmark | done | `RB5_SR_Benchmark_v1`, full 24-case, real-camera 8-scene set | Maintain only |
| eval-realsr | RealSR real-degradation lifecycle sanity | done | `evalhub_realsr_mini_10cases_20260720_v2` covers Canon/Nikon 5+5 host LiteRT cases; bicubic PSNR is higher, while SR SSIM/sharpness can improve, so visual review remains required | Use only before real-camera robustness claims; do not replace the 24-case main gate |
| eval-perceptual | LPIPS / NIQE / OCR diagnostic metrics | done | TextZoom OCR mini diagnostic exists at `RB5_SR_lab\results\textzoom_ocr\20260720_textzoom_ocr_mini_v2`; OCR similarity is low even on HR references, so it remains diagnostic-only and visual review still owns final quality decisions | Reopen only to calibrate OCR/LPIPS/NIQE against human review on a representative slice |
| app-fixed-replay | Android app fixed-sample replay | done | `20260720_app_fixed_replay_quicksr_3assets` runs 3 fixed assets through Android QNN/HTP, pulls 9 output images, and writes app e2e evidence | Maintain as a small regression layer; expand only if a concrete app regression appears |
| native-preprocess | native YUV ROI / RGB preprocessing | blocked_technical | Tensor-ready recheck after output bulk-copy is valid but still not better than default: tensor-ready e2e 15.0/21.0ms vs default 14.0/19.8ms; runner parsing bug for tensor logs was fixed | Further progress requires a more targeted native preprocessing experiment, not promoting the current tensor-ready path |
| buffer-reuse | buffer / object reuse | done | TFLite buffers, pixel arrays, sample-copy reduction, output Bitmap reuse, and reusable UINT8 output byte buffer | Maintain only |
| zero-copy | true zero-copy CameraX -> NPU | done | Phase 2 normal tensor vs shared custom allocation compare passed with matching checksum; shared invoke avg was 1,056us vs normal 1,104us, so invoke-level gain is small and this is still not CameraX buffer binding | Treat invoke-level probe as complete; any further work is a separate CameraX/native data-path integration project |
| mixed-precision | w8a16 mixed precision | blocked_needs_user | No current W8A8 quality blocker or layer-level sensitivity evidence | Reopen only with quantization failure evidence |
| temporal | frame skip / temporal reuse / double buffering | done | `sr_every_n=3` ImageAnalysis smoke is implemented and validated; effective enhanced FPS is about 9.4-9.9, while each enhanced frame remains about 21/25ms e2e | Treat as a cadence/product boundary; do not claim lower per-frame latency |
| tile | post-capture whole-image tile enhancement | done | Host MVP, host multi-scene comparison, and Android app tile entry are implemented; same-frame QuickSR vs Real-ESRGAN app evidence exists | Real-ESRGAN tile is the quality-priority post-capture route; QuickSR tile stays speed/conservative baseline |
| video | video every-N-frame enhancement | done | `20260720_demo_mode_wide_clear_20s` records the Demo Mode live ROI UI with `adb screenrecord`; `20260720_demo_relation_aligned_v3` explains display-aligned wide preview / model input / SR output; button access is preserved through default UI / overlay toggle / intent control | Treat as demo evidence only; full CameraX VideoCapture/Recorder waits for explicit product need |
| power | sustained power/perf-watt | done | Rooted battery-node current/voltage reads work; core smoke estimates exist | Use as board-level estimate only; do not claim external-meter precision |
| showcase | resume / README / demo / interview package | done | README, SHOWCASE_INDEX, DEMO_RUNBOOK, INTERVIEW_TALK_TRACK, resume draft | Maintain only |

## Current Required Next Unfinished Items

The current checkpoint is strong enough for showcase, but the full original
design still has unfinished required lanes:

1. `AIMET-CLE` / `mixed-precision`: concrete W8A8-vs-float failure crops exist,
   but native Windows AIMET execution is blocked; next step needs WSL/Linux or
   another supported AIMET toolchain from the user.
2. `native-preprocess` / `zero-copy`: small probes are complete, but true
   CameraX -> tensor -> display zero-copy is not implemented. Further work would
   be a larger CameraX/native data-path integration project, not another small
   shared-allocation probe.
3. `video`: Demo Mode screenrecord demo is complete; full CameraX
   VideoCapture/Recorder still needs explicit product need because it would be a
   different pipeline from the current live ROI app demo.

## Loop Rule

Future agents must choose the next task from this ledger unless the user's live
oral template gives a more specific P0 instruction. A completed showcase package
is not permission to stop the project or avoid the remaining design items.
