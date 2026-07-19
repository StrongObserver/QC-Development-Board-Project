# Real Camera Capture Plan

Updated: 2026-07-19

## Decision

Do not expand into a large real-camera dataset now.

Use a tiny showcase-oriented real-camera set only if needed for final demo
material.

## Minimum Capture Set

Capture exactly the small app-guided set unless there is a reason to retake.
The Android app now has a `真实相机证据` button that walks through these 8
scenes in order. Long press the button to reset to scene 1.

| scene type | count | why |
| --- | ---: | --- |
| text/signage | 2 | checks readability and stroke deformation |
| fine structure | 2 | checks branches, wires, fabric, or dense edges |
| low light / noise | 1 | checks noise amplification and structure loss |
| face / person-like object | 1 | checks unnatural skin/edge artifacts |
| everyday object texture | 1 | checks natural texture and over-sharpening |
| optional failure case | 1 | only if a clear artifact appears |

App scene ids:

```text
text_signage_01
text_signage_02
fine_structure_01
fine_structure_02
low_light_noise_01
people_object_01
object_texture_01
optional_failure_01
```

## Capture Rule

Use the current app path. For each scene, the app saves the smallest useful
evidence set automatically:

```text
input ROI 128
bicubic baseline 512
QuickSRNetSmall W8A8 QNN output 512
Real-ESRGAN W8A8 QNN output 512
```

Avoid collecting many near-duplicate photos.

Manual operation should be minimal:

1. Open the app and keep live SR off.
2. Point the board camera at the scene described by the `真实相机证据` button.
3. Put the target detail in the center of the preview.
4. Tap `真实相机证据` once.
5. Wait for the toast/status text saying the scene was saved.
6. Move to the next scene shown on the button/status text.

## File Location

On the RB5 device, the app saves raw capture evidence under:

```text
/sdcard/Pictures/RB5VisionLab/
```

File names follow:

```text
REALCAM_<session>_<scene_id>_input_128.png
REALCAM_<session>_<scene_id>_bicubic_512.png
REALCAM_<session>_<scene_id>_quicksr_qnn_512.png
REALCAM_<session>_<scene_id>_realesrgan_qnn_512.png
```

After capture, pull and organize the latest session on Windows:

```bat
cd /d C:\Users\Admin\Desktop\QC-Development-Board-Project
RB5_SR_lab\.venv-eval\Scripts\python.exe RB5_SR_lab\collect_real_camera_showcase.py
```

The script writes user-facing review assets under:

```text
C:\Users\Admin\Videos\RB5 gen2\real_camera_showcase\<session>_minimal_real_camera_set\
```

It generates:

```text
manifest.csv
review_template.csv
contact_sheet.png
SUMMARY.md
run_log.csv
loop_state.json
```

Do not commit raw images by default. Document paths and conclusions instead.

## Naming

Use the app-generated names. Do not rename individual files by hand before
running the collector, because the script depends on the standard pattern:

```text
REALCAM_20260719_153000_text_signage_01_input_128.png
REALCAM_20260719_153000_text_signage_01_bicubic_512.png
REALCAM_20260719_153000_text_signage_01_quicksr_qnn_512.png
REALCAM_20260719_153000_text_signage_01_realesrgan_qnn_512.png
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

The user only needs to frame each scene and tap the app button. The agent should
not invent real-camera evidence from benchmark files.
