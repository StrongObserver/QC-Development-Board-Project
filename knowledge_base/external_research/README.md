# RB5 External Research Knowledge Base

This folder stores selected external papers and repositories for the RB5 Gen2
AI image-enhancement project. It is intentionally small: do not dump every
related GitHub project here.

## Selection Rules

- Prefer resources that can break a real RB5 loop deadlock.
- Prioritize high match to the project over novelty.
- Use stars/citations as supporting signals, not the only decision.
- Keep one project or paper family in one folder.
- Do not treat these resources as project truth until verified on the fixed
  benchmark or on the RB5 device.

## Current Categories

```text
super_resolution/
  realesrgan/
  quicksrnet/
  bsrgan_real_degradation/

text_fidelity_sr/
  tpgsr/
  sgenet/

qnn_android/
  qualcomm_ai_hub_apps/
  edgeimpulse_qnn_android/
```

## How Future AI Should Use This

Use this folder only after the current oral-template prompt, project entrypoint,
loop state, and benchmark SOP have been read.

- For the current Real-ESRGAN baseline, read `super_resolution/realesrgan`.
- For a lightweight mobile fallback or model comparison, read
  `super_resolution/quicksrnet`.
- For real degradation design, read `super_resolution/bsrgan_real_degradation`.
- For text/signage SR failures, read `text_fidelity_sr/tpgsr` and `sgenet`.
- For Android/QNN integration references, read `qnn_android`.

Every new external resource added here should include a `RESOURCE_CARD.md`.
