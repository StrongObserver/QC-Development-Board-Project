# Resume Project Draft

Updated: 2026-07-18

## Chinese Version

**RB5 Gen2 / QCS8550 端侧 AI 画质增强 Pipeline 与 QNN 部署优化**  
个人项目，负责人

- 在 Qualcomm RB5 Gen2 / QCS8550 Android 平台上搭建 CameraX -> ROI 裁剪 -> TFLite SR -> QNN TFLite Delegate / HTP -> 屏幕显示的端侧画质增强链路，完成固定样张与实时 ROI 两条验证路径。
- 将 Real-ESRGAN W8A8 TFLite 接入 QNN Delegate，打通 HTP 后端与 `libQnnHtpV73Skel.so` app 内加载配置；固定样张 QNN inference 约 `4-5ms`，当前复验固定样张 total 约 `29ms`。
- 通过 app 侧分段 profiling 定位真实瓶颈：QNN inference 约 `3ms`，而 4000x3000 `ImageProxy.toBitmap()` 曾达 `41/43ms` p50/p95；将 live ImageAnalysis 收敛到 1280x960 后，live ROI e2e 从约 `63/65ms` 降到 `22/25ms`。
- 引入 QuickSRNetSmall W8A8 作为轻量 live ROI 候选，模型体积约 `43.7KB`；经 QNN Delegate live ROI 验证，P5 后 e2e 约 `19/24ms` p50/p95，5 分钟短持续运行无明显延迟漂移。
- 进一步优化 app 后处理路径，复用 TFLite input/output buffer 和像素数组，并将 live evidence sample copy 从每帧降为每 30 帧；Real-ESRGAN W8A8 postprocess 从约 `14/16ms` 降到 `10/13ms`，QuickSRNetSmall 从约 `15/18ms` 降到 `11/14ms`。
- 建立小型 SR 评测与工程闭环：固定 24-case benchmark、loop_state 机制、EvalHub 生命周期评测索引、Pass/Conditional/Fail 视觉 review、模型路线决策文档；明确 PSNR/SSIM 仅作 fidelity evidence，最终质量保留 visual veto。
- 基于模型体积、latency、初始化、内存和切换成本做工程路线判断：Real-ESRGAN -> QuickSRNet 动态切换约 `369ms`，因此不默认做自动双模型 live routing；当前路线为 QuickSRNetSmall 负责 live ROI，Real-ESRGAN 保留为 QNN/HTP 部署里程碑、对照基线和可选后处理/离线感知增强。

## English Version

**RB5 Gen2 / QCS8550 Edge AI Image Enhancement Pipeline with QNN Deployment Optimization**  
Personal project, owner

- Built an Android edge-AI image enhancement pipeline on Qualcomm RB5 Gen2 / QCS8550: CameraX -> ROI crop -> TFLite SR -> QNN TFLite Delegate / HTP -> display, with both fixed-sample and live-ROI validation paths.
- Integrated Real-ESRGAN W8A8 TFLite through QNN Delegate on HTP, including app-side `libQnnHtpV73Skel.so` packaging and `setSkelLibraryDir` configuration; fixed-sample QNN inference is around `4-5ms`, with current fixed-sample total around `29ms`.
- Profiled the real app path and found inference was not the live bottleneck: QNN inference was around `3ms`, while 4000x3000 `ImageProxy.toBitmap()` reached `41/43ms` p50/p95. Reducing live ImageAnalysis to 1280x960 cut live ROI e2e from about `63/65ms` to `22/25ms`.
- Added QuickSRNetSmall W8A8 as a lightweight live-ROI candidate with a model size around `43.7KB`; after QNN Delegate live-ROI validation and P5 optimization, e2e is about `19/24ms` p50/p95, with no meaningful drift in a 5-minute short sustained run.
- Optimized app postprocess overhead by reusing TFLite input/output buffers and pixel arrays, and reducing live evidence copying from every frame to every 30 frames; Real-ESRGAN W8A8 postprocess improved from about `14/16ms` to `10/13ms`, and QuickSRNetSmall from about `15/18ms` to `11/14ms`.
- Built a compact SR evaluation loop: fixed 24-case benchmark, machine-readable `loop_state`, EvalHub lifecycle evaluation index, Pass/Conditional/Fail visual review, and route-decision docs. PSNR/SSIM are treated as fidelity evidence, while visual veto remains the final quality decision.
- Made the model route decision from latency, model size, init/memory/switching cost, and quality tradeoffs. Since Real-ESRGAN -> QuickSRNet switching costs about `369ms`, automatic dual-model live routing is not the default. Current route: QuickSRNetSmall for live ROI; Real-ESRGAN as the QNN/HTP deployment milestone, comparison baseline, and optional post-capture/offline perceptual enhancement path.

## Boundary

Do not claim:

```text
true zero-copy implementation
full power/perf-watt characterization
automatic dual-model routing product readiness
QuickSRNet globally better than Real-ESRGAN
```

Do not interpret these boundaries as the final ambition of the project. They
only define what is currently evidenced enough to claim.
