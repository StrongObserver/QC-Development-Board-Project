"""Compare Real-ESRGAN W8A8 quantization configuration candidates."""

from __future__ import annotations

import csv
import time
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
from ai_edge_litert.interpreter import Interpreter


REPO_ROOT = Path(__file__).resolve().parents[1]
BENCHMARK_ROOT = Path(r"C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1")


def read_image(path: Path) -> np.ndarray:
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        raise FileNotFoundError(path)
    return image


def load_smoke_cases() -> list[dict[str, str]]:
    manifest: dict[str, dict[str, str]] = {}
    with (BENCHMARK_ROOT / "manifest.csv").open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            manifest[row["case_id"]] = row
    rows: list[dict[str, str]] = []
    with (BENCHMARK_ROOT / "qa" / "smoke_subset.csv").open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            rows.append(manifest[row["case_id"]])
    return rows


def quantize_if_needed(x: np.ndarray, tensor: dict) -> np.ndarray:
    if tensor["dtype"] == np.float32:
        return x.astype(np.float32)
    scale, zero_point = tensor["quantization"]
    q = np.round(x / scale + zero_point)
    info = np.iinfo(tensor["dtype"])
    return np.clip(q, info.min, info.max).astype(tensor["dtype"])


def dequantize_if_needed(y: np.ndarray, tensor: dict) -> np.ndarray:
    if tensor["dtype"] == np.float32:
        return y.astype(np.float32)
    scale, zero_point = tensor["quantization"]
    return (y.astype(np.float32) - zero_point) * scale


class TfliteModel:
    def __init__(self, path: Path):
        self.path = path
        self.interpreter = Interpreter(model_path=str(path))
        self.interpreter.allocate_tensors()
        self.input = self.interpreter.get_input_details()[0]
        self.output = self.interpreter.get_output_details()[0]

    def run(self, image_bgr: np.ndarray, runs: int = 3) -> tuple[np.ndarray, float]:
        rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        x = quantize_if_needed(rgb[None, ...], self.input)
        # one warmup
        self.interpreter.set_tensor(self.input["index"], x)
        self.interpreter.invoke()
        times: list[float] = []
        for _ in range(runs):
            self.interpreter.set_tensor(self.input["index"], x)
            t0 = time.perf_counter()
            self.interpreter.invoke()
            times.append((time.perf_counter() - t0) * 1000.0)
        y = dequantize_if_needed(self.interpreter.get_tensor(self.output["index"]), self.output)[0]
        out = cv2.cvtColor((np.clip(y, 0, 1) * 255.0).round().astype(np.uint8), cv2.COLOR_RGB2BGR)
        return out, float(np.median(times))


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


def mad(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.mean(np.abs(a.astype(np.float32) - b.astype(np.float32))))


def panel(image: np.ndarray, title: str, width: int = 220) -> np.ndarray:
    body = cv2.resize(image, (width, width), interpolation=cv2.INTER_AREA)
    header = np.full((36, width, 3), 25, dtype=np.uint8)
    cv2.putText(header, title[:26], (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
    return np.vstack([header, body])


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


def main() -> None:
    models = {
        "float": REPO_ROOT / "RB5_SR_lab" / "export_assets" / "real_esrgan_general_x4v3-tflite-float" / "real_esrgan_general_x4v3.tflite",
        "app_w8a8": REPO_ROOT / "RB5VisionLab" / "app" / "src" / "main" / "assets" / "real_esrgan_general_x4v3_w8a8.tflite",
        "calib10_default": REPO_ROOT / "RB5_SR_lab" / "export_assets" / "d8_config_realesrgan_w8a8_calib10_default" / "real_esrgan_general_x4v3-tflite-w8a8" / "real_esrgan_general_x4v3.tflite",
        "calib10_minmax": REPO_ROOT / "RB5_SR_lab" / "export_assets" / "d8_config_realesrgan_w8a8_calib10_minmax" / "real_esrgan_general_x4v3-tflite-w8a8" / "real_esrgan_general_x4v3.tflite",
    }
    runners = {name: TfliteModel(path) for name, path in models.items()}
    out_dir = REPO_ROOT / "RB5_SR_lab" / "results" / "d8_config_compare" / datetime.now().strftime("20260720_d8_config_smoke")
    out_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []
    overview_rows: list[np.ndarray] = []
    for case in load_smoke_cases():
        case_id = case["case_id"]
        print(f"[d8-config] {case_id}")
        lr = read_image(Path(case["lr_128"]))
        bicubic = read_image(Path(case["bicubic_512"]))
        hr = read_image(Path(case["hr_512"]))
        outputs: dict[str, np.ndarray] = {}
        timings: dict[str, float] = {}
        for name, runner in runners.items():
            outputs[name], timings[name] = runner.run(lr)
        case_dir = out_dir / "cases" / case_id
        case_dir.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(case_dir / "lr_128.png"), lr)
        cv2.imwrite(str(case_dir / "bicubic_512.png"), bicubic)
        cv2.imwrite(str(case_dir / "hr_512.png"), hr)
        for name, image in outputs.items():
            cv2.imwrite(str(case_dir / f"{name}_512.png"), image)
        sheet = np.hstack(
            [
                panel(lr, "LR"),
                panel(bicubic, "Bicubic"),
                panel(outputs["float"], "Float"),
                panel(outputs["app_w8a8"], "App W8A8"),
                panel(outputs["calib10_default"], "Calib10 default"),
                panel(outputs["calib10_minmax"], "Calib10 minmax"),
                panel(hr, "HR"),
            ]
        )
        cv2.imwrite(str(case_dir / "comparison.png"), sheet)
        overview_rows.append(sheet)
        for name, image in outputs.items():
            rows.append(
                {
                    "case_id": case_id,
                    "category": case["category"],
                    "variant": name,
                    "model_size": models[name].stat().st_size,
                    "median_ms": f"{timings[name]:.3f}",
                    "psnr_vs_hr": f"{psnr(hr, image):.3f}",
                    "ssim_vs_hr": f"{ssim(hr, image):.5f}",
                    "mad_vs_float": f"{mad(outputs['float'], image):.3f}",
                    "psnr_vs_float": f"{psnr(outputs['float'], image):.3f}",
                    "sharpness": f"{sharpness(image):.3f}",
                    "output": str(case_dir / f"{name}_512.png"),
                }
            )
    cv2.imwrite(str(out_dir / "overview.png"), np.vstack(overview_rows))
    write_csv(out_dir / "metrics.csv", rows)
    print(f"[ok] wrote {out_dir}")


if __name__ == "__main__":
    main()
