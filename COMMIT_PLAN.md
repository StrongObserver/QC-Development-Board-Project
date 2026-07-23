# Commit Plan

Updated: 2026-07-23

## Current Closeout Plan - Stage D Probe And Temporal Fix

The current worktree contains the P1-P6 engineering loop after the runtime docs
checkpoint `b42b3c0`. It adds a CameraX direct-YUV -> QNN custom tensor compare
probe, native data-path breakdown logging, optimized-tensor every-N cadence
support, and matching result documentation.

Use explicit staging only. Do not use `git add .`.

## Logical Commit Split

```text
test(runtime): add camera tensor allocation probe
docs(runtime): record stage d and cadence evidence
```

## Explicit Path Groups

Commit 1:

```text
RB5VisionLab/app/src/main/cpp/rb5visionlab.cpp
RB5VisionLab/app/src/main/java/com/cyf/rb5visionlab/MainActivity.kt
RB5_SR_lab/run_qnn_shared_memory_probe.py
RB5_SR_lab/run_app_live_roi_benchmark.py
```

Commit 2:

```text
FINAL_BENCHMARK_TABLE.md
PROJECT_FULL_SCOPE_LEDGER.md
LOOP_TASK_QUEUE.md
NEXT_ACTION.md
COMMIT_PLAN.md
```

## Verification For This Loop

```bat
RB5_SR_lab\.venv-eval\Scripts\python.exe -m py_compile RB5_SR_lab\run_qnn_shared_memory_probe.py RB5_SR_lab\run_app_live_roi_benchmark.py
cd /d C:\Users\Admin\Desktop\QC-Development-Board-Project\RB5VisionLab
set "JAVA_HOME=C:\Program Files\Android\Android Studio\jbr"
gradlew.bat --no-daemon :app:assembleDebug
adb -s ff5d3ab4 install -r RB5VisionLab\app\build\outputs\apk\debug\app-debug.apk
RB5_SR_lab\.venv-eval\Scripts\python.exe RB5_SR_lab\run_qnn_shared_memory_probe.py --phase phase3 --repeats 50 --timeout-s 90 --run-id 20260723_qnn_shared_camera_tensor_phase3_v2
RB5_SR_lab\.venv-eval\Scripts\python.exe RB5_SR_lab\run_app_live_roi_benchmark.py --use-app-default --min-frames 120 --timeout-s 120 --run-id 20260723_native_datapath_breakdown_120f
RB5_SR_lab\.venv-eval\Scripts\python.exe RB5_SR_lab\run_app_fixed_sample_replay.py --assets offline_text_edge_128.png --model QUICKSR_W8A8 --timeout-s 60 --run-id 20260723_qnn_profile_current_apk_recheck
RB5_SR_lab\.venv-eval\Scripts\python.exe RB5_SR_lab\parse_qnn_delegate_profile_buffer.py --profile "C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260723_qnn_profile_current_apk_recheck\profiles\offline_text_edge_128.png_QUICKSR_W8A8_profile.bin" --outdir "C:\Users\Admin\Desktop\QC-Development-Board-Project\RB5_SR_lab\results\qnn_profile_diagnostic\20260723_current_apk_profile_boundary"
RB5_SR_lab\.venv-eval\Scripts\python.exe RB5_SR_lab\run_app_live_roi_benchmark.py --use-app-default --every-n 3 --min-frames 80 --duration-s 30 --timeout-s 90 --run-id 20260723_every_n3_optimized_tensor_fixed
git diff --check
```

## Key Evidence

```text
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260723_qnn_shared_camera_tensor_phase3_v2
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260723_native_datapath_breakdown_120f
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260723_qnn_profile_current_apk_recheck
C:\Users\Admin\Desktop\QC-Development-Board-Project\RB5_SR_lab\results\qnn_profile_diagnostic\20260723_current_apk_profile_boundary
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260723_every_n3_optimized_tensor_fixed
```

## Do Not Stage

```text
RB5_SR_lab/results/
RB5_SR_lab/export_assets/
evalhub_data/
RB5VisionLab/app/build/
RB5VisionLab/app/.cxx/
external result folders under C:\Users\Admin\Videos\
APK files
```

## Historical Closeout Plan - Runtime Documentation Sweep

The current worktree is a documentation-only sweep triggered by the latest oral
template. It aligns the Runtime/Heterogeneous framing, current native-staging
`8/9/9ms` app evidence, current Demo Mode evidence, and trigger-gated
zero-copy/video boundaries.

