# Resume Project Draft

Updated: 2026-07-19

## Chinese Version

**RB5 Gen2 / QCS8550 端侧 AI 画质增强 Pipeline 与 QNN 部署优化**  
个人项目，负责人

- 在 Qualcomm RB5 Gen2 / QCS8550 Android 平台上搭建 CameraX -> ROI 裁剪 -> TFLite SR -> QNN TFLite Delegate / HTP -> 屏幕显示的端侧画质增强链路，完成固定样张与实时 ROI 两条验证路径。
- 将 Real-ESRGAN W8A8 TFLite 接入 QNN Delegate，打通 HTP 后端与 `libQnnHtpV73Skel.so` app 内加载配置；固定样张 QNN inference 约 `4-5ms`，当前复验固定样张 total 约 `29ms`。
- 通过 app 侧分段 profiling 定位真实瓶颈：QNN inference 约 `3ms`，而 4000x3000 `ImageProxy.toBitmap()` 曾达 `41/43ms` p50/p95；将 live ImageAnalysis 收敛到 1280x960 后，live ROI e2e 从约 `63/65ms` 降到 `22/25ms`。
- 将默认 live ROI 路线切换为 `QNN + QuickSRNetSmall W8A8 + direct-YUV native tensor input`，保留 Real-ESRGAN 作为 QNN/HTP 里程碑、感知增强/文字边缘对照与可选 post-capture 路径；当前默认 live ROI 验证 `app e2e p50/p95=10/12ms`。
- 进一步优化 app 后处理路径，复用 TFLite input/output buffer、像素数组和 UINT8 输出 byte buffer，减少每帧 sample copy 与 direct buffer 逐通道读取；最新 direct-YUV 默认 live ROI smoke 达到 `app e2e p50/p95=10/12ms`；此前 output bulk-copy 阶段为 `15/19ms`，现已不是最新口径。
- 建立小型 SR 评测与工程闭环：固定 24-case benchmark、真实相机 8-scene showcase set、loop_state 机制、EvalHub 生命周期评测索引、Pass/Conditional/Fail 视觉 review、模型路线决策文档；明确 PSNR/SSIM 仅作 fidelity evidence，最终质量保留 visual veto。
- 基于模型体积、latency、初始化、内存和切换成本做工程路线判断：Real-ESRGAN -> QuickSRNet 动态切换约 `369ms`，因此不默认做自动双模型 live routing；当前路线为 QuickSRNetSmall 负责 live ROI，Real-ESRGAN 保留为 QNN/HTP 部署里程碑、对照基线和可选后处理/离线感知增强。
- 完成 Kotlin/native YUV ROI 与 tensor-ready input 实验：Kotlin YUV ROI 正确但慢，native ROI 单帧更快，tensor-ready 单帧有收益；但 repeated live benchmark 中 tensor-ready e2e p50 不优于默认 Bitmap 路径，因此保留默认路径，仅采用 output Bitmap 复用降低 p95 tail latency。120 秒默认 live run 解析 3551 帧，e2e 首尾 p50/p95 为 `20.0/25.0ms -> 21.0/26.0ms`。

## English Version

**RB5 Gen2 / QCS8550 Edge AI Image Enhancement Pipeline with QNN Deployment Optimization**  
Personal project, owner

- Built an Android edge-AI image enhancement pipeline on Qualcomm RB5 Gen2 / QCS8550: CameraX -> ROI crop -> TFLite SR -> QNN TFLite Delegate / HTP -> display, with both fixed-sample and live-ROI validation paths.
- Integrated Real-ESRGAN W8A8 TFLite through QNN Delegate on HTP, including app-side `libQnnHtpV73Skel.so` packaging and `setSkelLibraryDir` configuration; fixed-sample QNN inference is around `4-5ms`, with current fixed-sample total around `29ms`.
- Profiled the real app path and found inference was not the live bottleneck: QNN inference was around `3ms`, while 4000x3000 `ImageProxy.toBitmap()` reached `41/43ms` p50/p95. Reducing live ImageAnalysis to 1280x960 cut live ROI e2e from about `63/65ms` to `22/25ms`.
- Switched the default live-ROI route to `QNN + QuickSRNetSmall W8A8 + direct-YUV native tensor input`, while keeping Real-ESRGAN as the QNN/HTP milestone, perceptual/text-edge comparison path, and optional post-capture enhancement path. Current default live-ROI validation reaches `app e2e p50/p95=10/12ms`.
- Optimized app postprocess overhead by reusing TFLite input/output buffers, pixel arrays, and a UINT8 output byte buffer, reducing live evidence copying and per-channel direct-buffer reads; latest default live-ROI smoke reached direct-YUV default `app e2e p50/p95=10/12ms` after the earlier output-path optimizations, with a 60-second sustained smoke drifting from `15/20ms` to `16/21ms`.
- Built a compact SR evaluation loop: fixed 24-case benchmark, real-camera 8-scene showcase set, machine-readable `loop_state`, EvalHub lifecycle evaluation index, Pass/Conditional/Fail visual review, and route-decision docs. PSNR/SSIM are treated as fidelity evidence, while visual veto remains the final quality decision.
- Made the model route decision from latency, model size, init/memory/switching cost, and quality tradeoffs. Since Real-ESRGAN -> QuickSRNet switching costs about `369ms`, automatic dual-model live routing is not the default. Current route: QuickSRNetSmall for live ROI; Real-ESRGAN as the QNN/HTP deployment milestone, comparison baseline, and optional post-capture/offline perceptual enhancement path.
- Evaluated Kotlin/native YUV ROI and tensor-ready input paths. Kotlin YUV ROI was correct but slower; native ROI was faster in a single-frame probe; tensor-ready input showed single-frame promise but did not beat the default Bitmap path in repeated live p50. Promoted the direct-YUV native ROI/RGB route after single-frame MAD 0.0 and default live e2e p50/p95 of `10/12ms`.

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
