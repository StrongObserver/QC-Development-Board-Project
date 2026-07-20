"""Run the RB5VisionLab QNN TFLite Delegate shared-memory Phase 0 probe."""

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
PACKAGE_NAME = "com.cyf.rb5visionlab"
APP_COMPONENT = "com.cyf.rb5visionlab/.MainActivity"

PROBE_RE = re.compile(r"(?:tensor )?probe result (?P<result>status=\S+ .*)")


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


def parse_probe_result(log_text: str) -> dict[str, object]:
    for line in log_text.splitlines():
        match = PROBE_RE.search(line)
        if not match:
            continue
        result_text = match.group("result")
        row: dict[str, object] = {
            "raw_log_prefix": line[:18],
            "raw_result": result_text,
        }
        for item in result_text.split():
            if "=" not in item:
                continue
            key, value = item.split("=", 1)
            row[key] = value
        return row
    return {}


def make_loop_state(run_id: str, out_dir: Path, row: dict[str, object], phase: str) -> dict[str, object]:
    passed = row.get("status") == "pass"
    if phase == "phase1":
        passed_status = "shared_memory_tensor_bind_validated"
        passed_stop = "qnn_delegate_custom_allocation_invoke_available"
        passed_next = "Compare C API tensor-binding timing against the Kotlin/TFLite default path, then decide whether to deepen the data-path probe."
        failed_next = "Inspect TFLite/QNN C API binding stages before attempting performance comparison."
        notes = "Phase 1 validates TFLite C API custom allocation, QNN Delegate binding, and one invoke; it is still not CameraX buffer binding."
    else:
        passed_status = "shared_memory_alloc_free_validated"
        passed_stop = "qnn_delegate_shared_memory_api_available"
        passed_next = "Design Phase 1 C++ TFLite Interpreter probe using SetCustomAllocationForTensor."
        failed_next = "Inspect libQnnTFLiteDelegate packaging/symbols before attempting C++ interpreter probe."
        notes = "Phase 0 only validates dlopen/dlsym and alloc/free for QNN Delegate shared-memory API; it is not tensor binding or true zero-copy."
    return {
        "schema_version": 1,
        "run_id": run_id,
        "output_dir": str(out_dir),
        "phase": phase,
        "status": passed_status if passed else "environment_blocked",
        "stop_reason": passed_stop if passed else "qnn_delegate_shared_memory_probe_failed",
        "next_priority_task": passed_next if passed else failed_next,
        "probe_result": row,
        "requires_human_review": False,
        "notes": notes if passed else f"{phase} did not validate shared-memory behavior in the app process.",
    }


def collect_probe_log(timeout_s: int, phase: str, repeats: int) -> str:
    adb("shell", "am", "force-stop", PACKAGE_NAME, check=False)
    adb("logcat", "-c")
    started = adb(
        "shell",
        "am",
        "start",
        "-n",
        APP_COMPONENT,
        "--ez",
        "run_qnn_shared_tensor_probe" if phase == "phase1" else "run_qnn_shared_memory_probe",
        "true",
        "--ei",
        "shared_tensor_repeats",
        str(repeats),
        check=False,
    )
    if started.returncode != 0:
        raise RuntimeError(started.stdout)
    deadline = time.time() + timeout_s
    final_log = ""
    while time.time() < deadline:
        time.sleep(1)
        dump = adb(
            "logcat",
            "-d",
            "-v",
            "time",
            "RB5_QNN_SHARED:D",
            "RB5_NATIVE:D",
            "AndroidRuntime:E",
            "*:S",
            check=False,
        )
        final_log = dump.stdout
        if "probe result status=" in final_log or "probe failed" in final_log:
            break
    adb("shell", "am", "force-stop", PACKAGE_NAME, check=False)
    return final_log


def write_summary(out_dir: Path, run_id: str, row: dict[str, object], loop_state: dict[str, object], phase: str) -> None:
    lines = [
        f"# QNN Shared-Memory {phase.upper()} Probe",
        "",
        f"- run_id: `{run_id}`",
        "- scope: dlopen/dlsym + alloc/free for QNN TFLite Delegate shared-memory C API"
        if phase == "phase0"
        else "- scope: TFLite C API interpreter + custom allocation + QNN Delegate invoke",
        f"- status: `{loop_state['status']}`",
        f"- next_priority_task: `{loop_state['next_priority_task']}`",
        "",
        "## Result",
        "",
        "| field | value |",
        "| --- | --- |",
    ]
    keys = [
        "status",
        "stage",
        "inputBytes",
        "outputBytes",
        "inputPtr",
        "outputPtr",
        "inputAligned",
        "outputAligned",
        "alignment",
        "inputAlloc",
        "outputAlloc",
        "allocate",
        "delegate",
        "invoke",
        "inputBound",
        "outputBound",
        "inputTensorBytes",
        "outputTensorBytes",
        "checksum",
        "sampledMin",
        "sampledMax",
        "repeats",
        "completedRuns",
        "delegateUs",
        "invokeAvgUs",
        "invokeMinUs",
        "invokeMaxUs",
    ]
    for key in keys:
        if key not in row:
            continue
        lines.append(f"| `{key}` | `{row.get(key, '')}` |")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "This is not CameraX buffer binding and not true zero-copy.",
            "Phase 0 only proves shared-memory API access and alloc/free. Phase 1 additionally proves tensor custom allocation and one TFLite/QNN invoke.",
            "",
            "## Outputs",
            "",
            f"- raw logcat: `{out_dir / 'raw_logcat.txt'}`",
            f"- probe metrics: `{out_dir / 'metrics.csv'}`",
            f"- loop state: `{out_dir / 'loop_state.json'}`",
        ]
    )
    (out_dir / "SUMMARY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=["phase0", "phase1"], default="phase0")
    parser.add_argument("--repeats", type=int, default=20)
    parser.add_argument("--run-id", default="")
    parser.add_argument("--timeout-s", type=int, default=20)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_id = args.run_id or datetime.now().strftime(f"%Y%m%d_%H%M%S_qnn_shared_memory_{args.phase}")
    out_dir = RESULTS_ROOT / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    devices = run(["adb", "devices"], check=False).stdout
    expected = f"{DEVICE_SERIAL}\tdevice"
    if expected not in devices:
        raise SystemExit(f"[blocked] {expected} not found")

    log_text = collect_probe_log(args.timeout_s, args.phase, max(1, args.repeats))
    row = parse_probe_result(log_text)
    loop_state = make_loop_state(run_id, out_dir, row, args.phase)
    (out_dir / "raw_logcat.txt").write_text(log_text, encoding="utf-8")
    write_csv(out_dir / "metrics.csv", [row] if row else [])
    write_csv(
        out_dir / "run_log.csv",
        [
            {
                "run_id": run_id,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M +0800"),
                "status": loop_state["status"],
                "stop_reason": loop_state["stop_reason"],
                "next_priority_task": loop_state["next_priority_task"],
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
    write_summary(out_dir, run_id, row, loop_state, args.phase)
    print(f"[ok] wrote {out_dir}")


if __name__ == "__main__":
    main()
