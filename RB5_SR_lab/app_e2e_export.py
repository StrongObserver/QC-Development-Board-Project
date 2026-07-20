"""Helpers for writing EvalHub-compatible app e2e log rows."""

from __future__ import annotations

import csv
import subprocess
from pathlib import Path


APP_E2E_FIELDS = [
    "run_id",
    "timestamp",
    "device",
    "android_version",
    "app_commit",
    "model_name",
    "model_variant",
    "backend",
    "input_source",
    "input_size",
    "output_size",
    "preprocess_ms",
    "inference_ms",
    "postprocess_ms",
    "e2e_ms",
    "steady_state_window",
    "p50_e2e_ms",
    "p95_e2e_ms",
    "memory_mb",
    "cpu_percent",
    "gpu_percent",
    "npu_or_dsp_note",
    "power_w",
    "skin_temp_c",
    "thermal_status",
    "fallback_code",
    "failure_code",
    "human_decision",
    "notes",
]


def git_commit_label(repo_root: Path) -> str:
    head = _run_text(["git", "rev-parse", "--short", "HEAD"], repo_root) or "unknown"
    dirty = subprocess.run(
        ["git", "diff", "--quiet", "--"],
        cwd=repo_root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    ).returncode != 0
    return f"{head}-dirty" if dirty else head


def model_name(model_label: str) -> str:
    if "QUICKSR" in model_label:
        return "QuickSRNetSmall"
    if "W8A8" in model_label or "REALESRGAN" in model_label:
        return "Real-ESRGAN general x4v3"
    if model_label == "APP_DEFAULT":
        return "App default SR model"
    return model_label


def model_variant(model_label: str) -> str:
    normalized = model_label.lower()
    if "tensor_rotated" in normalized:
        return "quicksr_w8a8_qnn_tensor_rotated_native_probe"
    if "tensor_ready" in normalized:
        return "quicksr_w8a8_qnn_tensor_ready_probe"
    if "quicksr" in normalized:
        return "quicksr_w8a8_qnn_delegate"
    if "w8a8" in normalized:
        return "realesrgan_w8a8_qnn_delegate"
    if model_label == "APP_DEFAULT":
        return "app_default_qnn_delegate"
    return normalized


def stage_value(stage_rows: list[dict[str, object]], stage: str, field: str) -> str:
    for row in stage_rows:
        if row.get("stage") == stage:
            return str(row.get(field, ""))
    return ""


def temperature_values_c(thermal_rows: list[dict[str, object]]) -> list[float]:
    values: list[float] = []
    for row in thermal_rows:
        raw = row.get("temperature") or row.get("temp_c")
        if raw in ("", None):
            continue
        try:
            value = float(str(raw))
        except ValueError:
            continue
        # dumpsys battery reports deci-Celsius; run_power_probe reports Celsius.
        values.append(value / 10.0 if value > 100.0 else value)
    return values


def last_temperature_c(thermal_rows: list[dict[str, object]]) -> str:
    values = temperature_values_c(thermal_rows)
    if not values:
        return ""
    return f"{values[-1]:.1f}"


def first_last_temperature_c(thermal_rows: list[dict[str, object]]) -> str:
    values = temperature_values_c(thermal_rows)
    if not values:
        return ""
    return f"{values[0]:.1f}->{values[-1]:.1f}"


def write_app_e2e_log(path: Path, row: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = {field: row.get(field, "") for field in APP_E2E_FIELDS}
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=APP_E2E_FIELDS)
        writer.writeheader()
        writer.writerow(normalized)


def mirror_app_e2e_log(repo_root: Path, run_id: str, source_path: Path) -> Path:
    target = repo_root / "evalhub_data" / "derived" / "app_e2e" / run_id / source_path.name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(source_path.read_text(encoding="utf-8"), encoding="utf-8")
    return target


def _run_text(cmd: list[str], cwd: Path) -> str:
    result = subprocess.run(
        cmd,
        cwd=cwd,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    return result.stdout.strip() if result.returncode == 0 else ""
