"""D8 W8A8 quantization baseline for RB5 super-resolution.

Runs the same fixed 128x128 inputs through the float TFLite model and the
W8A8 TFLite model, then writes output PNGs, contact sheets, and a compact CSV.
"""

from __future__ import annotations

import csv
import time
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from ai_edge_litert.interpreter import Interpreter


@dataclass(frozen=True)
class QuantCase:
    case_id: str
    scenario: str
    input_path: Path


def rel(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(path)


def first_existing(paths: list[Path]) -> Path:
    for path in paths:
        if path.exists():
            return path
    raise FileNotFoundError("none of the candidate model paths exist: " + ", ".join(str(p) for p in paths))


def load_image(path: Path, side: int = 128) -> np.ndarray:
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        raise FileNotFoundError(path)
    if image.shape[0] != side or image.shape[1] != side:
        image = cv2.resize(image, (side, side), interpolation=cv2.INTER_CUBIC)
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


def run_model(model_path: Path, image_bgr: np.ndarray, warmup: int = 1, runs: int = 3) -> tuple[np.ndarray, float]:
    interpreter = Interpreter(model_path=str(model_path))
    interpreter.allocate_tensors()
    inp = interpreter.get_input_details()[0]
    out = interpreter.get_output_details()[0]
    rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    x = quantize_if_needed(rgb[None, ...], inp)
    for _ in range(warmup):
        interpreter.set_tensor(inp["index"], x)
        interpreter.invoke()
    timings = []
    for _ in range(runs):
        interpreter.set_tensor(inp["index"], x)
        t0 = time.perf_counter()
        interpreter.invoke()
        timings.append((time.perf_counter() - t0) * 1000.0)
    y = dequantize_if_needed(interpreter.get_tensor(out["index"]), out)[0]
    out_bgr = cv2.cvtColor((np.clip(y, 0, 1) * 255.0).round().astype(np.uint8), cv2.COLOR_RGB2BGR)
    return out_bgr, float(np.median(timings))


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


def panel(image: np.ndarray, title: str, width: int = 320) -> np.ndarray:
    body = cv2.resize(image, (width, width), interpolation=cv2.INTER_AREA)
    header = np.full((42, width, 3), 25, dtype=np.uint8)
    cv2.putText(header, title[:30], (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (255, 255, 255), 1, cv2.LINE_AA)
    return np.vstack([header, body])


def contact_sheet(input_bgr: np.ndarray, bicubic: np.ndarray, float_out: np.ndarray, w8a8_out: np.ndarray) -> np.ndarray:
    return np.hstack([
        panel(input_bgr, "input 128"),
        panel(bicubic, "bicubic 512"),
        panel(float_out, "float TFLite"),
        panel(w8a8_out, "W8A8 TFLite"),
    ])


def append_existing_pair(
    rows: list[dict[str, str]],
    root: Path,
    out_dir: Path,
    sheet_dir: Path,
    case_id: str,
    scenario: str,
    input_path: Path,
    float_path: Path,
    w8a8_path: Path,
    float_model_size: int,
    w8a8_model_size: int,
    rb5_note: str,
) -> None:
    if not (input_path.exists() and float_path.exists() and w8a8_path.exists()):
        return
    image = load_image(input_path)
    bicubic = cv2.resize(image, (512, 512), interpolation=cv2.INTER_CUBIC)
    float_out = cv2.imread(str(float_path), cv2.IMREAD_COLOR)
    w8a8_out = cv2.imread(str(w8a8_path), cv2.IMREAD_COLOR)
    if float_out is None or w8a8_out is None:
        return
    sheet_path = sheet_dir / f"{case_id}_float_vs_w8a8.png"
    cv2.imwrite(str(sheet_path), contact_sheet(image, bicubic, float_out, w8a8_out))
    rows.append({
        "case_id": case_id,
        "scenario": scenario,
        "input_path": rel(root, input_path),
        "float_output": rel(root, float_path),
        "w8a8_output": rel(root, w8a8_path),
        "contact_sheet": rel(root, sheet_path),
        "float_model_size_bytes": str(float_model_size),
        "w8a8_model_size_bytes": str(w8a8_model_size),
        "host_float_median_ms": "",
        "host_w8a8_median_ms": "",
        "host_speedup_float_over_w8a8": "",
        "psnr_w8a8_vs_float": f"{psnr(float_out, w8a8_out):.2f}",
        "ssim_w8a8_vs_float": f"{ssim(float_out, w8a8_out):.4f}",
        "mean_abs_diff_w8a8_vs_float": f"{np.mean(np.abs(float_out.astype(np.float64) - w8a8_out.astype(np.float64))):.3f}",
        "sharpness_float": f"{sharpness(float_out):.2f}",
        "sharpness_w8a8": f"{sharpness(w8a8_out):.2f}",
        "boundary": "RB5 CPU app output pair. " + rb5_note,
    })


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    sr_lab = root / "RB5_SR_lab"
    project_assets = root / "project_assets"
    float_model = sr_lab / "export_assets" / "real_esrgan_general_x4v3-tflite-float" / "real_esrgan_general_x4v3.tflite"
    w8a8_model = first_existing([
        sr_lab / "export_assets" / "real_esrgan_general_x4v3-tflite-w8a8" / "real_esrgan_general_x4v3-tflite-w8a8" / "real_esrgan_general_x4v3.tflite",
        root / "RB5VisionLab" / "app" / "src" / "main" / "assets" / "real_esrgan_general_x4v3_w8a8.tflite",
    ])
    cases = [
        QuantCase("flower", "host_texture_color", sr_lab / "inputs" / "flower.png"),
        QuantCase("photo", "host_photo_general", sr_lab / "inputs" / "photo.png"),
        QuantCase("offline_text_edge", "rb5_offline_text_edge", project_assets / "offline_eval" / "OFFLINE_TEXT_EDGE_20251110_055715_CPU_input_128.png"),
        QuantCase("offline_lowlight_noise", "rb5_offline_lowlight_noise", project_assets / "offline_eval" / "OFFLINE_LOWLIGHT_NOISE_20251110_055715_CPU_input_128.png"),
    ]
    out_dir = sr_lab / "results" / "w8a8_baseline"
    sheet_dir = out_dir / "contact_sheets"
    sheet_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, str]] = []
    for case in cases:
        image = load_image(case.input_path)
        bicubic = cv2.resize(image, (512, 512), interpolation=cv2.INTER_CUBIC)
        float_out, float_ms = run_model(float_model, image)
        w8a8_out, w8a8_ms = run_model(w8a8_model, image)
        cv2.imwrite(str(out_dir / f"{case.case_id}_input_128.png"), image)
        cv2.imwrite(str(out_dir / f"{case.case_id}_bicubic_512.png"), bicubic)
        cv2.imwrite(str(out_dir / f"{case.case_id}_float_512.png"), float_out)
        cv2.imwrite(str(out_dir / f"{case.case_id}_w8a8_512.png"), w8a8_out)
        sheet_path = sheet_dir / f"{case.case_id}_float_vs_w8a8.png"
        cv2.imwrite(str(sheet_path), contact_sheet(image, bicubic, float_out, w8a8_out))
        rows.append({
            "case_id": case.case_id,
            "scenario": case.scenario,
            "input_path": rel(root, case.input_path),
            "float_output": rel(root, out_dir / f"{case.case_id}_float_512.png"),
            "w8a8_output": rel(root, out_dir / f"{case.case_id}_w8a8_512.png"),
            "contact_sheet": rel(root, sheet_path),
            "float_model_size_bytes": str(float_model.stat().st_size),
            "w8a8_model_size_bytes": str(w8a8_model.stat().st_size),
            "host_float_median_ms": f"{float_ms:.1f}",
            "host_w8a8_median_ms": f"{w8a8_ms:.1f}",
            "host_speedup_float_over_w8a8": f"{float_ms / w8a8_ms:.3f}" if w8a8_ms > 0 else "",
            "psnr_w8a8_vs_float": f"{psnr(float_out, w8a8_out):.2f}",
            "ssim_w8a8_vs_float": f"{ssim(float_out, w8a8_out):.4f}",
            "mean_abs_diff_w8a8_vs_float": f"{np.mean(np.abs(float_out.astype(np.float64) - w8a8_out.astype(np.float64))):.3f}",
            "sharpness_float": f"{sharpness(float_out):.2f}",
            "sharpness_w8a8": f"{sharpness(w8a8_out):.2f}",
            "boundary": "W8A8 passes only if contact sheet shows no obvious text deformation, geometry mismatch, color shift, or noise amplification.",
        })
    append_existing_pair(
        rows,
        root,
        out_dir,
        sheet_dir,
        "rb5_offline_text_edge_cpu",
        "rb5_android_cpu_offline_text_edge",
        project_assets / "offline_eval" / "OFFLINE_TEXT_EDGE_20251110_055715_CPU_input_128.png",
        project_assets / "offline_eval" / "OFFLINE_TEXT_EDGE_20251110_055715_CPU_sr_512.png",
        project_assets / "offline_eval_w8a8" / "OFFLINE_TEXT_EDGE_20251110_062920_CPU_W8A8_sr_512.png",
        float_model.stat().st_size,
        w8a8_model.stat().st_size,
        "Use visual review to confirm W8A8 does not deform letters or add ringing.",
    )
    append_existing_pair(
        rows,
        root,
        out_dir,
        sheet_dir,
        "rb5_offline_lowlight_noise_cpu",
        "rb5_android_cpu_offline_lowlight_noise",
        project_assets / "offline_eval" / "OFFLINE_LOWLIGHT_NOISE_20251110_055715_CPU_input_128.png",
        project_assets / "offline_eval" / "OFFLINE_LOWLIGHT_NOISE_20251110_055715_CPU_sr_512.png",
        project_assets / "offline_eval_w8a8" / "OFFLINE_LOWLIGHT_NOISE_20251110_062920_CPU_W8A8_sr_512.png",
        float_model.stat().st_size,
        w8a8_model.stat().st_size,
        "RB5 UI reported W8A8 low-light inference 361 ms, e2e about 379 ms; reject if noise is amplified.",
    )
    csv_path = out_dir / "w8a8_metrics.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"[ok] wrote {csv_path}")
    print(f"[ok] wrote contact sheets under {sheet_dir}")
    print(f"[ok] evaluated {len(rows)} W8A8 cases")


if __name__ == "__main__":
    main()
