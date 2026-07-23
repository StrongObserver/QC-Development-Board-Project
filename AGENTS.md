# QC Development Board Project — AI Agent Entry

This is the repository-level entrypoint for future AI agents. Keep it concise:
use it for routing, verified state, and rules. Do not turn it into a progress
log; detailed milestones belong in the project context document.

## First Read

0. RB5 Gen2 loop entrypoint. Read this first when the user asks to continue the
   RB5 project, then follow the listed priority order and latest run handoff:
   `C:\Users\Admin\Desktop\QC-Development-Board-Project\PROJECT_ENTRYPOINTS.md`
1. Project background, resume target, roadmap, and milestone history. This file
   is read-only unless the user explicitly asks to maintain it; if editing, obey
   its own maintenance rules first:
   - Windows: `C:\Users\Admin\Nutstore\1\Typora_save\自己的项目\RB5 Gen2_AI上下文.md`
   - Ubuntu: `/home/cyf/Nutstore Files/Typora_save/自己的项目/RB5 Gen2_AI上下文.md`
2. Repository commit and push convention:
   `push_readme.txt`

## AI Tooling

- Ubuntu development: use Codex CLI.
- Windows development: use TRAE CLI / Coco.
- Model choice: use GPT-5.5 when available; do not intentionally downgrade to
  weaker models unless the user explicitly approves.
- There is no Claude-as-lead / Codex-as-helper split in this project anymore.
  The active agent should own the current task end-to-end: gather context, plan,
  implement, verify, explain, and update handoff notes when appropriate.
- Avoid running two agents against the same worktree at the same time. If a
  second agent is used for review, give it complete context and make sure only
  one agent edits files.

## Project

- Device: Qualcomm RB5 Gen2 / QCM8550 / Android 13 / arm64-v8a.
- App: `RB5VisionLab`, package `com.cyf.rb5visionlab`.
- Main goal: build a resume-ready QCS8550端侧 AI Runtime / 模型部署 /
  量化 / 异构性能优化 project. Real-ESRGAN and QuickSRNet are representative
  workloads; the core evidence is QNN/HTP execution, profiling, data-path
  optimization, benchmark discipline, and defensible latency/quality/resource
  tradeoffs.
- Work style: single `main` branch, small verified steps, no branch workflow
  unless explicitly requested.
- Priority order:
  1. Implement important, demonstrable milestones first.
  2. Keep optional/low-value ideas for later or discard them.
  3. Learning matters, but a working, measurable demo comes first.
  4. Time is extremely tight: prefer reusing/adapting proven open-source or compliant internal references over writing fresh implementations from scratch.

## Main Paths

Windows current workspace:
- Repository root: `C:\Users\Admin\Desktop\QC-Development-Board-Project`
- Android app: `C:\Users\Admin\Desktop\QC-Development-Board-Project\RB5VisionLab`
- Host-side SR/model experiments: `C:\Users\Admin\Desktop\QC-Development-Board-Project\RB5_SR_lab`
- Project context document: `C:\Users\Admin\Nutstore\1\Typora_save\自己的项目\RB5 Gen2_AI上下文.md`

Ubuntu original development environment:
- Android app: `/home/cyf/AndroidStudioProjects/RB5VisionLab`
- Host-side SR/model experiments: `/home/cyf/AndroidStudioProjects/RB5_SR_lab`
- Project context document: `/home/cyf/Nutstore Files/Typora_save/自己的项目/RB5 Gen2_AI上下文.md`

Repository:
- Git remote: `https://github.com/StrongObserver/QC-Development-Board-Project`

Important code pointers:
- `RB5VisionLab/app/src/main/java/com/cyf/rb5visionlab/MainActivity.kt`
- `RB5VisionLab/app/src/main/java/com/cyf/rb5visionlab/SuperResolver.kt`
- `RB5VisionLab/app/src/main/cpp/rb5visionlab.cpp`
- `RB5VisionLab/app/src/main/res/layout/activity_main.xml`

## Current Verified Chain

Base camera/native chain:
```
Android Kotlin app
-> JNI / C++
-> CameraX Preview
-> ImageAnalysis YUV_420_888 (initially 640x480; current analyzer may use highest available resolution)
-> Y plane byte[] into C++
-> native OpenCV cv::Mat
-> cv::mean brightness result shown/logged
```

