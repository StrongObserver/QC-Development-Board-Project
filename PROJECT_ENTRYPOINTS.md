# RB5 Gen2 Project Entrypoints

This is the first file future AI agents should read for this project.

## Priority Order

```text
P0: User's current RB5 Gen2 project oral-template prompt
P1: PROJECT_ENTRYPOINTS.md
P2: Latest results/<run_id>/SUMMARY.md and NEXT_ACTION.md
P3: RB5 Gen2_AI上下文.md and benchmark QA SOP files
P4: metrics/contact sheets/review guides
P5: source code, raw files, detailed logs
```

The user's current prompt always wins over older `NEXT_ACTION.md`.

## Default Loop Engineering Rule

For benchmark or QNN work, future AI agents should treat the existing benchmark
runner outputs as the default loop controller, not as optional reports.

Use this order:

```text
1. Read the user's current oral-template prompt. It is the only P0 command.
2. Read this entrypoint.
3. Read the latest result folder's loop_state.json when present.
4. Read SUMMARY.md / NEXT_ACTION.md only as handoff context.
5. Continue only if the hard gates in loop_state.json allow it.
```

The current loop policy is implemented in:

```text
C:\Users\Admin\Desktop\QC-Development-Board-Project\RB5_SR_lab\loop_policy.py
C:\Users\Admin\Desktop\QC-Development-Board-Project\RB5_SR_lab\run_qnn_smoke_benchmark.py
```

Important meanings:

- `loop_state.json` is the machine-readable loop state: current status, stop
  reason, next priority task, hard gates, and whether human review is needed.
- `NEXT_ACTION.md` is still only a handoff suggestion. It must not override the
  user's current prompt.
- If hard gates fail, stop and fix runner/output validity before discussing
  visual quality or performance claims.
- If a low-light/natural-texture case is marked `conditional`, do not derail the
  main QNN path unless human review marks it as `fail`.
- The current mainline has already moved through:
  single smoke -> repeated smoke p50/p95 -> full 24-case benchmark -> Path B
  Android app QNN Delegate evidence. Do not restart old bring-up tasks unless the
  current prompt asks for a rerun or a regression appears.

## Redundant Knowledge Base Rule

The project now has a deliberately redundant internal-knowledge layer under:

```text
C:\Users\Admin\Nutstore\1\Typora_save\字节_嵌入式camera实习\丁大均
C:\Users\Admin\Nutstore\1\Typora_save\字节_嵌入式camera实习\超分
C:\Users\Admin\Nutstore\1\Typora_save\字节_嵌入式camera实习\万钰臻
```

All current Markdown files in these folders have a `RB5/Harness 读取摘要` section.
Future AI agents should use those sections as the first stop before reading the
full document.

Use this layer when the loop is stuck or when the failure type is unclear:

- SR quality, text/face distortion, low-light texture boundary: read `超分.md`,
  `客观化评测方法.md`, and `自然细腻的细节质感效果表现及客观分析（含 RAW 噪声回叠）.md`.
- QNN/HTP/LiteRT/runtime/app integration: read `高通NPU集成分析.md`,
  `端侧大模型 LiteRT 与高通 HTP 算子执行机制与量化管线分析.md`,
  `高通NPU算子开发.md`, and `阿里mnn代码分析.md`.
- Lightweight or fallback SR direction: read `FastSR：一种超快速的图像超分辨率方法.md`.
- Real camera, RAW noise, AI ISP, high-res still, deblur, HDR, or video paths:
  read the relevant `AI ISP`, `噪声标定`, `高像素超清`, `计算光学`, `长焦光学`,
  `防抖*`, and `鬼影` documents only when the task actually enters that area.

Image rule: do not delete image references. Read images only when the summary
or the current failure requires visual evidence, such as artifact examples,
workflow diagrams, profile screenshots, or quality comparisons.

The external research layer lives under:

```text
C:\Users\Admin\Desktop\QC-Development-Board-Project\knowledge_base\external_research
```

Read its `README.md` and each `RESOURCE_CARD.md` before opening a cloned
repository or paper PDF. Current first-batch resources cover Real-ESRGAN,
QuickSRNet, BSRGAN degradation, TPGSR/SGENet text SR, Qualcomm AI Hub Models,
and an Android QNN sample.

