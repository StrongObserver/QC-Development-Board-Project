"""Run RB5_SR_Benchmark_v1 cases with local RB5 QNN context binary.

This script stages QAIRT qnn-net-run under /data/local/tmp/qnn_sr, runs the
selected cases from RB5_SR_Benchmark_v1, converts QNN raw outputs to PNG, and
creates metrics plus contact sheets for quick human review.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import shutil
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

from loop_policy import environment_blocked_payload, make_loop_state_payload


REPO_ROOT = Path(__file__).resolve().parents[1]
BENCHMARK_ROOT = Path(r"C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1")
QAIRT_ROOT = Path(r"C:\Qualcomm\QAIRT\v2.45.0.260326\qairt\2.45.0.260326")
QNN_LOCAL_RUN = REPO_ROOT / "RB5_SR_lab" / "qnn_local_run"
DEVICE_SERIAL = "ff5d3ab4"
DEVICE_DIR = "/data/local/tmp/qnn_sr"
DEFAULT_CONTEXT_BINARY = (
    REPO_ROOT
    / "RB5_SR_lab"
    / "export_assets"
    / "real_esrgan_general_x4v3-qnn-w8a8-qcs8550-20260715"
    / "real_esrgan_general_x4v3-qnn_context_binary-w8a8-qualcomm_qcs8550_proxy"
    / "real_esrgan_general_x4v3.bin"
)

DEFAULT_OUTPUT_SCALE = 0.005237185396254063
DEFAULT_OUTPUT_ZERO_POINT = 25


@dataclass(frozen=True)
class BenchmarkCase:
    case_id: str
    category: str
    dataset: str
    source_id: str
    lr_128: Path
    bicubic_512: Path
    hr_512: Path
    selection_note: str


def run(cmd: list[str], *, cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, check=check, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


def adb(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return run(["adb", "-s", DEVICE_SERIAL, *args], check=check)


def require_file(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(path)


def load_cases(input_set: str) -> list[BenchmarkCase]:
    manifest: dict[str, dict[str, str]] = {}
    with (BENCHMARK_ROOT / "manifest.csv").open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            manifest[row["case_id"]] = row

    cases: list[BenchmarkCase] = []
    if input_set == "smoke":
        with (BENCHMARK_ROOT / "qa" / "smoke_subset.csv").open("r", encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                m = manifest[row["case_id"]]
                cases.append(
                    BenchmarkCase(
                        case_id=row["case_id"],
                        category=row["category"],
                        dataset=row["dataset"],
                        source_id=row["source_id"],
                        lr_128=Path(m["lr_128"]),
                        bicubic_512=Path(m["bicubic_512"]),
                        hr_512=Path(m["hr_512"]),
                        selection_note=row["why_in_smoke"],
                    )
                )
        return cases

    if input_set == "full":
        for row in manifest.values():
            cases.append(
                BenchmarkCase(
                    case_id=row["case_id"],
                    category=row["category"],
                    dataset=row["dataset"],
                    source_id=row["source_id"],
                    lr_128=Path(row["lr_128"]),
                    bicubic_512=Path(row["bicubic_512"]),
                    hr_512=Path(row["hr_512"]),
                    selection_note=row.get("selection_reason", ""),
                )
            )
        return cases

    raise ValueError(f"unsupported input_set: {input_set}")


def image_to_raw_rgb(path: Path, raw_path: Path) -> None:
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        raise FileNotFoundError(path)
    if image.shape[:2] != (128, 128):
        raise ValueError(f"expected 128x128 image, got {image.shape[:2]}: {path}")
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    raw_path.write_bytes(rgb.tobytes())


def qnn_raw_to_bgr(raw_path: Path, output_scale: float, output_zero_point: int) -> np.ndarray:
    raw = np.fromfile(raw_path, dtype=np.uint8)
    expected = 1 * 512 * 512 * 3
    if raw.size != expected:
        raise ValueError(f"expected {expected} bytes, got {raw.size}: {raw_path}")
    y = raw.reshape(1, 512, 512, 3)[0]
    rgb_f32 = np.clip((y.astype(np.float32) - output_zero_point) * output_scale, 0.0, 1.0)
    rgb_u8 = (rgb_f32 * 255.0 + 0.5).astype(np.uint8)
    return cv2.cvtColor(rgb_u8, cv2.COLOR_RGB2BGR)


def image_stddev(image: np.ndarray) -> float:
    return float(np.std(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)))


def psnr(reference: np.ndarray, candidate: np.ndarray) -> float:
    mse = np.mean((reference.astype(np.float64) - candidate.astype(np.float64)) ** 2)
    return 99.0 if mse == 0 else float(10.0 * np.log10((255.0 * 255.0) / mse))


def ssim(reference: np.ndarray, candidate: np.ndarray) -> float:
    ref = cv2.cvtColor(reference, cv2.COLOR_BGR2GRAY).astype(np.float64)
    cand = cv2.cvtColor(candidate, cv2.COLOR_BGR2GRAY).astype(np.float64)
    c1 = (0.01 * 255) ** 2
    c2 = (0.03 * 255) ** 2
    mu_ref = cv2.GaussianBlur(ref, (11, 11), 1.5)
    mu_cand = cv2.GaussianBlur(cand, (11, 11), 1.5)
    sigma_ref = cv2.GaussianBlur(ref * ref, (11, 11), 1.5) - mu_ref * mu_ref
    sigma_cand = cv2.GaussianBlur(cand * cand, (11, 11), 1.5) - mu_cand * mu_cand
    sigma_ref_cand = cv2.GaussianBlur(ref * cand, (11, 11), 1.5) - mu_ref * mu_cand
    numerator = (2 * mu_ref * mu_cand + c1) * (2 * sigma_ref_cand + c2)
    denominator = (mu_ref * mu_ref + mu_cand * mu_cand + c1) * (sigma_ref + sigma_cand + c2)
    return float(np.mean(numerator / np.maximum(denominator, 1e-12)))


def sharpness(image: np.ndarray) -> float:
    return float(cv2.Laplacian(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY), cv2.CV_64F).var())


def percentile(values: list[float], q: float) -> float:
    if not values:
        return float("nan")
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    pos = (len(ordered) - 1) * q
    lower = int(pos)
    upper = min(lower + 1, len(ordered) - 1)
    weight = pos - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def summarize_values(values: list[float]) -> tuple[str, str, str]:
    if not values:
        return "", "", ""
    return (
        f"{float(np.mean(values)):.1f}",
        f"{percentile(values, 0.50):.1f}",
        f"{percentile(values, 0.95):.1f}",
    )


def numeric_profile_value(profile: dict[str, str], key: str) -> float:
    try:
        return float(profile.get(key, ""))
    except ValueError:
        return float("nan")


def parse_profile(profile_csv: Path) -> dict[str, str]:
    result = {
        "netrun_execute_us": "",
        "qnn_execute_us": "",
        "qnn_accelerator_execute_us": "",
        "rpc_execute_us": "",
        "accelerator_execute_us": "",
        "ips": "",
    }
    if not profile_csv.exists():
        return result
    lines = profile_csv.read_text(encoding="utf-8").splitlines()
    header_index = next((i for i, line in enumerate(lines) if line.startswith("Msg Timestamp,")), None)
    if header_index is None:
        return result
    with profile_csv.open("r", encoding="utf-8", newline="") as f:
        for _ in range(header_index):
            next(f)
        for raw_row in csv.DictReader(f):
            row = {
                key.strip(): value.strip()
                for key, value in raw_row.items()
                if isinstance(key, str) and isinstance(value, str)
            }
            event = row.get("Event Identifier", "")
            msg = row.get("Message", "")
            time_value = row.get("Time", "")
            if event == "Graph 0: real_esrgan_general_x4v3" and msg == "EXECUTE":
                result["netrun_execute_us"] = time_value
            elif event == "QNN (execute) time":
                result["qnn_execute_us"] = time_value
            elif event == "QNN accelerator (execute) time":
                result["qnn_accelerator_execute_us"] = time_value
            elif event == "RPC (execute) time":
                result["rpc_execute_us"] = time_value
            elif event == "Accelerator (execute) time":
                result["accelerator_execute_us"] = time_value
            elif msg == "EXECUTE IPS":
                result["ips"] = time_value
    return result


def panel(image: np.ndarray, title: str, width: int = 220) -> np.ndarray:
    body = cv2.resize(image, (width, width), interpolation=cv2.INTER_AREA)
    header = np.full((36, width, 3), 25, dtype=np.uint8)
    cv2.putText(header, title[:26], (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
    return np.vstack([header, body])


def write_case_sheet(path: Path, lr: np.ndarray, bicubic: np.ndarray, qnn: np.ndarray, hr: np.ndarray) -> None:
    sheet = np.hstack([
        panel(lr, "LR 128"),
        panel(bicubic, "bicubic 512"),
        panel(qnn, "QNN W8A8"),
        panel(hr, "HR reference"),
    ])
    cv2.imwrite(str(path), sheet)


def write_contact_sheet(rows: list[dict[str, str]], out_path: Path) -> None:
    panels: list[np.ndarray] = []
    for row in rows:
        sheet = cv2.imread(row["case_contact_sheet"], cv2.IMREAD_COLOR)
        if sheet is None:
            continue
        thumb = cv2.resize(sheet, (880, 236), interpolation=cv2.INTER_AREA)
        header = np.full((34, 880, 3), 245, dtype=np.uint8)
        netrun_us = row.get("netrun_execute_p50_us", row.get("netrun_execute_us", ""))
        decision = row.get("auto_loop_decision", "")
        text = f"{row['case_id']} | {row['category']} | {decision} | QNN p50 {netrun_us} us | PSNR {row['psnr_qnn_vs_hr']}"
        cv2.putText(header, text[:115], (8, 23), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (20, 20, 20), 1, cv2.LINE_AA)
        panels.append(np.vstack([header, thumb]))
    cv2.imwrite(str(out_path), np.vstack(panels))


def average_number(rows: list[dict[str, str]], key: str) -> float:
    values = [float(row[key]) for row in rows if row.get(key)]
    return float(np.mean(values)) if values else float("nan")


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
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


def json_safe(value):
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, dict):
        return {key: json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    return value


def git_revision(repo_root: Path) -> str:
    try:
        head = subprocess.check_output(
            ["git", "-C", str(repo_root), "rev-parse", "--short", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        status = subprocess.check_output(
            ["git", "-C", str(repo_root), "status", "--short"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        return head + ("-dirty" if status else "")
    except Exception:
        return ""


def input_csv_label(input_set: str) -> str:
    return "qa/smoke_subset.csv" if input_set == "smoke" else "manifest.csv"


def run_scope_label(input_set: str) -> str:
    return "smoke" if input_set == "smoke" else "full 24-case"


def make_run_log(
    out_root: Path,
    run_id: str,
    rows: list[dict[str, str]],
    loop_state: dict[str, object],
    input_set: str,
) -> dict[str, str]:
    netrun_key = "netrun_execute_p50_us" if int(loop_state["repeat_count"]) > 1 else "netrun_execute_us"
    accel_key = "qnn_accelerator_execute_p50_us" if int(loop_state["repeat_count"]) > 1 else "qnn_accelerator_execute_us"
    netrun_values = [float(row[netrun_key]) / 1000.0 for row in rows if row.get(netrun_key)]
    accel_values = [float(row[accel_key]) / 1000.0 for row in rows if row.get(accel_key)]
    return {
        "run_id": run_id,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M +0800"),
        "operator": "",
        "device": "RB5 Gen2 QCS8550",
        "android_version": "Android 13",
        "app_or_script_commit": git_revision(REPO_ROOT),
        "model_name": "Real-ESRGAN general x4v3",
        "model_variant": "qnn_context_binary_w8a8",
        "backend": "QNN qnn-net-run HTP",
        "quantization": "w8a8",
        "input_set": input_csv_label(input_set),
        "output_dir": str(out_root),
        "num_cases": str(len(rows)),
        "main_variable": f"local RB5 QNN W8A8 {run_scope_label(input_set)} timing and validity",
        "frozen_variables": f"Real-ESRGAN general x4v3 W8A8 QNN context; {input_csv_label(input_set)}; 128x128 RGB uint8 input; 512x512 output; qnn-net-run retrieve_context path",
        "avg_latency_ms": f"netrun={float(np.mean(netrun_values)):.2f}; qnn_accel={float(np.mean(accel_values)):.2f}" if netrun_values and accel_values else "",
        "p50_latency_ms": f"netrun={percentile(netrun_values, 0.50):.2f}; qnn_accel={percentile(accel_values, 0.50):.2f}" if netrun_values and accel_values else "",
        "p95_latency_ms": f"netrun={percentile(netrun_values, 0.95):.2f}; qnn_accel={percentile(accel_values, 0.95):.2f}" if netrun_values and accel_values else "",
        "metric_summary": "Hard gates and auto loop decisions are in metrics.csv and loop_state.json; visual review remains final for quality.",
        "pass_count": str(loop_state["auto_decision_counts"]["pass"]),
        "conditional_count": str(loop_state["auto_decision_counts"]["conditional"]),
        "fail_count": str(loop_state["auto_decision_counts"]["fail"]),
        "blocked_by": str(loop_state["blocked_by"]),
        "notes": f"status={loop_state['status']}; stop_reason={loop_state['stop_reason']}; next={loop_state['next_priority_task']}",
    }


def make_blocked_run_log(out_root: Path, run_id: str, loop_state: dict[str, object], input_set: str) -> dict[str, str]:
    return {
        "run_id": run_id,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M +0800"),
        "operator": "",
        "device": "RB5 Gen2 QCS8550",
        "android_version": "Android 13",
        "app_or_script_commit": git_revision(REPO_ROOT),
        "model_name": "Real-ESRGAN general x4v3",
        "model_variant": "qnn_context_binary_w8a8",
        "backend": "QNN qnn-net-run HTP",
        "quantization": "w8a8",
        "input_set": input_csv_label(input_set),
        "output_dir": str(out_root),
        "num_cases": "0",
        "main_variable": f"environment preflight for local RB5 QNN W8A8 {run_scope_label(input_set)}",
        "frozen_variables": f"same QNN context, QAIRT root, device serial, and {input_csv_label(input_set)} protocol",
        "avg_latency_ms": "",
        "p50_latency_ms": "",
        "p95_latency_ms": "",
        "metric_summary": "Preflight failed before benchmark execution.",
        "pass_count": "0",
        "conditional_count": "0",
        "fail_count": "0",
        "blocked_by": str(loop_state["blocked_by"]),
        "notes": f"status={loop_state['status']}; stop_reason={loop_state['stop_reason']}; next={loop_state['next_priority_task']}",
    }


def write_blocked_closeout(
    out_root: Path,
    run_id: str,
    loop_state: dict[str, object],
    preflight_stdout: str,
    input_set: str,
) -> None:
    (out_root / "preflight_stdout.txt").write_text(preflight_stdout, encoding="utf-8")
    (out_root / "loop_state.json").write_text(
        json.dumps(json_safe(loop_state), ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    write_csv(out_root / "run_log.csv", [make_blocked_run_log(out_root, run_id, loop_state, input_set)])

    summary = [
        f"# RB5 QNN W8A8 {run_scope_label(input_set).title()} Summary",
        "",
        f"- run_id: {run_id}",
        f"- input_set: {input_csv_label(input_set)}",
        "- cases: 0",
        f"- loop_status: {loop_state['status']}",
        f"- stop_reason: {loop_state['stop_reason']}",
        f"- blocked_by: {loop_state['blocked_by']}",
        f"- next_priority_task: {loop_state['next_priority_task']}",
        "",
        "## What Happened",
        "",
        "Benchmark execution did not start because preflight failed.",
        "This is an environment/tooling blocker, not a model-quality or QNN-output result.",
        "",
        "## Evidence",
        "",
        f"- preflight stdout: `{out_root / 'preflight_stdout.txt'}`",
        f"- loop state: `{out_root / 'loop_state.json'}`",
        f"- run log: `{out_root / 'run_log.csv'}`",
        "",
        "## Boundary",
        "",
        "Do not use this run for latency, quality, or QNN correctness claims.",
    ]
    (out_root / "SUMMARY.md").write_text("\n".join(summary) + "\n", encoding="utf-8")

    next_action = [
        "# Next Action",
        "",
        "## 当前结论",
        "",
        f"本轮 QNN {run_scope_label(input_set)} benchmark 没有真正开始，预检阶段失败。该问题属于环境/设备连接阻塞，不是模型质量问题，也不是 QNN runner 输出错误。",
        "",
        "## 当前阻塞",
        "",
        str(loop_state["blocked_by"]),
        "",
        "## 下一步最高优先级任务",
        "",
        f"下一步优先做：【{loop_state['next_priority_task']}】",
        "",
        "## 为什么是这个任务",
        "",
        str(loop_state["notes"]),
        "",
        "## 下轮 AI 开始前必须先读",
        "",
        "```text",
        r"C:\Users\Admin\Desktop\QC-Development-Board-Project\PROJECT_ENTRYPOINTS.md",
        str(out_root / "SUMMARY.md"),
        str(out_root / "run_log.csv"),
        str(out_root / "loop_state.json"),
        str(out_root / "preflight_stdout.txt"),
        "```",
        "",
        "## 不要做什么",
        "",
        "- 不要把这个 run 当成性能或画质证据。",
        "- 不要触发画质知识库；当前还没有模型输出。",
        "- 不要跳到 Path B app 接入；先恢复 ADB/RB5 连接。",
        "",
        "## 需要用户人工判断的点",
        "",
        "需要用户确认 RB5 是否已连接并允许 ADB 访问。Windows 侧先运行 `adb devices`，必须能看到 `ff5d3ab4 device`。",
    ]
    (out_root / "NEXT_ACTION.md").write_text("\n".join(next_action) + "\n", encoding="utf-8")


def preflight_check(context_binary: Path) -> tuple[bool, str, str]:
    messages: list[str] = []
    for path in [QAIRT_ROOT, context_binary, QNN_LOCAL_RUN / "run_on_device.sh"]:
        if not path.exists():
            messages.append(f"MISSING_PATH: {path}")
    devices = run(["adb", "devices"], check=False)
    messages.append("$ adb devices")
    messages.append(devices.stdout.strip())
    expected = f"{DEVICE_SERIAL}\tdevice"
    if expected not in devices.stdout:
        messages.append(f"DEVICE_NOT_FOUND: expected `{expected}`")
    if any(line.startswith(("MISSING_PATH:", "DEVICE_NOT_FOUND:")) for line in messages):
        return False, "ADB_OR_REQUIRED_FILE_PREFLIGHT_FAILED", "\n".join(messages) + "\n"
    return True, "", "\n".join(messages) + "\n"


def write_summary(
    out_root: Path,
    run_id: str,
    rows: list[dict[str, str]],
    by_category: Path,
    loop_state: dict[str, object],
    input_set: str,
) -> None:
    summary_lines = [
        f"# RB5 QNN W8A8 {run_scope_label(input_set).title()} Summary",
        "",
        f"- run_id: {run_id}",
        f"- input_set: {input_csv_label(input_set)}",
        f"- cases: {len(rows)}",
        f"- repeat_count: {loop_state['repeat_count']}",
        "- device: RB5 Gen2 / QCS8550 / Android 13",
        "- runtime: QAIRT qnn-net-run 2.45.0.260326154327",
        "- context: real_esrgan_general_x4v3 QNN context binary W8A8",
        "- important: ADSP_LIBRARY_PATH is intentionally unset in run_on_device.sh",
        f"- loop_status: {loop_state['status']}",
        f"- stop_reason: {loop_state['stop_reason']}",
        f"- next_priority_task: {loop_state['next_priority_task']}",
        f"- main_variable: local RB5 QNN W8A8 {run_scope_label(input_set)} timing and validity",
        f"- frozen_variables: {input_csv_label(input_set)}, QNN context binary, QAIRT runner path, input/output tensor shape, and review protocol",
        "",
        "## Outputs",
        "",
        f"- metrics: `{out_root / 'metrics.csv'}`",
        f"- run log: `{out_root / 'run_log.csv'}`",
        f"- loop state: `{out_root / 'loop_state.json'}`",
        f"- contact sheet: `{out_root / 'contact_sheet.png'}`",
        f"- human review guide: `{out_root / 'HUMAN_REVIEW_GUIDE.md'}`",
        f"- next action: `{out_root / 'NEXT_ACTION.md'}`",
        f"- by category: `{by_category}`",
        "",
        "## Quick Result Table",
        "",
        "| case | category | decision | NetRun p50 us | QNN accel p50 us | PSNR QNN-HR | PSNR delta vs bicubic |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        summary_lines.append(
            f"| {row['case_id']} | {row['category']} | {row['auto_loop_decision']} | "
            f"{row.get('netrun_execute_p50_us', row.get('netrun_execute_us', ''))} | "
            f"{row.get('qnn_accelerator_execute_p50_us', row.get('qnn_accelerator_execute_us', ''))} | "
            f"{row['psnr_qnn_vs_hr']} | "
            f"{row['psnr_delta_qnn_minus_bicubic']} |"
        )
    summary_lines.extend(
        [
            "",
            "## Loop Boundary",
            "",
            f"- current status: `{loop_state['status']}`",
            f"- stop reason: `{loop_state['stop_reason']}`",
            f"- next priority task: `{loop_state['next_priority_task']}`",
            f"- human review required: `{str(loop_state['requires_human_review']).lower()}`",
            f"- notes: {loop_state['notes']}",
            "- metric policy: hard gates validate runner/output; PSNR/SSIM/sharpness are supporting evidence; contact sheet review owns quality.",
            "",
            "## Boundary",
            "",
            f"This is local RB5 `qnn-net-run` {run_scope_label(input_set)} evidence, not Android app end-to-end timing.",
            "For performance claims, run repeated inputs and report p50/p95 separately.",
        ]
    )
    (out_root / "SUMMARY.md").write_text("\n".join(summary_lines) + "\n", encoding="utf-8")


def write_human_review_guide(
    out_root: Path,
    rows: list[dict[str, str]],
    loop_state: dict[str, object],
    input_set: str,
) -> None:
    netrun_key = "netrun_execute_p50_us" if int(loop_state["repeat_count"]) > 1 else "netrun_execute_us"
    accel_key = "qnn_accelerator_execute_p50_us" if int(loop_state["repeat_count"]) > 1 else "qnn_accelerator_execute_us"
    avg_netrun = average_number(rows, netrun_key) / 1000.0
    avg_accel = average_number(rows, accel_key) / 1000.0
    guide = [
        "# 人工 Review 指南",
        "",
        f"这次结果用于验证：本地 RB5 能否通过 `qnn-net-run` 跑通 Real-ESRGAN W8A8 QNN context binary，并在 `{input_csv_label(input_set)}` 的 {len(rows)} 个 case 上产出可看的超分结果。",
        "",
        "## Loop 状态",
        "",
        f"- 当前状态：`{loop_state['status']}`",
        f"- 停止原因：`{loop_state['stop_reason']}`",
        f"- 下一步优先任务：`{loop_state['next_priority_task']}`",
        f"- 是否需要人工看图：`{str(loop_state['requires_human_review']).lower()}`",
        f"- 说明：{loop_state['notes']}",
        "",
        "## 已经通过的点",
        "",
        f"- {len(rows)} 个 {run_scope_label(input_set)} case 都已经在本地 RB5 上通过 `qnn-net-run` 执行成功。",
        "- 每个 case 都生成了 512x512 的 QNN 输出图。",
        "- 优先查看 `contact_sheet.png`，确认是否有空图、旋转、镜像、裁剪错位。",
        "- 输出风格应与 Real-ESRGAN / W8A8 一致：通常比 bicubic 更锐，但低光自然纹理可能出现 conditional 情况。",
        "",
        "## 怎么看总览图",
        "",
        f"优先打开：`{out_root / 'contact_sheet.png'}`",
        "",
        "每一行对应一个测试 case，排列顺序是：",
        "",
        "```text",
        "LR 128 | bicubic 512 | QNN W8A8 | HR reference",
        "```",
        "",
        "行标题里包含：",
        "",
        "```text",
        "case_id | 场景类别 | QNN NetRun 执行时间 | PSNR vs HR",
        "```",
        "",
        "## 每类重点看什么",
        "",
        "| 类别 | 重点看什么 |",
        "| --- | --- |",
        "| `structure_edges` | 线条是否锐利但不过度 halo，几何是否变形 |",
        "| `repeating_patterns` | 是否出现棋盘格、假周期纹理、彩色边缘异常 |",
        "| `natural_texture` | 纹理是否自然，是否变成假细节 |",
        "| `low_light_noise` | 是否放大噪声，暗部细节是否糊成一团 |",
        "| `text_signage` | 字是否更清楚，字形是否变形 |",
        "| `people_scene` | 人脸/皮肤/人体边缘是否不自然 |",
        "",
        "## 时延边界",
        "",
        "这里的时延是本地 RB5 上 `qnn-net-run` 的时延，不是 Android app 端到端时延。",
        "",
        f"- 平均 NetRun execute: 约 {avg_netrun:.2f} ms",
        f"- 平均 QNN accelerator execute: 约 {avg_accel:.2f} ms",
        "",
        "后续如果要写正式性能结论，需要重复多次运行并统计 p50 / p95。",
        "",
        "## 当前建议",
        "",
        "如果 contact sheet 未见阻断问题，按 `loop_state.json` 里的 `next_priority_task` 继续。用户当前口播模板的最新要求优先于这里的建议。",
    ]
    (out_root / "HUMAN_REVIEW_GUIDE.md").write_text("\n".join(guide) + "\n", encoding="utf-8")


def write_next_action(
    out_root: Path,
    run_id: str,
    rows: list[dict[str, str]],
    loop_state: dict[str, object],
    input_set: str,
) -> None:
    netrun_key = "netrun_execute_p50_us" if int(loop_state["repeat_count"]) > 1 else "netrun_execute_us"
    accel_key = "qnn_accelerator_execute_p50_us" if int(loop_state["repeat_count"]) > 1 else "qnn_accelerator_execute_us"
    avg_netrun = average_number(rows, netrun_key) / 1000.0
    avg_accel = average_number(rows, accel_key) / 1000.0
    next_action = [
        "# Next Action",
        "",
        "## 当前结论",
        "",
        f"本轮 `{run_id}` 已完成本地 RB5 QNN W8A8 {run_scope_label(input_set)} benchmark。{len(rows)} 个 case 均通过 `qnn-net-run --retrieve_context` 生成 512x512 QNN 输出；本轮平均 NetRun execute 约 "
        f"{avg_netrun:.2f} ms，平均 QNN accelerator execute 约 {avg_accel:.2f} ms。",
        "",
        "## 当前阻塞",
        "",
        "无阻塞。" if not loop_state["blocked_by"] else str(loop_state["blocked_by"]),
        "",
        "## 下一步最高优先级任务",
        "",
        f"下一步优先做：【{loop_state['next_priority_task']}】",
        "",
        "## 为什么是这个任务",
        "",
        str(loop_state["notes"]),
        "",
        "## 下轮 AI 开始前必须先读",
        "",
        "```text",
        r"C:\Users\Admin\Desktop\QC-Development-Board-Project\PROJECT_ENTRYPOINTS.md",
        r"C:\Users\Admin\Nutstore\1\Typora_save\自己的项目\RB5 Gen2_AI上下文.md",
        r"C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\qa\RESULT_SOP.md",
        str(out_root / "SUMMARY.md"),
        str(out_root / "HUMAN_REVIEW_GUIDE.md"),
        str(out_root / "metrics.csv"),
        str(out_root / "run_log.csv"),
        str(out_root / "loop_state.json"),
        str(out_root / "contact_sheet.png"),
        "```",
        "",
        "## 不要做什么",
        "",
        "- 不要把生成结果写回 `cases/`。",
        "- 不要把 AI Hub hosted profile 当成本地 app 端到端。",
        "- 不要把本轮 qnn-net-run 单次时延当成稳态 p50/p95。",
        "- 不要让本文件覆盖用户当前口播模板；用户最新要求永远优先。",
        "",
        "## 需要用户人工判断的点",
        "",
        "需要用户优先查看 `contact_sheet.png`。" if loop_state["requires_human_review"] else "暂不需要用户人工判断。",
    ]
    (out_root / "NEXT_ACTION.md").write_text("\n".join(next_action) + "\n", encoding="utf-8")


def stage_common_files(context_binary: Path) -> None:
    adb("root")
    adb("shell", f"mkdir -p {DEVICE_DIR}")
    pushes = [
        (QAIRT_ROOT / "bin" / "aarch64-android" / "qnn-net-run", f"{DEVICE_DIR}/qnn-net-run"),
        (QAIRT_ROOT / "bin" / "aarch64-android" / "qnn-profile-viewer", f"{DEVICE_DIR}/qnn-profile-viewer"),
        (QAIRT_ROOT / "lib" / "aarch64-android" / "libQnnHtp.so", f"{DEVICE_DIR}/libQnnHtp.so"),
        (QAIRT_ROOT / "lib" / "aarch64-android" / "libQnnHtpNetRunExtensions.so", f"{DEVICE_DIR}/libQnnHtpNetRunExtensions.so"),
        (QAIRT_ROOT / "lib" / "aarch64-android" / "libQnnHtpV73Stub.so", f"{DEVICE_DIR}/libQnnHtpV73Stub.so"),
        (QAIRT_ROOT / "lib" / "aarch64-android" / "libQnnHtpPrepare.so", f"{DEVICE_DIR}/libQnnHtpPrepare.so"),
        (QAIRT_ROOT / "lib" / "aarch64-android" / "libQnnSystem.so", f"{DEVICE_DIR}/libQnnSystem.so"),
        (context_binary, f"{DEVICE_DIR}/real_esrgan_general_x4v3.bin"),
        (QNN_LOCAL_RUN / "HtpConfigFile.json", f"{DEVICE_DIR}/HtpConfigFile.json"),
        (QNN_LOCAL_RUN / "PerfSetting.conf", f"{DEVICE_DIR}/PerfSetting.conf"),
        (QNN_LOCAL_RUN / "run_on_device.sh", f"{DEVICE_DIR}/run_on_device.sh"),
    ]
    for local, remote in pushes:
        require_file(local)
        adb("push", str(local), remote)
    adb("shell", f"chmod 755 {DEVICE_DIR}/qnn-net-run {DEVICE_DIR}/qnn-profile-viewer {DEVICE_DIR}/run_on_device.sh")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input-set",
        choices=["smoke", "full"],
        default="smoke",
        help="Use qa/smoke_subset.csv or the full manifest.csv.",
    )
    parser.add_argument("--repeats", type=int, default=1, help="Run each selected case this many times for p50/p95 timing.")
    parser.add_argument("--run-id", default="", help="Optional result folder name.")
    parser.add_argument(
        "--context-binary",
        type=Path,
        default=DEFAULT_CONTEXT_BINARY,
        help="QNN context binary to stage as real_esrgan_general_x4v3.bin.",
    )
    parser.add_argument("--output-scale", type=float, default=DEFAULT_OUTPUT_SCALE)
    parser.add_argument("--output-zero-point", type=int, default=DEFAULT_OUTPUT_ZERO_POINT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.repeats < 1:
        raise ValueError("--repeats must be >= 1")

    run_suffix = "qnn_w8a8_smoke_rb5" if args.input_set == "smoke" else "qnn_w8a8_full_rb5"
    run_id = args.run_id or datetime.now().strftime(f"%Y%m%d_%H%M%S_{run_suffix}")
    out_root = BENCHMARK_ROOT / "results" / run_id
    by_category = out_root / "by_category"
    raw_inputs = out_root / "raw_inputs"
    out_root.mkdir(parents=True, exist_ok=True)
    raw_inputs.mkdir(parents=True, exist_ok=True)

    context_binary = args.context_binary.resolve()
    preflight_ok, blocked_by, preflight_stdout = preflight_check(context_binary)
    if not preflight_ok:
        loop_state = environment_blocked_payload(
            run_id=run_id,
            output_dir=out_root,
            repeat_count=args.repeats,
            blocked_by=blocked_by,
            notes="Preflight failed before running qnn-net-run. Fix ADB device connection or required local paths, then rerun the same command.",
            input_set=args.input_set,
        )
        write_blocked_closeout(out_root, run_id, loop_state, preflight_stdout, args.input_set)
        print(f"[blocked] wrote {out_root}")
        return

    for path in [QAIRT_ROOT, context_binary, QNN_LOCAL_RUN / "run_on_device.sh"]:
        require_file(path)

    print(f"[stage] {DEVICE_DIR}")
    stage_common_files(context_binary)

    cases = load_cases(args.input_set)
    rows: list[dict[str, str]] = []
    for index, case in enumerate(cases, start=1):
        print(f"[{index}/{len(cases)}] {case.case_id}")
        case_dir = by_category / case.category / case.case_id
        case_dir.mkdir(parents=True, exist_ok=True)
        local_raw = raw_inputs / f"{case.case_id}.raw"
        image_to_raw_rgb(case.lr_128, local_raw)
        adb("push", str(local_raw), f"{DEVICE_DIR}/input.raw")
        (raw_inputs / "input_list.txt").write_text("input.raw\n", encoding="ascii")
        adb("push", str(raw_inputs / "input_list.txt"), f"{DEVICE_DIR}/input_list.txt")

        repeat_profiles: list[dict[str, str]] = []
        repeat_wall_ms: list[float] = []
        qnn_bgr: np.ndarray | None = None
        raw_out_size = 0

        for repeat_index in range(1, args.repeats + 1):
            print(f"  repeat {repeat_index}/{args.repeats}")
            t0 = time.perf_counter()
            completed = adb("shell", f"{DEVICE_DIR}/run_on_device.sh", check=False)
            wall_ms = (time.perf_counter() - t0) * 1000.0
            repeat_wall_ms.append(wall_ms)
            stdout_path = case_dir / (
                "qnn_net_run_stdout.txt" if args.repeats == 1 else f"qnn_net_run_stdout_r{repeat_index:02d}.txt"
            )
            stdout_path.write_text(completed.stdout, encoding="utf-8")
            if completed.returncode != 0:
                raise RuntimeError(f"qnn-net-run failed for {case.case_id} repeat {repeat_index}:\n{completed.stdout}")

            current_pull_dir = case_dir / (
                "pulled_output" if args.repeats == 1 else f"pulled_output_r{repeat_index:02d}"
            )
            if current_pull_dir.exists():
                shutil.rmtree(current_pull_dir)
            current_pull_dir.mkdir(parents=True)
            adb("pull", f"{DEVICE_DIR}/output", str(current_pull_dir))
            raw_out = current_pull_dir / "output" / "Result_0" / "upscaled_image_native.raw"
            require_file(raw_out)
            raw_out_size = raw_out.stat().st_size
            qnn_bgr = qnn_raw_to_bgr(raw_out, args.output_scale, args.output_zero_point)
            repeat_profiles.append(parse_profile(current_pull_dir / "output" / "profile_viewer.csv"))

        if qnn_bgr is None:
            raise RuntimeError(f"no QNN output generated for {case.case_id}")

        lr = cv2.imread(str(case.lr_128), cv2.IMREAD_COLOR)
        bicubic = cv2.imread(str(case.bicubic_512), cv2.IMREAD_COLOR)
        hr = cv2.imread(str(case.hr_512), cv2.IMREAD_COLOR)
        if lr is None or bicubic is None or hr is None:
            raise FileNotFoundError(case.case_id)

        cv2.imwrite(str(case_dir / "lr_128.png"), lr)
        cv2.imwrite(str(case_dir / "bicubic_512.png"), bicubic)
        cv2.imwrite(str(case_dir / "qnn_w8a8_512.png"), qnn_bgr)
        cv2.imwrite(str(case_dir / "hr_512.png"), hr)
        write_case_sheet(case_dir / "case_contact_sheet.png", lr, bicubic, qnn_bgr, hr)

        profile = repeat_profiles[-1]
        netrun_values = [numeric_profile_value(p, "netrun_execute_us") for p in repeat_profiles]
        qnn_values = [numeric_profile_value(p, "qnn_execute_us") for p in repeat_profiles]
        accel_values = [numeric_profile_value(p, "qnn_accelerator_execute_us") for p in repeat_profiles]
        rpc_values = [numeric_profile_value(p, "rpc_execute_us") for p in repeat_profiles]
        netrun_avg, netrun_p50, netrun_p95 = summarize_values(netrun_values)
        qnn_avg, qnn_p50, qnn_p95 = summarize_values(qnn_values)
        accel_avg, accel_p50, accel_p95 = summarize_values(accel_values)
        rpc_avg, rpc_p50, rpc_p95 = summarize_values(rpc_values)
        wall_avg, wall_p50, wall_p95 = summarize_values(repeat_wall_ms)
        rows.append({
            "case_id": case.case_id,
            "category": case.category,
            "dataset": case.dataset,
            "source_id": case.source_id,
            "main_variable": f"local RB5 QNN W8A8 {run_scope_label(args.input_set)} timing and validity",
            "frozen_variables": f"{input_csv_label(args.input_set)}; Real-ESRGAN W8A8 QNN context; 128 input; 512 output; qnn-net-run retrieve_context",
            "context_binary": str(context_binary),
            "output_scale": f"{args.output_scale:.12g}",
            "output_zero_point": str(args.output_zero_point),
            "repeat_count": str(args.repeats),
            "wall_ms": wall_avg,
            "wall_p50_ms": wall_p50,
            "wall_p95_ms": wall_p95,
            **profile,
            "netrun_execute_avg_us": netrun_avg,
            "netrun_execute_p50_us": netrun_p50,
            "netrun_execute_p95_us": netrun_p95,
            "qnn_execute_avg_us": qnn_avg,
            "qnn_execute_p50_us": qnn_p50,
            "qnn_execute_p95_us": qnn_p95,
            "qnn_accelerator_execute_avg_us": accel_avg,
            "qnn_accelerator_execute_p50_us": accel_p50,
            "qnn_accelerator_execute_p95_us": accel_p95,
            "rpc_execute_avg_us": rpc_avg,
            "rpc_execute_p50_us": rpc_p50,
            "rpc_execute_p95_us": rpc_p95,
            "output_size": f"{qnn_bgr.shape[1]}x{qnn_bgr.shape[0]}",
            "raw_output_bytes": str(raw_out_size),
            "output_stddev": f"{image_stddev(qnn_bgr):.3f}",
            "psnr_bicubic_vs_hr": f"{psnr(hr, bicubic):.2f}",
            "ssim_bicubic_vs_hr": f"{ssim(hr, bicubic):.4f}",
            "psnr_qnn_vs_hr": f"{psnr(hr, qnn_bgr):.2f}",
            "ssim_qnn_vs_hr": f"{ssim(hr, qnn_bgr):.4f}",
            "psnr_delta_qnn_minus_bicubic": f"{psnr(hr, qnn_bgr) - psnr(hr, bicubic):.2f}",
            "sharpness_bicubic": f"{sharpness(bicubic):.2f}",
            "sharpness_qnn": f"{sharpness(qnn_bgr):.2f}",
            "sharpness_qnn_over_bicubic": f"{sharpness(qnn_bgr) / sharpness(bicubic):.3f}" if sharpness(bicubic) > 0 else "",
            "case_contact_sheet": str(case_dir / "case_contact_sheet.png"),
            "qnn_png": str(case_dir / "qnn_w8a8_512.png"),
            "selection_note": case.selection_note,
            "review_hint": "Check QNN image against bicubic and HR; metrics are supporting evidence, not final visual judgment.",
        })

    loop_state = make_loop_state_payload(
        run_id=run_id,
        output_dir=out_root,
        rows=rows,
        repeat_count=args.repeats,
        input_set=args.input_set,
    )
    write_csv(out_root / "metrics.csv", rows)
    write_csv(out_root / "run_log.csv", [make_run_log(out_root, run_id, rows, loop_state, args.input_set)])
    (out_root / "loop_state.json").write_text(
        json.dumps(json_safe(loop_state), ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    write_contact_sheet(rows, out_root / "contact_sheet.png")
    write_summary(out_root, run_id, rows, by_category, loop_state, args.input_set)
    write_human_review_guide(out_root, rows, loop_state, args.input_set)
    write_next_action(out_root, run_id, rows, loop_state, args.input_set)
    print(f"[ok] wrote {out_root}")


if __name__ == "__main__":
    main()
