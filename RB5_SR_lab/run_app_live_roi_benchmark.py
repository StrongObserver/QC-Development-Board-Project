"""Collect Android app live-ROI SR timing from RB5 logcat.

This script starts RB5VisionLab with intent extras, waits until enough
``RB5_SR`` live-ROI timing lines are present in logcat, parses stage timings,
and writes a small result folder compatible with the project handoff style.
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import time
from datetime import datetime
from pathlib import Path
import re


REPO_ROOT = Path(__file__).resolve().parents[1]
RESULTS_ROOT = Path(r"C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results")
DEVICE_SERIAL = "ff5d3ab4"
APP_COMPONENT = "com.cyf.rb5visionlab/.MainActivity"
PACKAGE_NAME = "com.cyf.rb5visionlab"

LIVE_RE = re.compile(
    r"backend=(?P<backend>\w+) live ROI crop=(?P<crop_side>\d+)->128->512 "
    r"frame=(?P<frame_width>\d+)x(?P<frame_height>\d+) "
    r"cap=(?P<cap_ms>\d+) frameBitmap=(?P<frame_bitmap_ms>\d+) "
    r"roi=(?P<roi_ms>\d+) rotate=(?P<rotate_ms>\d+) "
    r"pre=(?P<pre_ms>\d+) inf=(?P<inf_ms>\d+) post=(?P<post_ms>\d+) "
    r"enhanceWall=(?P<enhance_wall_ms>\d+) sampleCopy=(?P<sample_copy_ms>\d+) "
    r"analyzer=(?P<analyzer_ms>\d+) e2e=(?P<e2e_ms>\d+)ms"
    r"(?: model=(?P<log_model>\w+))?"
)
TENSOR_LIVE_RE = re.compile(
    r"backend=(?P<backend>\w+) model=(?P<log_model>\w+) tensorLive crop=(?P<crop_side>\d+)->128->512 "
    r"frame=(?P<frame_width>\d+)x(?P<frame_height>\d+) "
    r"nativeRgb=(?P<native_rgb_ms>\d+) rotate=(?P<rotate_ms>\d+) "
    r"pre=(?P<pre_ms>\d+) inf=(?P<inf_ms>\d+) post=(?P<post_ms>\d+) "
    r"enhanceWall=(?P<enhance_wall_ms>\d+) analyzer=(?P<analyzer_ms>\d+) e2e=(?P<e2e_ms>\d+)ms"
)


def run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, check=check, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


def adb(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return run(["adb", "-s", DEVICE_SERIAL, *args], check=check)


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def percentile(values: list[float], q: float) -> float:
    if not values:
        raise ValueError("cannot summarize an empty timing list")
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    pos = (len(ordered) - 1) * q
    lower = int(pos)
    upper = min(lower + 1, len(ordered) - 1)
    weight = pos - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def summarize_stage(run_id: str, stage: str, values: list[float]) -> dict[str, object]:
    return {
        "run_id": run_id,
        "stage": stage,
        "count": len(values),
        "min_ms": f"{min(values):.1f}",
        "p50_ms": f"{percentile(values, 0.50):.1f}",
        "p95_ms": f"{percentile(values, 0.95):.1f}",
        "max_ms": f"{max(values):.1f}",
        "metric_role": "supporting_evidence" if stage not in {"sampleCopy"} else "diagnostic",
    }


def parse_live_rows(log_text: str, model: str, tensor_ready: bool) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for line in log_text.splitlines():
        match = TENSOR_LIVE_RE.search(line) if tensor_ready else LIVE_RE.search(line)
        if not match:
            continue
        values = match.groupdict()
        log_model = values.pop("log_model") or model
        row: dict[str, object] = {
            "index": len(rows) + 1,
            "model": log_model,
            "raw_log_prefix": line[:18],
        }
        for key, value in values.items():
            row[key] = value if key == "backend" else int(value)
        if tensor_ready:
            row["cap_ms"] = row["native_rgb_ms"]
            row["frame_bitmap_ms"] = 0
            row["roi_ms"] = row["native_rgb_ms"]
            row["sample_copy_ms"] = 0
        rows.append(row)
    return rows


def collect_logcat(
    model: str,
    min_frames: int,
    timeout_s: int,
    use_app_default: bool,
    tensor_ready: bool,
) -> tuple[str, list[dict[str, object]]]:
    start_cmd = [
        "shell",
        "am",
        "start",
        "-n",
        APP_COMPONENT,
        "--ez",
        "start_live_sr_tensor_ready" if tensor_ready else "start_live_sr",
        "true",
    ]
    if not use_app_default:
        start_cmd.extend(["--es", "sr_backend", "QNN", "--es", "sr_model", model])
    adb("logcat", "-c")
    adb("shell", "am", "force-stop", PACKAGE_NAME, check=False)
    started = adb(*start_cmd, check=False)
    if started.returncode != 0:
        raise RuntimeError(started.stdout)

    final_log = ""
    final_rows: list[dict[str, object]] = []
    deadline = time.time() + timeout_s
    try:
        while time.time() < deadline:
            time.sleep(2)
            dump = adb(
                "logcat",
                "-d",
                "-v",
                "time",
                "RB5_SR:D",
                "RB5_SR_TENSOR:D",
                "RB5_QNN:D",
                "AndroidRuntime:E",
                "*:S",
                check=False,
            )
            final_log = dump.stdout
            final_rows = parse_live_rows(final_log, model, tensor_ready)
            if len(final_rows) >= min_frames:
                break
    finally:
        adb("shell", "am", "force-stop", PACKAGE_NAME, check=False)
    return final_log, final_rows


def read_baseline_metrics(path: Path | None) -> dict[str, tuple[str, str]]:
    if path is None or not path.exists():
        return {}
    result: dict[str, tuple[str, str]] = {}
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            stage = row.get("stage", "")
            p50 = row.get("after_p50_ms") or row.get("p50_ms") or ""
            p95 = row.get("after_p95_ms") or row.get("p95_ms") or ""
            if stage and p50 and p95:
                result[stage] = (p50, p95)
    return result


def make_loop_state(
    run_id: str,
    out_dir: Path,
    model: str,
    parsed_frames: int,
    min_frames: int,
    blocked_by: str,
) -> dict[str, object]:
    passed = parsed_frames >= min_frames and not blocked_by
    return {
        "schema_version": 1,
        "run_id": run_id,
        "output_dir": str(out_dir),
        "status": "live_roi_default_validated" if passed and model == "APP_DEFAULT" else "ready_for_resource_measurement" if passed else "environment_blocked",
        "stop_reason": "app_default_live_roi_validated" if passed and model == "APP_DEFAULT" else "quick_sr_live_roi_validated" if passed else "live_roi_log_collection_failed",
        "next_priority_task": "Proceed to compact showcase documentation and commit planning."
        if passed and model == "APP_DEFAULT"
        else "P6 resource cost measurement before any automatic model strategy"
        if passed
        else "restore Android app live ROI logging and rerun P5",
        "model": model,
        "backend": "QNN",
        "min_required_frames": min_frames,
        "parsed_frames": parsed_frames,
        "blocked_by": blocked_by,
        "requires_human_review": False,
        "notes": (
            "QuickSRNet live ROI has enough app timing evidence; quality still needs visual review before default promotion."
            if passed
            else "No enough live ROI timing rows were parsed from logcat."
        ),
    }


def write_summary(
    out_dir: Path,
    run_id: str,
    model: str,
    frame_rows: list[dict[str, object]],
    stage_rows: list[dict[str, object]],
    baseline: dict[str, tuple[str, str]],
) -> None:
    def stage_pair(stage: str) -> tuple[str, str]:
        for row in stage_rows:
            if row["stage"] == stage:
                return str(row["p50_ms"]), str(row["p95_ms"])
        return "", ""

    lines = [
        f"# App Live ROI Summary - {model}",
        "",
        f"- run_id: `{run_id}`",
        "- device: RB5 Gen2 / QCS8550 / Android 13",
        f"- app path: CameraX live ROI -> {model} TFLite -> QNN TFLite Delegate / HTP",
        f"- parsed frames: {len(frame_rows)}",
        "- boundary: app-side timing evidence, not power, thermal, or visual-quality evidence",
        "",
        "## Key Timing",
        "",
        "| stage | Real-ESRGAN W8A8 baseline p50/p95 ms | this run p50/p95 ms |",
        "| --- | ---: | ---: |",
    ]
    stage_map = [
        ("frameBitmap_full_conversion", "frame_bitmap_ms", "ImageProxy.toBitmap()"),
        ("qnn_inference", "inf_ms", "QNN inference"),
        ("postprocess", "post_ms", "postprocess"),
        ("analyzer_wall", "analyzer_ms", "analyzer wall"),
        ("e2e", "e2e_ms", "app e2e"),
    ]
    stage_lookup = {
        "frame_bitmap_ms": "frameBitmap",
        "inf_ms": "inf",
        "post_ms": "post",
        "analyzer_ms": "analyzer",
        "e2e_ms": "e2e",
    }
    for baseline_stage, script_stage, label in stage_map:
        p50, p95 = stage_pair(stage_lookup[script_stage])
        base = baseline.get(baseline_stage, ("", ""))
        base_text = f"{base[0]} / {base[1]}" if base[0] else "n/a"
        lines.append(f"| `{label}` | {base_text} | {p50} / {p95} |")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "This run answers P5 only: whether QuickSRNetSmall can run in the same 1280x960 live ROI app path through QNN Delegate.",
            "It does not justify automatic dual-model routing by itself. P6 still needs init, memory, and switching measurements.",
            "",
            "## Outputs",
            "",
            f"- per-frame timings: `{out_dir / 'frame_metrics.csv'}`",
            f"- stage summary: `{out_dir / 'metrics.csv'}`",
            f"- raw logcat: `{out_dir / 'raw_logcat.txt'}`",
            f"- loop state: `{out_dir / 'loop_state.json'}`",
            "",
            "## Next",
            "",
            "Measure resource cost before any automatic strategy: init time, first-frame jank, single-model memory, two-model memory, and switch cost.",
        ]
    )
    (out_dir / "SUMMARY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="QUICKSR_W8A8", choices=["W8A8", "QUICKSR_W8A8"])
    parser.add_argument("--use-app-default", action="store_true", help="Do not pass sr_backend/sr_model extras; validate the app's compiled default.")
    parser.add_argument("--tensor-ready", action="store_true", help="Run the isolated native-RGB tensor-ready live path.")
    parser.add_argument("--min-frames", type=int, default=120)
    parser.add_argument("--timeout-s", type=int, default=90)
    parser.add_argument("--run-id", default="")
    parser.add_argument(
        "--baseline-metrics",
        type=Path,
        default=RESULTS_ROOT / "20260718_app_qnn_delegate_live_roi_1280x960" / "metrics.csv",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    model_label = "TENSOR_READY_QUICKSR_W8A8" if args.tensor_ready else "APP_DEFAULT" if args.use_app_default else args.model
    run_id = args.run_id or datetime.now().strftime(f"%Y%m%d_%H%M%S_app_{model_label.lower()}_live_roi_1280x960")
    out_dir = RESULTS_ROOT / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    devices = run(["adb", "devices"], check=False).stdout
    expected = f"{DEVICE_SERIAL}\tdevice"
    if expected not in devices:
        loop_state = make_loop_state(run_id, out_dir, args.model, 0, args.min_frames, f"missing {expected}")
        (out_dir / "loop_state.json").write_text(json.dumps(loop_state, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        raise SystemExit(f"[blocked] {expected} not found")

    log_text, frame_rows = collect_logcat(model_label, args.min_frames, args.timeout_s, args.use_app_default, args.tensor_ready)
    (out_dir / "raw_logcat.txt").write_text(log_text, encoding="utf-8")
    write_csv(out_dir / "frame_metrics.csv", frame_rows)

    blocked_by = "" if len(frame_rows) >= args.min_frames else f"parsed {len(frame_rows)} frames, expected at least {args.min_frames}"
    loop_state = make_loop_state(run_id, out_dir, model_label, len(frame_rows), args.min_frames, blocked_by)
    stage_rows: list[dict[str, object]] = []
    if frame_rows:
        for key, label in [
            ("frame_bitmap_ms", "frameBitmap"),
            ("native_rgb_ms", "nativeRgb"),
            ("cap_ms", "cap"),
            ("roi_ms", "roi"),
            ("rotate_ms", "rotate"),
            ("pre_ms", "pre"),
            ("inf_ms", "inf"),
            ("post_ms", "post"),
            ("enhance_wall_ms", "enhanceWall"),
            ("sample_copy_ms", "sampleCopy"),
            ("analyzer_ms", "analyzer"),
            ("e2e_ms", "e2e"),
        ]:
            if key in frame_rows[0]:
                stage_rows.append(summarize_stage(run_id, label, [float(row[key]) for row in frame_rows]))
    write_csv(out_dir / "metrics.csv", stage_rows)
    write_csv(
        out_dir / "run_log.csv",
        [
            {
                "run_id": run_id,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M +0800"),
                "device": "RB5 Gen2 QCS8550",
                "app_component": APP_COMPONENT,
                "backend": "QNN",
                "model": model_label,
                "parsed_frames": len(frame_rows),
                "status": loop_state["status"],
                "stop_reason": loop_state["stop_reason"],
                "next_priority_task": loop_state["next_priority_task"],
                "output_dir": str(out_dir),
            }
        ],
    )
    (out_dir / "loop_state.json").write_text(json.dumps(loop_state, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    (out_dir / "NEXT_ACTION.md").write_text(
        "\n".join(
            [
                "# Next Action",
                "",
                "## Current Conclusion",
                "",
                f"`{model_label}` live ROI timing collection parsed {len(frame_rows)} frames.",
                "",
                "## Next Priority",
                "",
                str(loop_state["next_priority_task"]),
                "",
                "## Boundary",
                "",
                "Do not enable automatic model routing until P6 resource-cost data exists.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    write_summary(out_dir, run_id, model_label, frame_rows, stage_rows, read_baseline_metrics(args.baseline_metrics))
    print(f"[ok] wrote {out_dir}")


if __name__ == "__main__":
    main()
