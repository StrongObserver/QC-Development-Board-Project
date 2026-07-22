"""Run the Android app direct-ByteBuffer YUV ROI probe.

This probe compares the existing ByteArray JNI path against a new direct
ImageProxy PlaneProxy ByteBuffer JNI path. It is a data-path experiment only:
it does not change the default live SR route and it is not QNN input zero-copy.
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


REPO_ROOT = Path(__file__).resolve().parents[1]
RESULTS_ROOT = REPO_ROOT / "RB5_SR_lab" / "results" / "direct_yuv_roi_probe"
DEVICE_SERIAL = "ff5d3ab4"
APP_COMPONENT = "com.cyf.rb5visionlab/.MainActivity"
PACKAGE_NAME = "com.cyf.rb5visionlab"
APK_PATH = REPO_ROOT / "RB5VisionLab" / "app" / "build" / "outputs" / "apk" / "debug" / "app-debug.apk"

PROBE_RE = re.compile(
    r"probe frame=(?P<frame_width>\d+)x(?P<frame_height>\d+) "
    r"rotation=(?P<rotation>\d+) "
    r"arrayMs=(?P<array_ms>\d+) directMs=(?P<direct_ms>\d+) "
    r"mad=(?P<mad>[\d.]+) "
    r"yDirect=(?P<y_direct>\w+) uDirect=(?P<u_direct>\w+) vDirect=(?P<v_direct>\w+) "
    r"yRow=(?P<y_row>\d+) uRow=(?P<u_row>\d+) vRow=(?P<v_row>\d+) "
    r"uPixel=(?P<u_pixel>\d+) vPixel=(?P<v_pixel>\d+) "
    r"saved=(?P<saved>.*)"
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
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
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
            if key == "saved":
                row["saved_paths"] = "|".join(item.strip() for item in value.split(",") if item.strip())
            elif key == "mad":
                row[key] = float(value)
            elif key.endswith("_direct"):
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
        "--es",
        "probe_mode",
        "direct_yuv_roi",
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
            "RB5_DIRECT_YUV:D",
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


def pull_saved_outputs(rows: list[dict[str, object]], out_dir: Path) -> list[dict[str, object]]:
    pulled: list[dict[str, object]] = []
    image_dir = out_dir / "images"
    image_dir.mkdir(parents=True, exist_ok=True)
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


def write_summary(out_dir: Path, run_id: str, rows: list[dict[str, object]], pulled: list[dict[str, object]]) -> None:
    row = rows[0] if rows else {}
    status = "passed" if rows and float(row["mad"]) <= 0.5 else "needs_review"
    lines = [
        "# Direct YUV ROI Probe",
        "",
        f"- run_id: `{run_id}`",
        f"- status: `{status}`",
        "- task: CameraX PlaneProxy direct ByteBuffer -> native ROI/RGB experiment",
        "- boundary: direct plane read only; not QNN input zero-copy and not default live path evidence",
        "",
        "## Result",
        "",
    ]
    if rows:
        delta = int(row["array_ms"]) - int(row["direct_ms"])
        lines.extend(
            [
                f"- frame: {row['frame_width']}x{row['frame_height']}, rotation {row['rotation']}",
                f"- array JNI path: {row['array_ms']} ms",
                f"- direct ByteBuffer JNI path: {row['direct_ms']} ms",
                f"- array-minus-direct delta: {delta} ms",
                f"- direct-vs-array MAD: {row['mad']}",
                f"- direct flags Y/U/V: {row['y_direct']} / {row['u_direct']} / {row['v_direct']}",
                f"- strides Y/U/V: {row['y_row']} / {row['u_row']} / {row['v_row']}",
            ]
        )
    else:
        lines.append("- no `RB5_DIRECT_YUV` probe row was parsed from logcat")
    lines.extend(
        [
            "",
            "## Outputs",
            "",
            f"- metrics: `{out_dir / 'metrics.csv'}`",
            f"- pulled images: `{out_dir / 'images'}`",
            f"- pulled image count: {len(pulled)}",
            f"- raw logcat: `{out_dir / 'raw_logcat.txt'}`",
            f"- loop state: `{out_dir / 'loop_state.json'}`",
        ]
    )
    (out_dir / "SUMMARY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", default="")
    parser.add_argument("--timeout-s", type=int, default=60)
    parser.add_argument("--install-apk", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_id = args.run_id or datetime.now().strftime("direct_yuv_roi_probe_%Y%m%d_%H%M%S")
    out_dir = RESULTS_ROOT / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    devices = run(["adb", "devices"], check=False).stdout
    expected = f"{DEVICE_SERIAL}\tdevice"
    if expected not in devices:
        raise SystemExit(f"[blocked] {expected} not found")

    install_stdout = ""
    if args.install_apk:
        if not APK_PATH.exists():
            raise SystemExit(f"[blocked] APK missing: {APK_PATH}")
        install_stdout = adb("install", "-r", str(APK_PATH), check=False, timeout=120).stdout
        (out_dir / "install_stdout.txt").write_text(install_stdout, encoding="utf-8")
        if "Success" not in install_stdout:
            raise SystemExit(f"[blocked] adb install failed: {install_stdout}")

    log_text, rows = collect_probe(args.timeout_s)
    (out_dir / "raw_logcat.txt").write_text(log_text, encoding="utf-8")
    write_csv(out_dir / "metrics.csv", rows)
    pulled = pull_saved_outputs(rows, out_dir)
    write_csv(out_dir / "pulled_images.csv", pulled)

    row = rows[0] if rows else {}
    passed = bool(rows) and float(row["mad"]) <= 0.5
    loop_state = {
        "schema_version": 1,
        "run_id": run_id,
        "output_dir": str(out_dir),
        "status": "direct_yuv_roi_passed" if passed else "needs_human_review_or_fix",
        "stop_reason": "direct_yuv_roi_probe_collected" if rows else "no_direct_yuv_roi_probe_row",
        "next_priority_task": "If direct path saves time without MAD regression, decide whether to wire it into an isolated live benchmark.",
        "requires_human_review": bool(rows),
        "blocked_by": "" if rows else "no RB5_DIRECT_YUV row parsed",
        "pulled_images": len(pulled),
        "boundary": "Direct ImageProxy PlaneProxy ByteBuffer read into native ROI/RGB; not QNN input zero-copy.",
    }
    if rows:
        loop_state["array_ms"] = row["array_ms"]
        loop_state["direct_ms"] = row["direct_ms"]
        loop_state["delta_array_minus_direct_ms"] = int(row["array_ms"]) - int(row["direct_ms"])
        loop_state["mad"] = row["mad"]
        loop_state["direct_flags"] = f"{row['y_direct']}/{row['u_direct']}/{row['v_direct']}"
    (out_dir / "loop_state.json").write_text(json.dumps(loop_state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_csv(
        out_dir / "run_log.csv",
        [
            {
                "run_id": run_id,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M +0800"),
                "status": loop_state["status"],
                "install_apk": args.install_apk,
                "install_stdout": install_stdout.strip().replace("\n", " | "),
                "output_dir": str(out_dir),
            }
        ],
    )
    write_summary(out_dir, run_id, rows, pulled)
    print(f"[ok] wrote {out_dir}")
    if not rows:
        raise SystemExit("[blocked] no direct yuv roi probe row parsed")


if __name__ == "__main__":
    main()
