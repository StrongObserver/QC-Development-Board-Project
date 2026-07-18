# Real-ESRGAN Resource Card

## Why It Is Here

Real-ESRGAN is the current RB5 project baseline model family. The Android app,
TFLite float baseline, W8A8 baseline, and QNN context binary all derive from
this direction.

## Local Contents

```text
repo\                         # shallow clone of https://github.com/xinntao/Real-ESRGAN
Real-ESRGAN_2107.10833.pdf     # paper PDF
```

## Use When

- explaining why current SR output has GAN-style perceptual artifacts
- checking model architecture or degradation assumptions
- comparing current RB5 implementation with upstream Real-ESRGAN behavior
- preparing interview/project narrative for the baseline model

## Do Not Misuse

- Do not treat upstream GPU/PyTorch performance as RB5 performance.
- Do not use Real-ESRGAN visual sharpness alone as quality pass.
- Do not blame QNN runner when a known GAN SR boundary appears in low-light or
  structured text/face regions.
