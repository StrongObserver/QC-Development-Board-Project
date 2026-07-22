"""Sample RB5 battery current/voltage for coarse power evidence.

Requires rooted adb access to /sys/class/power_supply/battery/current_now.
This script reports electrical power from current_now * voltage_now because
power_now is 0 on the current RB5 debug board.
"""

from __future__ import annotations

import argparse
import csv
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RESULTS_ROOT = REPO_ROOT / "RB5_SR_lab" / "results" / "power_probe"
DEVICE_SERIAL = "ff5d3ab4"
PACKAGE_NAME = "com.cyf.rb5visionlab"
APP_COMPONENT = "com.cyf.rb5visionlab/.MainActivity"
BATTERY = "/sys/class/power_supply/battery"


def run(cmd: list[str], *, check: bool = True, timeout: int | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, check=check, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)


def adb(*args: str, check: bool = True, timeout: int | None = None) -> subprocess.CompletedProcess[str]:
    return run(["adb", "-s", DEVICE_SERIAL, *args], check=check, timeout=timeout)


def adb_text(*args: str, default: str = "", timeout: int = 5) -> str:
    try:
        return adb(*args, check=False, timeout=timeout).stdout.strip()
    except Exception:
        return default


def read_int(path: str) -> int | None:
    text = adb_text("shell", "cat", path)
    try:
        return int(text)
    except ValueError:
        return None


def snapshot(elapsed_s: float, label: str) -> dict[str, object]:
    current_ua = read_int(f"{BATTERY}/current_now")
    voltage_uv = read_int(f"{BATTERY}/voltage_now")
    temp_decic = read_int(f"{BATTERY}/temp")
    capacity = read_int(f"{BATTERY}/capacity")
    status = adb_text("shell", "cat", f"{BATTERY}/status")
    # Many Android kernels use negative current for discharge.
    power_mw = ""
    if current_ua is not None and voltage_uv is not None:
        power_mw = abs(current_ua * voltage_uv) / 1_000_000_000.0
    return {
        "elapsed_s": f"{elapsed_s:.3f}",
        "label": label,
        "current_ua": current_ua if current_ua is not None else "",
        "voltage_uv": voltage_uv if voltage_uv is not None else "",
        "power_mw_abs": f"{power_mw:.3f}" if power_mw != "" else "",
        "temp_c": f"{temp_decic / 10.0:.1f}" if temp_decic is not None else "",
        "capacity_pct": capacity if capacity is not None else "",
        "status": status,
    }


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


def tile_model_for_scenario(scenario: str) -> str:
    if scenario == "tile_quicksr_once":
        return "QUICKSR"
    if scenario == "tile_realesrgan_once":
        return "REALESRGAN"
    raise ValueError(f"scenario is not a tile scenario: {scenario}")


def start_scenario(scenario: str) -> None:
    adb("shell", "am", "force-stop", PACKAGE_NAME, check=False)
    if scenario == "idle":
        return
    if scenario == "camera_preview":
        adb("shell", "am", "start", "-n", APP_COMPONENT)
        return
    if scenario == "live_quicksr":
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
            "QUICKSR_W8A8",
        )
        return
    if scenario == "live_direct_yuv":
        adb(
            "shell",
            "am",
            "start",
            "-n",
            APP_COMPONENT,
            "--ez",
            "start_live_sr_direct_yuv",
            "true",
        )
        return
    if scenario in {"tile_quicksr_once", "tile_realesrgan_once"}:
        adb(
            "shell",
            "am",
            "start",
            "-n",
            APP_COMPONENT,
            "--ez",
            "run_tile_still",
            "true",
            "--es",
            "tile_model",
            tile_model_for_scenario(scenario),
        )
        return
    raise ValueError(f"unsupported scenario: {scenario}")


def latest_tile_files(model_label: str) -> set[str]:
    out = adb_text("shell", "ls", "-1", "/sdcard/Pictures/RB5VisionLab", timeout=10)
    return {
        line.strip()
        for line in out.splitlines()
        if re.match(rf"TILE_STILL_.*_{model_label}_QNN_.*\.png$", line.strip())
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--scenario",
        choices=[
            "idle",
            "camera_preview",
            "live_quicksr",
            "live_direct_yuv",
            "tile_quicksr_once",
            "tile_realesrgan_once",
            "suite_core",
        ],
        required=True,
    )
    parser.add_argument("--duration-s", type=float, default=30.0)
    parser.add_argument("--live-duration-s", type=float, default=60.0)
    parser.add_argument("--baseline-duration-s", type=float, default=30.0)
    parser.add_argument("--interval-s", type=float, default=1.0)
    parser.add_argument("--timeout-s", type=float, default=180.0)
    parser.add_argument("--run-id", default="")
    return parser.parse_args()


