# TPGSR Resource Card

## Why It Is Here

TPGSR is included because text/signage is one of the highest-risk categories
for SR. It uses text recognition priors to guide scene text SR, directly
addressing the "sharper but wrong characters" failure mode.

## Local Contents

```text
repo\                   # shallow clone of https://github.com/mjq11302010044/TPGSR
TPGSR_2106.15368.pdf    # paper PDF
```

## Use When

- `text_signage` cases fail or become conditional
- OCR/readability becomes part of the RB5 quality gate
- explaining why blind SR should not guess characters
- planning a text-specific L2 investigation

## Do Not Misuse

- Do not use TPGSR as the main SR model for all content.
- Do not assume OCR priors are reliable when LR text is unreadable.
- Do not add a text-specific model to the app before the general QNN path is stable.
