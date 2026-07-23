"""Run the Android app ImageProxy HardwareBuffer / AHardwareBuffer probe."""

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

PROBE_RE = re.compile(
    r"probe frame=(?P<frame_width>\d+)x(?P<frame_height>\d+) "
    r"format=(?P<image_format>\d+) native=(?P<native>status=\S+ .*)"
)


def run(cmd: list[str], *, check: bool = True, timeout: int | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, check=check, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)


def adb(*args: str, check: bool = True, timeout: int | None = None) -> subprocess.CompletedProcess[str]:
    return run(["adb", "-s", DEVICE_SERIAL, *args], check=check, timeout=timeout)


def prepare_device_interactive() -> None:
    adb("shell", "input", "keyevent", "KEYCODE_WAKEUP", check=False)
    adb("shell", "wm", "dismiss-keyguard", check=False)
    adb("shell", "cmd", "statusbar", "collapse", check=False)
    time.sleep(0.3)


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


def parse_native_fields(native: str) -> dict[str, object]:
    row: dict[str, object] = {}
    for item in native.split():
        if "=" not in item:
            continue
        key, value = item.split("=", 1)
        if value.lstrip("-").isdigit():
            row[key] = int(value)
        else:
            row[key] = value
    return row


def parse_rows(log_text: str) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for line in log_text.splitlines():
        match = PROBE_RE.search(line)
        if not match:
            continue
        values = match.groupdict()
        row: dict[str, object] = {
            "index": len(rows) + 1,
            "raw_log_prefix": line[:18],
            "frame_width": int(values["frame_width"]),
            "frame_height": int(values["frame_height"]),
            "image_format": int(values["image_format"]),
            "native": values["native"],
        }
        row.update(parse_native_fields(values["native"]))
        rows.append(row)
    return rows


def collect_probe(timeout_s: int) -> tuple[str, list[dict[str, object]]]:
    prepare_device_interactive()
    adb("shell", "am", "force-stop", PACKAGE_NAME, check=False)
    time.sleep(0.5)
    adb("logcat", "-c", check=False)
    prepare_device_interactive()
    started = adb(
        "shell",
        "am",
        "start",
        "-n",
        APP_COMPONENT,
        "--ez",
        "run_hardware_buffer_probe",
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
            "RB5_HARDWARE_BUFFER:D",
            "RB5_SR:D",
            "RB5_NATIVE:D",
            "AndroidRuntime:E",
            "*:S",
            check=False,
        ).stdout
        rows = parse_rows(final_log)
        if rows:
            break
    adb("shell", "am", "force-stop", PACKAGE_NAME, check=False)
    return final_log, rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", default="")
    parser.add_argument("--timeout-s", type=int, default=45)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_id = args.run_id or datetime.now().strftime("app_hardware_buffer_probe_%Y%m%d_%H%M%S")
    out_dir = RESULTS_ROOT / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    devices = run(["adb", "devices"], check=False).stdout
    expected = f"{DEVICE_SERIAL}\tdevice"
    if expected not in devices:
        raise SystemExit(f"[blocked] {expected} not found")
    log_text, rows = collect_probe(args.timeout_s)
    (out_dir / "raw_logcat.txt").write_text(log_text, encoding="utf-8")
    write_csv(out_dir / "metrics.csv", rows)
    row = rows[0] if rows else {}
    status = str(row.get("status", ""))
    lock_planes = row.get("lockPlanes", "")
    plane_count = row.get("planeCount", "")
    loop_state = {
        "schema_version": 1,
        "run_id": run_id,
        "output_dir": str(out_dir),
        "status": "hardware_buffer_probe_collected" if rows else "environment_blocked",
        "stop_reason": "hardware_buffer_probe_collected" if rows else "no_hardware_buffer_probe_row",
        "next_priority_task": "Use this result to decide whether Stage D can proceed toward AHardwareBuffer/QNN memory registration.",
        "requires_human_review": False,
        "native_status": status,
        "lock_planes": lock_planes,
        "plane_count": plane_count,
        "blocked_by": "" if rows else "no RB5_HARDWARE_BUFFER row parsed",
        "boundary": "This checks ImageProxy.image.hardwareBuffer and AHardwareBuffer lockPlanes availability only; it does not register the buffer with QNN.",
    }
    (out_dir / "loop_state.json").write_text(json.dumps(loop_state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = [
        "# App HardwareBuffer Probe",
        "",
        f"- run_id: `{run_id}`",
        f"- status: `{loop_state['status']}`",
        "- boundary: HardwareBuffer/AHardwareBuffer reachability only, not QNN zero-copy",
        "",
        "## Result",
        "",
    ]
    if rows:
        summary.extend(
            [
                f"- frame: {row.get('frame_width')}x{row.get('frame_height')}",
                f"- image_format: {row.get('image_format')}",
                f"- native_status: `{status}`",
                f"- desc: {row.get('descWidth')}x{row.get('descHeight')} format={row.get('descFormat')} usage={row.get('descUsage')} stride={row.get('descStride')}",
                f"- lockPlanes: `{lock_planes}`",
                f"- planeCount: `{plane_count}`",
                f"- plane0: rowStride={row.get('plane0RowStride')} pixelStride={row.get('plane0PixelStride')} data={row.get('plane0Data')}",
            ]
        )
    else:
        summary.append("- no probe row parsed")
    summary.extend(
        [
            "",
            "## Outputs",
            "",
            f"- metrics: `{out_dir / 'metrics.csv'}`",
            f"- raw logcat: `{out_dir / 'raw_logcat.txt'}`",
            f"- loop state: `{out_dir / 'loop_state.json'}`",
        ]
    )
    (out_dir / "SUMMARY.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
    print(f"[ok] wrote {out_dir}")
    if not rows:
        raise SystemExit("[blocked] no hardware buffer probe row parsed")


if __name__ == "__main__":
    main()
