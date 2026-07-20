"""Record a low-cost RB5VisionLab live-ROI demo video.

This is deliberately a demo capture runner, not a VideoCapture/Recorder SR
pipeline. It starts the existing live ROI path through an intent, records the
device display with ``adb screenrecord``, and saves timing logs next to the MP4.
"""

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


def summarize_stage(run_id: str, stage: str, values: list[float]) -> dict[str, object]:
    return {
        "run_id": run_id,
        "stage": stage,
        "count": len(values),
        "min_ms": f"{min(values):.1f}",
        "p50_ms": f"{percentile(values, 0.50):.1f}",
        "p95_ms": f"{percentile(values, 0.95):.1f}",
        "max_ms": f"{max(values):.1f}",
        "metric_role": "supporting_evidence",
    }


def parse_live_rows(log_text: str, model: str, session_id: str) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for line in log_text.splitlines():
        match = LIVE_RE.search(line)
        if not match:
            continue
        values = match.groupdict()
        if values.get("session_id") != session_id:
            continue
        log_model = values.pop("log_model") or model
        row: dict[str, object] = {
            "index": len(rows) + 1,
            "model": log_model,
            "session_id": values.pop("session_id") or "",
            "raw_log_prefix": line[:18],
        }
        for key, value in values.items():
            if value is None:
                row[key] = ""
            elif key == "backend":
                row[key] = value
            elif key == "effective_enhanced_fps":
                row[key] = float(value)
            else:
                row[key] = int(value)
        rows.append(row)
    return rows


def write_loop_state(
    out_dir: Path,
    run_id: str,
    model: str,
    rows: list[dict[str, object]],
    local_video: Path,
    blocked_by: str,
) -> dict[str, object]:
    passed = not blocked_by and local_video.exists() and local_video.stat().st_size > 0 and len(rows) > 0
    state = {
        "schema_version": 1,
        "run_id": run_id,
        "output_dir": str(out_dir),
        "status": "low_cost_video_demo_collected" if passed else "environment_blocked",
        "stop_reason": "screenrecord_demo_collected" if passed else "video_demo_collection_failed",
        "next_priority_task": (
            "Human-review the MP4 for framing/readability; this is demo evidence, not true video SR."
            if passed
            else "Rerun after restoring device/app/screenrecord state."
        ),
        "model": model,
        "video_path": str(local_video),
        "parsed_frames": len(rows),
        "blocked_by": blocked_by,
        "requires_human_review": passed,
        "boundary": "adb screenrecord of demo-mode live ROI UI; not CameraX VideoCapture/Recorder and not temporal SR quality evidence",
    }
    (out_dir / "loop_state.json").write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return state


