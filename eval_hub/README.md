# RB5 EvalHub

EvalHub is the long-lived evaluation layer for the RB5 Gen2 super-resolution
project. It is deliberately separate from the current small benchmark:

```text
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1
```

`RB5_SR_Benchmark_v1` remains the fixed, compact, immediately-runnable 24-case
benchmark for the current `128x128 -> 512x512` Real-ESRGAN path. EvalHub is the
larger lifecycle evaluation plan around it: data source registry, scenario
coverage, metric policy, and scripts that can prepare or summarize data without
changing the fixed benchmark.

For the current frozen state, read first:

```text
eval_hub/EVAL_SYSTEM_FREEZE.md
```

## Storage Rule

Tracked in Git:

```text
eval_hub/
  README.md
  EVAL_SYSTEM_FREEZE.md
  registries/
  scripts/
```

Not tracked in Git:

```text
evalhub_data/
  raw/
  manifests/
  derived/
```

Large datasets, downloaded archives, extracted images, generated manifests, and
derived subsets stay under `evalhub_data/`, which is ignored by `.gitignore`.
This keeps the evaluation system reproducible without committing large assets.

## Lifecycle Coverage

The project needs several evaluation layers because one dataset cannot answer
every question:

| Layer | Purpose | Current Status |
| --- | --- | --- |
| `core_sr_fixed` | Stable 128->512 SR regression for float/W8A8/QNN/backend comparison | Existing `RB5_SR_Benchmark_v1`; keep as main gate |
| `sr_standard_public` | Wider synthetic SR sanity using known SR benchmarks | Register first; download only selected sets |
| `real_degradation_sr` | Real camera degradation and non-bicubic downsampling | Missing; RealSR/DRealSR-style data needed before real-camera claims |
| `text_fidelity` | Text/signage readability and character deformation | Missing; TextZoom/TPGSR-style data should be added if text category fails or app demo needs text proof |
| `iqa_artificial` | Artificial distortion IQA calibration and metric sanity | CSIQ is easy to fetch; TID/LIVE/KADID are optional/larger |
| `iqa_authentic_mobile` | Real-world photo quality/no-reference IQA | Missing; KonIQ/SPAQ/LIVE Challenge are optional lifecycle additions |
| `device_app_e2e` | Android app end-to-end latency, memory, power, temperature | Schema active; live ROI app e2e rows exist; fixed manifest replay is still future |
| `video_temporal` | Video/sequence SR stability, flicker, motion and thermal behavior | Future only; not part of current fixed-image gate |

## Metric Policy

Do not make every metric a gate. Use three roles:

| Role | Meaning | Examples |
| --- | --- | --- |
| Hard gate | Execution validity; failure blocks the run | output exists, size is correct, image is nonblank, profile fields exist |
| Supporting evidence | Useful numeric comparison, cannot override visual review | PSNR, SSIM, MS-SSIM, mean abs diff, sharpness ratio |
| Diagnostic | Optional deep investigation after a category issue appears | LPIPS, DISTS, VSI/FSIM/VIF, NIQE/MUSIQ/TOPIQ, Ringing, Visual Noise, MLLM labels |

Complex perceptual metrics should not become hard gates until calibrated against
human labels for this project. If a metric improves while the contact sheet looks
worse, record `METRIC_VISUAL_CONFLICT`.

## How To Use

1. Use `RB5_SR_Benchmark_v1` for current fixed comparisons.
2. Use `registries/dataset_registry.csv` to decide what larger sources are
   needed for the next lifecycle layer.
3. Use `scripts/fetch_evalhub_sources.py` to download sources marked
   `auto_download=yes` into `evalhub_data/raw/`.
4. Use `scripts/prepare_csiq_manifest.py` after CSIQ download to create a
   lightweight manifest without extracting all images.
5. Use `scripts/evalhub_status.py` to print which registered sources are present
   and what gaps remain.
6. Only promote a new dataset into a fixed benchmark after it has:
   - clear license/access notes,
   - a manifest,
   - category labels,
   - `LR | bicubic | candidate | reference` or an equivalent review view,
   - and a stable result folder format compatible with `RESULT_SOP.md`.

## Current Decision

For the current oral-template request, the system should become more complete,
but not chaotic. Therefore:

- Keep `RB5_SR_Benchmark_v1` unchanged as the main fixed gate.
- Add EvalHub as the long-cycle registry and data root.
- Download only direct, public, reasonably bounded datasets first.
- Register heavier or permission-gated datasets as planned sources instead of
  blocking the whole project on them.

## Current Local Data

The first direct-download source has been staged locally:

```text
evalhub_data/raw/csiq/archives/src_imgs.zip
evalhub_data/raw/csiq/archives/dst_imgs.zip
evalhub_data/raw/csiq/archives/csiq.DMOS.xlsx
evalhub_data/manifests/csiq_manifest.csv
evalhub_data/raw/set14_hf/archives/Set14_HR.tar.gz
evalhub_data/derived/set14_128x4_v1/manifest.csv
evalhub_data/derived/standard_sr_x4_v1/manifest.csv
evalhub_data/raw/realsr/已加速- RealSR(V3).tar.gz
evalhub_data/derived/realsr_v3_x4_test_128x4_v1/manifest.csv
evalhub_data/raw/textzoom/已加速- textzoom/
evalhub_data/derived/textzoom_test_128x4_v1/manifest.csv
```