Current default runtime/app chain:
```
CameraX ImageAnalysis
-> PlaneProxy direct ByteBuffer
-> native C++ center ROI / rotation / YUV->RGB
-> UINT8 NHWC tensor input
-> QuickSRNetSmall W8A8 TFLite
-> QNN TFLite Delegate / HTP
-> display
```

Current SR workload chain:
```
CameraX frame
-> Bitmap conversion
-> center ROI cropped with legacy-640-FOV rule, then resized to model input
-> TFLite Real-ESRGAN float inference (CPU / NNAPI / GPU selectable for 128->512)
-> enhanced result on screen
-> per-stage timing in UI / Logcat
-> optional sample saving: input / bicubic baseline / SR output
```

High-quality still-sample chain:
```
highest available CameraX analysis frame (RB5 observed 4000x3000)
-> legacy-FOV center crop -> 256x256 model input
-> 256->1024 Real-ESRGAN TFLite CPU inference
-> save input / bicubic baseline / SR PNGs
```

Key measured baselines so far:
- 128->512 Android TFLite CPU: inference ~579-610ms, e2e ~592-623ms.
- 128->512 Android TFLite NNAPI: no meaningful gain, close to CPU.
- 128->512 Android TFLite GPU delegate: inference ~126-148ms, e2e ~139-161ms (~4x faster than CPU).
- 128->512 W8A8 TFLite baseline: static Qualcomm AI Hub Models asset is integrated; model size ~1.31MB vs float ~4.88MB.
  Host CPU/XNNPACK shows ~1.6-1.9x speedup on fixed cases; RB5 app CPU W8A8 low-light offline sample reported inference ~361ms.
- AI Hub QCS8550 profile for the 128 float model: 5.9ms, 74 ops on NPU, 0 CPU fallback.
- W8A8 QNN context profile on QCS8550 Proxy: p50 ~1.778ms, NPU 72.
- Local RB5 qnn-net-run full 24-case benchmark: QNN accelerator p50/p95 ~9.75/10.39ms.
- Current compiled app default direct-YUV live ROI: e2e p50/p95 ~10/12ms.
- 256->1024 high-res still samples are useful for visual evidence, but not yet a real-time target.

## Important Commands

Ubuntu/dev-board workflow commands recorded from the original environment:
```
JAVA_HOME=/opt/android-studio/jbr ./gradlew --no-daemon :app:assembleDebug
adb install -r app/build/outputs/apk/debug/app-debug.apk
adb shell am start -n com.cyf.rb5visionlab/.MainActivity
adb logcat -d | grep -E 'RB5|RB5_CAMERA|RB5_NATIVE|RB5_SR|AndroidRuntime|UnsatisfiedLinkError'
adb shell am force-stop com.cyf.rb5visionlab
```

Windows notes:
- Use Android Studio terminal or the Windows Gradle wrapper from the repository
  root, for example `RB5VisionLab\gradlew.bat --no-daemon :app:assembleDebug`
  if the Android/JDK environment is configured.
- Hardware/USB/GPU/NPU commands may need the user's real terminal. Provide exact
  commands and ask the user to paste results if the agent cannot access devices.

## Native/OpenCV Notes

- OpenCV dependency: `org.opencv:opencv:4.12.0`.
- Gradle `prefab = true` is required for CMake.
- C++ STL must be shared: `-DANDROID_STL=c++_shared`.
- CMake package/target: `find_package(OpenCV REQUIRED CONFIG)` and
  `OpenCV::opencv_java4`.
- Native load order in Kotlin: `opencv_java4` before `rb5visionlab`.

## Project 1 Roadmap (runtime-first)

旧的 "5-frame capture/brightness" 和单纯“画质增强 App”叙事已废弃。当前项目定位是
`QCS8550 端侧 AI 推理 Runtime 与异构性能优化`：用 Real-ESRGAN /
QuickSRNet 作为 workload，证明模型部署、量化、QNN/HTP 执行、profiling、
数据搬运、功耗与评测闭环。完整阶段和历史证据见 `RB5 Gen2_AI上下文.md`
与最新 showcase / loop 文件；此处只记主线状态。

- [done] A1/A2 — PC PyTorch inference and AI Hub float TFLite export verified. TFLite I/O is
  `image[1,128,128,3]` f32 NHWC RGB /255 -> `upscaled_image[1,512,512,3]` f32 [0,1].
