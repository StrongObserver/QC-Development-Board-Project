# Next Action

## Current Conclusion

The current checkpoint has completed:

```text
real-camera capture support
accepted real-camera showcase set
default QNN/QuickSRNetSmall live ROI path
Kotlin-only YUV ROI correctness probe
two local commits on main
```

Local commits not yet pushed:

```text
47a98de feat(android): add real-camera capture and default QuickSR live path
29c272d docs(showcase): record real-camera route decisions
```

## Highest Priority

Next priority:

```text
Compress the showcase/resume narrative and decide whether to push the two local commits.
```

Do not reopen as unfinished:

```text
QNN Delegate app path
QuickSRNet app/live validation
real-camera minimum showcase set
app default model decision
Kotlin-only YUV ROI correctness probe
```

## Verified Evidence

App default live ROI:

```text
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20251110_app_default_quicksr_live_roi_smoke
```

Key numbers:

```text
resolved model: QUICKSR_W8A8
parsed frames: 95
QNN inference p50/p95: 1.0 / 1.0 ms
app e2e p50/p95: 19.0 / 26.3 ms
```

Real-camera showcase:

```text
C:\Users\Admin\Videos\RB5 gen2\real_camera_showcase\20251110_045328_minimal_real_camera_set
```

Result:

```text
8/8 scenes complete
32/32 standard images valid
status: accepted_with_caveats
no retake required
```

YUV ROI probe:

```text
C:\Users\Admin\Videos\RB5 gen2\real_camera_showcase\yuv_roi_probe_20251110_055422
```

Result:

```text
MAD=0.34
bitmapMs=8
bitmapCropMs=1
yuvRoiMs=16
```

Interpretation:

```text
Kotlin-only YUV ROI is visually aligned but slower than the current Bitmap path.
Do not replace the default live SR path with Kotlin-only YUV ROI.
If continuing performance work, use a native C++ or tensor-ready probe with a
2-3ms p50 e2e improvement gate.
```

## Next Engineering Choices

Recommended order:

```text
1. Finish showcase/resume narrative compression.
2. Ask the user whether to push local commits to origin/main.
3. If more engineering work is requested, design a native/tensor-ready ROI probe.
4. Only run sustained power/thermal validation if making sustained-use claims.
5. Keep AIMET/LPIPS/DISTS deferred until their trigger conditions appear.
```
