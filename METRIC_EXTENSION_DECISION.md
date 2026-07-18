# Metric Extension Decision

Updated: 2026-07-18

## Decision

Do not install or enable LPIPS / DISTS / pyiqa in the current loop.

Keep the current metric policy:

```text
PSNR / SSIM: fidelity supporting evidence
LPIPS / DISTS: planned diagnostic
human contact-sheet review: visual veto
```

## Environment Check

Current eval venv:

```text
C:\Users\Admin\Desktop\QC-Development-Board-Project\RB5_SR_lab\.venv-eval\Scripts\python.exe
```

Available:

```text
torch: yes
torchvision: yes
cv2: yes
numpy: yes
```

Not available:

```text
lpips: no
DISTS_pytorch: no
pyiqa: no
```

## Why Not Now

LPIPS/DISTS are useful, but current project decisions are not blocked on them:

```text
QNN/HTP app path is already validated by hard gates and app logs.
Live ROI route is driven mainly by latency, resource cost, and visual veto.
QuickSRNet vs Real-ESRGAN is a tradeoff question, not a PSNR-only ranking.
Human visual labels are still missing, so adding metrics now would not remove
the main uncertainty.
```

Installing new perceptual metric packages can add dependency/download risk and
may slow the loop. The current best step is to complete human visual review
first, then use LPIPS/DISTS only on disputed cases if needed.

## Trigger To Add LPIPS / DISTS Later

Add perceptual metrics only if at least one of these happens:

```text
1. Human review disagrees with PSNR/SSIM on important cases.
2. Real-ESRGAN looks better perceptually but worse numerically, and the story
   needs supporting metric evidence.
3. A future route decision depends on perceptual quality beyond visual labels.
4. EvalHub expands into IQA lifecycle work where metric calibration is the task.
```

## Implementation Boundary

If enabled later:

```text
Add metric code as diagnostic only.
Do not make LPIPS/DISTS a hard gate before calibration.
Write results into EvalHub metric policy and run outputs.
Keep human review as final visual veto.
```