def run_one(args: argparse.Namespace, scenario: str, run_id: str, duration_s: float, out_parent: Path = RESULTS_ROOT) -> Path:
    out_dir = RESULTS_ROOT / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    if out_parent != RESULTS_ROOT:
        out_dir = out_parent / run_id
        out_dir.mkdir(parents=True, exist_ok=True)
    tile_model = tile_model_for_scenario(scenario) if scenario in {"tile_quicksr_once", "tile_realesrgan_once"} else ""
    before_tile_files = latest_tile_files(tile_model) if tile_model else set()
    new_tile_files: set[str] = set()
    start_scenario(scenario)
    rows: list[dict[str, object]] = []
    start = time.perf_counter()
    while True:
        elapsed = time.perf_counter() - start
        if tile_model:
            after_tile_files = latest_tile_files(tile_model)
            new_tile_files = after_tile_files - before_tile_files
            if any(name.endswith("_tile_sr_2048.png") for name in new_tile_files):
                break
            if elapsed > args.timeout_s:
                break
        elif elapsed > duration_s:
            break
        rows.append(snapshot(elapsed, scenario))
        time.sleep(args.interval_s)
    rows.append(snapshot(time.perf_counter() - start, scenario))
    if scenario != "idle":
        adb("shell", "am", "force-stop", PACKAGE_NAME, check=False)
    write_csv(out_dir / "power_samples.csv", rows)
    powers = [float(row["power_mw_abs"]) for row in rows if row.get("power_mw_abs") not in ("", None)]
    actual_elapsed_s = float(rows[-1]["elapsed_s"]) if rows else 0.0
    # Trapezoid-style coarse integration over sampled board power.
    energy_mj = ""
    if len(rows) >= 2:
        energy = 0.0
        previous_t = float(rows[0]["elapsed_s"])
        previous_p = float(rows[0]["power_mw_abs"]) if rows[0].get("power_mw_abs") not in ("", None) else 0.0
        for row in rows[1:]:
            current_t = float(row["elapsed_s"])
            current_p = float(row["power_mw_abs"]) if row.get("power_mw_abs") not in ("", None) else previous_p
            energy += ((previous_p + current_p) / 2.0) * (current_t - previous_t)
            previous_t = current_t
            previous_p = current_p
        energy_mj = energy
    summary = {
        "run_id": run_id,
        "scenario": scenario,
        "requested_duration_s": duration_s,
        "actual_elapsed_s": f"{actual_elapsed_s:.3f}",
        "samples": len(rows),
        "mean_power_mw_abs": f"{sum(powers) / len(powers):.3f}" if powers else "",
        "min_power_mw_abs": f"{min(powers):.3f}" if powers else "",
        "max_power_mw_abs": f"{max(powers):.3f}" if powers else "",
        "energy_mj_abs": f"{energy_mj:.3f}" if energy_mj != "" else "",
        "tile_output_detected": str(bool(new_tile_files)) if tile_model else "",
        "new_tile_files": ";".join(sorted(new_tile_files)) if tile_model else "",
        "boundary": "battery current_now based board-level estimate; not an external power meter",
    }
    write_csv(out_dir / "summary.csv", [summary])
    print(f"[ok] wrote {out_dir}")
    return out_dir


def read_summary(path: Path) -> dict[str, str]:
    with (path / "summary.csv").open("r", encoding="utf-8", newline="") as f:
        return next(csv.DictReader(f))


def main() -> None:
    args = parse_args()
    root_id = adb_text("shell", "id")
    if "uid=0(root)" not in root_id:
        raise SystemExit("[blocked] adb shell is not root. Run `adb root` first.")
    if args.scenario == "suite_core":
        suite_id = args.run_id or datetime.now().strftime("20260720_power_suite_core_%H%M%S")
        suite_dir = RESULTS_ROOT / suite_id
        suite_dir.mkdir(parents=True, exist_ok=True)
        scenarios = [
            ("idle", args.baseline_duration_s),
            ("camera_preview", args.baseline_duration_s),
            ("live_quicksr", args.live_duration_s),
            ("live_direct_yuv", args.live_duration_s),
            ("tile_quicksr_once", args.duration_s),
            ("tile_realesrgan_once", args.duration_s),
        ]
        summary_rows = []
        for scenario, duration in scenarios:
            run_dir = run_one(args, scenario, scenario, duration, suite_dir)
            row = read_summary(run_dir)
            row["run_dir"] = str(run_dir)
            summary_rows.append(row)
        write_csv(suite_dir / "suite_summary.csv", summary_rows)
        print(f"[ok] wrote {suite_dir / 'suite_summary.csv'}")
        return

    run_id = args.run_id or datetime.now().strftime(f"%Y%m%d_%H%M%S_power_{args.scenario}")
    run_one(args, args.scenario, run_id, args.duration_s)


if __name__ == "__main__":
    main()
