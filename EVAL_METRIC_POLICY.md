# RB5 Runtime Workload Evaluation Metric Policy

Updated: 2026-07-23

## Project Frame

This policy now supports the Runtime project frame:

```text
QCS8550 端侧 AI 推理 Runtime 与异构性能优化
```

SR metrics remain useful because Real-ESRGAN and QuickSRNet are the current
workloads, but quality metrics are only one lane. Keep Runtime evidence
separate: AI Hub profile, local qnn-net-run profile, Android app e2e,
memory/init/switch cost, and board-level power estimates answer different
questions.

## Decision

Do not use PSNR alone to rank Real-ESRGAN and QuickSRNet.

The current project compares models with different goals:

```text
Real-ESRGAN: perceptual/GAN-style enhancement, stronger sharpening, higher hallucination risk.
QuickSRNetSmall: conservative reconstruction, better fidelity/structure behavior, lower perceptual punch.
```

Using only PSNR makes the comparison look simple, but it is not a fair final
quality decision for a perceptual SR model.

## Metric Roles

| Metric / Evidence | Role | Use |
| --- | --- | --- |
| Output exists, size, nonblank, no crash | hard gate | Validates runner/app correctness |
| PSNR / SSIM | fidelity supporting evidence | Measures closeness to HR reference |
| LPIPS / DISTS | perceptual supporting evidence | Needed before judging perceptual SR fairly |
| NIQE / MUSIQ / other no-reference IQA | diagnostic | Useful for real-camera/no-GT scenes after calibration |
| Sharpness / edge strength | diagnostic | Helps detect over-sharpening or under-enhancement |
| Contact sheet / human review | visual veto | Final decision for text, faces, tree branches, artifacts |
| Latency / model size / memory / power | engineering constraint | Determines deployability, not just quality |
| AI Hub / qnn-net-run / app e2e | runtime evidence lanes | Must not be collapsed into one latency number |

## Category Rules

| Category | Primary question | Preferred decision owner |
| --- | --- | --- |
| Structure edges | Are geometry and edges stable without ringing? | visual review + PSNR/SSIM |
| Repeating patterns | Is periodic texture stable without fake patterns? | visual review |
| Natural texture | Does texture look natural without hallucination? | visual review + perceptual metrics |
| Low-light noise | Is noise amplified or structure merged? | visual review + fidelity metrics |
| Text/signage | Are strokes readable and structurally correct? | visual veto, OCR later if needed |
| People/face | Are faces/skin/body boundaries natural? | visual veto |

## Current Evidence Interpretation

QuickSRNetSmall has better PSNR/SSIM on the tested structure-sensitive cases:

```text
low_light_div2k0852: +1.62dB PSNR vs Real-ESRGAN
people_scene_div2k0832: +3.60dB PSNR vs Real-ESRGAN
text_signage_urban076: +1.09dB PSNR vs Real-ESRGAN
```

This supports QuickSRNetSmall as a conservative candidate. It does not prove
that QuickSRNetSmall is globally better for all perceptual quality goals.

## Next Metric Work

Before making a final model-strategy claim:

1. Add LPIPS or DISTS on the fixed benchmark if the environment cost is acceptable.
2. Keep PSNR/SSIM in tables but remove wording that treats PSNR as final quality.
3. Keep human review as final authority for text, people, low-light tree branches, and visible artifacts.
4. Do not run AIMET only because PSNR differs between Real-ESRGAN and QuickSRNet; AIMET is only for W8A8-vs-float degradation inside one model family.

