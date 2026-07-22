# RB5 Gen2 Full Scope Ledger

Updated: 2026-07-22

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
| AIMET-CLE | AIMET CLE or Bias Correction | done | PyTorch FP source route is confirmed: local SRVGG weights export to ONNX with PSNR 95.046dB vs PyTorch. AIMET-Torch installs in short-path `.venv-a` with `PYTHONUTF8=1`; CLE runs and QuantSim small slice shows avg +0.115dB simulated INT8 improvement, but not every case improves | Keep as evidence. Only pursue deployable TFLite/QNN CLE export if a later quality claim needs it |
| AIMET-advanced | AdaRound / QAT | blocked_needs_user | High cost and no current quantization failure trigger | Reopen only after CLE/Bias is insufficient on a real failure crop |
| model-curve | Real-ESRGAN vs QuickSRNet quality/latency/size/power curve | done | Quality/latency/size evidence exists; board-level battery-node power smoke exists. QuickSRNet medium/large host curve was reviewed and user judged small to be at least as good visually, so small remains live workhorse | Do not add medium/large to Android unless a new scene shows a clear visual gain |
| eval-fixed | fixed scenario benchmark | done | `RB5_SR_Benchmark_v1`, full 24-case, real-camera 8-scene set | Maintain only |
| eval-realsr | RealSR real-degradation lifecycle sanity | done | `evalhub_realsr_mini_10cases_20260720_v2` covers Canon/Nikon 5+5 host LiteRT cases; bicubic PSNR is higher, while SR SSIM/sharpness can improve, so visual review remains required | Use only before real-camera robustness claims; do not replace the 24-case main gate |
| eval-perceptual | LPIPS / NIQE / OCR diagnostic metrics | done | TextZoom OCR mini diagnostic exists at `RB5_SR_lab\results\textzoom_ocr\20260720_textzoom_ocr_mini_v2`; OCR similarity is low even on HR references, so it remains diagnostic-only and visual review still owns final quality decisions | Reopen only to calibrate OCR/LPIPS/NIQE against human review on a representative slice |
| app-fixed-replay | Android app fixed-sample replay | done | `20260720_app_fixed_replay_quicksr_3assets` runs 3 fixed assets through Android QNN/HTP, pulls 9 output images, and writes app e2e evidence | Maintain as a small regression layer; expand only if a concrete app regression appears |
| native-preprocess | native YUV ROI / RGB preprocessing | done | Direct PlaneProxy ByteBuffer -> native ROI/RGB is now the default QNN/QuickSR live path. Same-frame direct-vs-array probe has MAD `0.0`; default app direct-YUV live ROI e2e p50/p95 is `10/12ms` | Maintain as default for QNN/QuickSR. Further zero-copy work is a separate larger data-path project |
| buffer-reuse | buffer / object reuse | done | TFLite buffers, pixel arrays, sample-copy reduction, output Bitmap reuse, and reusable UINT8 output byte buffer | Maintain only |
| zero-copy | true zero-copy CameraX -> NPU | done | Phase 2 normal tensor vs shared custom allocation compare passed with matching checksum; direct buffer probe confirms CameraX Y/U/V PlaneProxy buffers are direct and JNI `GetDirectBufferAddress` returns non-null native addresses. Direct-YUV default reads PlaneProxy buffers in native code, but this is still not QNN Delegate input binding | Treat invoke-level and direct-plane probes as complete; any further work is a larger CameraX/native data-path integration project |
| mixed-precision | w8a16 mixed precision | blocked_technical | Current generated Qualcomm AI Hub Models exporter for `real_esrgan_general_x4v3` supports float and w8a8 only; `--precision w8a16` is rejected for this model/runtime route | Reopen only if QAI Hub Models adds Real-ESRGAN w8a16 support, or if a custom lower-level AIMET/ONNX/QNN mixed-precision route is explicitly chosen |
| temporal | frame skip / temporal reuse / double buffering | done | `sr_every_n=3` ImageAnalysis smoke is implemented and validated; effective enhanced FPS is about 9.4-9.9, while each enhanced frame remains about 21/25ms e2e | Treat as a cadence/product boundary; do not claim lower per-frame latency |
| tile | post-capture whole-image tile enhancement | done | Host MVP, host multi-scene comparison, and Android app tile entry are implemented; same-frame QuickSR vs Real-ESRGAN app evidence exists | Real-ESRGAN tile is the quality-priority post-capture route; QuickSR tile stays speed/conservative baseline |
| video | video every-N-frame enhancement | done | `20260720_demo_mode_wide_clear_20s` records the Demo Mode live ROI UI with `adb screenrecord`; `20260720_demo_relation_aligned_v3` explains display-aligned wide preview / model input / SR output; button access is preserved through default UI / overlay toggle / intent control | Treat as demo evidence only; full CameraX VideoCapture/Recorder waits for explicit product need |
| power | sustained power/perf-watt | done | Rooted battery-node current/voltage reads work; core smoke estimates exist | Use as board-level estimate only; do not claim external-meter precision |
| showcase | resume / README / demo / interview package | done | README, SHOWCASE_INDEX, DEMO_RUNBOOK, INTERVIEW_TALK_TRACK, resume draft | Maintain only |

## Current Required Next Unfinished Items

The current checkpoint is strong enough for showcase, but the full original
design still has unfinished required lanes:

1. `AIMET-advanced`: still `blocked_needs_user`; only reopen after CLE/Bias is
   insufficient on a real failure crop and the user approves the added cost.
2. `zero-copy`: invoke-level and direct-plane native-preprocess probes are
   complete, and the default live ROI now uses direct-YUV. True CameraX buffer
   registration remains a separate larger data-path project.
3. `video`: Demo Mode screenrecord demo is complete; full CameraX
   VideoCapture/Recorder still needs explicit product need because it would be a
   different pipeline from the current live ROI app demo.
4. `AIMET-CLE deployable export`: local CLE checkpoint deployability is proven,
   but a CLE W8A8 TFLite/QNN artifact requires explicit user approval because it
   submits Qualcomm AI Hub remote quantize/compile/profile jobs.

## Loop Rule

Future agents must choose the next task from this ledger unless the user's live
oral template gives a more specific P0 instruction. A completed showcase package
is not permission to stop the project or avoid the remaining design items.
