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

Next valid performance-lane step:

```text
Move the hot ROI conversion loop to native C++ or a tensor-ready buffer only if
more latency reduction is needed. Keep the current Bitmap path as default until
native/tensor-ready evidence shows at least 2-3ms p50 e2e improvement without
color/crop/rotation regression.
```