CSIQ is for IQA metric sanity/calibration only. It is not an SR dataset and must
not be used to claim Real-ESRGAN/QNN output quality. Use it to check how PSNR,
SSIM, LPIPS/DISTS/etc. behave on known distortions before trusting those metrics
inside the RB5 SR loop.

Set14 is the first small standard-SR extension layer. It has been derived into
14 project-compatible cases with:

```text
lr_128.png
bicubic_512.png
hr_512.png
```

Use Set14 to sanity-check standard SR behavior or compare model families. Do not
use it to replace `RB5_SR_Benchmark_v1`, because v1 is better aligned with the
current RB5 category risks and loop policy.

The broader standard SR extension is derived from the existing local
`SelfExSR-master.zip` and currently contains:

```text
Set5: 5 cases
Set14: 14 cases
BSD100: 100 cases
Urban100: 100 cases
Total: 219 cases
```

This is useful for broader synthetic SR sanity, but it is still a synthetic x4
layer. It does not cover real camera degradation or text-specific OCR behavior.

RealSR V3 x4 Test has been derived into 100 project-compatible cases. Use it as
the first real-degradation SR layer before making real-camera robustness claims.

TextZoom test splits have been derived into 4373 project-compatible cases:

```text
easy: 1619
medium: 1411
hard: 1343
```

The TextZoom manifest preserves `text_label` for future OCR/readability checks.
Use it for text/signage fidelity, not as a general SR replacement.

Current EvalHub status:

```text
registered: 16
present: 6
P1 image/data gaps: none after RealSR and TextZoom manual downloads
remaining P1 gap: full rb5_app_e2e manifest replay. Live ROI app e2e rows now exist, but this is not an image dataset.
```

Manga109 is not treated as a blocker. It requires official approval and is only
useful if manga/line-art stress cases become important later.

The app/device lifecycle layer has a schema, protocol, and initial live ROI rows:

```text
eval_hub/registries/app_e2e_log_schema.csv
eval_hub/registries/app_e2e_protocol.md
evalhub_data/derived/app_e2e/20260720_app_e2e_schema_output_reuse_120f/app_e2e_log.csv
evalhub_data/derived/app_e2e/20260720_app_e2e_schema_output_reuse_60s/app_e2e_log.csv
```

Use these for app live ROI timing, sustained-run, memory, power, and fallback
records. Current `qnn-net-run` evidence must still not be reported as app e2e
evidence. The current app e2e layer is live ROI timing evidence, not full fixed
manifest replay evidence.

Manual/download-gated sources are tracked in:

```text
eval_hub/registries/manual_downloads.md
```

Useful commands:

```bat
python -B eval_hub\scripts\fetch_evalhub_sources.py --dataset csiq
python -B eval_hub\scripts\prepare_csiq_manifest.py
python -B eval_hub\scripts\fetch_evalhub_sources.py --dataset set14_hf --extract
RB5_SR_lab\.venv-eval\Scripts\python.exe -B eval_hub\scripts\prepare_set14_extension.py
RB5_SR_lab\.venv-eval\Scripts\python.exe -B eval_hub\scripts\prepare_standard_sr_suite.py
RB5_SR_lab\.venv-eval\Scripts\python.exe -B eval_hub\scripts\prepare_realsr_manifest.py
RB5_SR_lab\.venv-eval\Scripts\python.exe -B eval_hub\scripts\prepare_textzoom_manifest.py
RB5_SR_lab\.venv-eval\Scripts\python.exe -B eval_hub\scripts\validate_sr_manifest.py evalhub_data\derived\set14_128x4_v1\manifest.csv --check-size
RB5_SR_lab\.venv-eval\Scripts\python.exe -B eval_hub\scripts\validate_sr_manifest.py evalhub_data\derived\standard_sr_x4_v1\manifest.csv --check-size
RB5_SR_lab\.venv-eval\Scripts\python.exe -B eval_hub\scripts\validate_sr_manifest.py evalhub_data\derived\realsr_v3_x4_test_128x4_v1\manifest.csv --check-size
RB5_SR_lab\.venv-eval\Scripts\python.exe -B eval_hub\scripts\validate_sr_manifest.py evalhub_data\derived\textzoom_test_128x4_v1\manifest.csv --check-size
RB5_SR_lab\.venv-eval\Scripts\python.exe -B eval_hub\scripts\eval_sr_manifest.py --manifest evalhub_data\derived\set14_128x4_v1\manifest.csv --limit 2 --runs 1
python -B eval_hub\scripts\evalhub_status.py
```

`eval_sr_manifest.py` is the generic host-side EvalHub runner. It can run any
manifest with `case_id, category, dataset, source_id, lr_128, bicubic_512,
hr_512` columns and writes results under `evalhub_data/derived_runs/`. It is a
host LiteRT sanity runner, not RB5 QNN or Android app e2e evidence.