def write_summary(
    out_dir: Path,
    run_id: str,
    model: str,
    duration_s: int,
    local_video: Path,
    remote_video: str,
    rows: list[dict[str, object]],
    metrics: list[dict[str, object]],
    loop_state: dict[str, object],
    app_e2e_path: Path,
    app_e2e_mirror: Path,
) -> None:
    lines = [
        "# Low-Cost Video Demo Summary",
        "",
        f"- run_id: `{run_id}`",
        f"- model: `{model}`",
        f"- duration_s: {duration_s}",
        f"- parsed live ROI frames: {len(rows)}",
        f"- local MP4: `{local_video}`",
        f"- remote MP4: `{remote_video}`",
        f"- loop_status: `{loop_state['status']}`",
        "- boundary: screen recording of the demo-mode live ROI UI, not a true VideoCapture/Recorder SR pipeline",
        "",
        "## Timing",
        "",
        "| stage | p50 ms | p95 ms |",
        "| --- | ---: | ---: |",
    ]
    for row in metrics:
        lines.append(f"| `{row['stage']}` | {row['p50_ms']} | {row['p95_ms']} |")
    lines.extend(
        [
            "",
            "## Outputs",
            "",
            f"- video: `{local_video}`",
            f"- per-frame timings: `{out_dir / 'frame_metrics.csv'}`",
            f"- stage metrics: `{out_dir / 'metrics.csv'}`",
            f"- EvalHub app e2e row: `{app_e2e_path}`",
            f"- EvalHub ignored mirror: `{app_e2e_mirror}`",
            f"- raw logcat: `{out_dir / 'raw_logcat.txt'}`",
            f"- screenrecord output: `{out_dir / 'screenrecord_stdout.txt'}`",
            "",
            "## Review Boundary",
            "",
            "Use this MP4 as a low-cost project demo artifact only. It can show the app running demo-mode live ROI SR on device, but it does not prove temporal consistency, per-frame video enhancement, or external power efficiency.",
        ]
    )
    (out_dir / "SUMMARY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def collect_demo(
    model: str,
    duration_s: int,
    size: str,
    bit_rate: str,
    every_n: int,
    demo_mode: bool,
    pre_record_wait_s: float,
    out_dir: Path,
    run_id: str,
) -> tuple[str, Path, str]:
    remote_video = f"/sdcard/Movies/{run_id}.mp4"
    local_video = out_dir / f"{run_id}.mp4"
    adb("shell", "am", "force-stop", PACKAGE_NAME, check=False)
    adb("logcat", "-c", check=False)
    start_cmd = [
        "shell",
        "am",
        "start",
        "-n",
        APP_COMPONENT,
        "--ez",
        "start_live_sr",
        "true",
        "--es",
        "sr_session_id",
        run_id,
        "--es",
        "sr_backend",
        "QNN",
        "--es",
        "sr_model",
        model,
    ]
    if demo_mode:
        start_cmd.extend(["--ez", "demo_mode", "true"])
    if every_n > 1:
        start_cmd.extend(["--ei", "sr_every_n", str(every_n)])
    adb(*start_cmd)
    time.sleep(max(0.0, pre_record_wait_s))
    screen_cmd = [
        "adb",
        "-s",
        DEVICE_SERIAL,
        "shell",
        "screenrecord",
        "--time-limit",
        str(duration_s),
        "--size",
        size,
        "--bit-rate",
        bit_rate,
        remote_video,
    ]
    proc = subprocess.Popen(screen_cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    try:
        stdout, _ = proc.communicate(timeout=duration_s + 20)
    except subprocess.TimeoutExpired:
        proc.terminate()
        stdout, _ = proc.communicate(timeout=5)
    adb("shell", "am", "force-stop", PACKAGE_NAME, check=False)
    (out_dir / "screenrecord_stdout.txt").write_text(stdout or "", encoding="utf-8")
    log_text = adb("logcat", "-d", "-v", "time", "RB5_SR:D", "RB5_QNN:D", "AndroidRuntime:E", "*:S", check=False).stdout
    (out_dir / "raw_logcat.txt").write_text(log_text, encoding="utf-8")
    pull = adb("pull", remote_video, str(local_video), check=False, timeout=60)
    (out_dir / "adb_pull_video.txt").write_text(pull.stdout, encoding="utf-8")
    return log_text, local_video, remote_video


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", choices=["QUICKSR_W8A8", "W8A8"], default="QUICKSR_W8A8")
    parser.add_argument("--duration-s", type=int, default=20)
    parser.add_argument("--size", default="1280x720")
    parser.add_argument("--bit-rate", default="8M")
    parser.add_argument("--every-n", type=int, default=1)
    parser.add_argument("--demo-mode", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--pre-record-wait-s", type=float, default=4.0)
    parser.add_argument("--run-id", default="")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_id = args.run_id or datetime.now().strftime("low_cost_video_demo_%Y%m%d_%H%M%S")
    out_dir = RESULTS_ROOT / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    devices = run(["adb", "devices"], check=False).stdout
    expected = f"{DEVICE_SERIAL}\tdevice"
    blocked_by = ""
    if expected not in devices:
        blocked_by = f"missing {expected}"
        local_video = out_dir / f"{run_id}.mp4"
        rows: list[dict[str, object]] = []
        metrics: list[dict[str, object]] = []
    else:
        log_text, local_video, remote_video = collect_demo(
            args.model,
            args.duration_s,
            args.size,
            args.bit_rate,
            max(1, args.every_n),
            args.demo_mode,
            args.pre_record_wait_s,
            out_dir,
            run_id,
        )
        rows = parse_live_rows(log_text, args.model, run_id)
        write_csv(out_dir / "frame_metrics.csv", rows)
        metrics = []
        for key, label in [
            ("frame_bitmap_ms", "frameBitmap"),
            ("cap_ms", "cap"),
            ("pre_ms", "pre"),
            ("inf_ms", "inf"),
            ("post_ms", "post"),
            ("analyzer_ms", "analyzer"),
            ("e2e_ms", "e2e"),
            ("effective_enhanced_fps", "effectiveEnhancedFps"),
        ]:
            values = [float(row[key]) for row in rows if row.get(key) not in ("", None)]
            if values:
                metrics.append(summarize_stage(run_id, label, values))
        write_csv(out_dir / "metrics.csv", metrics)
        if not local_video.exists() or local_video.stat().st_size == 0:
            blocked_by = "screenrecord mp4 was not pulled"
        elif not rows:
            blocked_by = "no live ROI timing rows parsed for the screenrecord session"

    loop_state = write_loop_state(out_dir, run_id, args.model, rows, local_video, blocked_by)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M +0800")
    write_csv(
        out_dir / "run_log.csv",
        [
            {
                "run_id": run_id,
                "timestamp": timestamp,
                "device": "RB5 Gen2 QCS8550",
                "model": args.model,
                "duration_s": args.duration_s,
                "video_path": str(local_video),
                "parsed_frames": len(rows),
                "status": loop_state["status"],
                "boundary": loop_state["boundary"],
                "demo_mode": args.demo_mode,
                "pre_record_wait_s": args.pre_record_wait_s,
            }
        ],
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
            "model_name": model_name(args.model),
            "model_variant": model_variant(args.model),
            "backend": "QNN TFLite Delegate / HTP",
            "input_source": "screenrecorded_camera_roi_live_demo",
            "input_size": "128x128",
            "output_size": "512x512",
            "preprocess_ms": stage_value(metrics, "pre", "p50_ms"),
            "inference_ms": stage_value(metrics, "inf", "p50_ms"),
            "postprocess_ms": stage_value(metrics, "post", "p50_ms"),
            "e2e_ms": stage_value(metrics, "e2e", "p50_ms"),
            "steady_state_window": f"{args.duration_s}s adb screenrecord demo after {args.pre_record_wait_s}s pre-record wait; parsed frames={len(rows)}",
            "p50_e2e_ms": stage_value(metrics, "e2e", "p50_ms"),
            "p95_e2e_ms": stage_value(metrics, "e2e", "p95_ms"),
            "npu_or_dsp_note": "QNN Delegate configured for HTP backend; demo uses app logcat timings",
            "fallback_code": "none" if not blocked_by else "low_cost_video_demo_failed",
            "failure_code": "none" if not blocked_by else blocked_by,
            "human_decision": "not_reviewed",
            "notes": "Low-cost demo MP4 is adb screenrecord of the demo-mode live ROI UI, not a true VideoCapture/Recorder SR pipeline.",
        },
    )
    app_e2e_mirror = mirror_app_e2e_log(REPO_ROOT, run_id, app_e2e_path)
    write_summary(
        out_dir,
        run_id,
        args.model,
        args.duration_s,
        local_video,
        f"/sdcard/Movies/{run_id}.mp4",
        rows,
        metrics,
        loop_state,
        app_e2e_path,
        app_e2e_mirror,
    )
    print(f"[ok] wrote {out_dir}")
    if blocked_by:
        raise SystemExit(f"[blocked] {blocked_by}")


if __name__ == "__main__":
    main()
