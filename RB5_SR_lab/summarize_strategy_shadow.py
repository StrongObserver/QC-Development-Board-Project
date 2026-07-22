"""Summarize strategy-shadow fields from app live ROI logs.

The Android app logs luma, simple sharpness, motion MAD, and a shadow decision.
This script turns those logs into a small evidence table. It does not change
runtime behavior and does not promote frame skipping or model routing.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import defaultdict
from pathlib import Path

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[1]
RESULTS_ROOT = REPO_ROOT / "RB5_SR_lab" / "results" / "strategy_shadow_analysis"

LOG_RE = re.compile(
    r"backend=(?P<backend>\w+) model=(?P<model>\w+) tensorLive crop=(?P<crop_side>\d+)->128->512 "
    r"frame=(?P<frame_width>\d+)x(?P<frame_height>\d+) nativeRgb=(?P<native_rgb_ms>\d+) "
    r"rotate=(?P<rotation_degrees>\d+) pre=(?P<pre_ms>\d+) inf=(?P<inf_ms>\d+) "
    r"post=(?P<post_ms>\d+) enhanceWall=(?P<enhance_wall_ms>\d+) "
    r"analyzer=(?P<analyzer_ms>\d+) e2e=(?P<e2e_ms>\d+)ms "
    r"tensorPath=(?P<tensor_path>\w+) optimizedTensor=(?P<optimized_tensor>\w+) "
    r"shadowLuma=(?P<shadow_luma>[\d.]+) shadowSharp=(?P<shadow_sharp>[\d.]+) "
    r"shadowMotionMad=(?P<shadow_motion_mad>[\d.]+) shadowDecision=(?P<shadow_decision>\w+)"
)


def percentile(values: list[float], q: float) -> float:
    if not values:
        return float("nan")
    return float(np.percentile(values, q))


def parse_rows(path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        match = LOG_RE.search(line)
        if not match:
            continue
        values = match.groupdict()
        row: dict[str, object] = {
            "index": len(rows) + 1,
            "source_log": str(path),
            "raw_log_prefix": line[:18],
        }
        for key, value in values.items():
            if key in {"backend", "model", "tensor_path", "optimized_tensor", "shadow_decision"}:
                row[key] = value
            elif key.startswith("shadow_"):
                row[key] = float(value)
            else:
                row[key] = int(value)
        rows.append(row)
    return rows


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def summarize(rows: list[dict[str, object]], group_key: str) -> list[dict[str, object]]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[str(row[group_key])].append(row)
    summary: list[dict[str, object]] = []
    for group, items in sorted(grouped.items()):
        e2e = [float(row["e2e_ms"]) for row in items]
        native = [float(row["native_rgb_ms"]) for row in items]
        motion = [float(row["shadow_motion_mad"]) for row in items]
        luma = [float(row["shadow_luma"]) for row in items]
        sharp = [float(row["shadow_sharp"]) for row in items]
        summary.append(
            {
                group_key: group,
                "frames": len(items),
                "e2e_p50_ms": f"{percentile(e2e, 50):.3f}",
                "e2e_p95_ms": f"{percentile(e2e, 95):.3f}",
                "native_rgb_p50_ms": f"{percentile(native, 50):.3f}",
                "native_rgb_p95_ms": f"{percentile(native, 95):.3f}",
                "luma_avg": f"{float(np.mean(luma)):.3f}",
                "sharp_avg": f"{float(np.mean(sharp)):.3f}",
                "motion_mad_avg": f"{float(np.mean(motion)):.3f}",
            }
        )
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", default="20260722_strategy_shadow_summary")
    parser.add_argument("--log", action="append", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = RESULTS_ROOT / args.run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []
    for log_path in args.log:
        if log_path.exists():
            rows.extend(parse_rows(log_path))
    write_csv(out_dir / "strategy_shadow_frames.csv", rows)
    by_decision = summarize(rows, "shadow_decision")
    by_tensor_path = summarize(rows, "tensor_path")
    write_csv(out_dir / "summary_by_decision.csv", by_decision)
    write_csv(out_dir / "summary_by_tensor_path.csv", by_tensor_path)
    loop_state = {
        "schema_version": 1,
        "run_id": args.run_id,
        "output_dir": str(out_dir),
        "status": "strategy_shadow_summarized" if rows else "blocked_no_rows",
        "parsed_frames": len(rows),
        "requires_human_review": False,
        "blocked_by": "" if rows else "no strategy-shadow rows parsed",
        "boundary": "Shadow strategy analysis only; it does not enable frame skipping, model switching, or quality claims.",
    }
    (out_dir / "loop_state.json").write_text(json.dumps(loop_state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Strategy Shadow Summary",
        "",
        f"- status: `{loop_state['status']}`",
        f"- parsed frames: {len(rows)}",
        "- boundary: logs-only strategy evidence; no runtime behavior change",
        "",
        "## Decision",
        "",
        "Use this as evidence for whether a future real strategy mode is worth testing. Do not claim quality or power improvement from shadow decisions alone.",
        "",
        "## Outputs",
        "",
        f"- frames: `{out_dir / 'strategy_shadow_frames.csv'}`",
        f"- by decision: `{out_dir / 'summary_by_decision.csv'}`",
        f"- by tensor path: `{out_dir / 'summary_by_tensor_path.csv'}`",
    ]
    (out_dir / "SUMMARY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[ok] wrote {out_dir}")
    if not rows:
        raise SystemExit("[blocked] no strategy-shadow rows parsed")


if __name__ == "__main__":
    main()
