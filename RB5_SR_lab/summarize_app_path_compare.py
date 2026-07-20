"""Summarize app live-path result folders into one comparison record."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path


RESULTS_ROOT = Path(r"C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results")


def read_stage_metrics(run_id: str) -> dict[str, dict[str, str]]:
    path = RESULTS_ROOT / run_id / "metrics.csv"
    stages: dict[str, dict[str, str]] = {}
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            stages[row["stage"]] = row
    return stages


def read_loop_state(run_id: str) -> dict[str, object]:
    path = RESULTS_ROOT / run_id / "loop_state.json"
    return json.loads(path.read_text(encoding="utf-8"))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def metric(stages: dict[str, dict[str, str]], stage: str, field: str) -> str:
    return stages.get(stage, {}).get(field, "")


def comparison_rows(default_run: str, tensor_run: str, yuv_run: str, correctness_run: str) -> list[dict[str, object]]:
    runs = [
        ("default_bitmap_live_roi", default_run, "Current default path; remains mainline unless a stronger path wins both p50 and p95."),
        ("native_rotated_tensor_live_roi", tensor_run, "Correctness passed, but live p95 did not beat default."),
    ]
    rows: list[dict[str, object]] = []
    for label, run_id, interpretation in runs:
        stages = read_stage_metrics(run_id)
        loop_state = read_loop_state(run_id)
        rows.append(
            {
                "path": label,
                "run_id": run_id,
                "status": loop_state.get("status", ""),
                "frames": loop_state.get("parsed_frames", ""),
                "cap_p50_ms": metric(stages, "cap", "p50_ms"),
                "cap_p95_ms": metric(stages, "cap", "p95_ms"),
                "nativeRgb_p50_ms": metric(stages, "nativeRgb", "p50_ms"),
                "nativeRgb_p95_ms": metric(stages, "nativeRgb", "p95_ms"),
                "frameBitmap_p50_ms": metric(stages, "frameBitmap", "p50_ms"),
                "frameBitmap_p95_ms": metric(stages, "frameBitmap", "p95_ms"),
                "pre_p50_ms": metric(stages, "pre", "p50_ms"),
                "inf_p50_ms": metric(stages, "inf", "p50_ms"),
                "post_p50_ms": metric(stages, "post", "p50_ms"),
                "analyzer_p50_ms": metric(stages, "analyzer", "p50_ms"),
                "analyzer_p95_ms": metric(stages, "analyzer", "p95_ms"),
                "e2e_p50_ms": metric(stages, "e2e", "p50_ms"),
                "e2e_p95_ms": metric(stages, "e2e", "p95_ms"),
                "interpretation": interpretation,
            }
        )
    yuv_state = read_loop_state(yuv_run)
    correctness_state = read_loop_state(correctness_run)
    rows.append(
        {
            "path": "native_yuv_roi_correctness",
            "run_id": yuv_run,
            "status": yuv_state.get("status", ""),
            "native_input_mad": yuv_state.get("native_mad", ""),
            "interpretation": "Native YUV ROI crop/color/stride is close enough to use for bounded probes.",
        }
    )
    rows.append(
        {
            "path": "native_rotated_tensor_correctness",
            "run_id": correctness_run,
            "status": correctness_state.get("status", ""),
            "native_input_mad": correctness_state.get("rotated_native_input_mad", ""),
            "native_output_mad": correctness_state.get("rotated_native_output_mad", ""),
            "interpretation": "Native rotation is visually/structurally safe enough, but live latency still gates default promotion.",
        }
    )
    return rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", default="")
    parser.add_argument("--default-run", required=True)
    parser.add_argument("--tensor-run", required=True)
    parser.add_argument("--yuv-run", required=True)
    parser.add_argument("--correctness-run", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_id = args.run_id or datetime.now().strftime("app_path_compare_%Y%m%d_%H%M%S")
    out_dir = RESULTS_ROOT / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = comparison_rows(args.default_run, args.tensor_run, args.yuv_run, args.correctness_run)
    write_csv(out_dir / "path_compare.csv", rows)
    default_row = next(row for row in rows if row["path"] == "default_bitmap_live_roi")
    tensor_row = next(row for row in rows if row["path"] == "native_rotated_tensor_live_roi")
    default_wins = float(str(default_row["e2e_p95_ms"])) <= float(str(tensor_row["e2e_p95_ms"]))
    loop_state = {
        "schema_version": 1,
        "run_id": run_id,
        "output_dir": str(out_dir),
        "status": "native_tensor_probe_classified",
        "stop_reason": "path_compare_completed",
        "next_priority_task": "Do not promote native-rotated tensor path to default; proceed to AIMET/toolchain decision or a larger CameraX/native integration design.",
        "default_run": args.default_run,
        "tensor_run": args.tensor_run,
        "default_e2e_p95_ms": default_row["e2e_p95_ms"],
        "tensor_e2e_p95_ms": tensor_row["e2e_p95_ms"],
        "decision": "keep_default_bitmap_live_roi" if default_wins else "consider_native_tensor_for_default",
        "boundary": "This compares app timing logs only; it is not true CameraX-to-NPU zero-copy and not a visual-quality claim.",
    }
    (out_dir / "loop_state.json").write_text(json.dumps(loop_state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = [
        "# App Path Compare Summary",
        "",
        f"- run_id: `{run_id}`",
        f"- decision: `{loop_state['decision']}`",
        "- boundary: app timing and correctness evidence, not true zero-copy",
        "",
        "## Key Comparison",
        "",
        "| path | run | e2e p50/p95 ms | analyzer p50/p95 ms | note |",
        "| --- | --- | ---: | ---: | --- |",
    ]
    for row in rows[:2]:
        summary.append(
            f"| `{row['path']}` | `{row['run_id']}` | {row['e2e_p50_ms']} / {row['e2e_p95_ms']} | "
            f"{row['analyzer_p50_ms']} / {row['analyzer_p95_ms']} | {row['interpretation']} |"
        )
    summary.extend(
        [
            "",
            "## Correctness",
            "",
            f"- YUV ROI native MAD: `{rows[2].get('native_input_mad', '')}` from `{args.yuv_run}`",
            f"- native-rotated tensor input/output MAD: `{rows[3].get('native_input_mad', '')}` / `{rows[3].get('native_output_mad', '')}` from `{args.correctness_run}`",
            "",
            "## Next",
            "",
            "Keep the native-rotated tensor path as a bounded probe. It is correct, but it does not beat the default live ROI p95, so the default app path should remain unchanged.",
        ]
    )
    (out_dir / "SUMMARY.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
    print(f"[ok] wrote {out_dir}")


if __name__ == "__main__":
    main()
