"""Run and parse the RB5VisionLab QNN model resource probe."""

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

MEM_RE = re.compile(
    r"mem label=(?P<label>\S+) totalPssKb=(?P<totalPssKb>\d+) "
    r"dalvikPssKb=(?P<dalvikPssKb>\d+) nativePssKb=(?P<nativePssKb>\d+) "
    r"otherPssKb=(?P<otherPssKb>\d+) runtimeUsedKb=(?P<runtimeUsedKb>\d+) "
    r"runtimeFreeKb=(?P<runtimeFreeKb>\d+) runtimeMaxKb=(?P<runtimeMaxKb>\d+)"
)
INIT_RE = re.compile(r"init model=(?P<model>\S+) backend=(?P<backend>\S+) asset=(?P<asset>\S+) init=(?P<init_ms>\d+)")
ENHANCE_RE = re.compile(
    r"enhance phase=(?P<phase>\S+) run=(?P<run>\d+) pre=(?P<pre_ms>\d+) "
    r"inf=(?P<inf_ms>\d+) post=(?P<post_ms>\d+) total=(?P<total_ms>\d+)"
)
CLOSE_RE = re.compile(r"close label=(?P<label>\S+) close=(?P<close_ms>\d+)")
SWITCH_RE = re.compile(
    r"switch from=(?P<from_model>\S+) to=(?P<to_model>\S+) close=(?P<close_ms>\d+) "
    r"init=(?P<init_ms>\d+) first_total=(?P<first_total_ms>\d+) total=(?P<total_ms>\d+)"
)
ASSET_RE = re.compile(r"asset asset=(?P<asset>\S+) load=(?P<load_ms>\d+) bitmap=(?P<bitmap>\S+)")


def run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, check=check, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


