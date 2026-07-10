# RB5VisionLab AI Handoff

> 本文件是 Codex 的项目记忆，同时被 Claude Code 通过 `@AGENTS.md` 注入为共享上下文。
> 它是 Claude 与 Codex 的 single source of truth：设备、已验证链路、命令、native
> 注意事项、commit 规则、下一步，都以本文件为准。谁完成一步，谁负责更新它。

## Project
- Device: Qualcomm RB5 Gen2 / QCM8550 / Android 13 / arm64-v8a.
- App: `RB5VisionLab`, package `com.cyf.rb5visionlab`.
- Main goal: build a small, demonstrable camera/imaging pipeline on RB5.
- Work style: single `main` branch, small commits, no branch workflow unless explicitly requested.

## Current Verified Chain
```
Android Kotlin app
-> JNI / C++
-> CameraX Preview
-> ImageAnalysis 640x480 YUV_420_888
-> Y plane byte[] into C++
-> native OpenCV cv::Mat
-> cv::mean brightness result shown/logged
```

## Important Commands
```
JAVA_HOME=/opt/android-studio/jbr ./gradlew --no-daemon :app:assembleDebug
adb install -r app/build/outputs/apk/debug/app-debug.apk
adb shell am start -n com.cyf.rb5visionlab/.MainActivity
adb logcat -d | grep -E 'RB5|RB5_CAMERA|RB5_NATIVE|AndroidRuntime|UnsatisfiedLinkError'
adb shell am force-stop com.cyf.rb5visionlab
```

## Native/OpenCV Notes
- OpenCV dependency: `org.opencv:opencv:4.12.0`.
- Gradle `prefab = true` is required for CMake.
- C++ STL must be shared: `-DANDROID_STL=c++_shared`.
- CMake package/target: `find_package(OpenCV REQUIRED CONFIG)` and `OpenCV::opencv_java4`.
- Native load order in Kotlin: `opencv_java4` before `rb5visionlab`.

## Commit Rules
- Commit to `main` after each verified step.
- Commit message format: `area: short result`.
- Good examples:
  - `camera: add CameraX preview and analysis`
  - `native: pass Y plane to OpenCV`
  - `docs: record camera pipeline milestone`
- Each commit should include only one logical step.
- Before commit, run the relevant build or device verification and mention it in the commit body.
- Do not commit generated build outputs, `.gradle`, `.cxx`, `.idea/workspace.xml`, APKs, or `local.properties`.

## Project 1 Roadmap (model-first)
旧的 "5-frame capture/brightness" 计划已废弃：策略要等"增强能力"先有，故改为模型优先。
完整阶段 A–F 见 `RB5 Gen2_AI上下文.md` 的"下一步计划"，此处只记主线状态。
- [done] A1 — PC float inference 跑通。standalone `SRVGGNetCompact` 加载
  `realesr-general-x4v3.pth`，128x128 LR -> 512x512 (×4)，CPU ~0.5s/帧；视觉上明显比
  bicubic 锐，PSNR/SSIM 反而略低（GAN-SR 感知-失真权衡 + 干净下采样≠训练退化，属预期，
  印证文档"别只看 PSNR"）。PC 工作区（**不在本仓库**，纯探索）：
  `/home/cyf/AndroidStudioProjects/RB5_SR_lab`（`infer_realesrgan.py` + weights/inputs/results）。
  注意：torch 2.9 下 basicsr/realesrgan 因 `torchvision.transforms.functional_tensor`
  被移除而 import 失败，所以自带最小 arch、绕开这两个包。
- [done] A2 — 浮点 TFLite 导出 + 双重一致性验证通过。
  产物：`RB5_SR_lab/export_assets/real_esrgan_general_x4v3-tflite-float/real_esrgan_general_x4v3.tflite`
  （4.65MB）。I/O：输入 `image[1,128,128,3]` f32 NHWC RGB /255；输出 `upscaled_image[1,512,512,3]` f32 [0,1]。
  QCS8550 真机跑分：**5.9ms，74 算子全落 NPU（0 CPU 回退）**，峰值内存 3–7MB。
  一致性：on-device vs torch PSNR 72.8；本地 litert(`infer_tflite.py`) vs A1 PyTorch PSNR ~94。
  导出要点(可复现)：AI Hub 工具链在隔离 venv `RB5_SR_lab/.venv-aihub`（torch 2.8.0，与系统 2.9.1 并存）；
  装包用国内镜像 `-i https://pypi.tuna.tsinghua.edu.cn/simple`；导出命令需 `yes |` 自动同意 clone 源码、
  且加 `--profile-options="--qairt_version=default"`（服务端已弃用 2.43；注意别加到 compile，tflite 不收）。
