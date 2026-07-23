# RB5 Gen2 Checkpoint Report

Updated: 2026-07-23

## Current State

The project is at a clean, trigger-gated Runtime checkpoint.

```text
QCS8550 Android app Runtime
-> CameraX PlaneProxy direct ByteBuffer
-> native ROI / rotation / YUV->RGB
-> QuickSRNetSmall W8A8 TFLite
-> QNN TFLite Delegate / HTP
-> display at about 10/12ms app e2e p50/p95
```

Local and remote state:

```text
working tree should be clean after the latest push
use `git log --oneline -n 10` for the current commit list
stable rollback tag: rb5-stable-20260720
```

## What Is Proven

| Claim | Evidence |
| --- | --- |
| AI Hub QNN context route works | W8A8 QNN profile p50 about `1.778ms`, NPU 72 |
| Local qnn-net-run route works | full 24-case QNN accelerator p50/p95 about `9.75/10.39ms` |
| Android app QNN/HTP path works | `20260718_app_qnn_delegate_fixed_live_rb5` |
| App bottleneck was not QNN inference | `ImageProxy.toBitmap()` was about `41/43ms` before the 1280x960 fix |
| Current default live route is usable | latest app smoke reaches `10/12ms` e2e p50/p95 |
| RKNN-inspired runner/logging experiment | Explored stream-log collection and live profile slimming, then reverted code; keep as ignored evidence only |
| Output conversion was reduced | latest postprocess p50/p95 is `1/1ms` |
| Board-level power boundary exists | 5-minute direct-YUV mean about `6.30W`, battery-node estimate only |
| Sustained short run is stable enough for showcase | 60s e2e first/last p50/p95 `15/20ms -> 16/21ms` |
| every-N route is classified | `everyN=3` gives about `9.9` effective enhanced FPS, not lower per-frame latency |
| post-capture tile route is available | Real-ESRGAN tile is the quality-priority still route; QuickSR remains speed/conservative baseline |
| route decisions are evidence-based | automatic dual-model live routing is not default because switching costs about `369ms` |

## What Is Not Proven

Do not claim:

```text
true zero-copy
full external-meter perf/watt
automatic live dual-model routing readiness
QuickSRNet is globally better than Real-ESRGAN
fixed-manifest app replay coverage
video product readiness
AI Hub profile, local qnn-net-run profile, and app e2e timing as one number
```

## Current Technical Boundaries

| Area | Status | Boundary |
| --- | --- | --- |
| Output postprocess | closed | Reopen only on regression |
| every-N ImageAnalysis | done | Cadence evidence only, not latency win |
| Java/Kotlin shared memory | blocked_technical | `qtld-release.aar` Java wrapper exposes no custom allocation API |
| C++ shared-memory probe | gated | Only start with target beyond `10/12ms` app e2e and rollback plan |
| AIMET deployable export | blocked_needs_user | Local CLE deployability exists, but remote AI Hub quantize/compile/profile needs explicit approval |
| mixed precision | blocked_technical | Current generated Real-ESRGAN exporter rejects w8a16 |
| LPIPS / NIQE / OCR | blocked_needs_user | Requires visual/metric conflict or text-readability claim |
| CameraX VideoCapture | blocked_needs_user | Requires explicit demo/product need |
| Multi-instance live routing | mainline_not_justified_yet | Probe evidence showed high switch/memory cost; no default-path change kept |

## Commit Checkpoint

Core checkpoint commits pushed to `origin/main`:

```text
4b16bd8 perf(android): optimize live SR output and cadence logging
64b3f08 test(sr-lab): export app e2e logs and temporal state
e7c36b5 docs(route): record app e2e and temporal boundaries
fd78911 docs(showcase): refresh RB5 demo evidence
0a3a8cb docs(eval): record app e2e lifecycle evidence
c43f013 docs(loop): close full-scope trigger gates
be8c35d docs(report): add RB5 checkpoint report
e3768c9 docs(showcase): add RB5 oral interview script
b8f7664 docs(showcase): add final interview package
```

Rollback anchor:

```text
preferred: git revert later exploration commits, then keep main history linear
last resort: reset main to rb5-stable-20260720 only after explicit approval
```

## Verification

```bat
RB5_SR_lab\.venv-eval\Scripts\python.exe -m py_compile RB5_SR_lab\app_e2e_export.py RB5_SR_lab\run_app_live_roi_benchmark.py RB5_SR_lab\run_app_sustained_live_roi.py RB5_SR_lab\run_app_resource_probe.py
git diff --check
cd /d C:\Users\Admin\Desktop\QC-Development-Board-Project\RB5VisionLab
gradlew.bat --no-daemon :app:assembleDebug
adb -s ff5d3ab4 install -r app\build\outputs\apk\debug\app-debug.apk
```

Device smoke:

```text
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260720_every_n3_runner_state_fix_smoke
status: temporal_cadence_validated
parsed_frames: 79
skipped_frames: 158
every_n: 3
```

## Next Trigger

Continue only when one of these becomes true:

```text
1. A concrete W8A8-vs-float failure crop appears.
2. Visual review conflicts with PSNR/SSIM, or a text/OCR claim is required.
3. A deeper zero-copy probe has a clear target beyond the 10/12ms direct-YUV baseline.
4. A video demo/product path is explicitly needed.
5. A longer Runtime stability claim needs 20-30 minute p50/p95/p99, frame, and temperature evidence.
6. A cold/warm init or sticky-memory claim needs a consolidated table or rerun.
```