def adb(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return run(["adb", "-s", DEVICE_SERIAL, *args], check=check)


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


def parse_log(log_text: str) -> tuple[
    list[dict[str, object]],
    list[dict[str, object]],
    list[dict[str, object]],
    list[dict[str, object]],
    list[dict[str, object]],
    list[dict[str, object]],
]:
    memory_rows: list[dict[str, object]] = []
    init_rows: list[dict[str, object]] = []
    enhance_rows: list[dict[str, object]] = []
    close_rows: list[dict[str, object]] = []
    switch_rows: list[dict[str, object]] = []
    asset_rows: list[dict[str, object]] = []
    for line in log_text.splitlines():
        if "RB5_RESOURCE" not in line:
            continue
        if match := MEM_RE.search(line):
            row: dict[str, object] = {"raw_log_prefix": line[:18], **match.groupdict()}
            for key in row:
                if key not in {"label", "raw_log_prefix"}:
                    row[key] = int(row[key])
            memory_rows.append(row)
        elif match := INIT_RE.search(line):
            row = {"raw_log_prefix": line[:18], **match.groupdict()}
            row["init_ms"] = int(row["init_ms"])
            init_rows.append(row)
        elif match := ENHANCE_RE.search(line):
            row = {"raw_log_prefix": line[:18], **match.groupdict()}
            for key in ["run", "pre_ms", "inf_ms", "post_ms", "total_ms"]:
                row[key] = int(row[key])
            enhance_rows.append(row)
        elif match := CLOSE_RE.search(line):
            row = {"raw_log_prefix": line[:18], **match.groupdict()}
            row["close_ms"] = int(row["close_ms"])
            close_rows.append(row)
        elif match := SWITCH_RE.search(line):
            row = {"raw_log_prefix": line[:18], **match.groupdict()}
            for key in ["close_ms", "init_ms", "first_total_ms", "total_ms"]:
                row[key] = int(row[key])
            switch_rows.append(row)
        elif match := ASSET_RE.search(line):
            row = {"raw_log_prefix": line[:18], **match.groupdict()}
            row["load_ms"] = int(row["load_ms"])
            asset_rows.append(row)
    return memory_rows, init_rows, enhance_rows, close_rows, switch_rows, asset_rows


def summarize_enhance(run_id: str, rows: list[dict[str, object]]) -> list[dict[str, object]]:
    phases = sorted({str(row["phase"]) for row in rows})
    summary_rows: list[dict[str, object]] = []
    for phase in phases:
        phase_rows = [row for row in rows if row["phase"] == phase]
        totals = [float(row["total_ms"]) for row in phase_rows]
        infs = [float(row["inf_ms"]) for row in phase_rows]
        posts = [float(row["post_ms"]) for row in phase_rows]
        summary_rows.append(
            {
                "run_id": run_id,
                "phase": phase,
                "count": len(phase_rows),
                "total_p50_ms": f"{percentile(totals, 0.50):.1f}",
                "total_p95_ms": f"{percentile(totals, 0.95):.1f}",
                "inf_p50_ms": f"{percentile(infs, 0.50):.1f}",
                "inf_p95_ms": f"{percentile(infs, 0.95):.1f}",
                "post_p50_ms": f"{percentile(posts, 0.50):.1f}",
                "post_p95_ms": f"{percentile(posts, 0.95):.1f}",
            }
        )
    return summary_rows


def pss_delta(memory_rows: list[dict[str, object]], a: str, b: str) -> int | None:
    by_label = {str(row["label"]): row for row in memory_rows}
    if a not in by_label or b not in by_label:
        return None
    return int(by_label[b]["totalPssKb"]) - int(by_label[a]["totalPssKb"])


def run_probe(out_dir: Path, steady_runs: int, timeout_s: int) -> str:
    adb("logcat", "-c")
    adb("shell", "am", "force-stop", PACKAGE_NAME, check=False)
    log_path = out_dir / "raw_logcat.txt"
    with log_path.open("w", encoding="utf-8") as log_file:
        proc = subprocess.Popen(
            [
                "adb",
                "-s",
                DEVICE_SERIAL,
                "logcat",
                "-v",
                "time",
                "RB5_RESOURCE:D",
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
                "run_resource_probe",
                "true",
                "--ei",
                "resource_probe_runs",
                str(steady_runs),
            )
            deadline = time.time() + timeout_s
            while time.time() < deadline:
                time.sleep(1)
                log_file.flush()
                current = log_path.read_text(encoding="utf-8", errors="replace")
                if "probe done status=pass" in current or "probe failed" in current:
                    break
        finally:
            adb("shell", "am", "force-stop", PACKAGE_NAME, check=False)
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
    return log_path.read_text(encoding="utf-8", errors="replace")


def make_loop_state(
    run_id: str,
    out_dir: Path,
    memory_rows: list[dict[str, object]],
    init_rows: list[dict[str, object]],
    enhance_rows: list[dict[str, object]],
    switch_rows: list[dict[str, object]],
    log_text: str,
) -> dict[str, object]:
    required_memory = {"start", "after_real_init", "after_both_init", "end"}
    memory_labels = {str(row["label"]) for row in memory_rows}
    passed = (
        "probe done status=pass" in log_text
        and required_memory.issubset(memory_labels)
        and any(row.get("model") == "W8A8" for row in init_rows)
        and any(row.get("model") == "QUICKSR_W8A8" for row in init_rows)
        and bool(enhance_rows)
        and bool(switch_rows)
    )
    return {
        "schema_version": 1,
        "run_id": run_id,
        "output_dir": str(out_dir),
        "status": "ready_for_route_update" if passed else "environment_blocked",
        "stop_reason": "resource_cost_measured" if passed else "resource_probe_incomplete",
        "next_priority_task": "P8 update route decision using live ROI and resource-cost evidence"
        if passed
        else "rerun P6 resource probe after fixing app/logcat collection",
        "required_memory_labels": sorted(required_memory),
        "observed_memory_labels": sorted(memory_labels),
        "init_rows": len(init_rows),
        "enhance_rows": len(enhance_rows),
        "switch_rows": len(switch_rows),
        "requires_human_review": False,
        "notes": "P6 resource data is sufficient for strategy decision; still not power or thermal evidence."
        if passed
        else "The app did not emit a complete RB5_RESOURCE probe log.",
    }


def write_summary(
    out_dir: Path,
    run_id: str,
    memory_rows: list[dict[str, object]],
    init_rows: list[dict[str, object]],
    enhance_summary: list[dict[str, object]],
    switch_rows: list[dict[str, object]],
    loop_state: dict[str, object],
) -> None:
    lines = [
        "# App QNN Resource Probe Summary",
        "",
        f"- run_id: `{run_id}`",
        "- device: RB5 Gen2 / QCS8550 / Android 13",
        "- scope: model init, fixed-sample first/steady inference, dual residency memory, and switch cost",
        "- boundary: app-side short-run resource probe; not a power or thermal run",
        f"- loop_status: `{loop_state['status']}`",
        f"- next_priority_task: `{loop_state['next_priority_task']}`",
        "",
        "## Init Cost",
        "",
        "| model | init ms | note |",
        "| --- | ---: | --- |",
    ]
    for row in init_rows:
        lines.append(f"| `{row['model']}` | {row['init_ms']} | asset `{row['asset']}` |")
    lines.extend(["", "## Memory PSS", "", "| label | total PSS KB | native PSS KB | runtime used KB |", "| --- | ---: | ---: | ---: |"])
    for row in memory_rows:
        lines.append(f"| `{row['label']}` | {row['totalPssKb']} | {row['nativePssKb']} | {row['runtimeUsedKb']} |")
    deltas = [
        ("single Real-ESRGAN load", pss_delta(memory_rows, "after_asset_load", "after_real_init")),
        ("add QuickSRNet while Real-ESRGAN resident", pss_delta(memory_rows, "after_real_runs", "after_both_init")),
        ("both models vs start", pss_delta(memory_rows, "start", "after_both_init")),
        ("after close both vs start", pss_delta(memory_rows, "start", "after_close_both")),
    ]
    lines.extend(["", "## Memory Deltas", "", "| comparison | delta KB |", "| --- | ---: |"])
    for label, delta in deltas:
        lines.append(f"| {label} | {delta if delta is not None else 'n/a'} |")
    lines.extend(["", "## Enhance Timing", "", "| phase | count | total p50/p95 ms | inference p50/p95 ms | post p50/p95 ms |", "| --- | ---: | ---: | ---: | ---: |"])
    for row in enhance_summary:
        lines.append(
            f"| `{row['phase']}` | {row['count']} | {row['total_p50_ms']} / {row['total_p95_ms']} | "
            f"{row['inf_p50_ms']} / {row['inf_p95_ms']} | {row['post_p50_ms']} / {row['post_p95_ms']} |"
        )
    lines.extend(["", "## Switch Cost", "", "| from | to | close ms | init ms | first total ms | switch total ms |", "| --- | --- | ---: | ---: | ---: | ---: |"])
    for row in switch_rows:
        lines.append(
            f"| `{row['from_model']}` | `{row['to_model']}` | {row['close_ms']} | {row['init_ms']} | "
            f"{row['first_total_ms']} | {row['total_ms']} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "The resource cost is now measured enough to block automatic live routing from being treated as free.",
            "Dynamic switching has a visible cold path because it includes closing one QNN interpreter, creating the next QNN delegate/interpreter, and running the first frame.",
            "Keeping both models resident is technically possible in this short probe, but it has a measurable PSS cost and still needs power/thermal evidence before product-style claims.",
            "",
            "## Outputs",
            "",
            f"- raw logcat: `{out_dir / 'raw_logcat.txt'}`",
            f"- memory: `{out_dir / 'memory_metrics.csv'}`",
            f"- init: `{out_dir / 'init_metrics.csv'}`",
            f"- enhance: `{out_dir / 'enhance_metrics.csv'}`",
            f"- enhance summary: `{out_dir / 'metrics.csv'}`",
            f"- switch: `{out_dir / 'switch_metrics.csv'}`",
            f"- loop state: `{out_dir / 'loop_state.json'}`",
        ]
    )
    (out_dir / "SUMMARY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", default="")
    parser.add_argument("--steady-runs", type=int, default=5)
    parser.add_argument("--timeout-s", type=int, default=90)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_id = args.run_id or datetime.now().strftime("%Y%m%d_%H%M%S_app_qnn_resource_probe")
    out_dir = RESULTS_ROOT / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    devices = run(["adb", "devices"], check=False).stdout
    expected = f"{DEVICE_SERIAL}\tdevice"
    if expected not in devices:
        raise SystemExit(f"[blocked] {expected} not found")

    log_text = run_probe(out_dir, args.steady_runs, args.timeout_s)
    memory_rows, init_rows, enhance_rows, close_rows, switch_rows, asset_rows = parse_log(log_text)
    enhance_summary = summarize_enhance(run_id, enhance_rows) if enhance_rows else []
    loop_state = make_loop_state(run_id, out_dir, memory_rows, init_rows, enhance_rows, switch_rows, log_text)

    write_csv(out_dir / "memory_metrics.csv", memory_rows)
    write_csv(out_dir / "init_metrics.csv", init_rows)
    write_csv(out_dir / "enhance_metrics.csv", enhance_rows)
    write_csv(out_dir / "metrics.csv", enhance_summary)
    write_csv(out_dir / "close_metrics.csv", close_rows)
    write_csv(out_dir / "switch_metrics.csv", switch_rows)
    write_csv(out_dir / "asset_metrics.csv", asset_rows)
    write_csv(
        out_dir / "run_log.csv",
        [
            {
                "run_id": run_id,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M +0800"),
                "device": "RB5 Gen2 QCS8550",
                "backend": "QNN",
                "steady_runs": args.steady_runs,
                "status": loop_state["status"],
                "stop_reason": loop_state["stop_reason"],
                "next_priority_task": loop_state["next_priority_task"],
                "output_dir": str(out_dir),
            }
        ],
    )
    (out_dir / "loop_state.json").write_text(json.dumps(loop_state, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    (out_dir / "NEXT_ACTION.md").write_text(
        "\n".join(
            [
                "# Next Action",
                "",
                "## Current Conclusion",
                "",
                f"P6 resource probe status: `{loop_state['status']}`.",
                "",
                "## Next Priority",
                "",
                str(loop_state["next_priority_task"]),
                "",
                "## Boundary",
                "",
                "Do not enable automatic live model routing until route decision is updated from this evidence and sustained power/thermal limits are considered.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    write_summary(out_dir, run_id, memory_rows, init_rows, enhance_summary, switch_rows, loop_state)
    print(f"[ok] wrote {out_dir}")


if __name__ == "__main__":
    main()
