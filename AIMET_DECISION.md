# AIMET Decision

Updated: 2026-07-18

## Decision Scope

Current scope: `implementation_gate`.

Do not start AIMET CLE / Bias Correction / AdaRound in the current mainline
loop. This is not a permanent rejection of AIMET.

Status:

```text
AIMET: deferred_with_trigger
```

## Why

AIMET should fix quantization degradation inside one model family. It should not
be used to explain or force a winner between Real-ESRGAN and QuickSRNet.

Current evidence does not show a blocking Real-ESRGAN W8A8-vs-float degradation
on the main showcase path:

```text
W8A8 TFLite baseline exists.
QNN context and app delegate paths work.
The current low-light/structure limitations are mostly model or input-detail
capacity boundaries, not a proven quantization-only failure.
The route has moved toward QuickSRNetSmall for live ROI and Real-ESRGAN as
QNN/HTP milestone / optional perceptual enhancement.
```

Starting AIMET now would add toolchain cost without being the highest-value
mainline step. AIMET remains a valid quality exploration lane if a real
W8A8-vs-float degradation appears.

## Trigger To Reconsider

Start AIMET only if one of these is true:

```text
1. Human visual review finds W8A8 visibly worse than float on a main showcase case.
2. Float Real-ESRGAN preserves a structure/text/face detail that W8A8 consistently loses.
3. The final project story needs a quantization-recovery section and there is
   time to produce before/after evidence.
4. QNN W8A8 becomes the default perceptual/post-capture model and quality is
   the blocking issue.
```

## If AIMET Starts Later

Use the lightest path first:

```text
1. Re-run fixed W8A8-vs-float cases and identify exact failure crops.
2. Try CLE or Bias Correction first.
3. Measure whether quality improves on the failure crop without hurting general cases.
4. Use AdaRound or QAT only if the lighter methods fail and time allows.
```

## Boundary

Do not use AIMET to improve an outlier if it harms general cases. Do not use it
to paper over missing input detail that neither float nor W8A8 can reconstruct.
