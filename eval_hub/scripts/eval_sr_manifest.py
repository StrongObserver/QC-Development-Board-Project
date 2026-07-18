"""Evaluate a generic SR manifest with float and W8A8 TFLite models.

The manifest must contain:

``case_id, category, dataset, source_id, lr_128, bicubic_512, hr_512``

This script is intentionally host-side only. It extends the current Harness
shape to EvalHub-derived manifests without replacing RB5_SR_Benchmark_v1.
"""

from __future__ import annotations

import argparse
import csv
import subprocess
import time
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
from ai_edge_litert.interpreter import Interpreter

from evalhub_common import DATA_ROOT, REPO_ROOT, read_csv, write_csv


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


def read_image(path: Path) -> np.ndarray:
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        raise FileNotFoundError(path)
    return image


def quantize_if_needed(x: np.ndarray, tensor: dict) -> np.ndarray:
    if tensor["dtype"] == np.float32:
        return x.astype(np.float32)
    scale, zero_point = tensor["quantization"]
    if scale == 0:
        raise ValueError(f"invalid input quantization: {tensor}")
    info = np.iinfo(tensor["dtype"])
    q = np.round(x / scale + zero_point)
    return np.clip(q, info.min, info.max).astype(tensor["dtype"])


def dequantize_if_needed(y: np.ndarray, tensor: dict) -> np.ndarray:
    if tensor["dtype"] == np.float32:
        return y.astype(np.float32)
    scale, zero_point = tensor["quantization"]
    if scale == 0:
        raise ValueError(f"invalid output quantization: {tensor}")
    return (y.astype(np.float32) - zero_point) * scale


def run_model(model_path: Path, image_bgr: np.ndarray, warmup: int, runs: int) -> tuple[np.ndarray, float, float, float]:
    interpreter = Interpreter(model_path=str(model_path))
    interpreter.allocate_tensors()
    inp = interpreter.get_input_details()[0]
    out = interpreter.get_output_details()[0]
    if image_bgr.shape[:2] != (128, 128):
        raise ValueError(f"expected 128x128 input, got {image_bgr.shape[:2]} for {model_path}")
    rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    x = quantize_if_needed(rgb[None, ...], inp)
    for _ in range(warmup):
        interpreter.set_tensor(inp["index"], x)
        interpreter.invoke()
    timings: list[float] = []
    for _ in range(runs):
        interpreter.set_tensor(inp["index"], x)
        t0 = time.perf_counter()
        interpreter.invoke()
        timings.append((time.perf_counter() - t0) * 1000.0)
    y = dequantize_if_needed(interpreter.get_tensor(out["index"]), out)[0]
    out_bgr = cv2.cvtColor((np.clip(y, 0, 1) * 255.0).round().astype(np.uint8), cv2.COLOR_RGB2BGR)
    return out_bgr, float(np.mean(timings)), float(np.median(timings)), float(np.percentile(timings, 95))


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


