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
| aimet-cle-deploy | deployable CLE W8A8 TFLite/QNN export | done | Remote AI Hub quantize/compile/profile/link succeeded for CLE checkpoint; QCS8550 Proxy profile estimated `1.7ms`, NPU 72; local RB5 full 24-case qnn-net-run passed, but average PSNR delta vs current W8A8 is `-0.011dB` and QNN accelerator is about `+208us` slower | Keep as quantization due-diligence evidence; do not replace app model |
| aimet-advanced | AdaRound / QAT | blocked_needs_user | High cost and no current quantization failure trigger | Reopen only after CLE/Bias is insufficient on a real failure crop |
| model-route | Real-ESRGAN vs QuickSRNet quality/latency/size/power route | done | Quality/latency/size evidence exists; QuickSRNetSmall remains live workhorse; Real-ESRGAN remains milestone/comparison/post-capture route | Maintain route decision |
| app-e2e | app e2e schema and fixed replay | done | `app_e2e_log.csv`, fixed-sample replay, direct-YUV live timing, result mirrors, stream-log live collection, and P99 runner metrics exist | Maintain as regression/evidence layer |
| data-path-direct-yuv | direct-YUV native tensor input | done | Direct PlaneProxy ByteBuffer -> native staging ROI/RGB is default; same-frame MAD `0.0`; current 20-minute app e2e p50/p95/p99 `8/9/9ms` | Maintain as default data path |
| buffer-reuse | buffer / object reuse | done | TFLite buffers, pixel arrays, sample-copy reduction, output Bitmap reuse, reusable UINT8 output byte buffer | Maintain only |
| qnn-profile | QNN Delegate profile collection and decode boundary | done | App can collect raw profile buffer; official `qnn-profile-viewer` rejects Java raw bytes, best-effort diagnostic parser exists. Live tensor logs now use slim profile output, while fixed-sample diagnostics can keep full hex | Do not claim official per-op app profile |
| zero-copy | true CameraX buffer -> QNN input binding | queued | Invoke-level shared custom allocation and direct-plane probes are complete, but not CameraX buffer binding. Native staging is complete and improved e2e from `11/12/12ms` to `8/9/9ms`; `ZERO_COPY_SCOPE_PLAN.md` defines remaining Stage D route | Pursue only as larger data-path project beyond the current 8/9/9ms native staging baseline |
| mixed-precision | w8a16 mixed precision | blocked_technical | Current generated Real-ESRGAN exporter supports float/w8a8 only and rejects w8a16 | Reopen only with new exporter or custom route |
| sustained-p99 | sustained P50/P95/P99 and thermal curve | done | current native-staging 20-minute stream-log direct-YUV run recorded 35719 frames, 0 skipped frames, and e2e p50/p95/p99 `8/9/9ms`; companion battery-node board-level power run reports mean about `4.96W`, temp `24.0C -> 24.0C` | Maintain as app timing plus board-level estimate; do not claim external-meter perf/watt |
| init-memory | cold/warm init, switch cost, sticky memory table | done | Current APK resource probe records Real init `2.4-2.9s`, Quick init `155/624ms`, Real->Quick switch `800ms`, close-both PSS still about `+83MB` vs start | Maintain table; do not enable automatic live switching |
| power | board-level power/perf-watt boundary | done | Rooted battery-node current/voltage reads work; core smoke estimates exist | Use as board-level estimate only |
| eval-fixed | fixed scenario benchmark | done | `RB5_SR_Benchmark_v1`, full 24-case, real-camera 8-scene set | Maintain as workload correctness/quality gate |
| eval-lifecycle | RealSR/TextZoom lifecycle diagnostics | done | RealSR mini and TextZoom OCR mini exist; both are diagnostic/lifecycle evidence | Do not replace 24-case main gate |
| temporal | every-N cadence and demo video boundary | done | `sr_every_n=3` smoke, Demo Mode screenrecord, and `DEMO_RUNBOOK.md` video capture boundary exist | Do not claim full VideoCapture/Recorder |
| tile | post-capture tile workload evidence | done | Host MVP, host comparison, Android app tile entry, same-frame QuickSR vs Real-ESRGAN evidence exist | Treat as supporting workload evidence |
| showcase | Runtime resume / README / demo / interview package | in_progress | Materials exist but are being reframed from image-enhancement to Runtime | Finish text sweep |

## Current Required Next Unfinished Items

The current checkpoint is strong enough for showcase. The remaining items are
Runtime-evidence or explicit-decision lanes, not old SR feature gaps:

1. `showcase`: finish the Runtime/Heterogeneous wording sweep around the final
   benchmark table.
2. `zero-copy`: only reopen as a larger CameraX-to-QNN buffer-registration
   experiment with target, budget, and rollback beyond the 8/9/9ms native-staging
   baseline.
3. `video`: full CameraX VideoCapture/Recorder still needs explicit product
   need because it is a different pipeline from the current screenrecorded live
   ROI demo.

## Loop Rule

Future agents must choose the next task from this ledger unless the user's live
oral template gives a more specific P0 instruction. A completed showcase package
is not permission to stop the project or avoid the remaining design items.
