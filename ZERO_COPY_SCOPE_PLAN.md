# RB5 Zero-Copy Scope Plan

Updated: 2026-07-23

## Current Boundary

Current default live path:

```text
CameraX PlaneProxy direct ByteBuffer
-> native center ROI / rotation / YUV->RGB
-> UINT8 NHWC tensor input
-> QNN TFLite Delegate / HTP
-> display
```

This is a measured direct-YUV data-path win. It is not true QNN input
zero-copy, because the app still stages RGB bytes into the TFLite input tensor.

Current baseline:

```text
20-minute native staging direct-YUV run:
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260723_native_staging_default_live_roi_20min
frames=35719
e2e p50/p95/p99=8/9/9ms
nativeRgb p50/p95/p99=4/5/5ms
QNN inference p50/p95/p99=2/2/2ms
```

## Decision

Do not start a large CameraX -> QNN input registration project as the next main
task. The current live path is already below the practical demo target, and
invoke-level shared allocation only showed microsecond-scale gain.

Use a staged plan if this lane is reopened.

## Stage A: Boundary Documentation

Goal:

```text
Keep claims precise: direct PlaneProxy read is implemented; true QNN input
zero-copy is not.
```

Success metric:

```text
All showcase/resume/interview docs avoid "zero-copy" unless they explicitly
say "not true zero-copy".
```

Status: done.

## Stage B: Shared Tensor C API Probe

Goal:

```text
Use TFLite C API + QNN Delegate custom allocation on fixed synthetic input.
No CameraX integration.
```

Success metrics:

```text
normal-vs-shared checksum matches
500 invokes complete
shared allocation is not slower at invoke level
output remains valid 512x512
```

Evidence:

```text
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260723_rknn_shared_memory_phase2_500
normal avg=1028us
shared avg=1004us
delta=-24us
checksum match
```

Status: done as invoke-level feasibility.

## Stage C: Native Staging Buffer Probe

Goal:

```text
Reuse native-side input staging buffers and avoid avoidable allocation churn,
without claiming QNN input buffer registration.
```

Success metrics:

```text
e2e p50 or p99 improves by at least 1ms against the 20-minute direct-YUV
baseline, or allocation/p99 stability improves without quality regression.
MAD/color/rotation checks stay within current direct-YUV boundary.
```

Budget:

```text
1-2 days maximum.
```

Rollback:

```text
Keep current direct-YUV path as default. Any native staging change must be
behind an explicit probe path until it beats current default p50 and p99.
```

Evidence:

```text
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260723_native_staging_default_live_roi_120f
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260723_native_staging_default_live_roi_20min
```

Result:

```text
Before native staging:
  e2e p50/p95/p99=11/12/12ms
  nativeRgb p50/p95/p99=7/8/8ms

After native staging:
  e2e p50/p95/p99=8/9/9ms
  nativeRgb p50/p95/p99=4/5/5ms
  frames=35719, skipped=0 over 20 minutes
```

Status: done. This is a near-zero-copy/staging-buffer win, not QNN input buffer
registration.

## Stage D: True CameraX Buffer Registration Research

Goal:

```text
Determine whether a normal Android app can register CameraX / AHardwareBuffer /
DMA-BUF memory as QNN Delegate input, or whether native QNN C API and platform
permissions are required.
```

Success metrics:

```text
clear API route
clear permission / SELinux boundary
clear rollback to current direct-YUV default
expected latency gain larger than 1ms
```

Budget:

```text
1-2 days research/probe before any implementation.
Full implementation can be 1-3 weeks and is not current mainline.
```

Status: blocked_needs_user / product-scope decision.

## ROI

Near-term ROI is now proven for Stage C: reusing a native-side staging buffer
reduced the live app e2e path from `11/12/12ms` to `8/9/9ms` p50/p95/p99 over
20 minutes. True CameraX buffer registration remains a deeper Runtime topic,
but it is not necessary for the current demo or resume claim.
