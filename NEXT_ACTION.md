# Next Action

## Current Conclusion

Current checkpoint has advanced beyond the previous closeout. The app e2e
schema export, output-path optimization, every-N smoke, shared-memory feasibility
classification, and related handoff updates have been reviewed, verified, and
split into logical commits on local `main`.

The stable deliverable is archived as:

```text
rb5-stable-20260720
```

Future exploration should keep this tag as the rollback anchor.

```text
real-camera capture support
accepted real-camera showcase set
default QNN/QuickSRNetSmall live ROI path
native + tensor-ready ROI probes
tensor-ready repeated live benchmark
output-reuse default live optimization
UINT8 output bulk-copy optimization
EvalHub-compatible app e2e log export
120s default QuickSR live sustained validation
README / demo runbook / interview talk track
showcase index
Nutstore long-term context updated with final closeout and full-scope ledger
```

## Highest Priority

Next priority:

```text
The project is at a clean trigger-gated checkpoint. Continue only when one of
these gates opens:
1. a concrete W8A8-vs-float failure crop appears -> AIMET/CLE or mixed precision;
2. visual review conflicts with PSNR/SSIM or a text-readability claim is needed -> LPIPS/NIQE/OCR diagnostics;
3. shared-memory Phase 1 passed -> compare timing and output validity against the Kotlin/TFLite default path;
4. the user wants a video demo/product path -> CameraX VideoCapture/Recorder protocol and implementation.
```

Do not reopen as unfinished:

```text
QNN Delegate app path
QuickSRNet app/live validation
real-camera minimum showcase set
app default model decision
Kotlin-only YUV ROI correctness probe
native YUV ROI single-frame probe
tensor-ready single-frame probe
tensor-ready repeated live benchmark
output-reuse default live optimization
UINT8 output bulk-copy optimization
EvalHub-compatible app e2e log export
every-N ImageAnalysis smoke
120s default live sustained validation
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

Output-reuse default live ROI:

```text
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20251110_output_reuse_default_live_roi
```

Key numbers:

```text
app e2e p50/p95: 19.0 / 24.7 ms
analyzer p50/p95: 21.0 / 26.0 ms
```

120s sustained default QuickSR live:

```text
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20251110_output_reuse_quicksr_live_roi_120s
```

Key numbers:

```text
parsed frames: 3551
e2e first/last 20% p50/p95: 20.0 / 25.0 ms -> 21.0 / 26.0 ms
battery temperature coarse signal: 24.0C -> 24.0C
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

Native / tensor-ready ROI:

```text
YUV_ROI_PROBE_20251110_061600: nativeYuvRoiMs=5, nativeMAD=0.41
TENSOR_READY_PROBE_20251110_064501: bitmapPath=37ms, rgbPath=20ms, outputMAD=0.74
20251110_tensor_ready_live_roi_1280x960: tensor-ready live e2e p50/p95=20.0/25.7ms
current Bitmap default remains better on p50 after output reuse: 19.0/24.7ms
```

Latest app e2e schema + output-path smoke:

```text
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260720_app_e2e_schema_output_reuse_120f
```

Key numbers:

```text
parsed frames: 163
postprocess p50/p95: 1.0 / 1.0 ms
app e2e p50/p95: 15.0 / 19.0 ms
EvalHub schema row: app_e2e_log.csv
ignored EvalHub mirror: evalhub_data\derived\app_e2e\20260720_app_e2e_schema_output_reuse_120f\app_e2e_log.csv
```

Latest 60s sustained smoke:

```text
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260720_app_e2e_schema_output_reuse_60s
```

Key numbers:

```text
parsed frames: 1763
e2e first/last 20% p50/p95: 15.0 / 20.0 ms -> 16.0 / 21.0 ms
battery temperature coarse signal: 24.0C -> 24.0C
EvalHub schema row: app_e2e_log.csv
```

Every-N ImageAnalysis smoke:

```text
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260720_every_n3_live_roi_60s_final
```

Key numbers:

```text
everyN: 3
enhanced frames: 85
skipped frames: 169
effective enhanced FPS p50/p95: 9.9 / 9.9
per-enhanced-frame e2e p50/p95: 22.0 / 25.0 ms
boundary: reduces enhancement frequency, not the latency of enhanced frames
```

Shared-memory feasibility:

```text
QNN TFLite Delegate C API supports shared memory:
  TfLiteQnnDelegateAllocCustomMem / TfLiteQnnDelegateFreeCustomMem
  TFLite C++ Interpreter::SetCustomAllocationForTensor

Native QNN sample supports shared buffer:
  SampleAppSharedBuffer
  libcdsprpc.so / rpcmem / QnnMem_register

Current Java/Kotlin QnnDelegate wrapper does not expose equivalent custom tensor
allocation APIs. `javap` on `qtld-release.aar` confirms the public Java API only
exposes backend/skel/perf/profile/skip options, not custom allocation.
This is a C++ delegate/native probe lane, not a direct Kotlin SuperResolver patch.
```

Shared-memory Phase 0:

```text
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260720_qnn_shared_memory_phase0
status: shared_memory_alloc_free_validated
inputBytes: 49152
outputBytes: 786432
alignment: 64
boundary: alloc/free only; not tensor binding or true zero-copy
```

Shared-memory Phase 1:

```text
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260720_qnn_shared_memory_phase1
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260720_qnn_shared_memory_phase1_timing
status: shared_memory_tensor_bind_validated
inputBound: true
outputBound: true
delegate: 0
invoke: 0
invoke avg/min/max: 1,051 / 1,010 / 1,436 us over 50 runs
boundary: tensor binding + invoke only; not CameraX buffer binding
```

## Next Engineering Choices

Recommended order:

```text
1. Do not reopen app output postprocess unless a regression appears.
2. Treat every-N as a completed cadence boundary: valid, but not a latency win.
3. Decide whether to build a bounded C API e2e comparison path around
   CameraX/ROI/output after Phase 1 showed ~1.05ms invoke timing, keeping
   rb5-stable-20260720 as rollback anchor.
4. Keep AIMET, mixed precision, LPIPS/NIQE/OCR behind their documented triggers.
5. Full VideoCapture/Recorder waits for an explicit demo/product need.
```
