# Commit Plan

Updated: 2026-07-20

## Current Local Closeout Plan

The current worktree contains a verified follow-up after the pushed
`93e6d07 docs(loop): close RB5 long-loop queue` checkpoint.

Current logical commit split:

```text
1. perf(android): optimize live SR output and cadence logging
2. test(sr-lab): export app e2e logs and temporal state
3. docs(route): record app e2e and temporal boundaries
4. docs(showcase): refresh RB5 demo evidence
5. docs(eval): record app e2e lifecycle evidence
6. docs(loop): close full-scope trigger gates
```

Explicit path groups:

```text
Commit 1:
RB5VisionLab/app/src/main/java/com/cyf/rb5visionlab/MainActivity.kt
RB5VisionLab/app/src/main/java/com/cyf/rb5visionlab/SuperResolver.kt

Commit 2:
RB5_SR_lab/app_e2e_export.py
RB5_SR_lab/run_app_live_roi_benchmark.py
RB5_SR_lab/run_app_sustained_live_roi.py

Commit 3:
AIMET_DECISION.md
APP_DEFAULT_MODEL_DECISION.md
HARNESS_LOOP_ENGINEERING.md
LOOP_TASK_QUEUE.md
METRIC_EXTENSION_DECISION.md
MODEL_ROUTE_DECISION.md
NATIVE_YUV_ROI_PLAN.md
NEXT_ACTION.md
PROJECT_ENTRYPOINTS.md
PROJECT_FULL_SCOPE_LEDGER.md
ROADMAP_NEXT.md
ROUTE_DECISION.md

Commit 4:
README.md
DEMO_RUNBOOK.md
INTERVIEW_TALK_TRACK.md
RESUME_PROJECT_DRAFT.md
SHOWCASE_INDEX.md
SHOWCASE_MATERIALS.md
SHOWCASE_NARRATIVE.md

Commit 5:
eval_hub/README.md
eval_hub/EVAL_SYSTEM_FREEZE.md

Commit 6:
PROJECT_FULL_SCOPE_LEDGER.md
LOOP_TASK_QUEUE.md
NEXT_ACTION.md
ROUTE_DECISION.md
COMMIT_PLAN.md
```

Verification already run for this closeout:

```bat
RB5_SR_lab\.venv-eval\Scripts\python.exe -m py_compile RB5_SR_lab\app_e2e_export.py RB5_SR_lab\run_app_live_roi_benchmark.py RB5_SR_lab\run_app_sustained_live_roi.py RB5_SR_lab\run_app_resource_probe.py
git diff --check
cd RB5VisionLab && gradlew.bat --no-daemon :app:assembleDebug
adb -s ff5d3ab4 install -r RB5VisionLab\app\build\outputs\apk\debug\app-debug.apk
RB5_SR_lab\.venv-eval\Scripts\python.exe RB5_SR_lab\run_app_live_roi_benchmark.py --use-app-default --every-n 3 --min-frames 12 --duration-s 8 --timeout-s 30 --run-id 20260720_every_n3_runner_state_fix_smoke
```

Device smoke result:

```text
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260720_every_n3_runner_state_fix_smoke
status: temporal_cadence_validated
parsed_frames: 79
skipped_frames: 158
every_n: 3
```

Additional trigger-gate evidence:

```text
QAIRT shared-memory tutorial confirms TfLiteQnnDelegateAllocCustomMem +
SetCustomAllocationForTensor is a C/C++ route.
QNN SampleAppSharedBuffer confirms rpcmem/QnnMem_register native route.
`javap` on `qtld-release.aar` confirms Java QnnDelegate/Options do not expose
custom tensor allocation APIs.
```

Do not stage:

```text
.state/
RB5_SR_lab/__pycache__/
RB5VisionLab/.gradle/
RB5VisionLab/app/build/
evalhub_data/
external result folders under C:\Users\Admin\Videos\
```

## Historical Plan

This file records how the large RB5 checkpoint was split. The split has already
been committed and pushed. Keep this file as a rollback/staging reference for
future work; do not treat it as an unfinished commit TODO.

Current pushed checkpoint:

```text
e30141c docs(loop): scope negative evidence gates
```

Pushed commits in order:

```text
db0a6bf feat(app): add QNN delegate SR path
fe55bc9 test(sr-lab): add RB5 loop evidence runners
23350a3 docs(sr): record RB5 route decisions
7c114d0 feat(sr): add QuickSRNet candidate assets
3c3feb8 docs(eval): add EvalHub and research indexes
0e92191 docs(showcase): add RB5 resume draft
0e4cb83 docs(app): keep explicit SR model selection
e30141c docs(loop): scope negative evidence gates
```

The worktree was clean after push. Continue to stage explicit paths only; do not
use `git add .`.

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
