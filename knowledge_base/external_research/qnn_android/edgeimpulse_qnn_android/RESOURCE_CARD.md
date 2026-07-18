# Edge Impulse QNN Android Resource Card

## Why It Is Here

This repository is included as an Android QNN integration reference. It is not
an SR project, but it demonstrates how an Android app can use Qualcomm QNN /
AI Engine Direct acceleration without rewriting the whole app architecture.

## Local Contents

```text
repo\    # shallow clone of https://github.com/edgeimpulse/qnn-hardware-acceleration
```

## Use When

- designing Path B Android app integration
- checking QNN TFLite delegate integration patterns
- comparing app-level setup against the current qnn-net-run Path A
- looking for Android build/package examples around QNN

## Do Not Misuse

- Do not assume object-detection sample code maps directly to SR tensors.
- Do not bypass the existing RB5 QNN smoke/full benchmark gates.
- Do not change global Android SDK/NDK setup just to mimic this sample.
