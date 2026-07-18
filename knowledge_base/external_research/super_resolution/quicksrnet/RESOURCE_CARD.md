# QuickSRNet Resource Card

## Why It Is Here

QuickSRNet is the strongest first fallback/model-comparison candidate for this
RB5 project because it was designed for fast mobile super-resolution and is
available through Qualcomm AI Hub model tooling.

## Local Contents

```text
repo\                         # shallow clone of https://github.com/quic/aimet-model-zoo
QuickSRNet_2303.04336.pdf      # paper PDF
```

Related paths also exist in the AI Hub Models clone:

```text
..\..\qnn_android\qualcomm_ai_hub_apps\repo\src\qai_hub_models\models\quicksrnetsmall
..\..\qnn_android\qualcomm_ai_hub_apps\repo\src\qai_hub_models\models\quicksrnetmedium
..\..\qnn_android\qualcomm_ai_hub_apps\repo\src\qai_hub_models\models\quicksrnetlarge
```

## Use When

- QNN/app integration is blocked and a lighter SR model is needed
- comparing latency/size/quality against Real-ESRGAN
- preparing D9 QuickSRNet model comparison
- looking for quantization-friendly mobile SR architecture ideas

## Do Not Misuse

- Do not expect Real-ESRGAN-like perceptual texture generation.
- Do not compare QuickSRNet and Real-ESRGAN without the same benchmark cases.
- Do not treat AI Hub hosted performance as Android app e2e performance.
