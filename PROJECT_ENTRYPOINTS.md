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

## First Read Checklist

Read these before planning non-trivial RB5 work:

```text
C:\Users\Admin\Nutstore\1\Typora_save\自己的项目\RB5 Gen2_AI上下文.md
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\AI_CONTEXT.md
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\qa\RESULT_SOP.md
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\qa\TEST_PROTOCOL.md
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

Current next engineering direction is either:

1. repeat QNN smoke/full benchmark for stable p50/p95, or
2. start Path B native runner / Android app integration.

Always let the user's current oral-template prompt choose between these.
