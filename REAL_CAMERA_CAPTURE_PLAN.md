# Real Camera Capture Plan

Updated: 2026-07-18

## Decision

Do not expand into a large real-camera dataset now.

Use a tiny showcase-oriented real-camera set only if needed for final demo
material.

## Minimum Capture Set

Capture at most 8 scenes:

| scene type | count | why |
| --- | ---: | --- |
| text/signage | 2 | checks readability and stroke deformation |
| fine structure | 2 | checks branches, wires, fabric, or dense edges |
| low light / noise | 1 | checks noise amplification and structure loss |
| face / person-like object | 1 | checks unnatural skin/edge artifacts |
| everyday object texture | 1 | checks natural texture and over-sharpening |
| optional failure case | 1 | only if a clear artifact appears |

## Capture Rule

Use the current app path. For each useful scene, keep only the smallest evidence
set:

```text
input ROI
bicubic baseline
QuickSRNet live/app output
optional Real-ESRGAN output if comparing model roles
one short note
```

Avoid collecting many near-duplicate photos.

## File Location

Save user-facing review assets under:

```text
C:\Users\Admin\Videos\RB5 gen2\real_camera_showcase\
```

Suggested folder:

```text
C:\Users\Admin\Videos\RB5 gen2\real_camera_showcase\20260718_minimal_real_camera_set\
```

Do not commit raw images by default. Document paths and conclusions instead.

## Naming

Use readable names:

```text
text_signage_01_input.png
text_signage_01_bicubic.png
text_signage_01_quicksr.png
text_signage_01_realesrgan_optional.png
```

## Review Labels

Use:

```text
pass
conditional
fail
```

Decision examples:

| label | Meaning |
| --- | --- |
| `pass` | useful showcase evidence |
| `conditional` | useful but must mention caveat |
| `fail` | do not use in showcase unless investigating failure |

## Route Impact

This set is for showcase credibility, not model training.

Only change the route if the real-camera set reveals a repeated, important
failure pattern. Do not change route for a single awkward scene.

## Manual Step Needed

The user needs to capture or approve real-camera images. The agent should not
invent real-camera evidence from benchmark files.
