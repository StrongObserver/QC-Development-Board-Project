"""Run sustained app live-ROI SR timing with lightweight thermal snapshots."""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path

from app_e2e_export import (
    first_last_temperature_c,
    git_commit_label,
    last_temperature_c,
    mirror_app_e2e_log,
    model_name,
    model_variant,
    stage_value,
    write_app_e2e_log,
)


RESULTS_ROOT = Path(r"C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results")
REPO_ROOT = Path(__file__).resolve().parents[1]
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
)


def run(cmd: list[str], *, check: bool = True, timeout: int | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        check=check,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
    )


def adb(*args: str, check: bool = True, timeout: int | None = None) -> subprocess.CompletedProcess[str]:
    return run(["adb", "-s", DEVICE_SERIAL, *args], check=check, timeout=timeout)


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
        raise ValueError("empty values")
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    pos = (len(ordered) - 1) * q
    lower = int(pos)
    upper = min(lower + 1, len(ordered) - 1)
    weight = pos - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def parse_live_rows(log_text: str, model: str) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for line in log_text.splitlines():
        match = LIVE_RE.search(line)
        if not match:
            continue
        row: dict[str, object] = {
            "index": len(rows) + 1,
            "model": model,
            "raw_log_prefix": line[:18],
        }
        for key, value in match.groupdict().items():
            row[key] = value if key == "backend" else int(value)
        rows.append(row)
    return rows


def battery_snapshot(elapsed_s: float) -> dict[str, object]:
    row: dict[str, object] = {"elapsed_s": f"{elapsed_s:.1f}"}
    try:
        out = adb("shell", "dumpsys", "battery", check=False, timeout=5).stdout
    except Exception as exc:
        row["error"] = str(exc)
        return row
    for line in out.splitlines():
        stripped = line.strip()
        if ":" not in stripped:
            continue
        key, value = [part.strip() for part in stripped.split(":", 1)]
        normalized = key.lower().replace(" ", "_")
        if normalized in {"status", "level", "voltage", "temperature", "usb_powered", "ac_powered"}:
            row[normalized] = value
    return row


def stage_summary(run_id: str, model: str, rows: list[dict[str, object]], fraction: tuple[float, float]) -> list[dict[str, object]]:
    start, end = fraction
    n = len(rows)
    if not rows:
        return []
    lo = int(n * start)
    hi = max(lo + 1, int(n * end))
    segment = rows[lo:hi]
    summary: list[dict[str, object]] = []
    for key, label in [
        ("frame_bitmap_ms", "frameBitmap"),
        ("pre_ms", "pre"),
        ("inf_ms", "inf"),
        ("post_ms", "post"),
        ("analyzer_ms", "analyzer"),
        ("e2e_ms", "e2e"),
    ]:
        values = [float(row[key]) for row in segment]
        summary.append(
            {
                "run_id": run_id,
                "model": model,
                "segment": f"{int(start * 100)}_{int(end * 100)}",
                "stage": label,
                "count": len(values),
                "p50_ms": f"{percentile(values, 0.50):.1f}",
                "p95_ms": f"{percentile(values, 0.95):.1f}",
                "min_ms": f"{min(values):.1f}",
                "max_ms": f"{max(values):.1f}",
            }
        )
    return summary


def collect_sustained(model: str, duration_s: int, thermal_interval_s: int, out_dir: Path) -> tuple[str, list[dict[str, object]]]:
    adb("logcat", "-c")
    adb("shell", "am", "force-stop", PACKAGE_NAME, check=False)
    log_path = out_dir / "raw_logcat.txt"
    thermal_rows: list[dict[str, object]] = []
    with log_path.open("w", encoding="utf-8") as log_file:
        proc = subprocess.Popen(
            [
                "adb",
                "-s",
                DEVICE_SERIAL,
                "logcat",
                "-v",
                "time",
                "RB5_SR:D",
                "RB5_QNN:D",
                "AndroidRuntime:E",
                "*:S",
            ],
            stdout=log_file,
            stderr=subprocess.STDOUT,
            text=True,
        )
        try:
            adb(
                "shell",
                "am",
                "start",
                "-n",
                APP_COMPONENT,
                "--ez",
                "start_live_sr",
                "true",
                "--es",
                "sr_backend",
                "QNN",
                "--es",
                "sr_model",
                model,
            )
            start = time.time()
            next_thermal = start
            while time.time() - start < duration_s:
                now = time.time()
                if now >= next_thermal:
                    thermal_rows.append(battery_snapshot(now - start))
                    next_thermal = now + thermal_interval_s
                time.sleep(1)
            thermal_rows.append(battery_snapshot(time.time() - start))
        finally:
            adb("shell", "am", "force-stop", PACKAGE_NAME, check=False)
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
    return log_path.read_text(encoding="utf-8", errors="replace"), thermal_rows


