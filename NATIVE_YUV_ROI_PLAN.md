# Native / YUV ROI Plan

Updated: 2026-07-19

## Decision Scope

Current scope: `implementation_gate`.

Do not start AHardwareBuffer, DMA-BUF, or true zero-copy work in the current
mainline loop. This is not a ban on deeper data-path exploration.

The next realistic data-path optimization is:

```text
ImageProxy YUV_420_888 -> crop only the center ROI -> RGB 128x128 Bitmap/tensor
```

This should replace full-frame `imageProxy.toBitmap()` in live ROI only after a
small benchmark proves correctness and speed.

## Current State

Current live path:

```text
ImageProxy.toBitmap()
-> cropCenterRoiKeepingLegacyFov(full, 128)
-> optional rotate
-> SuperResolver.enhance(roi Bitmap)
```

Current native path:

```text
processYPlane(yData, width, height, rowStride)
-> OpenCV mean brightness only
```

So native code is already loaded and OpenCV works, but it does not yet produce
RGB ROI input for the SR model.

## Why YUV ROI Is The Next Step

After the 1280x960 data-path fix and P5 postprocess/sample-copy optimization,
the app is already around:

```text
Real-ESRGAN W8A8 live e2e: about 20/25ms
QuickSRNetSmall live e2e: about 19/24ms
```

The remaining full-frame conversion still costs about 4-8ms in recent runs.
YUV ROI conversion is the next reasonable way to attack that without jumping to
fragile zero-copy architecture.

## Proposed Implementation Steps

### Step 1: Kotlin-only ROI Extraction Probe

Purpose:

```text
Prove that center ROI coordinates, rotation, and row/pixel stride handling are correct.
```

Implementation idea:

```text
Read Y, U, V planes from ImageProxy.
Crop only the legacy-FOV center ROI.
Convert the cropped 128x128 area to ARGB/RGB.
Compare visually against current toBitmap()->crop path.
```

Boundary:

```text
Must handle rowStride and pixelStride correctly.
Do not assume contiguous UV data.
```

### Step 2: Native ROI Conversion

Purpose:

```text
Move the hot ROI conversion loop to C++ only after Kotlin probe is correct.
```

JNI shape:

```text
nativeYuvToRgbRoi(
    y, u, v,
    width, height,
    yRowStride,
    uRowStride, vRowStride,
    uPixelStride, vPixelStride,
    cropLeft, cropTop, cropSize,
    outputSide
) -> IntArray or ByteArray RGB
```

Boundary:

```text
Prefer returning a direct RGB tensor-ready buffer later.
First milestone can return ARGB pixels for Bitmap correctness.
```

### Step 3: Tensor-Ready Path

Purpose:

```text
Avoid Bitmap as intermediate before TFLite input.
```

This requires changing `SuperResolver` to accept an RGB byte/float input buffer,
not only a `Bitmap`.

Boundary:

```text
This is a larger contract change. Do it only after Step 1/2 show measurable gain.
```

## Metrics To Require

For each step, compare against current P5 live path:

```text
frameBitmap / ROI conversion p50/p95
preprocess p50/p95
postprocess p50/p95
analyzer wall p50/p95
app e2e p50/p95
visual alignment on saved sample
```

Success threshold:

```text
At least 2-3ms e2e p50 improvement without rotation/color/crop regression.
```

## Risks

| risk | mitigation |
| --- | --- |
| wrong UV pixelStride handling | test on saved side-by-side image before using for route claims |
| color shift | compare against current Bitmap path on same frame |
| rotation mismatch | keep current display rotation logic until proven equivalent |
| too much JNI copy | start with correctness, then move toward direct tensor buffer |
| high-res still sample regression | keep high-res still path separate from live ROI path |

## Current Recommendation

Kotlin-only Step 1 has now been validated as a correctness probe, not as a
replacement path.

Result:

```text
YUV_ROI_PROBE_20251110_055422
frame=1280x960
rotation=270
bitmapMs=8
bitmapCropMs=1
yuvRoiMs=16
mean_abs_diff=0.34
```

Evidence:

