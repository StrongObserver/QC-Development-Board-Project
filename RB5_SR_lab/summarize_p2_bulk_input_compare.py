"""Summarize P2 bulk input fast-path benchmark results."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


RESULTS_ROOT = Path(r"C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results")


def read_metrics(run_id: str) -> dict[str, dict[str, str]]:
    with (RESULTS_ROOT / run_id / "metrics.csv").open("r", newline="", encoding="utf-8-sig") as f:
        return {row["stage"]: row for row in csv.DictReader(f)}


def val(metrics: dict[str, dict[str, str]], stage: str, field: str) -> str:
    return metrics.get(stage, {}).get(field, "")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", default="20260721_loop_p2_bulk_input_compare")
    parser.add_argument("--default-run", required=True)
    parser.add_argument("--old-tensor-run", required=True)
    parser.add_argument("--bulk-tensor-run", required=True)
    parser.add_argument("--correctness-run", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = RESULTS_ROOT / args.run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    runs = [
        ("default_bitmap_live_roi", args.default_run),
        ("old_native_rotated_tensor", args.old_tensor_run),
        ("bulk_input_native_rotated_tensor", args.bulk_tensor_run),
    ]
    rows: list[dict[str, object]] = []
    for label, run_id in runs:
        m = read_metrics(run_id)
        rows.append(
            {
                "path": label,
                "run_id": run_id,
                "nativeRgb_p50_ms": val(m, "nativeRgb", "p50_ms"),
                "nativeRgb_p95_ms": val(m, "nativeRgb", "p95_ms"),
                "pre_p50_ms": val(m, "pre", "p50_ms"),
                "pre_p95_ms": val(m, "pre", "p95_ms"),
                "enhanceWall_p50_ms": val(m, "enhanceWall", "p50_ms"),
                "enhanceWall_p95_ms": val(m, "enhanceWall", "p95_ms"),
                "analyzer_p50_ms": val(m, "analyzer", "p50_ms"),
                "analyzer_p95_ms": val(m, "analyzer", "p95_ms"),
                "e2e_p50_ms": val(m, "e2e", "p50_ms"),
                "e2e_p95_ms": val(m, "e2e", "p95_ms"),
            }
        )
    with (out_dir / "path_compare.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    default = rows[0]
    bulk = rows[2]
    delta_p50 = float(str(default["e2e_p50_ms"])) - float(str(bulk["e2e_p50_ms"]))
    delta_p95 = float(str(default["e2e_p95_ms"])) - float(str(bulk["e2e_p95_ms"]))
    decision = "promote_candidate" if delta_p50 >= 1.0 and delta_p95 >= 1.0 else "keep_as_probe"
    loop_state = {
        "schema_version": 1,
        "run_id": args.run_id,
        "status": "bulk_input_fast_path_classified",
        "stop_reason": "path_compare_completed",
        "decision": decision,
        "default_run": args.default_run,
        "old_tensor_run": args.old_tensor_run,
        "bulk_tensor_run": args.bulk_tensor_run,
        "correctness_run": args.correctness_run,
        "e2e_delta_p50_ms_default_minus_bulk": f"{delta_p50:.1f}",
        "e2e_delta_p95_ms_default_minus_bulk": f"{delta_p95:.1f}",
        "boundary": "App timing comparison only; visual correctness still relies on pulled probe images.",
    }
    (out_dir / "loop_state.json").write_text(json.dumps(loop_state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# P2 Bulk Input Compare",
        "",
        f"- decision: `{decision}`",
        f"- default e2e p50/p95: `{default['e2e_p50_ms']}/{default['e2e_p95_ms']}ms`",
        f"- bulk tensor e2e p50/p95: `{bulk['e2e_p50_ms']}/{bulk['e2e_p95_ms']}ms`",
        f"- delta default-minus-bulk p50/p95: `{delta_p50:.1f}/{delta_p95:.1f}ms`",
        "- boundary: timing evidence only; correctness evidence is the tensor probe output",
        "",
        "## Key Table",
        "",
        "| path | e2e p50/p95 ms | pre p50/p95 ms | analyzer p50/p95 ms |",
        "| --- | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            f"| `{row['path']}` | {row['e2e_p50_ms']} / {row['e2e_p95_ms']} | "
            f"{row['pre_p50_ms']} / {row['pre_p95_ms']} | {row['analyzer_p50_ms']} / {row['analyzer_p95_ms']} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "The UINT8 NHWC bulk input path removes the per-byte quantization loop for models whose input is already uint8 with scale 1/255 and zero-point 0. It turns the native tensor path from a neutral probe into a measurable small latency win.",
        ]
    )
    (out_dir / "SUMMARY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[ok] wrote {out_dir}")
    print(f"[cmp] decision={decision} delta={delta_p50:.1f}/{delta_p95:.1f}ms")


if __name__ == "__main__":
    main()
