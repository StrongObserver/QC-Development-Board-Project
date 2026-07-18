r"""Run RB5_SR_Benchmark_v1 through float and W8A8 TFLite models.

This script is the host-side bridge between the fixed benchmark dataset under
``C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1`` and the current
Real-ESRGAN model assets in this repository.

It intentionally follows the benchmark QA protocol:

- read cases from manifest.csv or qa/smoke_subset.csv
- keep benchmark inputs immutable
- write one self-contained result folder per run
- generate metrics, run log, and contact sheets for human review
"""

from __future__ import annotations

import argparse
import csv
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
from ai_edge_litert.interpreter import Interpreter


DEFAULT_BENCHMARK_ROOT = Path(r"C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1")


@dataclass(frozen=True)
class BenchmarkCase:
    case_id: str
    category: str
    dataset: str
    source_id: str
    lr_128: Path
    bicubic_512: Path
    hr_512: Path
    selection_reason: str


def first_existing(paths: list[Path]) -> Path:
    for path in paths:
        if path.exists():
            return path
    raise FileNotFoundError("none of the candidate paths exist: " + ", ".join(str(p) for p in paths))


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


def rel(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(path)


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
    if mse == 0:
        return 99.0
    return float(10.0 * np.log10((255.0 * 255.0) / mse))


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
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def mean_abs_diff(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.mean(np.abs(a.astype(np.float64) - b.astype(np.float64))))


def image_size(image: np.ndarray) -> str:
    height, width = image.shape[:2]
    return f"{width}x{height}"


def panel(image: np.ndarray, title: str, width: int = 260) -> np.ndarray:
    body = cv2.resize(image, (width, width), interpolation=cv2.INTER_AREA)
    header = np.full((40, width, 3), 25, dtype=np.uint8)
    cv2.putText(header, title[:28], (8, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
    return np.vstack([header, body])


def write_case_sheet(
    out_path: Path,
    lr: np.ndarray,
    bicubic: np.ndarray,
    float_out: np.ndarray,
    w8a8_out: np.ndarray,
    hr: np.ndarray,
) -> None:
    sheet = np.hstack(
        [
            panel(lr, "LR 128"),
            panel(bicubic, "bicubic 512"),
            panel(float_out, "float TFLite"),
            panel(w8a8_out, "W8A8 TFLite"),
            panel(hr, "HR reference"),
        ]
    )
    cv2.imwrite(str(out_path), sheet)


def write_overview_sheet(case_sheets: list[tuple[str, Path]], out_path: Path) -> None:
    if not case_sheets:
        return
    thumbs: list[np.ndarray] = []
    for case_id, sheet_path in case_sheets:
        image = read_image(sheet_path)
        thumb = cv2.resize(image, (650, 170), interpolation=cv2.INTER_AREA)
        header = np.full((30, thumb.shape[1], 3), 245, dtype=np.uint8)
        cv2.putText(header, case_id[:50], (8, 21), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (20, 20, 20), 1, cv2.LINE_AA)
        thumbs.append(np.vstack([header, thumb]))
    cols = 1 if len(thumbs) <= 8 else 2
    rows = []
    for i in range(0, len(thumbs), cols):
        row_items = thumbs[i : i + cols]
        if len(row_items) < cols:
            blank = np.full_like(row_items[0], 255)
            row_items.append(blank)
        rows.append(np.hstack(row_items))
    cv2.imwrite(str(out_path), np.vstack(rows))


def load_manifest(benchmark_root: Path) -> list[BenchmarkCase]:
    manifest = benchmark_root / "manifest.csv"
    cases: list[BenchmarkCase] = []
    with manifest.open("r", newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            cases.append(
                BenchmarkCase(
                    case_id=row["case_id"],
                    category=row["category"],
                    dataset=row["dataset"],
                    source_id=row["source_id"],
                    lr_128=Path(row["lr_128"]),
                    bicubic_512=Path(row["bicubic_512"]),
                    hr_512=Path(row["hr_512"]),
                    selection_reason=row.get("selection_reason", ""),
                )
            )
    return cases


def load_smoke_ids(benchmark_root: Path) -> set[str]:
    smoke_path = benchmark_root / "qa" / "smoke_subset.csv"
    with smoke_path.open("r", newline="", encoding="utf-8-sig") as f:
        return {row["case_id"] for row in csv.DictReader(f)}


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


def average(rows: list[dict[str, str]], key: str) -> float:
    values = [float(row[key]) for row in rows if row.get(key) not in (None, "")]
    return float(np.mean(values)) if values else float("nan")


def summarize_by_category(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    categories = sorted({row["category"] for row in rows})
    summary: list[dict[str, str]] = []
    for category in categories:
        group = [row for row in rows if row["category"] == category]
        summary.append(
            {
                "category": category,
                "count": str(len(group)),
                "float_p50_avg_ms": f"{average(group, 'float_p50_ms'):.1f}",
                "w8a8_p50_avg_ms": f"{average(group, 'w8a8_p50_ms'):.1f}",
                "speedup_avg": f"{average(group, 'host_speedup_float_over_w8a8'):.3f}",
                "psnr_bicubic_vs_hr_avg": f"{average(group, 'psnr_bicubic_vs_hr'):.2f}",
                "psnr_float_vs_hr_avg": f"{average(group, 'psnr_float_vs_hr'):.2f}",
                "psnr_w8a8_vs_hr_avg": f"{average(group, 'psnr_w8a8_vs_hr'):.2f}",
                "psnr_w8a8_vs_float_avg": f"{average(group, 'psnr_w8a8_vs_float'):.2f}",
                "mad_w8a8_vs_float_avg": f"{average(group, 'mean_abs_diff_w8a8_vs_float'):.3f}",
                "sharpness_float_over_bicubic_avg": f"{average(group, 'sharpness_float_over_bicubic'):.3f}",
                "sharpness_w8a8_over_bicubic_avg": f"{average(group, 'sharpness_w8a8_over_bicubic'):.3f}",
            }
        )
    return summary


def make_run_log(
    run_id: str,
    timestamp: str,
    out_dir: Path,
    args: argparse.Namespace,
    num_cases: int,
    rows: list[dict[str, str]],
    model_name: str,
    script_commit: str,
) -> dict[str, str]:
    float_p50 = np.median([float(row["float_p50_ms"]) for row in rows])
    w8a8_p50 = np.median([float(row["w8a8_p50_ms"]) for row in rows])
    float_p95 = np.percentile([float(row["float_p50_ms"]) for row in rows], 95)
    w8a8_p95 = np.percentile([float(row["w8a8_p50_ms"]) for row in rows], 95)
    return {
        "run_id": run_id,
        "timestamp": timestamp,
        "operator": "",
        "device": "Windows host",
        "android_version": "not_applicable",
        "app_or_script_commit": script_commit,
        "model_name": model_name,
        "model_variant": "float32_vs_w8a8",
        "backend": "host_cpu_litert",
        "quantization": "float32_and_w8a8",
        "input_set": "qa/smoke_subset.csv" if args.smoke else "manifest.csv",
        "output_dir": str(out_dir),
        "num_cases": str(num_cases),
        "main_variable": "model quantization variant: float32 vs W8A8 on host CPU LiteRT",
        "frozen_variables": "same benchmark input set; same Real-ESRGAN x4v3 architecture; same 128x128 input and 512x512 HR reference; same host LiteRT timing loop",
        "avg_latency_ms": f"float={np.mean([float(row['float_mean_ms']) for row in rows]):.1f}; w8a8={np.mean([float(row['w8a8_mean_ms']) for row in rows]):.1f}",
        "p50_latency_ms": f"float={float_p50:.1f}; w8a8={w8a8_p50:.1f}",
        "p95_latency_ms": f"float={float_p95:.1f}; w8a8={w8a8_p95:.1f}",
        "metric_summary": "See metrics.csv. PSNR/SSIM are against HR reference; perceptual review still required.",
        "pass_count": "",
        "conditional_count": "",
        "fail_count": "",
        "blocked_by": "",
        "notes": "Host-side benchmark run. Use contact_sheet.png and qa/failure_taxonomy.md for human decision.",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark-root", type=Path, default=DEFAULT_BENCHMARK_ROOT)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--run-id", default="")
    parser.add_argument("--smoke", action="store_true", help="Run only qa/smoke_subset.csv cases.")
    parser.add_argument("--warmup", type=int, default=1)
    parser.add_argument("--runs", type=int, default=3)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    benchmark_root = args.benchmark_root.resolve()
    repo_root = args.repo_root.resolve()
    sr_lab = repo_root / "RB5_SR_lab"
    float_model = sr_lab / "export_assets" / "real_esrgan_general_x4v3-tflite-float" / "real_esrgan_general_x4v3.tflite"
    w8a8_model = first_existing(
        [
            sr_lab / "export_assets" / "real_esrgan_general_x4v3-tflite-w8a8" / "real_esrgan_general_x4v3-tflite-w8a8" / "real_esrgan_general_x4v3.tflite",
            repo_root / "RB5VisionLab" / "app" / "src" / "main" / "assets" / "real_esrgan_general_x4v3_w8a8.tflite",
        ]
    )

    cases = load_manifest(benchmark_root)
    if args.smoke:
        smoke_ids = load_smoke_ids(benchmark_root)
        cases = [case for case in cases if case.case_id in smoke_ids]

    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    run_id = args.run_id or f"{timestamp}_realesrgan_host_float_vs_w8a8_{'smoke' if args.smoke else 'full'}"
    out_dir = benchmark_root / "results" / run_id
    case_out_root = out_dir / "cases"
    sheet_dir = out_dir / "contact_sheets"
    case_out_root.mkdir(parents=True, exist_ok=True)
    sheet_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, str]] = []
    case_sheets: list[tuple[str, Path]] = []
    for index, case in enumerate(cases, start=1):
        print(f"[{index}/{len(cases)}] {case.case_id}")
        lr = read_image(case.lr_128)
        bicubic = read_image(case.bicubic_512)
        hr = read_image(case.hr_512)
        float_out, float_mean, float_p50, float_p95 = run_model(float_model, lr, args.warmup, args.runs)
        w8a8_out, w8a8_mean, w8a8_p50, w8a8_p95 = run_model(w8a8_model, lr, args.warmup, args.runs)

        case_out = case_out_root / case.case_id
        case_out.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(case_out / "lr_128.png"), lr)
        cv2.imwrite(str(case_out / "bicubic_512.png"), bicubic)
        cv2.imwrite(str(case_out / "float_512.png"), float_out)
        cv2.imwrite(str(case_out / "w8a8_512.png"), w8a8_out)
        cv2.imwrite(str(case_out / "hr_512.png"), hr)
        sheet_path = sheet_dir / f"{case.case_id}.png"
        write_case_sheet(sheet_path, lr, bicubic, float_out, w8a8_out, hr)
        case_sheets.append((case.case_id, sheet_path))
        bicubic_psnr = psnr(hr, bicubic)
        float_psnr = psnr(hr, float_out)
        w8a8_psnr = psnr(hr, w8a8_out)
        bicubic_ssim = ssim(hr, bicubic)
        float_ssim = ssim(hr, float_out)
        w8a8_ssim = ssim(hr, w8a8_out)
        bicubic_sharpness = sharpness(bicubic)
        float_sharpness = sharpness(float_out)
        w8a8_sharpness = sharpness(w8a8_out)

        rows.append(
            {
                "case_id": case.case_id,
                "category": case.category,
                "dataset": case.dataset,
                "source_id": case.source_id,
                "main_variable": "model quantization variant: float32 vs W8A8 on host CPU LiteRT",
                "frozen_variables": "manifest/smoke subset; LR/Bicubic/HR triplet; model architecture; host LiteRT runner; warmup/runs settings",
                "input_size": image_size(lr),
                "output_size": image_size(float_out),
                "float_mean_ms": f"{float_mean:.1f}",
                "float_p50_ms": f"{float_p50:.1f}",
                "float_p95_ms": f"{float_p95:.1f}",
                "w8a8_mean_ms": f"{w8a8_mean:.1f}",
                "w8a8_p50_ms": f"{w8a8_p50:.1f}",
                "w8a8_p95_ms": f"{w8a8_p95:.1f}",
                "host_speedup_float_over_w8a8": f"{float_p50 / w8a8_p50:.3f}" if w8a8_p50 > 0 else "",
                "psnr_bicubic_vs_hr": f"{bicubic_psnr:.2f}",
                "ssim_bicubic_vs_hr": f"{bicubic_ssim:.4f}",
                "psnr_float_vs_hr": f"{float_psnr:.2f}",
                "ssim_float_vs_hr": f"{float_ssim:.4f}",
                "psnr_w8a8_vs_hr": f"{w8a8_psnr:.2f}",
                "ssim_w8a8_vs_hr": f"{w8a8_ssim:.4f}",
                "psnr_delta_float_minus_bicubic": f"{float_psnr - bicubic_psnr:.2f}",
                "psnr_delta_w8a8_minus_bicubic": f"{w8a8_psnr - bicubic_psnr:.2f}",
                "psnr_w8a8_vs_float": f"{psnr(float_out, w8a8_out):.2f}",
                "ssim_w8a8_vs_float": f"{ssim(float_out, w8a8_out):.4f}",
                "mean_abs_diff_w8a8_vs_float": f"{mean_abs_diff(float_out, w8a8_out):.3f}",
                "sharpness_bicubic": f"{bicubic_sharpness:.2f}",
                "sharpness_float": f"{float_sharpness:.2f}",
                "sharpness_w8a8": f"{w8a8_sharpness:.2f}",
                "sharpness_float_over_bicubic": f"{float_sharpness / bicubic_sharpness:.3f}" if bicubic_sharpness > 0 else "",
                "sharpness_w8a8_over_bicubic": f"{w8a8_sharpness / bicubic_sharpness:.3f}" if bicubic_sharpness > 0 else "",
                "lr_128": rel(benchmark_root, case.lr_128),
                "bicubic_512": rel(benchmark_root, case.bicubic_512),
                "hr_512": rel(benchmark_root, case.hr_512),
                "float_output": rel(benchmark_root, case_out / "float_512.png"),
                "w8a8_output": rel(benchmark_root, case_out / "w8a8_512.png"),
                "contact_sheet": rel(benchmark_root, sheet_path),
                "selection_reason": case.selection_reason,
                "review_boundary": "Use human review for Real-ESRGAN perceptual quality; PSNR/SSIM alone are not final acceptance.",
                "metric_role": "PSNR/SSIM/sharpness are supporting evidence; contact sheet review owns final quality until calibrated.",
            }
        )

    write_csv(out_dir / "metrics.csv", rows)
    write_csv(out_dir / "category_summary.csv", summarize_by_category(rows))
    write_overview_sheet(case_sheets, out_dir / "contact_sheet.png")
    script_commit = git_revision(repo_root)
    run_log = make_run_log(
        run_id=run_id,
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M +0800"),
        out_dir=out_dir,
        args=args,
        num_cases=len(cases),
        rows=rows,
        model_name="Real-ESRGAN general x4v3",
        script_commit=script_commit,
    )
    write_csv(out_dir / "run_log.csv", [run_log])

    print(f"[ok] wrote {out_dir / 'metrics.csv'}")
    print(f"[ok] wrote {out_dir / 'category_summary.csv'}")
    print(f"[ok] wrote {out_dir / 'run_log.csv'}")
    print(f"[ok] wrote {out_dir / 'contact_sheet.png'}")
    print(f"[ok] evaluated {len(cases)} cases")


if __name__ == "__main__":
    main()
