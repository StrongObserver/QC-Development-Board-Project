# RB5 Gen2 Interview Talk Track

Updated: 2026-07-19

## 30-Second Version

```text
I built an Android on-device image enhancement pipeline on Qualcomm RB5 Gen2 /
QCS8550. The app captures CameraX frames, crops a center ROI, runs W8A8 SR
models through QNN TFLite Delegate on HTP, and displays the enhanced result.

The main engineering point was not just running a model. After QNN inference was
down to 1-3ms, I profiled the app path and found the real bottleneck was camera
frame conversion and output processing. I reduced live e2e latency from about
63/65ms to about 10/12ms p50/p95 in the latest app smoke, and used benchmark plus real-camera review
to decide that QuickSRNetSmall should be the live workhorse while Real-ESRGAN
stays as the perceptual comparison and optional post-capture path.
```

## 2-Minute Version

```text
This project is an RB5 Gen2 / QCS8550 Android edge-AI image enhancement
pipeline. I started from the basic app path: CameraX ImageAnalysis, ROI crop,
TFLite super-resolution, and display. Then I moved the deployment path from
CPU/GPU experiments to QNN TFLite Delegate on HTP.

The first stable milestone was Real-ESRGAN W8A8 through QNN Delegate. The key
integration issue was not the model itself, but making the Android app process
load the correct QNN HTP runtime and skel library. Packaging
libQnnHtpV73Skel.so and setting setSkelLibraryDir(nativeLibraryDir) made the HTP
path stable.

After that, I profiled the real app path. QNN inference was already only a few
milliseconds, but full-frame CameraX to Bitmap conversion at 4000x3000 was about
41/43ms p50/p95. Reducing live ImageAnalysis to 1280x960 cut the live ROI path
from about 63/65ms to about 22/25ms. Later buffer reuse, output Bitmap reuse,
and UINT8 output bulk-copy reduced the output path further; the later direct-YUV default QuickSR live smoke is about 10/12ms p50/p95.

I also compared model roles instead of treating PSNR as the only answer.
QuickSRNetSmall is tiny and conservative, so it became the default live ROI
workhorse. Real-ESRGAN is sharper and more perceptual, especially on text and
edges, so I kept it as the QNN/HTP milestone, comparison baseline, and optional
post-capture enhancement path.

Finally, I measured resource and routing risks. Real-ESRGAN to QuickSRNet
switching cost about 369ms, so I did not enable automatic dual-model live
routing. I also tried Kotlin YUV ROI, native YUV ROI, and tensor-ready input.
The tensor-ready path worked but repeated live timing did not beat the default
median, so I kept the default path and documented the boundary.
```

## Numbers To Remember

| Claim | Number |
| --- | ---: |
| Android TFLite CPU Real-ESRGAN baseline | about 579-610ms inference |
| Android TFLite GPU Real-ESRGAN | about 126-148ms inference |
| AI Hub QCS8550 float profile | 5.9ms, 74 ops on HTP, 0 fallback |
| Old 4000x3000 live ROI app e2e | about 63/65ms p50/p95 |
| Current default QuickSR live e2e after output reuse | 19.0/24.7ms p50/p95 |
| Current default direct-YUV QuickSR live e2e | 10/12ms p50/p95 |
| Historical output-bulk-copy sustained smoke | 15/20ms -> 16/21ms first/last p50/p95 |
| 120s sustained default live | 20/25ms -> 21/26ms first/last p50/p95 |
| Real-ESRGAN -> QuickSRNet switch | about 369ms |
| QuickSRNetSmall W8A8 model size | about 43.7KB |

## Likely Follow-Up Questions

### Why not use Real-ESRGAN as the default live model?

Real-ESRGAN remains useful, but it is more perceptual and aggressive. The
real-camera and benchmark evidence showed that QuickSRNetSmall is safer and
lighter for live ROI. Real-ESRGAN is kept for QNN/HTP milestone evidence,
comparison, and optional post-capture enhancement.

### Why not automatic routing between the two models?

Because switching is not free. The measured Real-ESRGAN -> QuickSRNet switch was
about 369ms, and routing risk was not justified by the current evidence. The
project keeps explicit model control instead of hiding a complex automatic route
behind the live path.

### What was the biggest optimization?

The biggest gain came from profiling the app path, not from changing the model.
QNN inference was already a few milliseconds. The main bottleneck was full-frame
ImageProxy.toBitmap at 4000x3000. Reducing live ImageAnalysis to 1280x960 cut
the path from about 63/65ms to about 22/25ms, and later output conversion work
reduced the latest default live smoke to about 10/12ms.

### Did you implement zero-copy?

No. I deliberately did not claim zero-copy. I tested Kotlin YUV ROI, native YUV
ROI, and tensor-ready input. Native/tensor-ready paths were technically valid,
but repeated live timing did not justify replacing the default path yet. True
zero-copy would require a different level of Android buffer and QNN memory
integration.

### How did you judge quality?

I used fixed benchmark cases, real-camera contact sheets, and visual review
labels. PSNR/SSIM are treated as fidelity evidence, not final judgment. This is
important because perceptual SR can look sharper while damaging text, faces, or
structure.

## Boundary

Do not claim:

```text
QuickSRNet is globally better than Real-ESRGAN
automatic dual-model routing is product-ready
true zero-copy is implemented
full power/perf-watt is characterized
```

Claim:

```text
I built and profiled an Android QNN/HTP SR pipeline, identified the true live
bottlenecks, validated model roles with benchmark and real-camera evidence, and
made a defensible route decision from latency, quality, memory, and product
risk.
```
