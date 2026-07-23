# Resume Project Draft

Updated: 2026-07-23

## Chinese Version

**QCS8550 端侧 AI 推理 Runtime 与异构性能优化（QNN/HTP / TFLite / AIMET）**
个人项目，负责人

- 在 Qualcomm RB5 Gen2 / QCS8550 Android 平台构建端侧 AI 推理与评测系统，以 Real-ESRGAN / QuickSRNet 为工作负载，打通 TFLite CPU/NNAPI/GPU、AI Hub、`qnn-net-run` 与 Android QNN TFLite Delegate / HTP 三层验证。
- 完成 Real-ESRGAN W8A8 QNN/HTP 真机部署；AI Hub QCS8550 Proxy W8A8 profile p50 约 `1.778ms`，本地 24-case `qnn-net-run` QNN accelerator p50/p95 约 `9.75/10.39ms`，并完成 app 与 runner 同输入输出对齐。
- 对比 TFLite CPU/NNAPI/GPU 与 QNN 后端：Real-ESRGAN CPU inference 约 `579-610ms`，GPU inference 约 `126-148ms`，NNAPI 当前组合无明显收益；进一步将 QuickSRNetSmall W8A8 部署至 HTP，当前 direct-YUV native staging 默认 live ROI e2e 达 `8/9/9ms p50/p95/p99`。
- 通过 app 分段 profiling 定位 4000x3000 `ImageProxy.toBitmap()` 为主要瓶颈（p50/p95 约 `41/43ms`），将 ImageAnalysis 收敛到 1280x960，并实现 native ROI、direct PlaneProxy ByteBuffer 读取、native RGB staging、UINT8 tensor bulk-copy 和 buffer 复用，使 app e2e 从约 `63/65ms` 优化到 `8/9/9ms`。
- 构建 24-case 主门禁、真实相机 8-scene showcase、EvalHub 生命周期评测、Pass/Conditional/Fail review 和 `loop_state` 机制，区分 AI Hub profile、本地 qnn-net-run profile、Android app e2e timing 与人工视觉 veto，避免把不同证据混成同一个性能或质量结论。
- 基于模型体积、latency、初始化、内存和切换成本做路线判断：QuickSRNetSmall 约 `43.7KB`，适合作为 live workhorse；Real-ESRGAN 约 `1.31MB` W8A8，保留为 QNN/HTP 部署里程碑、对照基线和 post-capture 感知增强路径；Real-ESRGAN -> QuickSRNet 切换约 `369ms`，因此不默认启用自动双模型 live routing。
- 完成 AIMET-Torch CLE 可部署性验证：PyTorch FP source route 可导出 ONNX，并完成 AI Hub W8A8 QNN export/profile 与本地 RB5 24-case `qnn-net-run` 对比；CLE 版本可部署但相对当前 W8A8 平均 PSNR 约 `-0.011dB`、QNN accelerator 约 `+208us`，因此不替换当前 app 模型。

## English Version

**QCS8550 On-device AI Inference Runtime and Heterogeneous Performance Optimization**
Personal project, owner

- Built an on-device AI inference and evaluation system on Qualcomm RB5 Gen2 / QCS8550 using Real-ESRGAN and QuickSRNet as workloads, covering TFLite CPU/NNAPI/GPU, AI Hub, local `qnn-net-run`, and Android QNN TFLite Delegate / HTP validation paths.
- Deployed Real-ESRGAN W8A8 through QNN/HTP with three evidence layers: AI Hub QCS8550 Proxy W8A8 p50 about `1.778ms`, local 24-case `qnn-net-run` QNN accelerator p50/p95 about `9.75/10.39ms`, and Android app output alignment against the runner.
- Compared heterogeneous backends: Real-ESRGAN CPU inference about `579-610ms`, GPU inference about `126-148ms`, NNAPI no meaningful gain on the current stack, and QuickSRNetSmall W8A8 through HTP reaching current direct-YUV native-staging app e2e `8/9/9ms p50/p95/p99`.
- Used app-side profiling to identify data movement rather than QNN inference as the live bottleneck: 4000x3000 `ImageProxy.toBitmap()` was about `41/43ms` p50/p95. Reduced ImageAnalysis to 1280x960 and added native ROI, direct PlaneProxy ByteBuffer reads, native RGB staging, UINT8 tensor bulk-copy, and buffer reuse to cut app e2e from about `63/65ms` to `8/9/9ms`.
- Built a repeatable evaluation harness with a 24-case main gate, real-camera 8-scene showcase, EvalHub lifecycle diagnostics, Pass/Conditional/Fail review, and machine-readable `loop_state`, keeping AI Hub profile, qnn-net-run profile, Android app e2e timing, and visual veto as separate evidence lanes.
- Made the model route decision from size, latency, initialization, memory, switching cost, and visual risk: QuickSRNetSmall (~`43.7KB`) is the live workhorse, while Real-ESRGAN W8A8 (~`1.31MB`) remains the QNN/HTP milestone, comparison baseline, and post-capture perceptual route. Automatic dual-model live routing is not default because switching costs about `369ms`.
- Validated AIMET-Torch CLE deployability: PyTorch FP source export to ONNX works, AI Hub W8A8 QNN export/profile succeeds, and local RB5 24-case `qnn-net-run` comparison passes; the CLE route is kept as quantization due-diligence evidence rather than replacing the app model because average PSNR is about `-0.011dB` and QNN accelerator timing is about `+208us` versus the current W8A8 route.

## Boundary

Do not claim:

```text
true zero-copy implementation
full power/perf-watt characterization
automatic dual-model routing product readiness
QuickSRNet globally better than Real-ESRGAN
AI Hub profile, local qnn-net-run, and app e2e as one latency number
```

Do not interpret these boundaries as the final ambition of the project. They
only define what is currently evidenced enough to claim.
