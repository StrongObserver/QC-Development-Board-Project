"""Run the Android app tensor-ready single-frame probe and archive outputs."""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path


RESULTS_ROOT = Path(r"C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results")
DEVICE_SERIAL = "ff5d3ab4"
APP_COMPONENT = "com.cyf.rb5visionlab/.MainActivity"
PACKAGE_NAME = "com.cyf.rb5visionlab"

TENSOR_PROBE_RE = re.compile(
    r"probe frame=(?P<frame_width>\d+)x(?P<frame_height>\d+) rotation=(?P<rotation>\d+) "
    r"bitmapMs=(?P<bitmap_ms>\d+) bitmapCropMs=(?P<bitmap_crop_ms>\d+) "
    r"nativeRgbMs=(?P<native_rgb_ms>\d+) rotatedNativeRgbMs=(?P<rotated_native_rgb_ms>\d+) "
    r"bitmapPre=(?P<bitmap_pre_ms>\d+) bitmapInf=(?P<bitmap_inf_ms>\d+) bitmapPost=(?P<bitmap_post_ms>\d+) "
    r"bitmapEnhanceWall=(?P<bitmap_enhance_wall_ms>\d+) bitmapPath=(?P<bitmap_path_ms>\d+) "
    r"rgbPre=(?P<rgb_pre_ms>\d+) rgbInf=(?P<rgb_inf_ms>\d+) rgbPost=(?P<rgb_post_ms>\d+) "
    r"rgbEnhanceWall=(?P<rgb_enhance_wall_ms>\d+) rgbPath=(?P<rgb_path_ms>\d+) "
    r"rotatedNativePre=(?P<rotated_native_pre_ms>\d+) rotatedNativeInf=(?P<rotated_native_inf_ms>\d+) "
    r"rotatedNativePost=(?P<rotated_native_post_ms>\d+) "
    r"rotatedNativeEnhanceWall=(?P<rotated_native_enhance_wall_ms>\d+) "
    r"rotatedNativePath=(?P<rotated_native_path_ms>\d+) "
    r"inputMad=(?P<input_mad>[\d.]+) outputMad=(?P<output_mad>[\d.]+) "
    r"rotatedNativeInputMad=(?P<rotated_native_input_mad>[\d.]+) "
    r"rotatedNativeOutputMad=(?P<rotated_native_output_mad>[\d.]+) saved=(?P<saved>.*)"
)


def run(cmd: list[str], *, check: bool = True, timeout: int | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, check=check, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)


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


def parse_probe_rows(log_text: str) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for line in log_text.splitlines():
        match = TENSOR_PROBE_RE.search(line)
        if not match:
            continue
        values = match.groupdict()
        row: dict[str, object] = {"index": len(rows) + 1, "raw_log_prefix": line[:18]}
        for key, value in values.items():
            if key == "saved":
                saved_paths = [item.strip() for item in value.split(",") if item.strip()]
                row["saved_paths"] = "|".join(saved_paths)
            elif key.endswith("_mad"):
                row[key] = float(value)
            else:
                row[key] = int(value)
        rows.append(row)
    return rows


def collect_probe(timeout_s: int) -> tuple[str, list[dict[str, object]]]:
    adb("shell", "am", "force-stop", PACKAGE_NAME, check=False)
    time.sleep(0.5)
    adb("logcat", "-c", check=False)
    started = adb(
        "shell",
        "am",
        "start",
        "-n",
        APP_COMPONENT,
        "--ez",
        "run_tensor_ready_probe",
        "true",
        check=False,
    )
    if started.returncode != 0:
        raise RuntimeError(started.stdout)

    deadline = time.time() + timeout_s
    final_log = ""
    rows: list[dict[str, object]] = []
    while time.time() < deadline:
        time.sleep(1)
        final_log = adb(
            "logcat",
            "-d",
            "-v",
            "time",
            "RB5_TENSOR_READY:D",
            "RB5_SR:D",
            "AndroidRuntime:E",
            "*:S",
            check=False,
        ).stdout
        rows = parse_probe_rows(final_log)
        if rows:
            break
    adb("shell", "am", "force-stop", PACKAGE_NAME, check=False)
    return final_log, rows


def pull_saved_outputs(rows: list[dict[str, object]], out_dir: Path) -> list[dict[str, object]]:
    pulled: list[dict[str, object]] = []
    image_dir = out_dir / "images"
    image_dir.mkdir(exist_ok=True)
    for row in rows:
        for remote_path in str(row.get("saved_paths", "")).split("|"):
            if not remote_path:
                continue
            local_path = image_dir / Path(remote_path).name
            adb("pull", remote_path, str(local_path), check=False, timeout=60)
            if local_path.exists() and local_path.stat().st_size > 0:
                pulled.append(
                    {
                        "remote_path": remote_path,
                        "local_path": str(local_path),
                        "file_name": local_path.name,
                        "bytes": local_path.stat().st_size,
                    }
                )
    return pulled


