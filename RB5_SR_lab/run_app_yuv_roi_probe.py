"""Run the Android app YUV ROI correctness probe and archive its outputs."""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RESULTS_ROOT = Path(r"C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results")
DEVICE_SERIAL = "ff5d3ab4"
APP_COMPONENT = "com.cyf.rb5visionlab/.MainActivity"
PACKAGE_NAME = "com.cyf.rb5visionlab"

YUV_ROI_RE = re.compile(
    r"probe frame=(?P<frame_width>\d+)x(?P<frame_height>\d+) rotation=(?P<rotation>\d+) "
    r"bitmapMs=(?P<bitmap_ms>\d+) bitmapCropMs=(?P<bitmap_crop_ms>\d+) "
    r"yuvRoiMs=(?P<yuv_roi_ms>\d+) nativeRoiMs=(?P<native_roi_ms>\d+) "
    r"yuvMad=(?P<yuv_mad>[\d.]+) nativeMad=(?P<native_mad>[\d.]+) "
    r"yRow=(?P<y_row_stride>\d+) uRow=(?P<u_row_stride>\d+) vRow=(?P<v_row_stride>\d+) "
    r"uPixel=(?P<u_pixel_stride>\d+) vPixel=(?P<v_pixel_stride>\d+) saved=(?P<saved>.*)"
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
        match = YUV_ROI_RE.search(line)
        if not match:
            continue
        values = match.groupdict()
        saved_paths = [item.strip() for item in values["saved"].split(",") if item.strip()]
        rows.append(
            {
                "index": len(rows) + 1,
                "frame_width": int(values["frame_width"]),
                "frame_height": int(values["frame_height"]),
                "rotation": int(values["rotation"]),
                "bitmap_ms": int(values["bitmap_ms"]),
                "bitmap_crop_ms": int(values["bitmap_crop_ms"]),
                "yuv_roi_ms": int(values["yuv_roi_ms"]),
                "native_roi_ms": int(values["native_roi_ms"]),
                "yuv_mad": float(values["yuv_mad"]),
                "native_mad": float(values["native_mad"]),
                "y_row_stride": int(values["y_row_stride"]),
                "u_row_stride": int(values["u_row_stride"]),
                "v_row_stride": int(values["v_row_stride"]),
                "u_pixel_stride": int(values["u_pixel_stride"]),
                "v_pixel_stride": int(values["v_pixel_stride"]),
                "saved_paths": "|".join(saved_paths),
                "raw_log_prefix": line[:18],
            }
        )
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
        "run_yuv_roi_probe",
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
            "RB5_YUV_ROI:D",
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
    status = "passed" if rows and float(row["native_mad"]) <= 6.0 else "needs_review"
    lines = [
        "# App YUV ROI Probe Summary",
        "",
        f"- run_id: `{run_id}`",
        "- task: P0-2 native ROI correctness recheck",
        f"- status: `{status}`",
        "- boundary: correctness and timing probe only; not live tensor zero-copy evidence",
        "",
        "## Result",
        "",
    ]
    if rows:
        lines.extend(
            [
                f"- frame: {row['frame_width']}x{row['frame_height']}, rotation {row['rotation']}",
                f"- bitmap path: toBitmap {row['bitmap_ms']} ms + crop/rotate {row['bitmap_crop_ms']} ms",
                f"- Kotlin YUV ROI: {row['yuv_roi_ms']} ms, MAD vs bitmap {row['yuv_mad']}",
                f"- native YUV ROI: {row['native_roi_ms']} ms, MAD vs bitmap {row['native_mad']}",
                f"- strides: Y {row['y_row_stride']}, U {row['u_row_stride']}/{row['u_pixel_stride']}, V {row['v_row_stride']}/{row['v_pixel_stride']}",
            ]
        )
    else:
        lines.append("- no `RB5_YUV_ROI` probe row was parsed from logcat")
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
            "",
            "## Next",
            "",
            "If native MAD is visually acceptable, proceed to a targeted native tensor-path experiment. If not, fix color/crop/rotation before any performance work.",
        ]
    )
    (out_dir / "SUMMARY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", default="")
    parser.add_argument("--timeout-s", type=int, default=30)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_id = args.run_id or datetime.now().strftime("app_yuv_roi_probe_%Y%m%d_%H%M%S")
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

    blocked_by = "" if rows else "no RB5_YUV_ROI probe row parsed"
    native_mad = float(rows[0]["native_mad"]) if rows else None
    status = "native_yuv_roi_validated" if rows and native_mad is not None and native_mad <= 6.0 else "needs_human_review_or_fix"
    loop_state = {
        "schema_version": 1,
        "run_id": run_id,
        "output_dir": str(out_dir),
        "status": status,
        "stop_reason": "native_yuv_roi_probe_collected" if rows else "yuv_roi_probe_missing",
        "next_priority_task": "Proceed to native tensor-path probe if visual side-by-side is acceptable.",
        "requires_human_review": bool(rows),
        "blocked_by": blocked_by,
        "native_mad": native_mad,
        "pulled_images": len(pulled_rows),
        "boundary": "YUV ROI correctness/timing probe; not true zero-copy and not live e2e evidence",
    }
    (out_dir / "loop_state.json").write_text(json.dumps(loop_state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_csv(
        out_dir / "run_log.csv",
        [
            {
                "run_id": run_id,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M +0800"),
                "status": status,
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
