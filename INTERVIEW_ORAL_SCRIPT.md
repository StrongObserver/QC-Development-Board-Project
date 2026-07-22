# RB5 Interview Oral Script

Updated: 2026-07-20

## 30 Seconds

```text
我做的是一个 RB5 Gen2 / QCS8550 Android 端侧画质增强项目。
链路是 CameraX 取实时帧，裁中心 ROI，用 TFLite 模型走 QNN Delegate
落到 HTP，再把增强结果显示出来。

这个项目的重点不是“模型能跑”，而是我把它做成了一个可 profiling、
可评测、可解释取舍的端侧 pipeline。QNN inference 已经只有 1-3ms，
真正瓶颈在 CameraX 转 Bitmap 和输出后处理。我把 live ROI e2e 从
约 63/65ms 优化到最新 direct-YUV 默认路径 10/12ms p50/p95，并用固定 benchmark 和真实
相机场景决定 QuickSRNetSmall 做 live workhorse，Real-ESRGAN 保留
为感知增强和 post-capture 对照路线。
```

## 2 Minutes

```text
这个项目起点是把超分模型真正落到 RB5 Gen2 Android 设备上，而不是只
在 PC 上跑 demo。我先打通 CameraX ImageAnalysis、中心 ROI 裁剪、
TFLite 推理和屏幕显示，然后做 CPU、NNAPI、GPU、QNN 的路径对比。

QNN 侧我先用 Real-ESRGAN W8A8 建立部署里程碑。最关键的坑不是模型
结构，而是 Android app 进程里如何稳定加载 QNN HTP runtime 和 skel
库。最后有效路线是 QNN TFLite Delegate，加上把
libQnnHtpV73Skel.so 打进 app，并调用 setSkelLibraryDir。

跑通之后我没有继续盲目换模型，而是做 app 分段 profiling。结果发现
QNN inference 已经只有几毫秒，老路径真正慢的是 4000x3000 全帧
ImageProxy.toBitmap，大约 41/43ms。把 live analysis 收敛到 1280x960
后，e2e 从约 63/65ms 降到 22/25ms。后面再做 buffer reuse、output
Bitmap reuse 和 UINT8 output bulk-copy，最新 app smoke 达到 direct-YUV 默认路径 10/12ms。

模型路线上，我把 Real-ESRGAN 和 QuickSRNetSmall 分开看。QuickSRNet
更小、更保守，更适合 live ROI；Real-ESRGAN 更锐、更感知，适合做
QNN/HTP 里程碑、对照和 post-capture tile。我也测了双模型切换，约
369ms，所以没有把自动 routing 做成默认路径。

最后我补了固定 24-case benchmark、真实相机 8-scene 小集、EvalHub
生命周期评测和 loop_state handoff。PSNR/SSIM 只是 fidelity evidence，
最终画质仍保留 visual review veto。
```

## Deep-Dive Answers

### 为什么不用 Real-ESRGAN 做默认 live？

```text
因为它和 QuickSRNet 不是同一种取舍。Real-ESRGAN 更感知、更锐，但也
更可能在细结构、低光纹理、文字和人脸上产生激进补细节。QuickSRNetSmall
模型只有约 43.7KB，更保守，live ROI 下 QNN inference 约 1-2ms，
更适合当默认 workhorse。Real-ESRGAN 我保留在 post-capture 和对照路线。
```

### 最大优化点是什么？

```text
不是换模型，而是 profiling 后发现瓶颈不在 NPU inference。QNN 已经很快，
老路径慢在 4000x3000 全帧转 Bitmap 和输出后处理。先把 live analysis
分辨率收敛到 1280x960，再优化输出 buffer，最终把 e2e 从约 63/65ms
推进到 direct-YUV 默认路径 10/12ms。
```

### 有没有做 zero-copy？

```text
没有，我不会把 near-zero-copy 或 buffer reuse 包装成 true zero-copy。
当前 Java/Kotlin QnnDelegate wrapper 不暴露 custom tensor allocation。
QAIRT 文档里的 shared memory 要走 C/C++：
TfLiteQnnDelegateAllocCustomMem + SetCustomAllocationForTensor，或者 native
QNN 的 rpcmem / QnnMem_register。所以目前 true zero-copy 是一个 C++ probe
lane，不是当前 Kotlin 主线已经实现的能力。
```

### 为什么不做自动双模型 routing？

```text
因为 route risk 和切换成本没有被证明值得。Real-ESRGAN -> QuickSRNet
切换约 369ms，这对 live preview 是可感知的。再加上场景分类、功耗和
误判风险还没建立，所以我选择显式模型路线：QuickSRNet 做 live，Real-ESRGAN
做感知增强和 post-capture，而不是隐藏复杂自动策略。
```

## Numbers

| Topic | Number |
| --- | ---: |
| CPU Real-ESRGAN baseline | about `579-610ms` inference |
| GPU Real-ESRGAN | about `126-148ms` inference |
| AI Hub QCS8550 float profile | `5.9ms`, 74 ops on HTP |
| Old app live ROI e2e | about `63/65ms` |
| Latest default app live ROI e2e | `10/12ms` |
| Current default direct-YUV live e2e | `10/12ms` |
| Historical output-bulk-copy sustained smoke | `15/20ms -> 16/21ms` |
| everyN=3 effective enhanced FPS | about `9.9` |
| Real-ESRGAN -> QuickSRNet switch | about `369ms` |
| QuickSRNetSmall W8A8 size | about `43.7KB` |

## Do Not Say

```text
QuickSRNet is globally better than Real-ESRGAN.
Automatic routing is product-ready.
True zero-copy has been implemented.
Current battery-node power is external-meter perf/watt.
The app e2e logs are fixed-manifest visual quality evidence.
```
