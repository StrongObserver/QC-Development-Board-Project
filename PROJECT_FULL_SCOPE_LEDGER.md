# RB5 Gen2 Runtime Scope Ledger

Updated: 2026-07-23

## Purpose

This ledger prevents a recurring loop failure:

```text
Stable milestone != whole project complete.
```

Every original project-design item must stay visible until it is completed or
blocked with concrete evidence. Hard or time-consuming work can be ordered
later, but it must not disappear.

The accepted project framing has been refined to:

```text
QCS8550 端侧 AI 推理 Runtime 与异构性能优化
```

The ledger therefore tracks Runtime/deployment/profiling/evaluation capability
coverage. SR, CameraX, tile, and real-camera evidence remain as representative
workloads and validation assets, but the project should not be described as
only an image-enhancement app.

## State Values

| state | meaning |
| --- | --- |
| `done` | implemented and verified with evidence |
| `in_progress` | currently being executed |
| `queued` | required but not the immediate step |
| `blocked_needs_user` | needs a concrete user action/device/access |
| `blocked_technical` | attempted and blocked by a concrete technical issue |
| `not_viable_with_evidence` | proven not viable under current constraints |

## Runtime Design Coverage

| id | design item | state | current evidence / blocker | next action |
| --- | --- | --- | --- | --- |
| runtime-backends | CPU / NNAPI / GPU / QNN backend comparison | done | CPU ~579-610ms, GPU ~126-148ms, NNAPI no gain, QNN/HTP app path works | Keep as core Runtime evidence |
| qnn-path-a | QNN/HTP local runner | done | `qnn-net-run --retrieve_context` smoke/full benchmark exists; accelerator p50/p95 ~9.75/10.39ms | Maintain only |
| qnn-path-b | Android QNN TFLite Delegate app path | done | QNN TFLite Delegate + HTP app path works with skel lib and `setSkelLibraryDir` | Maintain only |
| quant-baseline | W8A8 quantized baseline | done | Real-ESRGAN W8A8 TFLite/QNN and QuickSRNetSmall W8A8 default live path | Maintain only |
| quant-config | calibration / quantization configuration comparison | done | First-pass AI Hub comparison completed for current app W8A8, calib10 default, and calib10 minmax; minmax is worse | Do not replace app model without stronger evidence |
| aimet-cle-local | AIMET CLE local feasibility | done | PyTorch FP source route is confirmed; AIMET-Torch CLE runs; QuantSim small slice shows avg +0.115dB simulated INT8 improvement | Keep as quantization evidence |
| aimet-cle-deploy | deployable CLE W8A8 TFLite/QNN export | blocked_needs_user | Local deployability checkpoint passes, but remote AI Hub quantize/compile/profile job has not been approved | Reopen only with explicit user approval |
| aimet-advanced | AdaRound / QAT | blocked_needs_user | High cost and no current quantization failure trigger | Reopen only after CLE/Bias is insufficient on a real failure crop |
| model-route | Real-ESRGAN vs QuickSRNet quality/latency/size/power route | done | Quality/latency/size evidence exists; QuickSRNetSmall remains live workhorse; Real-ESRGAN remains milestone/comparison/post-capture route | Maintain route decision |
| app-e2e | app e2e schema and fixed replay | done | `app_e2e_log.csv`, fixed-sample replay, direct-YUV live timing, and result mirrors exist. A stream-log/P99 runner experiment exists only as ignored evidence because its code was reverted | Maintain as regression/evidence layer |
| data-path-direct-yuv | direct-YUV native tensor input | done | Direct PlaneProxy ByteBuffer -> native ROI/RGB is default; same-frame MAD `0.0`; app e2e p50/p95 `10/12ms` | Maintain as default data path |
| buffer-reuse | buffer / object reuse | done | TFLite buffers, pixel arrays, sample-copy reduction, output Bitmap reuse, reusable UINT8 output byte buffer | Maintain only |
| qnn-profile | QNN Delegate profile collection and decode boundary | done | App can collect raw profile buffer; official `qnn-profile-viewer` rejects Java raw bytes, best-effort diagnostic parser exists. Live profile-slim experiment was reverted, so current code still emits the previous profile summary format | Do not claim official per-op app profile |
| zero-copy | true CameraX buffer -> QNN input binding | blocked_needs_user | Invoke-level shared custom allocation and direct-plane probes are complete, but not CameraX buffer binding | Only pursue as larger data-path project with explicit target |
| mixed-precision | w8a16 mixed precision | blocked_technical | Current generated Real-ESRGAN exporter supports float/w8a8 only and rejects w8a16 | Reopen only with new exporter or custom route |
| sustained-p99 | sustained P50/P95/P99 and thermal curve | conditional | 5-minute stream-log default direct-YUV run recorded 8941 frames and e2e p50/p95/p99 `11/12/12ms`, but the stream-log code was reverted. Board-level power run reports mean about `6.30W`, temp `24.0C -> 24.0C` | Treat as useful local evidence; rerun only if stream-log runner is re-approved |
| init-memory | cold/warm init, switch cost, sticky memory table | done | Current APK resource probe records Real init `2.4-2.9s`, Quick init `155/624ms`, Real->Quick switch `800ms`, close-both PSS still about `+83MB` vs start | Maintain table; do not enable automatic live switching |
| power | board-level power/perf-watt boundary | done | Rooted battery-node current/voltage reads work; core smoke estimates exist | Use as board-level estimate only |
| eval-fixed | fixed scenario benchmark | done | `RB5_SR_Benchmark_v1`, full 24-case, real-camera 8-scene set | Maintain as workload correctness/quality gate |
| eval-lifecycle | RealSR/TextZoom lifecycle diagnostics | done | RealSR mini and TextZoom OCR mini exist; both are diagnostic/lifecycle evidence | Do not replace 24-case main gate |
| temporal | every-N cadence and demo video boundary | done | `sr_every_n=3` smoke and Demo Mode screenrecord exist | Do not claim full VideoCapture/Recorder |
| tile | post-capture tile workload evidence | done | Host MVP, host comparison, Android app tile entry, same-frame QuickSR vs Real-ESRGAN evidence exist | Treat as supporting workload evidence |
| showcase | Runtime resume / README / demo / interview package | in_progress | Materials exist but are being reframed from image-enhancement to Runtime | Finish text sweep |

## Current Required Next Unfinished Items

The current checkpoint is strong enough for showcase. The remaining items are
Runtime-evidence or explicit-decision lanes, not old SR feature gaps:

1. `showcase`: finish the Runtime/Heterogeneous wording sweep and final
   benchmark table.
2. `aimet-cle-deploy`: only run with explicit user approval because it submits
   Qualcomm AI Hub remote quantize/compile/profile jobs.
3. `zero-copy`: only reopen as a larger CameraX-to-QNN buffer-registration
   experiment with target, budget, and rollback beyond the 10/12ms direct-YUV
   baseline.
4. `video`: full CameraX VideoCapture/Recorder still needs explicit product
   need because it is a different pipeline from the current live ROI demo.

## Loop Rule

Future agents must choose the next task from this ledger unless the user's live
oral template gives a more specific P0 instruction. A completed showcase package
is not permission to stop the project or avoid the remaining design items.