## EvalHub Rule

Lifecycle-level evaluation data and metric policy now live under:

```text
C:\Users\Admin\Desktop\QC-Development-Board-Project\eval_hub
C:\Users\Admin\Desktop\QC-Development-Board-Project\evalhub_data
```

Use EvalHub when the user asks to strengthen the evaluation system, extend the
dataset beyond the fixed 24-case benchmark, add IQA/perceptual metrics, or
prepare lifecycle coverage for real degradation/text/app/video stages.

Key files:

```text
C:\Users\Admin\Desktop\QC-Development-Board-Project\eval_hub\README.md
C:\Users\Admin\Desktop\QC-Development-Board-Project\eval_hub\EVAL_SYSTEM_FREEZE.md
C:\Users\Admin\Desktop\QC-Development-Board-Project\eval_hub\registries\dataset_registry.csv
C:\Users\Admin\Desktop\QC-Development-Board-Project\eval_hub\registries\metric_policy.csv
C:\Users\Admin\Desktop\QC-Development-Board-Project\eval_hub\registries\lifecycle_matrix.md
```

Large downloaded datasets and derived artifacts stay in `evalhub_data\`, which
is ignored by Git. Do not commit raw datasets. Do not let EvalHub replace
`RB5_SR_Benchmark_v1` silently; promote a new source only after it has a stable
manifest, contact sheet, result SOP, and reviewed run.

## First Read Checklist

Read these before planning non-trivial RB5 work:

```text
C:\Users\Admin\Nutstore\1\Typora_save\自己的项目\RB5 Gen2_AI上下文.md
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\AI_CONTEXT.md
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\qa\RESULT_SOP.md
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\qa\TEST_PROTOCOL.md
```

For evaluation-system expansion, also read:

```text
C:\Users\Admin\Desktop\QC-Development-Board-Project\eval_hub\README.md
C:\Users\Admin\Desktop\QC-Development-Board-Project\eval_hub\EVAL_SYSTEM_FREEZE.md
C:\Users\Admin\Desktop\QC-Development-Board-Project\eval_hub\registries\lifecycle_matrix.md
```

Then read the latest run folder under:

```text
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results
```

Prefer the newest folder that contains:

```text
SUMMARY.md
NEXT_ACTION.md
metrics.csv
run_log.csv
loop_state.json
contact_sheet.png
```

If `NEXT_ACTION.md` is missing, read `SUMMARY.md` and continue, then create `NEXT_ACTION.md` before ending the loop.

## Loop Closeout Rule

Before ending a substantial loop, make sure the output follows:

```text
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\qa\RESULT_SOP.md
```

If a run/result directory was created, it should include:

```text
SUMMARY.md
HUMAN_REVIEW_GUIDE.md
NEXT_ACTION.md
metrics.csv
run_log.csv
loop_state.json
contact_sheet.png
by_category\
```

`NEXT_ACTION.md` must be generated from:

```text
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\qa\NEXT_ACTION_TEMPLATE.md
```

## Current High-Level Direction

The project has already reached local RB5 QNN Path A:

```text
qnn-net-run --retrieve_context real_esrgan_general_x4v3.bin
```

It has also reached the current Path B mainline through the official QNN TFLite
Delegate route:

```text
W8A8 TFLite -> QNN TFLite Delegate -> HTP backend -> Android app fixed sample and CameraX live ROI
```

Key boundary: the working app route is QNN TFLite Delegate with the SDK skel
library packaged in `jniLibs` and `setSkelLibraryDir(nativeLibraryDir)`. Direct
QNN context-binary C API and app-subprocess `qnn-net-run` remain non-blocking
experimental paths.

Current next engineering direction is usually:

1. clean and stabilize the QNN Delegate app path,
2. turn the existing app fixed-sample/live-ROI evidence into a more formal app
   e2e record, or
3. choose the next project-value task such as QuickSRNet comparison, AIMET
   precision recovery, or native preprocessing/copy reduction.

Always let the user's current oral-template prompt choose between these.
