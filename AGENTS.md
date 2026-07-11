# QC Development Board Project — AI Agent Entry

This is the repository-level entrypoint for future AI agents. Keep it concise:
use it for routing, verified state, and rules. Do not turn it into a progress
log; detailed milestones belong in the project context document.

## First Read

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
- Main goal: build a resume-ready RB5 Gen2端侧 AI 画质增强 pipeline while also
  learning real engineering workflow.
- Work style: single `main` branch, small verified steps, no branch workflow
  unless explicitly requested.
- Priority order:
  1. Implement important, demonstrable milestones first.
  2. Keep optional/low-value ideas for later or discard them.
  3. Learning matters, but a working, measurable demo comes first.

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
-> ImageAnalysis 640x480 YUV_420_888
-> Y plane byte[] into C++
-> native OpenCV cv::Mat
-> cv::mean brightness result shown/logged
```

Current SR demo chain:
```
CameraX frame
-> center 128x128 ROI
-> TFLite Real-ESRGAN float CPU inference
-> 512x512 enhanced result on screen
-> per-stage timing in UI / Logcat
```

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

## Project 1 Roadmap (model-first)

旧的 "5-frame capture/brightness" 计划已废弃：策略要等“增强能力”先有，故改为模型优先。
完整阶段 A–F 见 `RB5 Gen2_AI上下文.md` 的“下一步计划”，此处只记主线状态。

- [done] A1 — PC float inference 跑通。standalone `SRVGGNetCompact` 加载
  `realesr-general-x4v3.pth`，128x128 LR -> 512x512 (×4)，CPU ~0.5s/帧；视觉上明显比
  bicubic 锐。PSNR/SSIM 反而略低属 GAN-SR 感知-失真权衡，印证“别只看 PSNR”。
- [done] A2 — 浮点 TFLite 导出 + 双重一致性验证通过。I/O：输入
  `image[1,128,128,3]` f32 NHWC RGB /255；输出 `upscaled_image[1,512,512,3]` f32 [0,1]。
  QCS8550 真机跑分：**5.9ms，74 算子全落 NPU（0 CPU 回退）**，峰值内存 3–7MB。
- [done] B3 — 浮点 TFLite 在 Android【CPU】上对 assets 静态图跑通、增强图上屏。
  依赖 `org.tensorflow:tensorflow-lite:2.16.1`；RB5(QCS8550) 实测 **592–751ms**。
- [done] B5 — 分段计时已加：capture / preprocess / inference / postprocess / e2e。
- [done] C6 — CameraX 当前帧中心 128x128 ROI 实时超分上屏。RB5(QCS8550) CPU：
  inference ~600ms、e2e ~620ms（~1.6fps，CPU baseline，发卡属正常）。**第一验收已达成。**
- [next] 优化 / 第二验收：优先 D7（TFLite 换 NNAPI/GPU delegate 提速 + 后端对比）或
  E10（QNN/NPU——A2 已证明该模型 NPU 仅 5.9ms）；B4（预处理下沉 native）、D8（w8a8 量化）随后。

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
