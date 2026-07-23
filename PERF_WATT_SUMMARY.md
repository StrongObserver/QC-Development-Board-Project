# RB5 Perf/Watt Summary

Updated: 2026-07-23

## Scope

This file records board-level battery-node power evidence for the current
default live ROI path. It is not external power-meter evidence.

Current default path:

```text
CameraX PlaneProxy direct ByteBuffer
-> native staging RGB buffer
-> UINT8 NHWC tensor input
-> QuickSRNetSmall W8A8
-> QNN TFLite Delegate / HTP
-> display
```

## Current 20-Minute Evidence

Timing:

```text
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260723_native_staging_default_live_roi_20min
frames=35719
skipped=0
app e2e p50/p95/p99=8/9/9ms
nativeRgb p50/p95/p99=4/5/5ms
QNN inference p50/p95/p99=2/2/2ms
duration_s=1200.071
```

Power:

```text
C:\Users\Admin\Desktop\QC-Development-Board-Project\RB5_SR_lab\results\power_probe\20260723_power_live_native_staging_20min
mean_power=4.959W
min/max=4.653/5.964W
energy=5947.125J
temperature=24.0C -> 24.0C
```

Derived estimate:

```text
enhanced_fps=29.764
energy_per_enhanced_frame=166.498mJ
```

## Boundary

These numbers use rooted `/sys/class/power_supply/battery/current_now` and
`voltage_now`:

```text
abs(current_now * voltage_now) / 1,000,000,000
```

Use this only as board-level power/energy evidence. Do not call it external
meter perf/watt or product-grade battery-life characterization.
