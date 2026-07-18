# Visual Review Queue

Updated: 2026-07-18

This file keeps P2 small: review only the evidence that changes the project
route or showcase claim. Metrics are supporting evidence; visual veto owns the
final quality decision.

## Decision Labels

Use exactly one label per item:

```text
pass
conditional
fail
```

Meanings:

| label | Meaning |
| --- | --- |
| `pass` | Good enough for the claimed purpose; no blocking artifact is visible |
| `conditional` | Usable with a clear caveat; keep the caveat in the project story |
| `fail` | Do not use this evidence for the claim until fixed or replaced |

## Review Items

| priority | evidence | file | what to check | expected decision |
| ---: | --- | --- | --- | --- |
| 1 | QNN Delegate fixed sample | `C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260718_app_qnn_delegate_fixed_live_rb5\fixed_sample_contact_sheet.png` | QNN output is nonblank, aligned, not rotated/mirrored, and visibly comparable to bicubic/input | `pass` or `conditional` |
| 2 | App QNN Delegate vs qnn-net-run | `C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260718_app_qnn_delegate_fixed_live_rb5\app_vs_qnn_net_run_contact_sheet.png` | App delegate output and qnn-net-run output are visually aligned; no obvious geometry/color mismatch | `pass` |
| 3 | QuickSRNet vs Real-ESRGAN full host set | `C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260718_145028_quicksrnet_small_vs_realesrgan_w8a8_full_host\contact_sheet.png` | QuickSRNet is safer on structure/text/people cases without unacceptable softness; Real-ESRGAN perceptual sharpness is still acknowledged | `conditional` |
| 4 | Three structure-sensitive app cases | `C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results\20260718_app_strategy_three_case_fixed_compare\contact_sheet.png` | QuickSRNet visually preserves low-light branches, people/face structure, and signage better than Real-ESRGAN | `pass` or `conditional` |

## Minimal Review Table

Fill only this table after looking at the four images:

| evidence | decision | one-line reason | route impact |
| --- | --- | --- | --- |
| QNN Delegate fixed sample | `pass` | APP QNN output is nonblank, aligned, not rotated/mirrored, and sharper than bicubic on the fixed text/edge sample. | Confirms QNN/HTP app milestone |
| App delegate vs qnn-net-run | `pass` | APP QNN Delegate and qnn-net-run outputs are visually aligned; only small pixel-level differences are visible in the amplified diff. | Confirms app output alignment |
| QuickSRNet full host set | `conditional` | QuickSRNet is generally more conservative and structure-safe, while Real-ESRGAN keeps a sharper perceptual style; this supports a tradeoff story, not a global winner claim. | Supports QuickSRNet workhorse candidacy with caveat |
| Three app strategy cases | `conditional` | QuickSRNet is safer on low-light structure and people/face-like content, but text/screen texture still needs caveated presentation. | Supports QuickSRNet for structure-sensitive scenes with caveat |

## Route Boundary

Current engineering route before human visual review:

```text
QuickSRNetSmall is the strongest live ROI workhorse candidate.
Real-ESRGAN remains the QNN/HTP deployment milestone and perceptual/post-capture baseline.
Automatic live dual-model routing remains out of the default path.
```

If any item is marked `fail`, do not rewrite the whole project route
automatically. First decide whether the failure blocks only showcase material,
only QuickSRNet promotion, or the QNN Delegate milestone itself.
