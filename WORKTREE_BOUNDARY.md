# Worktree Boundary

Updated: 2026-07-18

This file freezes the current dirty worktree boundary before continuing the
RB5 Gen2 loop. Do not use `git add .`.

## Current Working Rule

The current worktree contains multiple logical scopes:

```text
QNN Delegate Android app milestone
Benchmark loop and app evidence scripts
Route / metric / roadmap decisions
QuickSRNet candidate model and fixed-sample assets
EvalHub registries and scripts
External research cards and cloned reference repos
```

Stage explicit paths only. Treat generated outputs, raw logs, APKs, local
datasets, cloned repositories, and PDFs as local evidence unless the user
explicitly asks to commit them.

## Safe Commit Groups

### 1. QNN Delegate App Milestone

Purpose:

```text
Record the working Android app path:
W8A8 TFLite -> QNN TFLite Delegate -> HTP -> fixed sample / live ROI.
```

Candidate paths:

```text
RB5VisionLab/app/build.gradle.kts
RB5VisionLab/app/libs/qtld-release.aar
RB5VisionLab/app/src/main/AndroidManifest.xml
RB5VisionLab/app/src/main/cpp/rb5visionlab.cpp
RB5VisionLab/app/src/main/java/com/cyf/rb5visionlab/MainActivity.kt
RB5VisionLab/app/src/main/java/com/cyf/rb5visionlab/SuperResolver.kt
RB5VisionLab/app/src/main/res/layout/activity_main.xml
RB5VisionLab/app/src/main/jniLibs/arm64-v8a/libQnnHtp.so
RB5VisionLab/app/src/main/jniLibs/arm64-v8a/libQnnHtpPrepare.so
RB5VisionLab/app/src/main/jniLibs/arm64-v8a/libQnnHtpV73Skel.so
RB5VisionLab/app/src/main/jniLibs/arm64-v8a/libQnnHtpV73Stub.so
RB5VisionLab/app/src/main/jniLibs/arm64-v8a/libQnnSystem.so
```

Do not include:

```text
RB5VisionLab/app/src/main/jniLibs/**/libPlatformValidatorShared.so
RB5VisionLab/app/src/main/jniLibs/**/libQnnHtpNetRunExtensions.so
RB5VisionLab/app/src/main/jniLibs/**/libQnnIr.so
RB5VisionLab/app/src/main/jniLibs/**/libQnnSaver.so
RB5VisionLab/app/src/main/jniLibs/**/libqnn_net_run_exec.so
RB5VisionLab/app/src/main/jniLibs/**/libqnn_profile_viewer_exec.so
```

### 2. Benchmark Loop And Evidence Scripts

Candidate paths:

```text
PROJECT_ENTRYPOINTS.md
RB5_SR_lab/loop_policy.py
RB5_SR_lab/test_loop_policy.py
RB5_SR_lab/run_qnn_smoke_benchmark.py
RB5_SR_lab/eval_benchmark_v1.py
RB5_SR_lab/eval_quicksrnet_compare.py
RB5_SR_lab/run_app_live_roi_benchmark.py
RB5_SR_lab/run_app_resource_probe.py
```

Verification:

```bat
python RB5_SR_lab\test_loop_policy.py
python -m py_compile RB5_SR_lab\run_app_live_roi_benchmark.py RB5_SR_lab\run_app_resource_probe.py
```

### 3. Route, Metric, And Handoff Docs

Candidate paths:

```text
ROUTE_DECISION.md
EVAL_METRIC_POLICY.md
ROADMAP_NEXT.md
NEXT_ACTION.md
COMMIT_PLAN.md
WORKTREE_BOUNDARY.md
docs/prompts/
tools/
```

### 4. QuickSRNet Candidate Assets

Candidate paths:

```text
RB5VisionLab/app/src/main/assets/quicksrnetsmall_w8a8.tflite
RB5VisionLab/app/src/main/assets/case_low_light_div2k0852.png
RB5VisionLab/app/src/main/assets/case_people_scene_div2k0832.png
RB5VisionLab/app/src/main/assets/case_text_signage_urban076.png
```

These are small fixed-sample validation assets. Do not add generated outputs.

### 5. EvalHub

Candidate paths:

```text
eval_hub/
```

Do not include:

```text
evalhub_data/
```

### 6. External Research Indexes

Candidate paths:

```text
knowledge_base/external_research/README.md
knowledge_base/external_research/**/RESOURCE_CARD.md
```

Do not include:

```text
knowledge_base/external_research/**/repo/
knowledge_base/external_research/**/*.pdf
```

Reason:

```text
The current knowledge_base tree is about 402MB / 8549 files. Most of that is
cloned reference repos and PDFs. Keep the index cards in Git; keep heavy cache
content local.
```

## Current P0 Decision

P0 is complete when:

```text
1. The logical commit groups above are preserved.
2. .gitignore protects heavy external research cache content.
3. Future staging uses explicit paths from this file or COMMIT_PLAN.md.
```