- [done] B3/B5/C6 — Android app runs Real-ESRGAN on assets/camera ROI, shows SR output, and logs
  capture / preprocess / inference / postprocess / e2e timing. **First acceptance gate is done.**
- [done] D7 — Android TFLite backend comparison is done: CPU baseline, NNAPI no gain, GPU delegate ~4x faster.
- [done] D75 — High-resolution CameraX input and legacy-FOV ROI fix are done for 256->1024 still samples.
- [done] D8/QNN/HTP — W8A8 TFLite/QNN context/app QNN Delegate routes are verified through AI Hub,
  local qnn-net-run, and Android app fixed/live evidence.
- [done] Runtime/data path — default app live ROI now uses direct-YUV native tensor input with
  QNN/QuickSRNetSmall, around 10/12ms e2e p50/p95.

## Evaluation Baseline Policy

The project currently has working runtime/app paths; evaluation exists to keep
performance, correctness, and quality claims separate. Before the next
optimization, use the fixed harness rather than adding features blindly:

- Fixed inputs: keep a tiny, representative image/ROI set covering text/edges/texture/face-or-object/low-light if available.
- Comparisons: always save or compute input, bicubic baseline, float SR, and candidate SR output on the same input.
- Runtime/performance metrics: record model size, preprocess/inference/postprocess/e2e latency, backend, HTP/QNN evidence, resolution, device, memory/power boundary, and cold/warm status.
- Quality metrics: use PSNR/SSIM only as distortion references; for GAN SR they may disagree with visual quality. Add crop-level visual judgment
  for artifacts such as oversharpening, ringing, texture hallucination, color shift, and text deformation.
- Pass/fail gates: define scenario-specific boundaries. For example, a faster backend is not acceptable if it introduces obvious color/geometry
  corruption; a sharper result is not acceptable if text becomes less readable; a larger input is not useful if latency/memory makes the demo unusable.
- Evidence discipline: preserve only the smallest useful set of PNGs/logs/tables; do not commit large generated assets unless explicitly requested.
- Current baseline script: `RB5_SR_lab/eval_baseline.py`. Run it with the local eval venv when available:
  `RB5_SR_lab/.venv-eval/Scripts/python.exe RB5_SR_lab/eval_baseline.py`. It writes
  `RB5_SR_lab/results/eval_baseline/baseline_metrics.csv`,
  `RB5_SR_lab/results/eval_baseline/acceptance_review_template.csv`, and side-by-side contact sheets under
  `RB5_SR_lab/results/eval_baseline/contact_sheets/`.
- Current visual review status: host TFLite-vs-PyTorch consistency cases pass; D7 CPU/GPU camera ROI cases are conditional demo evidence;
  D75 256 still sample currently fails quality acceptance because the SR output does not match the bicubic/input geometry/orientation;
  offline text/edge and low-light/noise cases now exist as fixed RB5 app asset inputs and are conditional until human review fills final decisions.

## Reuse-First Problem Solving

This project is effect-first, not originality-first. When blocked or when a feature looks non-trivial, first look for a working reference:

1. Search GitHub / official samples / existing local scripts for similar SR, TFLite, QNN, AIMET, CameraX, or Android imaging pipelines.
2. If the README looks relevant to the current blocker, clone the project to a scratch location outside tracked source and inspect the actual code path before reimplementing.
3. Reuse, adapt, or rewrite from proven references when it is faster and explainable. Avoid only black-box stitching that cannot be debugged or described in interviews.
4. If public material is insufficient and the user can access company-internal compliant resources, ask the user to query internal AI. Provide a focused prompt asking for document links, repo paths, key files/functions, commands, pitfalls, and minimal snippets.

Internal-AI prompt template:
```text
我在做 RB5 Gen2 / QCS8550 / Android 端侧 AI Runtime、模型部署、量化和异构性能优化项目，当前卡点是：【一句话描述卡点】。
请优先搜索公司内部开放且合规可参考的技术文档、代码仓库、sample、历史项目或最佳实践，重点找：
1. 与 Android CameraX / TFLite / QNN / QAIRT / AIMET / NNAPI / GPU delegate / 超分 / 画质评测 / 端侧 AI pipeline 相关的资料；
2. 能直接说明工程架构、关键 API、命令、性能数据、踩坑和适用边界的内容；
3. 可复用或可借鉴的最小代码路径，而不是只给概念介绍。
请按以下格式返回：最相关的 3-5 个资料或仓库；每个资料最值得看的文件/章节/函数；可直接借鉴的命令/API/代码片段；已知坑点和不适合照搬的地方；如果没有强相关资料，请明确说没有，并给最接近替代方向。
```

