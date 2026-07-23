"""Collect a short Perfetto trace for the RB5 default live ROI path."""

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
TENSOR_FRAME_RE = re.compile(r"RB5_SR_TENSOR.*tensorLive .* e2e=(?P<e2e_ms>\d+)ms")


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


def prepare_device_interactive() -> None:
    adb("shell", "input", "keyevent", "KEYCODE_WAKEUP", check=False)
    adb("shell", "wm", "dismiss-keyguard", check=False)
    adb("shell", "cmd", "statusbar", "collapse", check=False)
    time.sleep(0.3)


def wait_for_live_frame(timeout_s: int = 15) -> tuple[bool, str]:
    deadline = time.time() + timeout_s
    last_log = ""
    while time.time() < deadline:
        time.sleep(1)
        last_log = adb(
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
        ).stdout
        if TENSOR_FRAME_RE.search(last_log):
            return True, last_log
    return False, last_log


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration-s", type=int, default=15)
    parser.add_argument("--run-id", default="")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_id = args.run_id or datetime.now().strftime("20260723_perfetto_direct_yuv_%H%M%S")
    out_dir = RESULTS_ROOT / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    device_trace = f"/data/misc/perfetto-traces/{run_id}.perfetto-trace"
    host_trace = out_dir / f"{run_id}.perfetto-trace"

    devices = run(["adb", "devices"], check=False).stdout
    if f"{DEVICE_SERIAL}\tdevice" not in devices:
        raise SystemExit(f"[blocked] {DEVICE_SERIAL} not connected")

    prepare_device_interactive()
    adb("shell", "rm", "-f", device_trace, check=False)
    adb("shell", "am", "force-stop", PACKAGE_NAME, check=False)
    adb("logcat", "-c", check=False)
    adb(
        "shell",
        "am",
        "start",
        "-n",
        APP_COMPONENT,
        "--ez",
        "start_live_sr_direct_yuv",
        "true",
        check=False,
    )
    live_ready, pre_trace_log = wait_for_live_frame()
    (out_dir / "pre_trace_logcat.txt").write_text(pre_trace_log, encoding="utf-8")
    if not live_ready:
        adb("shell", "am", "force-stop", PACKAGE_NAME, check=False)
        loop_state = {
            "schema_version": 1,
            "run_id": run_id,
            "status": "environment_blocked",
            "duration_s": args.duration_s,
            "trace": str(host_trace),
            "trace_bytes": 0,
            "notes": "Live SR frames did not appear before trace start; check camera/app state before rerunning.",
        }
        (out_dir / "loop_state.json").write_text(json.dumps(loop_state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        raise SystemExit(f"[blocked] no RB5_SR_TENSOR frame before trace; wrote {out_dir}")

    perfetto_cmd = [
        "adb",
        "-s",
        DEVICE_SERIAL,
        "shell",
        "perfetto",
        "-t",
        f"{args.duration_s}s",
        "-b",
        "64mb",
        "-o",
        device_trace,
        "sched",
        "freq",
        "idle",
        "view",
        "gfx",
        "camera",
        "dalvik",
        "am",
        "wm",
        "-a",
        PACKAGE_NAME,
    ]
    proc = subprocess.Popen(perfetto_cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    stdout = proc.communicate(timeout=args.duration_s + 30)[0]
    (out_dir / "perfetto_stdout.txt").write_text(stdout or "", encoding="utf-8")
    adb("shell", "am", "force-stop", PACKAGE_NAME, check=False)
    trace_pull = subprocess.run(
        ["adb", "-s", DEVICE_SERIAL, "exec-out", "cat", device_trace],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    host_trace.write_bytes(trace_pull.stdout or b"")
    if trace_pull.stderr:
        (out_dir / "perfetto_pull_stderr.txt").write_bytes(trace_pull.stderr)
    logcat = adb(
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
    ).stdout
    (out_dir / "raw_logcat.txt").write_text(logcat, encoding="utf-8")
    trace_exists = host_trace.exists() and host_trace.stat().st_size > 0
    loop_state = {
        "schema_version": 1,
        "run_id": run_id,
        "status": "perfetto_trace_collected" if trace_exists else "environment_blocked",
        "duration_s": args.duration_s,
        "trace": str(host_trace),
        "trace_bytes": host_trace.stat().st_size if host_trace.exists() else 0,
        "notes": "Trace contains app atrace markers plus sched/freq/view/gfx/camera categories; use Perfetto UI for visual timeline inspection.",
    }
    (out_dir / "loop_state.json").write_text(json.dumps(loop_state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_csv(
        out_dir / "trace_manifest.csv",
        [
            {
                "run_id": run_id,
                "duration_s": args.duration_s,
                "trace": str(host_trace),
                "trace_bytes": loop_state["trace_bytes"],
                "raw_logcat": str(out_dir / "raw_logcat.txt"),
                "boundary": "Perfetto timeline evidence; not a latency summary by itself.",
            }
        ],
    )
    summary = [
        "# App Perfetto Trace Summary",
        "",
        f"- run_id: `{run_id}`",
        f"- duration_s: `{args.duration_s}`",
        f"- trace: `{host_trace}`",
        f"- trace_bytes: `{loop_state['trace_bytes']}`",
        "",
        "## Boundary",
        "",
        "This is timeline evidence for app/runtime path inspection. Use it with logcat/app_e2e timing; do not treat the trace file alone as a benchmark result.",
    ]
    (out_dir / "SUMMARY.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
    print(f"[ok] wrote {out_dir}")


if __name__ == "__main__":
    main()
