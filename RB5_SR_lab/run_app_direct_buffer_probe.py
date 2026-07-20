"""Run the Android app ImageProxy direct-buffer feasibility probe."""

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
    r"yDirect=(?P<y_direct>\w+) uDirect=(?P<u_direct>\w+) vDirect=(?P<v_direct>\w+) "
    r"yRemaining=(?P<y_remaining>\d+) uRemaining=(?P<u_remaining>\d+) vRemaining=(?P<v_remaining>\d+) "
    r"yRow=(?P<y_row>\d+) uRow=(?P<u_row>\d+) vRow=(?P<v_row>\d+) "
    r"uPixel=(?P<u_pixel>\d+) vPixel=(?P<v_pixel>\d+) native=(?P<native>.*)"
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
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def parse_rows(log_text: str) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for line in log_text.splitlines():
        match = PROBE_RE.search(line)
        if not match:
            continue
        values = match.groupdict()
        row: dict[str, object] = {"index": len(rows) + 1, "raw_log_prefix": line[:18]}
        for key, value in values.items():
            if key.endswith("_direct"):
                row[key] = value
            elif key == "native":
                row[key] = value
            else:
                row[key] = int(value)
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
        "run_direct_buffer_probe",
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
            "RB5_DIRECT_BUFFER:D",
            "RB5_SR:D",
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
    run_id = args.run_id or datetime.now().strftime("app_direct_buffer_probe_%Y%m%d_%H%M%S")
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
    native = str(row.get("native", ""))
    non_null = "DirectAddress=non_null" in native
    loop_state = {
        "schema_version": 1,
        "run_id": run_id,
        "output_dir": str(out_dir),
        "status": "direct_buffer_probe_collected" if rows else "environment_blocked",
        "stop_reason": "direct_buffer_probe_collected" if rows else "no_direct_buffer_probe_row",
        "next_priority_task": "Use this result to decide whether JNI direct plane reads are worth a C++ ROI path experiment.",
        "requires_human_review": False,
        "has_native_direct_address": non_null,
        "blocked_by": "" if rows else "no RB5_DIRECT_BUFFER row parsed",
        "boundary": "This checks ImageProxy plane ByteBuffer direct-address feasibility only; it does not bind CameraX buffers to QNN Delegate input tensors.",
    }
    (out_dir / "loop_state.json").write_text(json.dumps(loop_state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = [
        "# App Direct Buffer Probe",
        "",
        f"- run_id: `{run_id}`",
        f"- status: `{loop_state['status']}`",
        f"- has_native_direct_address: `{non_null}`",
        "- boundary: direct ByteBuffer feasibility only, not QNN zero-copy",
        "",
        "## Result",
        "",
    ]
    if rows:
        summary.extend(
            [
                f"- frame: {row['frame_width']}x{row['frame_height']}",
                f"- direct flags Y/U/V: {row['y_direct']} / {row['u_direct']} / {row['v_direct']}",
                f"- remaining Y/U/V: {row['y_remaining']} / {row['u_remaining']} / {row['v_remaining']}",
                f"- strides Y/U/V: {row['y_row']} / {row['u_row']} / {row['v_row']}",
                f"- native: `{native}`",
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
        ]
    )
    (out_dir / "SUMMARY.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
    print(f"[ok] wrote {out_dir}")
    if not rows:
        raise SystemExit("[blocked] no direct buffer probe row parsed")


if __name__ == "__main__":
    main()