def panel(image: np.ndarray, title: str, width: int = 220) -> np.ndarray:
    body = cv2.resize(image, (width, width), interpolation=cv2.INTER_AREA)
    header = np.full((34, width, 3), 25, dtype=np.uint8)
    cv2.putText(header, title[:24], (8, 23), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
    return np.vstack([header, body])


def write_case_sheet(path: Path, lr: np.ndarray, bicubic: np.ndarray, float_out: np.ndarray, w8a8_out: np.ndarray, hr: np.ndarray) -> None:
    sheet = np.hstack([
        panel(lr, "LR 128"),
        panel(bicubic, "bicubic 512"),
        panel(float_out, "float"),
        panel(w8a8_out, "W8A8"),
        panel(hr, "HR 512"),
    ])
    cv2.imwrite(str(path), sheet)


def write_overview(rows: list[dict[str, str]], out_path: Path) -> None:
    thumbs = []
    for row in rows:
        image = cv2.imread(row["case_contact_sheet"], cv2.IMREAD_COLOR)
        if image is None:
            continue
        thumb = cv2.resize(image, (760, 170), interpolation=cv2.INTER_AREA)
        header = np.full((30, thumb.shape[1], 3), 245, dtype=np.uint8)
        text = f"{row['case_id']} | {row['category']} | PSNR float {row['psnr_float_vs_hr']} | W8A8 {row['psnr_w8a8_vs_hr']}"
        cv2.putText(header, text[:110], (8, 21), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (20, 20, 20), 1, cv2.LINE_AA)
        thumbs.append(np.vstack([header, thumb]))
    if thumbs:
        cv2.imwrite(str(out_path), np.vstack(thumbs))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--run-id", default="")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--warmup", type=int, default=1)
    parser.add_argument("--runs", type=int, default=3)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rows_in = read_csv(args.manifest)
    if args.limit:
        rows_in = rows_in[: args.limit]
    sr_lab = REPO_ROOT / "RB5_SR_lab"
    float_model = sr_lab / "export_assets" / "real_esrgan_general_x4v3-tflite-float" / "real_esrgan_general_x4v3.tflite"
    w8a8_model = REPO_ROOT / "RB5VisionLab" / "app" / "src" / "main" / "assets" / "real_esrgan_general_x4v3_w8a8.tflite"
    for path in [float_model, w8a8_model]:
        if not path.exists():
            raise FileNotFoundError(path)

    run_id = args.run_id or datetime.now().strftime("evalhub_%Y%m%d_%H%M%S_host_float_vs_w8a8")
    out_root = DATA_ROOT / "derived_runs" / run_id
    out_root.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, str]] = []
    for index, row in enumerate(rows_in, start=1):
        print(f"[{index}/{len(rows_in)}] {row['case_id']}")
        lr = read_image(Path(row["lr_128"]))
        bicubic = read_image(Path(row["bicubic_512"]))
        hr = read_image(Path(row["hr_512"]))
        float_out, float_mean, float_p50, float_p95 = run_model(float_model, lr, args.warmup, args.runs)
        w8a8_out, w8a8_mean, w8a8_p50, w8a8_p95 = run_model(w8a8_model, lr, args.warmup, args.runs)
        case_dir = out_root / "cases" / row["category"] / row["case_id"]
        case_dir.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(case_dir / "lr_128.png"), lr)
        cv2.imwrite(str(case_dir / "bicubic_512.png"), bicubic)
        cv2.imwrite(str(case_dir / "float_512.png"), float_out)
        cv2.imwrite(str(case_dir / "w8a8_512.png"), w8a8_out)
        cv2.imwrite(str(case_dir / "hr_512.png"), hr)
        sheet = case_dir / "case_contact_sheet.png"
        write_case_sheet(sheet, lr, bicubic, float_out, w8a8_out, hr)
        bicubic_sharp = sharpness(bicubic)
        rows.append({
            "case_id": row["case_id"],
            "category": row["category"],
            "dataset": row["dataset"],
            "source_id": row["source_id"],
            "main_variable": "EvalHub manifest host float vs W8A8 sanity",
            "frozen_variables": "manifest input triplet; Real-ESRGAN x4v3; host LiteRT runner; 128 input; 512 output",
            "float_mean_ms": f"{float_mean:.1f}",
            "float_p50_ms": f"{float_p50:.1f}",
            "float_p95_ms": f"{float_p95:.1f}",
            "w8a8_mean_ms": f"{w8a8_mean:.1f}",
            "w8a8_p50_ms": f"{w8a8_p50:.1f}",
            "w8a8_p95_ms": f"{w8a8_p95:.1f}",
            "psnr_bicubic_vs_hr": f"{psnr(hr, bicubic):.2f}",
            "ssim_bicubic_vs_hr": f"{ssim(hr, bicubic):.4f}",
            "psnr_float_vs_hr": f"{psnr(hr, float_out):.2f}",
            "ssim_float_vs_hr": f"{ssim(hr, float_out):.4f}",
            "psnr_w8a8_vs_hr": f"{psnr(hr, w8a8_out):.2f}",
            "ssim_w8a8_vs_hr": f"{ssim(hr, w8a8_out):.4f}",
            "sharpness_float_over_bicubic": f"{sharpness(float_out) / bicubic_sharp:.3f}" if bicubic_sharp > 0 else "",
            "sharpness_w8a8_over_bicubic": f"{sharpness(w8a8_out) / bicubic_sharp:.3f}" if bicubic_sharp > 0 else "",
            "case_contact_sheet": str(sheet),
            "metric_role": "PSNR/SSIM/sharpness are supporting evidence; contact sheet review owns final quality until calibrated.",
        })

    write_csv(out_root / "metrics.csv", rows)
    run_log = [{
        "run_id": run_id,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M +0800"),
        "device": "Windows host",
        "app_or_script_commit": git_revision(REPO_ROOT),
        "backend": "host_cpu_litert",
        "input_set": str(args.manifest),
        "output_dir": str(out_root),
        "num_cases": str(len(rows)),
        "main_variable": "EvalHub manifest host float vs W8A8 sanity",
        "frozen_variables": "manifest; model assets; host LiteRT runner",
        "metric_summary": "See metrics.csv; visual review remains final.",
    }]
    write_csv(out_root / "run_log.csv", run_log)
    write_overview(rows[: min(40, len(rows))], out_root / "contact_sheet.png")
    (out_root / "SUMMARY.md").write_text(
        "\n".join([
            "# EvalHub SR Manifest Summary",
            "",
            f"- run_id: {run_id}",
            f"- manifest: `{args.manifest}`",
            f"- cases: {len(rows)}",
            f"- metrics: `{out_root / 'metrics.csv'}`",
            f"- contact sheet: `{out_root / 'contact_sheet.png'}`",
            "",
            "Boundary: host LiteRT sanity only, not RB5 QNN/app e2e.",
            "",
        ]),
        encoding="utf-8",
    )
    print(f"[ok] wrote {out_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

