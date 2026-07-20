# AIMET Decision

Updated: 2026-07-18

## Decision Scope

Current scope: `implementation_gate`.

Do not start AIMET CLE / Bias Correction / AdaRound in the current mainline
loop. This is not a permanent rejection of AIMET.

Status:

```text
AIMET: trigger_candidate_found
```

2026-07-20 recheck:

```text
The latest app work changed output-buffer handling and app e2e logging only.
It did not introduce a new W8A8-vs-float visual failure crop. Therefore AIMET
remains deferred_with_trigger.
```

2026-07-20 active trigger search:

```text
RB5_SR_lab\find_aimet_failure_crops.py
RB5_SR_lab\results\aimet_trigger_search\20260720_full_v2_patch96
```

Automated local-crop search over `20260715_1950_realesrgan_host_float_vs_w8a8_full_v2`
found 18 candidate crops and 3 strong candidates under the current threshold.
The strongest two are `structure_edges_urban067` crops:

```text
structure_edges_urban067 x=336 y=48  delta=2.044dB  MAD=6.511
structure_edges_urban067 x=336 y=96  delta=2.069dB  MAD=5.725
```

Interpretation:

```text
This is now enough to justify an AIMET feasibility validation, because there is
a concrete W8A8-vs-float local regression candidate. It is not yet proof that
AIMET will fix the issue. Human review should inspect candidate_overview.png,
then the next technical step is checking whether the local AIMET toolchain can
run CLE or Bias Correction for this model without derailing the stable baseline.
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

Start AIMET feasibility validation if one of these is true:

```text
1. Human visual review finds W8A8 visibly worse than float on a main showcase case.
2. Float Real-ESRGAN preserves a structure/text/face detail that W8A8 consistently loses.
3. The final project story needs a quantization-recovery section and there is
   time to produce before/after evidence.
4. QNN W8A8 becomes the default perceptual/post-capture model and quality is
   the blocking issue.
```

## Windows Feasibility Check

2026-07-20 recheck on the current Win11 host:

```text
RB5_SR_lab\.venv-eval\Scripts\python.exe --version
Python 3.12.10

RB5_SR_lab\.venv-eval\Scripts\python.exe -m pip index versions aimet-onnx
ERROR: No matching distribution found for aimet-onnx

PyPI aimet-onnx 2.35.1 file:
aimet_onnx-2.35.1-cp310-abi3-manylinux_2_34_x86_64.whl

RB5_SR_lab\.venv-eval\Scripts\python.exe -m pip install --dry-run aimet-torch==2.35.1
Would install aimet-torch-2.35.1
```

Interpretation:

```text
Native Windows is not a supported path for the ONNX AIMET package needed for a
TFLite/ONNX-style PTQ flow: the available aimet-onnx wheel is Linux manylinux,
and pip finds no matching Windows distribution in the current Python 3.12
environment.

aimet-torch being visible to pip is not enough to start the current deployment
flow, because the Android model path is TFLite/QNN and the project currently
needs a quantization-recovery workflow around the FP/ONNX or export pipeline.
Use aimet-torch only if a PyTorch FP source model and export path are confirmed.
```

Current action:

```text
Keep AIMET-CLE as blocked_needs_user for the current Windows-only environment.
Next valid step is one of:
1. provide WSL/Linux or another supported AIMET environment for aimet-onnx; or
2. confirm a PyTorch FP source model path and then assess aimet-torch separately.
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