- [done] B3 ★ — 浮点 TFLite 在 Android【CPU】上对 assets 静态图跑通、增强图上屏。
  依赖 `org.tensorflow:tensorflow-lite:2.16.1`；`SuperResolver.kt` 加载 assets 模型，
  128→512 ×4（输入 NHWC RGB /255）；按钮触发、后台线程跑、出结果时隐藏相机预览并
  `bringToFront()` 显示。RB5(QCS8550) 实测 **592–751ms (TFLite CPU)**，增强图已上屏。
  注意：app 内分别用 `org.tensorflow.lite.Interpreter`(B3) 与既有 CameraX/JNI；关闭
  interpreter 必须排到推理之后(已在 onDestroy 用同一单线程 executor 串行)。
- [done] B5 — 分段计时已加（capture/preprocess/inference/postprocess/e2e），随 C6 落地。
- [done] C6 ★ — CameraX 当前帧中心 128×128 ROI 实时超分上屏。RB5(QCS8550) CPU：
  inference ~600ms、e2e ~620ms（~1.6fps，CPU 基线，发卡属正常）。**第一验收已达成。**
  UI：结果图铺满到按钮上方；按钮切换"实时超分"开/关。
- [next] 优化 / 第二验收：优先 D7（TFLite 换 NNAPI/GPU delegate 提速 + 后端对比）或
  E10（QNN/NPU——A2 已证明该模型 NPU 仅 5.9ms）；B4（预处理下沉 native）、D8（w8a8 量化）随后。

Keep changes minimal and explain modified files in plain language for the user.

## Collaboration (for Codex)
Claude Code 是主驾驶，你（Codex）被它通过 `codex` MCP 工具叫来时，角色是独立审查 + 边界清晰的单点实现。Claude 负责真机构建/JNI/Gradle/提交，你不要去碰这些工程编排，聚焦被指派的那块。

### 作为审稿人（审 diff 或方案时）
做挑剔、独立的第二双眼睛。换个视角抓 bug，别因为对方写得自信就附和；有问题就说，理由具体到 文件:行号；没问题也明确说"通过"。结合本工程重点排查：
- JNI 边界：Y plane 的 `byte[]` 传入 native 时，长度/步幅（rowStride vs width）、字节拷贝范围有没有错；jbyteArray 的获取/释放有没有泄漏或越界。
- YUV 处理：640x480 YUV_420_888 只取 Y plane 做亮度时，有没有误用带 padding 的 rowStride 当宽度；后续扩展到 UV 时平面偏移是否正确。
- OpenCV native：`cv::Mat` 构造是否拷贝/是否持有会被回收的缓冲；数据类型（CV_8UC1）与通道数是否匹配；`cv::mean` 结果取用是否正确。
- 加载与链接：native load order（`opencv_java4` 先于 `rb5visionlab`）有没有被破坏；改动会不会引入 `UnsatisfiedLinkError`；`c++_shared` STL 假设是否仍成立。
- 性能（项目1相关）：5 帧缓存有没有不必要的整帧深拷贝；计时口径是否一致、是否把首帧冷启动算进了稳态统计。

### 作为专项手（被指派实现单点模块时）
- 只实现被划定的那块（如自包含的 C++ tile/ROI 函数、Python 量化/评测脚本），接口边界严格按 Claude 给的约定，不擅自改动周边文件。
- 遵守上面的 Commit Rules 与 Work style；不提交生成物。

### 输出格式
审查结论第一行给「通过」或「需修改」，然后逐条列：文件:行号 + 问题 + 建议改法，保持简洁。认为整体思路有误时直接指出错在哪，不要绕。
