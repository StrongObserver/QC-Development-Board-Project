# RB5 Evaluation System Freeze

更新时间：2026-07-17

本文是 RB5 Gen2 超分项目评测系统的封盘记录。它不替代
`RB5_SR_Benchmark_v1`，也不替代项目上下文文档；它只记录当前评测底座
已经具备什么、还缺什么、后续如何小幅演进。

## 结论

当前评测系统已经达到“可以长期支撑当前项目主线”的状态：

- 当前主门禁稳定：`RB5_SR_Benchmark_v1` 仍是 128x128 -> 512x512 主评测入口。
- 生命周期扩展层已建立：EvalHub 已覆盖标准 SR、真实退化 SR、文字保真 SR、IQA 校准、app e2e 协议，并已有初始 live ROI app e2e 行。
- 数据和方法已经绑定：每个数据层有明确用途、指标角色和边界，避免每次进展后重做评测系统。
- 大数据不进 Git：`evalhub_data/` 被 `.gitignore` 忽略，仓库只跟踪注册表、脚本和 SOP。

当前仍未完成的不是图片数据集，而是完整 app 端到端 manifest replay：
`rb5_app_e2e_logs` 已有 live ROI timing 行，但还没有覆盖固定 manifest
回放、截图/视频证据和完整 resource/power 组合。

## 当前数据层

| Layer | Dataset | Cases / Contents | Current Use | Boundary |
| --- | --- | ---: | --- | --- |
| 主门禁 | `RB5_SR_Benchmark_v1` | 24 cases | QNN/TFLite/W8A8/backend 主比较 | 不静默替换 |
| IQA 校准 | CSIQ | 30 source + 900 distorted + DMOS | 指标 sanity / 校准 | 不做 SR 画质声明 |
| 标准 SR 小层 | Set14 HF | 14 cases | 小型标准 SR sanity | 不替代主门禁 |
| 标准 SR 扩展 | Set5/Set14/BSD100/Urban100 | 219 cases | 更宽标准 SR sanity | 合成 x4，不是真实退化 |
| 真实退化 SR | RealSR V3 x4 Test | 100 cases | 真实相机退化鲁棒性 | 只在需要 real-camera claim 时启用 |
| 文字保真 SR | TextZoom test easy/medium/hard | 4373 cases | 文字可读性/变形专项 | 不作为通用 SR 替代 |
| app e2e | app logs schema/protocol + initial live ROI rows | 2 live ROI rows | 端到端延迟/功耗/温度 | 不是完整 manifest replay |

## 评测方法绑定

| Data Layer | Runner / Method | Metrics | Decision Owner |
| --- | --- | --- | --- |
| `RB5_SR_Benchmark_v1` | QNN runner / host runner / future app runner | hard gate + PSNR/SSIM/sharpness + contact sheet | `loop_state` + human review |
| standard SR layers | `eval_sr_manifest.py` host sanity; future QNN/app if needed | PSNR/SSIM/sharpness/contact sheet | supporting evidence + human review |
| RealSR | `eval_sr_manifest.py` host sanity; future QNN/app if real-camera claim | PSNR/SSIM/sharpness/contact sheet | human review owns real-degradation claim |
| TextZoom | `eval_sr_manifest.py` host sanity; future OCR/readability metric | PSNR/SSIM/sharpness + `text_label` + visual text review | human review, OCR optional later |
| CSIQ | future IQA metric scripts | PSNR/SSIM/LPIPS/DISTS/etc. vs DMOS | metric calibration only |
| app e2e | Android/QNN app logs | e2e p50/p95, memory, power, temperature, fallback | hard gates + human review |

Metric roles are fixed in `eval_hub/registries/metric_policy.csv`:

- `hard_gate`: runner/output validity only.
- `supporting_evidence`: PSNR, SSIM, mean abs diff, sharpness.
- `diagnostic`: LPIPS, DISTS, NIQE/MUSIQ/TOPIQ, Ringing, Visual Noise, MLLM labels.
- `visual_veto`: structured human review.

Do not promote a diagnostic metric to a hard gate until it is calibrated against
project-specific human labels.

## Files To Read First

For ordinary benchmark work:

```text
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\AI_CONTEXT.md
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\qa\RESULT_SOP.md
C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\qa\TEST_PROTOCOL.md
```

For evaluation-system expansion:

```text
C:\Users\Admin\Desktop\QC-Development-Board-Project\eval_hub\README.md
C:\Users\Admin\Desktop\QC-Development-Board-Project\eval_hub\registries\lifecycle_matrix.md
C:\Users\Admin\Desktop\QC-Development-Board-Project\eval_hub\registries\dataset_registry.csv
C:\Users\Admin\Desktop\QC-Development-Board-Project\eval_hub\registries\metric_policy.csv
```

## Key Commands

Status:

```bat
python -B eval_hub\scripts\evalhub_status.py
```

Manifest validation:

```bat
RB5_SR_lab\.venv-eval\Scripts\python.exe -B eval_hub\scripts\validate_sr_manifest.py <manifest.csv> --check-size
```

Generic host sanity runner:

```bat
RB5_SR_lab\.venv-eval\Scripts\python.exe -B eval_hub\scripts\eval_sr_manifest.py --manifest <manifest.csv> --limit 2 --runs 1
```

Current QNN full benchmark should still start from `RB5_SR_Benchmark_v1`, not
from EvalHub expansion layers.

## Current Evidence

Validation completed:

```text
RB5_SR_Benchmark_v1 manifest: 24 cases OK
set14_128x4_v1 manifest: 14 cases OK
standard_sr_x4_v1 manifest: 219 cases OK
realsr_v3_x4_test_128x4_v1 manifest: 100 cases OK
textzoom_test_128x4_v1 manifest: 4373 cases OK
loop_policy dry-run: passed
EvalHub status: registered=16, present=6
```

Smoke host sanity runs exist under:

```text
evalhub_data\derived_runs\evalhub_smoke_set14_2cases
evalhub_data\derived_runs\evalhub_smoke_realsr_2cases
evalhub_data\derived_runs\evalhub_smoke_textzoom_2cases
```

These are host LiteRT sanity checks only, not RB5 QNN/app e2e evidence.

Initial app e2e rows exist under:

```text
evalhub_data\derived\app_e2e\20260720_app_e2e_schema_output_reuse_120f\app_e2e_log.csv
evalhub_data\derived\app_e2e\20260720_app_e2e_schema_output_reuse_60s\app_e2e_log.csv
```

These are Android app live ROI timing rows. They are not fixed manifest replay,
not visual quality evidence, and not `qnn-net-run` evidence.

## What Not To Do

- Do not replace `RB5_SR_Benchmark_v1` with EvalHub data.
- Do not commit `evalhub_data/`.
- Do not treat CSIQ as an SR benchmark.
- Do not report host LiteRT EvalHub runs as RB5 QNN or app e2e.
- Do not report app live ROI timing rows as fixed manifest replay or visual quality evidence.
- Do not build video/temporal evaluation before fixed-image and app paths are stable.
- Do not treat Manga109 as a blocker; it requires official approval and is optional.

## Next Evaluation Work

The evaluation system is stable enough to resume engineering work. The next
evaluation action depends on the claim:

```text
For fixed SR quality/performance claims: use RB5_SR_Benchmark_v1.
For app live ROI claims: use app_e2e_log_schema.csv rows from the Android app runners.
For stronger app e2e claims: add fixed manifest replay or screenshot/video evidence.
```

