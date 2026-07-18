# BSRGAN / Real Degradation Resource Card

## Why It Is Here

BSRGAN is included for degradation-model thinking. It helps explain why real
SR quality depends heavily on how the low-resolution input was generated and
why blindly stacking degradations can hurt structured regions.

## Local Contents

```text
repo\                   # shallow clone of https://github.com/cszn/BSRGAN
BSRGAN_ICCV2021.pdf     # paper PDF
```

## Use When

- designing or criticizing SR degradation pipelines
- diagnosing real-image generalization failures
- planning future low-light or real camera SR datasets
- deciding whether current RB5 fixed benchmark is too synthetic

## Do Not Misuse

- Do not immediately retrain Real-ESRGAN with BSRGAN degradation.
- Do not overcomplicate the current RB5 benchmark before QNN/app evidence is stable.
- Do not apply strong degradation logic to text/face regions without a semantic
  fidelity gate.