When a result is visually useful for interviews, remind the user to save
screenshots, before/after images, short videos, profiling tables, or logs.

## Workflow

- Make minimal, goal-directed changes. Do not refactor or clean unrelated code.
- Environment issues follow the "minimum-intrusion principle": when dependencies,
  SDK/JDK paths, adb, Gradle, or device tooling are missing or conflicting, prefer
  temporary/session-scoped fixes and explicit commands over changing global system
  configuration, rewriting project-local machine files, or reinstalling toolchains.
- If a broad environment change is truly necessary, ask the user first. Explain
  why it is needed, what will be modified, and what damage/risk it may cause
  (for example breaking Android Studio, changing another project's SDK/JDK, or
  affecting an already working device setup).
- Explain modified files in plain Chinese: why this change is needed, what was
  changed, and how to verify it.
- Before coding, check existing local changes with `git status` / `git diff` and
  avoid overwriting user work.
- Prefer small verified steps: build/test/device verification should match the
  scope of the change.
- During device/app verification, if a UI action is hard to simulate reliably via
  adb or scripted commands (for example long press, camera permission prompts,
  physical-device interaction, or a fragile coordinate tap), ask the user to do
  that manual step. Be explicit: what to press/do, what result to watch for, and
  what log/screenshot/result to report back.
- At each verified milestone, remind the user how to preserve the result for the
  resume/project record:
  1. Text results: if they can be represented as text, update the project context
     document directly with the key conclusion, commands, timings, logs, and next
     step.
  2. Image/video results: if screenshots, before/after images, screen recordings,
     or demo videos are needed, tell the user exactly what to capture and where to
     save the files; then document the saved paths and conclusions.
  Keep artifacts minimal and critical: do not ask the user to preserve lots of
  screenshots/videos for every stage. For each milestone, keep only the smallest
  set of evidence that proves the key result, avoids bloating the final showcase,
  and saves time.
- If a non-trivial diff needs independent review, the current agent may ask
  another agent/tool for review, but must provide full context and must not
  blindly follow the review.

## Git Rules

- Single-person workflow on `main`; do not create branches unless requested.
- Commit only after a verified milestone or a small independently revertible
  step. Do not commit automatically unless the user asks.
- Follow `push_readme.txt` for commit subjects:
  `<type>(<scope>): <imperative summary>`
- Use one of: `feat`, `fix`, `perf`, `refactor`, `test`, `build`, `ci`, `docs`,
  `chore`, `revert`.
- Commit body for non-trivial changes should include:
  `Why:`, `Change:`, `Verify:`, `Rollback:`.
- Stage explicit paths; avoid blind `git add .`.
- Push only after the user explicitly asks. Normal push target is `origin main`.
- Never force-push `main` unless the user explicitly approves after risks are
  explained.

## Do Not Commit

- Build outputs: `**/build/`, `**/.gradle/`, `**/.cxx/`, APKs.
- Local machine/IDE files: `**/.idea/`, `local.properties`, `*.iml`.
- Secrets or tokens: `.env*`, AI Hub token files, credentials.
- Large/generated experiment artifacts unless the user deliberately wants them
  tracked. Prefer documenting paths and summary results instead.

## Review Checklist

For code review, be a critical second set of eyes. If there is a problem, cite
`file:line` and suggest a concrete fix; if not, say it passes.

- JNI boundary: Y plane `byte[]` length/stride (`rowStride` vs `width`), copy
  range, and release behavior.
- YUV handling: do not confuse padded `rowStride` with image width; be careful
  when later extending to UV planes.
- OpenCV native: `cv::Mat` construction, data type (`CV_8UC1`), channel count,
  and buffer lifetime.
- Loading/linking: `opencv_java4` must load before `rb5visionlab`; avoid changes
  that introduce `UnsatisfiedLinkError`.
- Performance: keep timing definitions consistent, separate cold start from
  steady state, and avoid unnecessary full-frame deep copies.

## Safety Gate

- Low-risk reads and scoped local edits are OK.
- Ask before destructive actions, broad cleanup, history rewrite, force push,
  system/global environment changes, or actions affecting hardware devices,
  credentials, long-running jobs, or remote state.