Use explicit staging only. Do not use `git add .`.

## Logical Commit Split

```text
docs(runtime): align final runtime evidence boundaries
```

## Explicit Path Group

```text
README.md
SHOWCASE_INDEX.md
FINAL_BENCHMARK_TABLE.md
INTERVIEW_ORAL_SCRIPT.md
DEMO_RUNBOOK.md
CHECKPOINT_REPORT.md
PROJECT_ENTRYPOINTS.md
HARNESS_LOOP_ENGINEERING.md
LOOP_TASK_QUEUE.md
PROJECT_FULL_SCOPE_LEDGER.md
COMMIT_PLAN.md
```

## Verification For This Sweep

```bat
git diff --check
rg -n "current.*10/12|Current.*10/12|latest.*10/12|Latest.*10/12|当前.*10/12|target beyond.*10/12|10/12ms direct-YUV baseline|around 10/12ms|display at about 10/12ms|AIMET deployable export \| blocked_needs_user" README.md SHOWCASE_INDEX.md FINAL_BENCHMARK_TABLE.md FINAL_INTERVIEW_PACKAGE.md SHOWCASE_MATERIALS.md SHOWCASE_NARRATIVE.md INTERVIEW_ORAL_SCRIPT.md INTERVIEW_TALK_TRACK.md RESUME_PROJECT_DRAFT.md DEMO_RUNBOOK.md ZERO_COPY_SCOPE_PLAN.md NEXT_ACTION.md CHECKPOINT_REPORT.md PROJECT_ENTRYPOINTS.md LOOP_TASK_QUEUE.md PROJECT_FULL_SCOPE_LEDGER.md HARNESS_LOOP_ENGINEERING.md
rg -n "8/9/9ms|20260723_native_staging_default_live_roi_20min|20260723_demo_mode_direct_yuv_current_timing|runtime-harness-reframe|showcase \| Runtime" README.md SHOWCASE_INDEX.md FINAL_BENCHMARK_TABLE.md FINAL_INTERVIEW_PACKAGE.md SHOWCASE_MATERIALS.md SHOWCASE_NARRATIVE.md INTERVIEW_ORAL_SCRIPT.md INTERVIEW_TALK_TRACK.md RESUME_PROJECT_DRAFT.md DEMO_RUNBOOK.md ZERO_COPY_SCOPE_PLAN.md NEXT_ACTION.md CHECKPOINT_REPORT.md PROJECT_ENTRYPOINTS.md LOOP_TASK_QUEUE.md PROJECT_FULL_SCOPE_LEDGER.md HARNESS_LOOP_ENGINEERING.md
```

No device rerun is required for this sweep because it only updates documents to
point at already-collected evidence.

## Do Not Stage

```text
C:\Users\Admin\Nutstore\1\Typora_save\自己的项目\RB5 Gen2_AI上下文.md
RB5_SR_lab/results/
RB5_SR_lab/export_assets/
evalhub_data/
RB5VisionLab/app/build/
RB5VisionLab/app/.cxx/
external result folders under C:\Users\Admin\Videos\
APK files
```

## Historical Closeout Plan - Runtime Evidence And Native Staging

The current worktree contains the verified follow-up after the Runtime reframe:
stream-log/P99 tooling, AIMET CLE deployability, native staging data-path
optimization, Perfetto trace collection, QNN profile diagnostics, current demo
evidence, and updated showcase/route docs.

Use explicit staging only. Do not use `git add .`.

## Logical Commit Split

```text
1. test(sr-lab): support runtime evidence collection
2. perf(android): reduce direct yuv staging overhead
3. docs(runtime): record final benchmark boundaries
4. docs(demo): update runtime demo and zero-copy scope
```

## Explicit Path Groups

Commit 1:

```text
.gitignore
RB5_SR_lab/compare_qnn_runs.py
RB5_SR_lab/parse_qnn_delegate_profile_buffer.py
RB5_SR_lab/run_app_live_roi_benchmark.py
RB5_SR_lab/run_app_perfetto_trace.py
RB5_SR_lab/run_qnn_smoke_benchmark.py
```

Commit 2:

```text
RB5VisionLab/app/src/main/cpp/rb5visionlab.cpp
RB5VisionLab/app/src/main/java/com/cyf/rb5visionlab/MainActivity.kt
RB5VisionLab/app/src/main/java/com/cyf/rb5visionlab/SuperResolver.kt
```

