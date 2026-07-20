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

from app_e2e_export import (
    git_commit_label,
    mirror_app_e2e_log,
    model_name,
    model_variant,
    stage_value,
    write_app_e2e_log,
)


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
    r"(?: session=(?P<session_id>\S+))?"
    r"(?: everyN=(?P<every_n>\d+) frameIndex=(?P<frame_index>\d+) "
    r"enhancedIndex=(?P<enhanced_index>\d+) effectiveEnhancedFps=(?P<effective_enhanced_fps>[\d.]+))?"
)
SKIP_RE = re.compile(
    r"backend=(?P<backend>\w+) live ROI skip everyN=(?P<every_n>\d+) "
    r"frameIndex=(?P<frame_index>\d+) enhancedIndex=(?P<enhanced_index>\d+) "
    r"model=(?P<log_model>\w+)(?: session=(?P<session_id>\S+))?"
)
TENSOR_LIVE_RE = re.compile(
    r"backend=(?P<backend>\w+) model=(?P<log_model>\w+) tensorLive crop=(?P<crop_side>\d+)->128->512 "
    r"frame=(?P<frame_width>\d+)x(?P<frame_height>\d+) "
    r"nativeRgb=(?P<native_rgb_ms>\d+) rotate=(?P<rotate_ms>\d+) "
    r"pre=(?P<pre_ms>\d+) inf=(?P<inf_ms>\d+) post=(?P<post_ms>\d+) "
    r"enhanceWall=(?P<enhance_wall_ms>\d+) analyzer=(?P<analyzer_ms>\d+) e2e=(?P<e2e_ms>\d+)ms"
)


def latest_session_log(log_text: str) -> str:
    start = -1
    for marker in ["auto live SR from intent", "auto tensor-ready live SR from intent"]:
        pos = log_text.rfind(marker)
        if pos > start:
            start = pos
    if start < 0:
        return log_text
    line_start = log_text.rfind("\n", 0, start)
    return log_text[line_start + 1 :]


def filter_session_lines(log_text: str, session_id: str) -> str:
    if not session_id:
        return log_text
    lines = []
    for line in log_text.splitlines():
        if f"session={session_id}" in line or f"sr_session_id={session_id}" in line:
            lines.append(line)
    return "\n".join(lines) + ("\n" if lines else "")


def run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, check=check, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


