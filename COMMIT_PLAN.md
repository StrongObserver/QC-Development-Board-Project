# Commit Plan

Updated: 2026-07-18

This repository currently contains several logical changes in one working tree.
Do not use `git add .`.

## Commit 1: QNN Delegate App Milestone

Purpose:

```text
Record the working Android app path:
W8A8 TFLite -> QNN TFLite Delegate -> HTP -> fixed sample / live ROI,
including the low-risk postprocess/sample-copy optimization.
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

Verification:

```text
RB5VisionLab\gradlew.bat --no-daemon :app:assembleDebug
adb fixed sample smoke
adb live ROI smoke
```

## Commit 2: Benchmark Loop And Evaluation Harness

Purpose:

```text
Record loop policy, benchmark runner closeout, and host comparison scripts.
```

Candidate paths:

```text
PROJECT_ENTRYPOINTS.md
WORKTREE_BOUNDARY.md
RB5_SR_lab/loop_policy.py
RB5_SR_lab/test_loop_policy.py
RB5_SR_lab/run_qnn_smoke_benchmark.py
RB5_SR_lab/eval_benchmark_v1.py
RB5_SR_lab/eval_quicksrnet_compare.py
RB5_SR_lab/run_app_live_roi_benchmark.py
RB5_SR_lab/run_app_resource_probe.py
RB5_SR_lab/run_app_sustained_live_roi.py
```

Verification:

```text
python RB5_SR_lab\test_loop_policy.py
```

## Commit 3: Route And Metric Decisions

Purpose:

```text
Record route decision and metric policy so future work does not drift back to
PSNR-only model ranking or automatic dual-model routing. This scope now also
records the P5/P6 route evidence: QuickSRNet live ROI and app resource probe.
```

Candidate paths:

```text
ROUTE_DECISION.md
MODEL_ROUTE_DECISION.md
EVAL_METRIC_POLICY.md
ROADMAP_NEXT.md
NEXT_ACTION.md
VISUAL_REVIEW_QUEUE.md
SHOWCASE_NARRATIVE.md
SHOWCASE_MATERIALS.md
METRIC_EXTENSION_DECISION.md
AIMET_DECISION.md
REAL_CAMERA_CAPTURE_PLAN.md
NATIVE_YUV_ROI_PLAN.md
docs/prompts/
tools/
```

## Commit 4: QuickSRNet Candidate App Assets

Purpose:

```text
Keep QuickSRNetSmall app fixed-sample validation assets separate from the QNN
Delegate Real-ESRGAN milestone.
```

Candidate paths:

```text
RB5VisionLab/app/src/main/assets/quicksrnetsmall_w8a8.tflite
RB5VisionLab/app/src/main/assets/case_low_light_div2k0852.png
RB5VisionLab/app/src/main/assets/case_people_scene_div2k0832.png
RB5VisionLab/app/src/main/assets/case_text_signage_urban076.png
```

Boundary:

```text
These are small fixed-sample validation assets. Do not add generated outputs.
```

## Commit 5: EvalHub And Knowledge Base

Purpose:

```text
Record long-lived evaluation and reference indexes.
```

Candidate paths:

```text
eval_hub/
knowledge_base/external_research/README.md
knowledge_base/external_research/**/RESOURCE_CARD.md
```

Warning:

```text
Do not commit cloned repos or PDFs under knowledge_base. They are local cache.
`.gitignore` now ignores `knowledge_base/external_research/**/repo/` and
`knowledge_base/external_research/**/*.pdf`.
```

## Do Not Commit

```text
RB5VisionLab/app/build/
RB5VisionLab/app/.cxx/
RB5VisionLab/app/libs/qtld_tmp/
RB5VisionLab/app/src/main/jniLibs/**/libqnn_net_run_exec.so
RB5VisionLab/app/src/main/jniLibs/**/libqnn_profile_viewer_exec.so
RB5_SR_lab/qnn_local_run/app_quicksr_fixed_*.png
RB5_SR_lab/qnn_local_run/host_quicksr_fixed_sr_512.png
RB5_SR_lab/qnn_local_run/app_strategy_cases/
RB5_SR_lab/results/
RB5_SR_lab/export_assets/
evalhub_data/
project_assets/
knowledge_base/external_research/**/repo/
knowledge_base/external_research/**/*.pdf
*.apk
```
