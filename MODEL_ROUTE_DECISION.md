# Model Route Decision

Updated: 2026-07-21

## Decision

Use decision **C** as the current engineering route:

```text
QuickSRNetSmall W8A8 for live ROI.
Real-ESRGAN W8A8 for QNN/HTP deployment milestone, comparison baseline, and
optional post-capture/offline perceptual enhancement.
```

Do not make automatic dual-model live routing the default path yet. This is a
mainline gate, not a permanent rejection of routing experiments.

## Why C, Not D

Automatic routing sounds attractive, but the measured system costs do not make
it free:

```text
Real-ESRGAN -> QuickSRNet switch total: about 369ms
Real-ESRGAN QNN init: about 781ms first init, 679ms later init
QuickSRNet init after switching: about 293ms
QNN/runtime memory remains sticky after close()
```

This means dynamic live switching can create visible cold-path jank and resource
complexity. A single live workhorse plus an optional enhancement path is more
defensible for the current mainline. A future routing experiment is still valid
if it has a clear hypothesis, success metric, budget, rollback, and baseline.

## Why QuickSRNet For Live ROI

QuickSRNetSmall now has enough engineering evidence to be the live ROI
workhorse candidate:

| Evidence | Result |
| --- | --- |
| Android fixed sample through QNN Delegate | pass |
| App-vs-host output alignment | PSNR 46.92dB, MAD 0.939 on same input |
| Optimized default live ROI | e2e p50/p95 about 11/17ms, preprocess 0/0ms |
| QNN inference | about 1-2ms in recent live runs |
| 5-minute sustained run | no meaningful e2e drift, coarse battery temp 24.0C -> 24.0C |
| Model size | about 43.7KB |
| Structure-sensitive metrics | better PSNR/SSIM than Real-ESRGAN on three selected cases |
| Real-camera showcase set | accepted with caveats; no retake required |

## Why Small Remains Default

QuickSRNet medium and large were checked as a model-curve branch, not as a
pre-decided replacement. The comparison output is:

```text
C:\Users\Admin\Desktop\QC-Development-Board-Project\RB5_SR_lab\results\quicksrnet_curve\20260721_quicksrnet_sml_curve
```

Human review of the most relevant sheets found:

```text
offline_text_edge_contact_sheet.png:
  small looks at least as good as medium; medium appears more yellow and does
  not provide a clear sharpness/readability improvement.

offline_lowlight_noise_contact_sheet.png:
  small / medium / large have similar perceived effect; large does not show a
  strong enough gain to justify the added model size and latency risk.
```

This means the medium/large work was not wasted. It turned a model-choice
question into evidence:

```text
larger QuickSRNet variants are not promoted unless they show a visible quality
gain that is worth app packaging and RB5 QNN e2e validation.
```

## Why Keep Real-ESRGAN

Real-ESRGAN remains valuable:

```text
It is the proven QNN/HTP deployment milestone.
It represents the perceptual/GAN-style enhancement branch.
It is the main comparison baseline for model tradeoff analysis.
It may be useful for post-capture or offline enhancement where latency is less strict.
```

Do not describe Real-ESRGAN as obsolete or simply worse. It optimizes a
different perceptual tradeoff.

## Real-Camera Gate

The minimum real-camera showcase gate is complete and accepted with caveats:

```text
C:\Users\Admin\Videos\RB5 gen2\real_camera_showcase\20251110_045328_minimal_real_camera_set
```

Promotion rule after this review:

```text
Keep decision C.
Do not claim QuickSRNet is globally better.
Do not claim Real-ESRGAN is obsolete.
Do not enable automatic live dual-model routing as the default.
```

## App Default Boundary

The Android app default live SR path is now:

```text
QNN backend + QuickSRNetSmall W8A8 + optimized native tensor input path
```

This is a default workhorse change, not automatic scene routing. Real-ESRGAN
must remain explicitly reachable for comparison and optional post-capture /
perceptual enhancement evidence.

## Boundary Rules

- Do not add QuickSRNetMedium to the Android app by default.
- Do not add QuickSRNetLarge to the Android app by default.
- Keep the downloaded medium/large assets ignored as local evidence.
- Reopen this route only if a new scene shows a clear small-vs-medium quality
  gap that matters for the project story.
- Keep bounded routing experiments open, but do not let them replace the stable
  default without cold-start, memory, power, and quality evidence.

## Interview Framing

The useful story:

```text
We did not blindly choose the largest model or build automatic routing by
default. We compared small/medium/large, checked latency/size and visual
results, and kept the smallest model because the larger variants did not show
enough visual benefit for live ROI. Real-ESRGAN remains the perceptual
comparison and post-capture branch.
```