def make_loop_state(run_id: str, out_dir: Path, rows: list[dict[str, object]], duration_s: int) -> dict[str, object]:
    passed = len(rows) >= max(60, duration_s)
    return {
        "schema_version": 1,
        "run_id": run_id,
        "output_dir": str(out_dir),
        "status": "sustained_live_roi_validated" if passed else "environment_blocked",
        "stop_reason": "sustained_live_roi_collected" if passed else "too_few_live_roi_frames",
        "next_priority_task": "Use this as sustained app e2e evidence; do not reopen output postprocess unless a regression appears."
        if passed
        else "rerun sustained live ROI with stable camera/app state",
        "duration_s": duration_s,
        "parsed_frames": len(rows),
        "requires_human_review": False,
    }


def write_summary(
    out_dir: Path,
    run_id: str,
    model: str,
    duration_s: int,
    rows: list[dict[str, object]],
    metrics: list[dict[str, object]],
    thermal_rows: list[dict[str, object]],
    loop_state: dict[str, object],
    app_e2e_path: Path,
    app_e2e_mirror: Path,
) -> None:
    def find(segment: str, stage: str, field: str) -> str:
        for row in metrics:
            if row["segment"] == segment and row["stage"] == stage:
                return str(row[field])
        return ""

    temp_values = []
    for row in thermal_rows:
        value = row.get("temperature")
        if value is not None:
            try:
                temp_values.append(float(str(value)) / 10.0)
            except ValueError:
                pass

    lines = [
        f"# Sustained Live ROI Summary - {model}",
        "",
        f"- run_id: `{run_id}`",
        f"- duration_s: {duration_s}",
        f"- parsed_frames: {len(rows)}",
        "- backend: QNN TFLite Delegate / HTP",
        "- boundary: battery temperature is a coarse system signal, not a full power measurement",
        f"- loop_status: `{loop_state['status']}`",
        f"- next_priority_task: `{loop_state['next_priority_task']}`",
        "",
        "## Timing Drift",
        "",
        "| stage | first 20% p50/p95 ms | last 20% p50/p95 ms |",
        "| --- | ---: | ---: |",
    ]
    for stage in ["frameBitmap", "pre", "inf", "post", "analyzer", "e2e"]:
        lines.append(
            f"| `{stage}` | {find('0_20', stage, 'p50_ms')} / {find('0_20', stage, 'p95_ms')} | "
            f"{find('80_100', stage, 'p50_ms')} / {find('80_100', stage, 'p95_ms')} |"
        )
    lines.extend(["", "## Temperature", ""])
    if temp_values:
        lines.append(f"- battery temperature: {min(temp_values):.1f}C -> {max(temp_values):.1f}C")
    else:
        lines.append("- battery temperature: not available")
    lines.extend(
        [
            "",
            "## Outputs",
            "",
            f"- per-frame timings: `{out_dir / 'frame_metrics.csv'}`",
            f"- stage metrics: `{out_dir / 'metrics.csv'}`",
            f"- EvalHub app e2e row: `{app_e2e_path}`",
            f"- EvalHub ignored mirror: `{app_e2e_mirror}`",
            f"- thermal snapshots: `{out_dir / 'thermal_metrics.csv'}`",
            f"- raw logcat: `{out_dir / 'raw_logcat.txt'}`",
            f"- loop state: `{out_dir / 'loop_state.json'}`",
        ]
    )
    (out_dir / "SUMMARY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", choices=["W8A8", "QUICKSR_W8A8"], required=True)
    parser.add_argument("--duration-s", type=int, default=300)
    parser.add_argument("--thermal-interval-s", type=int, default=30)
    parser.add_argument("--run-id", default="")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_id = args.run_id or datetime.now().strftime(f"%Y%m%d_%H%M%S_sustained_{args.model.lower()}_live_roi")
    out_dir = RESULTS_ROOT / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    devices = run(["adb", "devices"], check=False).stdout
    expected = f"{DEVICE_SERIAL}\tdevice"
    if expected not in devices:
        raise SystemExit(f"[blocked] {expected} not found")
    log_text, thermal_rows = collect_sustained(args.model, args.duration_s, args.thermal_interval_s, out_dir)
    rows = parse_live_rows(log_text, args.model)
    metrics = []
    metrics.extend(stage_summary(run_id, args.model, rows, (0.0, 0.2)))
    metrics.extend(stage_summary(run_id, args.model, rows, (0.0, 1.0)))
    metrics.extend(stage_summary(run_id, args.model, rows, (0.8, 1.0)))
    loop_state = make_loop_state(run_id, out_dir, rows, args.duration_s)
    write_csv(out_dir / "frame_metrics.csv", rows)
    write_csv(out_dir / "metrics.csv", metrics)
    write_csv(out_dir / "thermal_metrics.csv", thermal_rows)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M +0800")
    write_csv(
        out_dir / "run_log.csv",
        [
            {
                "run_id": run_id,
                "timestamp": timestamp,
                "model": args.model,
                "backend": "QNN",
                "duration_s": args.duration_s,
                "parsed_frames": len(rows),
                "status": loop_state["status"],
                "stop_reason": loop_state["stop_reason"],
                "output_dir": str(out_dir),
            }
        ],
    )
    (out_dir / "loop_state.json").write_text(json.dumps(loop_state, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    (out_dir / "NEXT_ACTION.md").write_text(
        "# Next Action\n\n"
        f"- status: `{loop_state['status']}`\n"
        f"- next_priority_task: `{loop_state['next_priority_task']}`\n",
        encoding="utf-8",
    )
    all_segment_metrics = [row for row in metrics if row.get("segment") == "0_100"]
    last_segment_metrics = [row for row in metrics if row.get("segment") == "80_100"]
    temp_trend = first_last_temperature_c(thermal_rows)
    app_e2e_path = out_dir / "app_e2e_log.csv"
    write_app_e2e_log(
        app_e2e_path,
        {
            "run_id": run_id,
            "timestamp": timestamp,
            "device": "RB5 Gen2 QCS8550",
            "android_version": "Android 13",
            "app_commit": git_commit_label(REPO_ROOT),
            "model_name": model_name(args.model),
            "model_variant": model_variant(args.model),
            "backend": "QNN TFLite Delegate / HTP",
            "input_source": "camera_roi_live_sustained",
            "input_size": "128x128",
            "output_size": "512x512",
            "preprocess_ms": stage_value(all_segment_metrics, "pre", "p50_ms"),
            "inference_ms": stage_value(all_segment_metrics, "inf", "p50_ms"),
            "postprocess_ms": stage_value(all_segment_metrics, "post", "p50_ms"),
            "e2e_ms": stage_value(all_segment_metrics, "e2e", "p50_ms"),
            "steady_state_window": f"{args.duration_s}s run; all frames and last 20% tracked",
            "p50_e2e_ms": stage_value(all_segment_metrics, "e2e", "p50_ms"),
            "p95_e2e_ms": stage_value(all_segment_metrics, "e2e", "p95_ms"),
            "npu_or_dsp_note": "QNN Delegate configured for HTP backend; sustained run uses app logcat timings",
            "skin_temp_c": last_temperature_c(thermal_rows),
            "thermal_status": "coarse_battery_temperature_only",
            "fallback_code": "none" if loop_state["status"] != "environment_blocked" else "too_few_frames",
            "failure_code": "none" if loop_state["status"] != "environment_blocked" else "too_few_frames",
            "human_decision": "not_reviewed",
            "notes": (
                "Sustained app live ROI e2e row. Last-20% e2e p50/p95="
                f"{stage_value(last_segment_metrics, 'e2e', 'p50_ms')}/"
                f"{stage_value(last_segment_metrics, 'e2e', 'p95_ms')} ms. "
                f"Battery temperature trend={temp_trend or 'n/a'} C. "
                "Temperature is coarse battery signal, not external thermal instrumentation."
            ),
        },
    )
    app_e2e_mirror = mirror_app_e2e_log(REPO_ROOT, run_id, app_e2e_path)
    write_summary(
        out_dir,
        run_id,
        args.model,
        args.duration_s,
        rows,
        metrics,
        thermal_rows,
        loop_state,
        app_e2e_path,
        app_e2e_mirror,
    )
    print(f"[ok] wrote {out_dir}")


if __name__ == "__main__":
    main()
