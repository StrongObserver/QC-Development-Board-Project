# RB5 Final Interview Package

Updated: 2026-07-20

## One Sentence

```text
I built and profiled an Android/QCS8550 on-device image-enhancement pipeline
that runs W8A8 super-resolution models through QNN TFLite Delegate on HTP, then
made model and data-path decisions from latency, quality, memory, and risk.
```

## 30-Second Pitch

```text
我做的是 RB5 Gen2 / QCS8550 Android 端侧画质增强项目。链路是
CameraX 取实时帧，裁中心 ROI，用 TFLite SR 模型走 QNN Delegate 落到
HTP，再显示增强结果。

项目重点不是单纯把模型跑起来，而是把 pipeline 做成可 profiling、可评测、
可解释取舍的工程闭环。QNN inference 已经只有 1-3ms，真正瓶颈在
CameraX 转 Bitmap 和输出后处理。我把 live ROI e2e 从约 63/65ms 推到
最新 direct-YUV 默认路径 10/12ms p50/p95，并用固定 benchmark 和真实相机小集决定
QuickSRNetSmall 做 live workhorse，Real-ESRGAN 保留为感知增强和
post-capture 对照路线。
```

## 2-Minute Pitch

```text
这个项目起点是把超分模型真正落到 RB5 Gen2 Android 设备上。我先打通
CameraX ImageAnalysis、中心 ROI 裁剪、TFLite 推理和屏幕显示，再做
CPU、NNAPI、GPU、QNN 路径对比。

QNN 侧先用 Real-ESRGAN W8A8 建立部署里程碑。关键问题不是模型结构，
而是 Android app 进程里如何稳定加载 QNN HTP runtime 和 skel。最终有效
路线是 QNN TFLite Delegate，加上打包 libQnnHtpV73Skel.so 并设置
setSkelLibraryDir(nativeLibraryDir)。

跑通后我做 app 分段 profiling，发现 QNN inference 已经只有几毫秒，
老路径慢在 4000x3000 全帧 ImageProxy.toBitmap，约 41/43ms。把 live
analysis 收敛到 1280x960 后，e2e 从约 63/65ms 降到 22/25ms。后面继续
做 buffer reuse、output Bitmap reuse 和 UINT8 output bulk-copy，最新
app smoke 达到 direct-YUV 默认路径 10/12ms。

模型路线上我把 Real-ESRGAN 和 QuickSRNetSmall 分开看。QuickSRNet 更小、
更保守，更适合 live ROI；Real-ESRGAN 更锐、更感知，适合做 QNN/HTP
里程碑、对照和 post-capture tile。我测了双模型切换，约 369ms，所以没有
把自动 routing 做成默认路径。

最后我补了固定 24-case benchmark、真实相机 8-scene 小集、EvalHub
生命周期评测和 loop_state handoff。PSNR/SSIM 只是 fidelity evidence，
最终画质仍保留 visual review veto。
```

## Numbers To Remember

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

## Three Likely Questions

### 1. Why is QuickSRNetSmall the live workhorse?

```text
Because live ROI cares about stable latency, conservative structure, and low
runtime cost. QuickSRNetSmall is much smaller and safer for structure-sensitive
cases. Real-ESRGAN is still useful, but it is more perceptual and aggressive, so
I keep it as the QNN/HTP milestone, comparison baseline, and post-capture path.
```

### 2. What was the biggest engineering optimization?

```text
Profiling showed the bottleneck was not QNN inference. The big win came from
reducing full-frame CameraX conversion and output processing. Moving live
ImageAnalysis from 4000x3000 to 1280x960 cut e2e from about 63/65ms to 22/25ms;
output reuse and UINT8 bulk-copy then pushed the latest smoke to the current direct-YUV default 10/12ms.
```

### 3. Did you implement zero-copy?

```text
No. I tested and documented the boundary instead of over-claiming. Current
Java/Kotlin QnnDelegate does not expose custom tensor allocation. QAIRT shared
memory needs C/C++ APIs like TfLiteQnnDelegateAllocCustomMem and
SetCustomAllocationForTensor, or native QNN rpcmem/QnnMem_register. So true
zero-copy is a separate C++ probe lane, not something already implemented.
```

## Boundaries

Do not say:

```text
QuickSRNet is globally better than Real-ESRGAN.
Automatic routing is product-ready.
True zero-copy has been implemented.
Battery-node power is external-meter perf/watt.
App e2e timing rows prove visual quality.
```

Supported claim:

```text
The project proves a working Android QNN/HTP SR pipeline, shows profiling-driven
data-path optimization, and makes defensible model-route decisions from measured
latency, visual review, memory, and implementation risk.
```

## Evidence Pointers

| Purpose | Path |
| --- | --- |
| Current checkpoint | `CHECKPOINT_REPORT.md` |
| Showcase index | `SHOWCASE_INDEX.md` |
| Detailed evidence package | `SHOWCASE_MATERIALS.md` |
| Longer narrative | `SHOWCASE_NARRATIVE.md` |
| Oral practice script | `INTERVIEW_ORAL_SCRIPT.md` |
| Resume bullets | `RESUME_PROJECT_DRAFT.md` |