Commit 3:

```text
FINAL_BENCHMARK_TABLE.md
PERF_WATT_SUMMARY.md
README.md
RESUME_PROJECT_DRAFT.md
SHOWCASE_INDEX.md
SHOWCASE_MATERIALS.md
FINAL_INTERVIEW_PACKAGE.md
PROJECT_FULL_SCOPE_LEDGER.md
LOOP_TASK_QUEUE.md
NEXT_ACTION.md
```

Commit 4:

```text
DEMO_RUNBOOK.md
ZERO_COPY_SCOPE_PLAN.md
COMMIT_PLAN.md
```

## Verification Already Run

```bat
RB5_SR_lab\.venv-eval\Scripts\python.exe -m py_compile RB5_SR_lab\run_app_perfetto_trace.py RB5_SR_lab\run_app_live_roi_benchmark.py RB5_SR_lab\run_qnn_smoke_benchmark.py RB5_SR_lab\compare_qnn_runs.py RB5_SR_lab\parse_qnn_delegate_profile_buffer.py
cd /d C:\Users\Admin\Desktop\QC-Development-Board-Project\RB5VisionLab && gradlew.bat --no-daemon :app:assembleDebug
adb -s ff5d3ab4 install -r RB5VisionLab\app\build\outputs\apk\debug\app-debug.apk
RB5_SR_lab\.venv-eval\Scripts\python.exe RB5_SR_lab\run_app_perfetto_trace.py --duration-s 15 --run-id 20260723_perfetto_direct_yuv_trace_smoke_v4
RB5_SR_lab\.venv-eval\Scripts\python.exe RB5_SR_lab\run_app_live_roi_benchmark.py --use-app-default --min-frames 120 --timeout-s 90 --run-id 20260723_native_staging_default_live_roi_120f
RB5_SR_lab\.venv-eval\Scripts\python.exe RB5_SR_lab\run_app_live_roi_benchmark.py --use-app-default --min-frames 1200 --timeout-s 1500 --duration-s 1200 --run-id 20260723_native_staging_default_live_roi_20min
RB5_SR_lab\.venv-eval\Scripts\python.exe RB5_SR_lab\run_power_probe.py --scenario live_direct_yuv --duration-s 1200 --interval-s 5 --run-id 20260723_power_live_native_staging_20min
RB5_SR_lab\.venv-eval\Scripts\python.exe RB5_SR_lab\parse_qnn_delegate_profile_buffer.py --profile "C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260721_loop_p4_qnn_profile_decode_attempt\profiles\offline_text_edge_128.png_QUICKSR_W8A8_profile.bin" --outdir "C:\Users\Admin\Desktop\QC-Development-Board-Project\RB5_SR_lab\results\qnn_profile_diagnostic\20260723_fixed_sample_profile_boundary"
git diff --check
```

P6 AIMET CLE remote export/profile and local RB5 comparison were also completed:

```text
AI Hub profile succeeds: estimated inference 1.7ms, 72 NPU ops.
Local RB5 full 24-case CLE run: 23 pass + 1 conditional.
CLE vs current W8A8: PSNR -0.011dB, SSIM +0.00180, QNN accelerator +208us.
Decision: keep as quantization due-diligence evidence, do not replace app model.
```

## Key Evidence

```text
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260723_native_staging_default_live_roi_20min
C:\Users\Admin\Desktop\QC-Development-Board-Project\RB5_SR_lab\results\power_probe\20260723_power_live_native_staging_20min
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260723_perfetto_direct_yuv_trace_smoke_v4
C:\Users\Admin\Desktop\QC-Development-Board-Project\RB5_SR_lab\results\qnn_profile_diagnostic\20260723_fixed_sample_profile_boundary
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260723_demo_mode_direct_yuv_current_20s
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260723_demo_mode_direct_yuv_current_timing
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260723_cle_qnn_w8a8_full_rb5
C:\Users\Admin\Desktop\QC-Development-Board-Project\RB5_SR_lab\results\aimet_deployability\20260723_cle_vs_baseline_full_qnn_compare
```

## Do Not Stage

```text
.state/
RB5_SR_lab/__pycache__/
RB5_SR_lab/results/
RB5_SR_lab/export_assets/
RB5VisionLab/.gradle/
RB5VisionLab/app/build/
RB5VisionLab/app/.cxx/
evalhub_data/
external result folders under C:\Users\Admin\Videos\
APK files
```

## Historical Local Closeout Plan

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