def write_summary(out_dir: Path, run_id: str, rows: list[dict[str, object]], pulled_rows: list[dict[str, object]]) -> None:
    row = rows[0] if rows else {}
    passed = bool(rows) and float(row["rotated_native_input_mad"]) <= 1.0 and float(row["rotated_native_output_mad"]) <= 1.0
    lines = [
        "# App Tensor-Ready Probe Summary",
        "",
        f"- run_id: `{run_id}`",
        "- task: P0-3 tensor native-rotation correctness probe",
        f"- status: `{'passed' if passed else 'needs_review'}`",
        "- boundary: single-frame correctness/timing probe; not default live path evidence by itself",
        "",
        "## Result",
        "",
    ]
    if rows:
        lines.extend(
            [
                f"- frame: {row['frame_width']}x{row['frame_height']}, rotation {row['rotation']}",
                f"- bitmap path: {row['bitmap_path_ms']} ms",
                f"- old RGB-bytes path: {row['rgb_path_ms']} ms, input/output MAD {row['input_mad']} / {row['output_mad']}",
                f"- native-rotated RGB-bytes path: {row['rotated_native_path_ms']} ms, input/output MAD {row['rotated_native_input_mad']} / {row['rotated_native_output_mad']}",
            ]
        )
    else:
        lines.append("- no `RB5_TENSOR_READY` probe row was parsed from logcat")
    lines.extend(
        [
            "",
            "## Outputs",
            "",
            f"- metrics: `{out_dir / 'metrics.csv'}`",
            f"- pulled images: `{out_dir / 'images'}`",
            f"- pulled image count: {len(pulled_rows)}",
            f"- raw logcat: `{out_dir / 'raw_logcat.txt'}`",
            f"- loop state: `{out_dir / 'loop_state.json'}`",
        ]
    )
    (out_dir / "SUMMARY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", default="")
    parser.add_argument("--timeout-s", type=int, default=60)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_id = args.run_id or datetime.now().strftime("app_tensor_ready_probe_%Y%m%d_%H%M%S")
    out_dir = RESULTS_ROOT / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    devices = run(["adb", "devices"], check=False).stdout
    expected = f"{DEVICE_SERIAL}\tdevice"
    if expected not in devices:
        raise SystemExit(f"[blocked] {expected} not found")

    log_text, rows = collect_probe(args.timeout_s)
    (out_dir / "raw_logcat.txt").write_text(log_text, encoding="utf-8")
    write_csv(out_dir / "metrics.csv", rows)
    pulled_rows = pull_saved_outputs(rows, out_dir)
    write_csv(out_dir / "pulled_images.csv", pulled_rows)

    row = rows[0] if rows else {}
    passed = bool(rows) and float(row["rotated_native_input_mad"]) <= 1.0 and float(row["rotated_native_output_mad"]) <= 1.0
    blocked_by = "" if rows else "no RB5_TENSOR_READY probe row parsed"
    loop_state = {
        "schema_version": 1,
        "run_id": run_id,
        "output_dir": str(out_dir),
        "status": "tensor_rotated_native_correctness_passed" if passed else "needs_human_review_or_fix",
        "stop_reason": "tensor_probe_collected" if rows else "tensor_probe_missing",
        "next_priority_task": "Compare live ROI p50/p95 against default and decide whether native-rotated tensor path should remain a probe.",
        "requires_human_review": bool(rows),
        "blocked_by": blocked_by,
        "pulled_images": len(pulled_rows),
        "boundary": "single-frame tensor input/output correctness; not true zero-copy",
    }
    if rows:
        loop_state["rotated_native_input_mad"] = row["rotated_native_input_mad"]
        loop_state["rotated_native_output_mad"] = row["rotated_native_output_mad"]
        loop_state["rotated_native_path_ms"] = row["rotated_native_path_ms"]
        loop_state["bitmap_path_ms"] = row["bitmap_path_ms"]
    (out_dir / "loop_state.json").write_text(json.dumps(loop_state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_csv(
        out_dir / "run_log.csv",
        [
            {
                "run_id": run_id,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M +0800"),
                "status": loop_state["status"],
                "blocked_by": blocked_by,
                "pulled_images": len(pulled_rows),
                "output_dir": str(out_dir),
            }
        ],
    )
    write_summary(out_dir, run_id, rows, pulled_rows)
    print(f"[ok] wrote {out_dir}")


if __name__ == "__main__":
    main()