```text
C:\Users\Admin\Videos\RB5 gen2\real_camera_showcase\yuv_roi_probe_20251110_055422
```

Interpretation:

```text
The Kotlin-only YUV ROI path is visually aligned with the current Bitmap crop
path, but it is slower than the current toBitmap + crop path in this probe.
Do not replace the live SR path with Kotlin-only YUV ROI.
```

Native probe result:

```text
YUV_ROI_PROBE_20251110_061600
frame=1280x960
rotation=270
bitmapMs=7
bitmapCropMs=1
kotlinYuvRoiMs=14
nativeYuvRoiMs=5
kotlinMAD=0.41
nativeMAD=0.41
```

Native evidence:

```text
C:\Users\Admin\Videos\RB5 gen2\real_camera_showcase\yuv_roi_probe_20251110_061600
```

Interpretation:

```text
The native C++ ROI conversion is visually aligned and faster than both the
Kotlin-only YUV path and this run's Bitmap+crop timing. It is promising, but it
is still only a one-frame probe and does not yet prove a 2-3ms p50 app e2e gain.
Do not switch the default live SR path until native ROI is tested inside the
live path with repeated p50/p95 timing.
```

Next valid performance-lane step:

```text
Use the native ROI conversion in an isolated live-path experiment or move toward
a tensor-ready input buffer. Keep the current Bitmap path as default until
native/tensor-ready evidence shows at least 2-3ms p50 e2e improvement without
color/crop/rotation regression.
```

Tensor-ready single-frame probe:

```text
TENSOR_READY_PROBE_20251110_064501
frame=1280x960
rotation=270
bitmapMs=8
bitmapCropMs=2
nativeRgbMs=8
bitmapEnhanceWall=27
rgbEnhanceWall=12
bitmapPath=37
rgbPath=20
inputMAD=0.49
outputMAD=0.74
```

Tensor-ready evidence:

```text
C:\Users\Admin\Videos\RB5 gen2\real_camera_showcase\tensor_ready_probe_20251110_064501
```

Interpretation:

```text
The tensor-ready probe is visually aligned and shows a strong single-frame
path reduction by bypassing Bitmap input preparation. This is the first
positive evidence that native ROI + RGB bytes can matter at the SR pipeline
level, not only at the isolated ROI conversion level.

Boundary: this is still a one-frame probe and includes some debug image
generation work. Do not switch the default live path yet. The next step should
be an isolated repeated live-path benchmark that uses native RGB bytes for
QuickSRNet input and reports p50/p95 against the current Bitmap default.
```

Repeated tensor-ready live benchmark:

```text
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20251110_tensor_ready_live_roi_1280x960
parsed_frames=167
current Bitmap default e2e p50/p95: 19.0 / 26.3 ms
tensor-ready e2e p50/p95: 20.0 / 25.7 ms
current Bitmap default analyzer p50/p95: 21.0 / 29.0 ms
tensor-ready analyzer p50/p95: 21.0 / 26.7 ms
```

Decision:

```text
mainline_not_justified_yet
```

Interpretation:

```text
The tensor-ready live path is technically valid, but repeated live timing does
not meet the promotion gate. It slightly improves p95 analyzer/e2e but does not
improve p50 app e2e, so the default Bitmap live path should remain in place.

This is not a dead end. It means a future performance experiment must remove
more than Bitmap input preparation, likely by reducing output/postprocess cost
or avoiding extra debug/Bitmap work in a deeper tensor-ready path.
```

Output reuse follow-up:

```text
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20251110_output_reuse_default_live_roi
previous default e2e p50/p95: 19.0 / 26.3 ms
output-reuse e2e p50/p95: 19.0 / 24.7 ms
previous default analyzer p50/p95: 21.0 / 29.0 ms
output-reuse analyzer p50/p95: 21.0 / 26.0 ms
```

Interpretation:

```text
Reusing the live output Bitmap does not improve p50, but it improves tail
latency and is low risk. Keep the output-reuse change. The default path remains
Bitmap input + QuickSRNetSmall/QNN; tensor-ready live remains experimental.
```
