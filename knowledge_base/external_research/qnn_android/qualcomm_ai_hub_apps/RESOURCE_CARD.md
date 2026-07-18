# Qualcomm AI Hub Models Resource Card

## Why It Is Here

This repository is the most directly relevant external codebase for RB5 model
export and Qualcomm-device deployment. It contains Real-ESRGAN and QuickSRNet
model definitions, export scripts, performance metadata, and static asset
recipes.

## Local Contents

```text
repo\    # shallow clone of https://github.com/quic/ai-hub-models
```

Useful local paths:

```text
repo\src\qai_hub_models\models\real_esrgan_general_x4v3
repo\src\qai_hub_models\models\quicksrnetsmall
repo\src\qai_hub_models\models\quicksrnetmedium
repo\src\qai_hub_models\models\quicksrnetlarge
```

## Use When

- exporting or inspecting Qualcomm AI Hub model assets
- comparing Real-ESRGAN vs QuickSRNet routes
- checking QNN/TFLite/W8A8 static asset availability
- preparing model cards or reproducible export commands

## Do Not Misuse

- Do not treat hosted profile numbers as local Android app e2e latency.
- Do not download large model assets into git without a deliberate decision.
- Do not assume every model has QNN context binary assets for QCS8550.