def adb(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return run(["adb", "-s", DEVICE_SERIAL, *args], check=check)


def wait_package_stopped(timeout_s: float = 5.0) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        result = adb("shell", "pidof", PACKAGE_NAME, check=False)
        if result.returncode != 0 or not result.stdout.strip():
            return True
        time.sleep(0.2)
    return False


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


def parse_skip_rows(log_text: str, session_id: str = "") -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for line in log_text.splitlines():
        match = SKIP_RE.search(line)
        if not match:
            continue
        values = match.groupdict()
        if session_id and values.get("session_id") != session_id:
            continue
        rows.append(
            {
                "index": len(rows) + 1,
                "backend": values["backend"],
                "model": values["log_model"],
                "session_id": values.get("session_id") or "",
                "every_n": int(values["every_n"]),
                "frame_index": int(values["frame_index"]),
                "enhanced_index": int(values["enhanced_index"]),
                "raw_log_prefix": line[:18],
            }
        )
    return rows


def parse_live_rows(log_text: str, model: str, tensor_ready: bool, session_id: str = "") -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for line in log_text.splitlines():
        match = TENSOR_LIVE_RE.search(line) if tensor_ready else LIVE_RE.search(line)
        if not match:
            continue
        values = match.groupdict()
        if session_id and values.get("session_id") != session_id:
            continue
        log_model = values.pop("log_model") or model
        row: dict[str, object] = {
            "index": len(rows) + 1,
            "model": log_model,
            "session_id": values.pop("session_id") or "",
            "raw_log_prefix": line[:18],
        }
        for key, value in values.items():
            if key == "backend":
                row[key] = value
            elif key == "effective_enhanced_fps":
                row[key] = float(value) if value is not None else ""
            elif value is not None:
                row[key] = int(value)
        if tensor_ready:
            row["cap_ms"] = row["native_rgb_ms"]
            row["frame_bitmap_ms"] = 0
            row["roi_ms"] = row["native_rgb_ms"]
            row["sample_copy_ms"] = 0
        rows.append(row)
    return rows


def add_normalized_session_indices(rows: list[dict[str, object]], skip_rows: list[dict[str, object]]) -> None:
    frame_indices = [
        int(row["frame_index"])
        for row in [*rows, *skip_rows]
        if row.get("frame_index") not in ("", None)
    ]
    enhanced_indices = [
        int(row["enhanced_index"])
        for row in [*rows, *skip_rows]
        if row.get("enhanced_index") not in ("", None)
    ]
    first_frame = min(frame_indices) if frame_indices else 1
    first_enhanced = min(enhanced_indices) if enhanced_indices else 1
    for row in [*rows, *skip_rows]:
        if row.get("frame_index") not in ("", None):
            row["session_frame_index"] = int(row["frame_index"]) - first_frame + 1
        if row.get("enhanced_index") not in ("", None):
            row["session_enhanced_index"] = int(row["enhanced_index"]) - first_enhanced + 1


def collect_logcat(
    model: str,
    min_frames: int,
    timeout_s: int,
    use_app_default: bool,
    tensor_ready: bool,
    every_n: int,
    duration_s: int,
    session_id: str,
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
        "--es",
        "sr_session_id",
        session_id,
    ]
    if not use_app_default:
        start_cmd.extend(["--es", "sr_backend", "QNN", "--es", "sr_model", model])
    if every_n > 1 and not tensor_ready:
        start_cmd.extend(["--ei", "sr_every_n", str(every_n)])
    adb("shell", "am", "force-stop", PACKAGE_NAME, check=False)
    time.sleep(0.5)
    adb("shell", "am", "force-stop", PACKAGE_NAME, check=False)
    if not wait_package_stopped():
        raise RuntimeError(f"{PACKAGE_NAME} did not stop cleanly before collection")
    adb("logcat", "-c")
    started = adb(*start_cmd, check=False)
    if started.returncode != 0:
        raise RuntimeError(started.stdout)

    final_log = ""
    final_rows: list[dict[str, object]] = []
    start_time = time.time()
    deadline = start_time + timeout_s
    duration_deadline = start_time + duration_s if duration_s > 0 else 0.0
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
            final_rows = parse_live_rows(latest_session_log(final_log), model, tensor_ready, session_id)
            duration_done = duration_s <= 0 or time.time() >= duration_deadline
            if len(final_rows) >= min_frames and duration_done:
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
    every_n: int,
    skipped_frames: int,
) -> dict[str, object]:
    passed = parsed_frames >= min_frames and not blocked_by
    is_every_n = every_n > 1
    if passed and is_every_n:
        status = "temporal_cadence_validated"
        stop_reason = "every_n_live_roi_collected"
        next_priority_task = "Decide whether every-N ImageAnalysis is useful as a product/display cadence; do not report it as per-frame latency improvement."
    elif passed and model == "APP_DEFAULT":
        status = "live_roi_default_validated"
        stop_reason = "app_default_live_roi_validated"
        next_priority_task = "Proceed to compact showcase documentation and commit planning."
    elif passed:
        status = "live_roi_model_validated"
        stop_reason = "quick_sr_live_roi_validated"
        next_priority_task = "Use this as app timing evidence; resource-cost probing is already complete unless a regression appears."
    else:
        status = "environment_blocked"
        stop_reason = "live_roi_log_collection_failed"
        next_priority_task = "restore Android app live ROI logging and rerun the smoke"
    return {
        "schema_version": 1,
        "run_id": run_id,
        "output_dir": str(out_dir),
        "status": status,
        "stop_reason": stop_reason,
        "next_priority_task": next_priority_task,
        "model": model,
        "backend": "QNN",
        "min_required_frames": min_frames,
        "parsed_frames": parsed_frames,
        "every_n": every_n,
        "skipped_frames": skipped_frames,
        "blocked_by": blocked_by,
        "requires_human_review": False,
        "notes": (
            "Every-N reduces enhancement cadence, not the latency of enhanced frames."
            if passed and is_every_n
            else "App live ROI has enough timing evidence; quality still needs visual review before product-style promotion."
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
    app_e2e_path: Path,
    app_e2e_mirror: Path,
    skip_rows: list[dict[str, object]],
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
        f"- skipped frames: {len(skip_rows)}",
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
            "This run is app-side live ROI timing evidence through QNN Delegate.",
            "If `everyN` is greater than 1, the result is a cadence/product probe: it reduces how often SR runs, not the latency of an enhanced frame.",
            "It does not justify automatic dual-model routing by itself and is not visual-quality evidence.",
            "",
            "## Outputs",
            "",
            f"- per-frame timings: `{out_dir / 'frame_metrics.csv'}`",
            f"- skipped-frame log rows: `{out_dir / 'skip_metrics.csv'}`",
            f"- stage summary: `{out_dir / 'metrics.csv'}`",
            f"- EvalHub app e2e row: `{app_e2e_path}`",
            f"- EvalHub ignored mirror: `{app_e2e_mirror}`",
            f"- raw logcat: `{out_dir / 'raw_logcat.txt'}`",
            f"- parsed session logcat: `{out_dir / 'session_logcat.txt'}`",
            f"- loop state: `{out_dir / 'loop_state.json'}`",
            "",
            "## Next",
            "",
            "Close the current diff after review. Continue every-N only if it is useful as a product/display cadence; do not reopen output postprocess unless a regression appears.",
        ]
    )
    (out_dir / "SUMMARY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="QUICKSR_W8A8", choices=["W8A8", "QUICKSR_W8A8"])
    parser.add_argument("--use-app-default", action="store_true", help="Do not pass sr_backend/sr_model extras; validate the app's compiled default.")
    parser.add_argument("--tensor-ready", action="store_true", help="Run the isolated native-RGB tensor-ready live path.")
    parser.add_argument("--every-n", type=int, default=1, help="Enhance every Nth ImageAnalysis frame for temporal smoke.")
    parser.add_argument("--min-frames", type=int, default=120)
    parser.add_argument("--timeout-s", type=int, default=90)
    parser.add_argument("--duration-s", type=int, default=0, help="Keep collecting until this duration is reached as well as min-frames.")
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
        loop_state = make_loop_state(run_id, out_dir, args.model, 0, args.min_frames, f"missing {expected}", args.every_n, 0)
        (out_dir / "loop_state.json").write_text(json.dumps(loop_state, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        raise SystemExit(f"[blocked] {expected} not found")

    every_n = max(1, args.every_n)
    if args.tensor_ready and every_n > 1:
        raise SystemExit("[blocked] --every-n is only supported for the Bitmap live ROI path")
    log_text, frame_rows = collect_logcat(
        model_label,
        args.min_frames,
        args.timeout_s,
        args.use_app_default,
        args.tensor_ready,
        every_n,
        max(0, args.duration_s),
        run_id,
    )
    session_log_text = filter_session_lines(latest_session_log(log_text), run_id)
    frame_rows = parse_live_rows(session_log_text, model_label, args.tensor_ready, run_id)
    skip_rows = parse_skip_rows(session_log_text, run_id)
    add_normalized_session_indices(frame_rows, skip_rows)
    (out_dir / "raw_logcat.txt").write_text(log_text, encoding="utf-8")
    (out_dir / "session_logcat.txt").write_text(session_log_text, encoding="utf-8")
    write_csv(out_dir / "frame_metrics.csv", frame_rows)
    write_csv(out_dir / "skip_metrics.csv", skip_rows)

    blocked_by = "" if len(frame_rows) >= args.min_frames else f"parsed {len(frame_rows)} frames, expected at least {args.min_frames}"
    loop_state = make_loop_state(run_id, out_dir, model_label, len(frame_rows), args.min_frames, blocked_by, every_n, len(skip_rows))
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
        if "effective_enhanced_fps" in frame_rows[0]:
            fps_values = [float(row["effective_enhanced_fps"]) for row in frame_rows if row.get("effective_enhanced_fps") not in ("", None)]
            if fps_values:
                stage_rows.append(summarize_stage(run_id, "effectiveEnhancedFps", fps_values))
    write_csv(out_dir / "metrics.csv", stage_rows)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M +0800")
    write_csv(
        out_dir / "run_log.csv",
        [
            {
                "run_id": run_id,
                "timestamp": timestamp,
                "device": "RB5 Gen2 QCS8550",
                "app_component": APP_COMPONENT,
                "backend": "QNN",
                "model": model_label,
                "parsed_frames": len(frame_rows),
                "skipped_frames": len(skip_rows),
                "every_n": every_n,
                "duration_s": args.duration_s,
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
    app_e2e_path = out_dir / "app_e2e_log.csv"
    write_app_e2e_log(
        app_e2e_path,
        {
            "run_id": run_id,
            "timestamp": timestamp,
            "device": "RB5 Gen2 QCS8550",
            "android_version": "Android 13",
            "app_commit": git_commit_label(REPO_ROOT),
            "model_name": model_name(model_label),
            "model_variant": model_variant(model_label),
            "backend": "QNN TFLite Delegate / HTP",
            "input_source": "camera_roi_live",
            "input_size": "128x128",
            "output_size": "512x512",
            "preprocess_ms": stage_value(stage_rows, "pre", "p50_ms"),
            "inference_ms": stage_value(stage_rows, "inf", "p50_ms"),
            "postprocess_ms": stage_value(stage_rows, "post", "p50_ms"),
            "e2e_ms": stage_value(stage_rows, "e2e", "p50_ms"),
            "steady_state_window": f"all enhanced frames ({len(frame_rows)}); everyN={every_n}; skipped={len(skip_rows)}; duration_s={args.duration_s}",
            "p50_e2e_ms": stage_value(stage_rows, "e2e", "p50_ms"),
            "p95_e2e_ms": stage_value(stage_rows, "e2e", "p95_ms"),
            "npu_or_dsp_note": "QNN Delegate configured for HTP backend; per-run fallback not detected from RB5_SR timing logs",
            "fallback_code": "none" if not blocked_by else "live_roi_log_collection_failed",
            "failure_code": "none" if not blocked_by else "too_few_frames",
            "human_decision": "not_reviewed",
            "notes": f"App live ROI e2e schema row derived from RB5_SR logcat timings; everyN={every_n}; skipped={len(skip_rows)}; duration_s={args.duration_s}; not visual quality evidence.",
        },
    )
    app_e2e_mirror = mirror_app_e2e_log(REPO_ROOT, run_id, app_e2e_path)
    write_summary(
        out_dir,
        run_id,
        model_label,
        frame_rows,
        stage_rows,
        read_baseline_metrics(args.baseline_metrics),
        app_e2e_path,
        app_e2e_mirror,
        skip_rows,
    )
    print(f"[ok] wrote {out_dir}")


if __name__ == "__main__":
    main()
