# RB5 Evaluation Lifecycle Matrix

更新时间：2026-07-17

This matrix defines the stable evaluation shape for the project. The goal is not
to download every dataset immediately. The goal is to prevent evaluation drift:
future progress should compare against a stable layer, and new layers should be
added deliberately.

## Layers

| Layer | When It Is Required | Data Source | Metric/Review Shape | Current State |
| --- | --- | --- | --- | --- |
| L0 runner validity | Every model/backend/runner change | `qa/smoke_subset.csv` | hard gates: output exists, size, nonblank, profile | Active |
| L1 fixed SR regression | Any quality/performance claim on current 128->512 path | `RB5_SR_Benchmark_v1/manifest.csv` | PSNR/SSIM/sharpness + contact sheet + human taxonomy | Active, must run full next |
| L2 category investigation | A category is conditional/fail or metrics conflict with review | subset by category from v1 or EvalHub source | category-specific review and diagnostics | Active as protocol, run only when triggered |
| L3 artificial IQA calibration | Adding LPIPS/DISTS/VSI/NR-IQA or metric thresholds | CSIQ first, then TID/LIVE/KADID if needed | metric-human alignment sanity, no SR claim | CSIQ downloaded; others registered |
| L4 real degradation SR | Claiming real camera robustness | RealSR/DRealSR/real degradation data | paired real LR/HR or high-quality reference review | RealSR V3 x4 Test derived |
| L5 text fidelity | Claiming text/signage robustness or text category fails | TextZoom / text-specific SR resources | text readability, OCR/recognition if available, visual veto | TextZoom test splits derived |
| L6 app/device e2e | Moving from runner to product demo | Android app logs + device profiling | e2e latency, memory, power/thermal, fallback behavior | Schema/protocol ready; needs app integration |
| L7 video/temporal | Moving from still image to video | future clips/sequences | flicker, temporal consistency, thermal sustained run | Future only |

## Promotion Rules

1. `RB5_SR_Benchmark_v1` stays the main gate for the current model path.
2. EvalHub sources do not replace v1 automatically.
3. A new source becomes a gate only after it has a manifest, stable categories,
   contact sheets, result SOP, and at least one reviewed run.
4. Metrics can move from diagnostic to supporting evidence only after they agree
   with human review on a representative slice.
5. A diagnostic metric must not become a hard gate unless it checks execution
   validity rather than quality.

## Immediate Recommendation

Do not pause the project to download all registered datasets. The practical next
evaluation work is:

1. Run QNN W8A8 full 24-case benchmark on `RB5_SR_Benchmark_v1`.
2. Fill human review labels for the full contact sheet.
3. Use CSIQ only to sanity-check optional perceptual/IQA metric behavior.
4. Use the standard SR extension only as a broader sanity layer, not as the main
   project gate.
5. Use RealSR/TextZoom as lifecycle layers when the project is ready to make
   real-camera or text-specific quality claims. They should not replace the
   main fixed gate.

