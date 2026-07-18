# RB5 App End-to-End Evaluation Protocol

更新时间：2026-07-17

This protocol is a lifecycle placeholder for the app/device layer. It should be
used after QNN/native app integration exists. It is not a replacement for the
current `qnn-net-run` benchmark.

## Purpose

The runner benchmark answers:

```text
Can the QNN context execute correctly and how fast is qnn-net-run?
```

The app e2e protocol answers:

```text
Can the real Android app process frames end-to-end under stable latency,
resource, thermal, and fallback conditions?
```

## Required Evidence

Each app e2e run should produce a result directory compatible with
`RB5_SR_Benchmark_v1/qa/RESULT_SOP.md` and include:

```text
SUMMARY.md
HUMAN_REVIEW_GUIDE.md
NEXT_ACTION.md
run_log.csv
metrics.csv
contact_sheet.png or screenshot/video evidence
raw_logs/
```

Use `app_e2e_log_schema.csv` for the row format.

## Minimum Test Modes

1. Fixed manifest input replay, when possible:
   - uses `RB5_SR_Benchmark_v1/manifest.csv` or an EvalHub manifest,
   - produces comparable outputs and contact sheets.
2. Camera ROI live mode:
   - records app capture/preprocess/inference/postprocess/e2e timing,
   - separates warmup from steady state.
3. Sustained run:
   - runs long enough to observe thermal or memory drift,
   - records p50/p95 and any fallback/throttling.

## Metric Roles

Hard gates:

- app starts,
- model/backend loads,
- output exists,
- output size is correct,
- no crash,
- no unexpected fallback.

Supporting evidence:

- p50/p95 e2e latency,
- per-stage latency,
- memory,
- power/temperature when available.

Visual veto:

- contact sheet,
- screenshot,
- screen recording,
- failure taxonomy labels.

## Current Boundary

Current QNN evidence is still `qnn-net-run` runner evidence. Do not report it as
Android app e2e. This protocol becomes active when Path B native runner / Android
app integration is implemented.

