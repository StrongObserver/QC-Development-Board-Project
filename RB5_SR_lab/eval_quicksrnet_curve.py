"""Compare QuickSRNet Small/Medium/Large W8A8 TFLite assets on fixed inputs."""

from __future__ import annotations

import argparse
import csv
import time
from pathlib import Path

import cv2
import numpy as np
from ai_edge_litert.interpreter import Interpreter


def find_model(repo_root: Path, name: str) -> Path:
    candidates = {
        "small": [
            repo_root / "RB5VisionLab" / "app" / "src" / "main" / "assets" / "quicksrnetsmall_w8a8.tflite",
            repo_root / "RB5_SR_lab" / "export_assets" / "quicksrnetsmall-tflite-w8a8" / "quicksrnetsmall-tflite-w8a8" / "quicksrnetsmall.tflite",
        ],
        "medium": [
            repo_root / "RB5_SR_lab" / "export_assets" / "quicksrnetmedium-tflite-w8a8" / "quicksrnetmedium-tflite-w8a8" / "quicksrnetmedium.tflite",
        ],
        "large": [
            repo_root / "RB5_SR_lab" / "export_assets" / "quicksrnetlarge-tflite-w8a8" / "quicksrnetlarge-tflite-w8a8" / "quicksrnetlarge.tflite",
        ],
    }[name]
    for path in candidates:
        if path.exists():
            return path
    raise FileNotFoundError(name)


def fixed_inputs(repo_root: Path) -> list[tuple[str, Path]]:
    items = [
        ("flower", repo_root / "RB5_SR_lab" / "inputs" / "flower.png"),
        ("photo", repo_root / "RB5_SR_lab" / "inputs" / "photo.png"),
        ("offline_text_edge", repo_root / "project_assets" / "offline_eval" / "OFFLINE_TEXT_EDGE_20251110_055715_CPU_input_128.png"),
        ("offline_lowlight_noise", repo_root / "project_assets" / "offline_eval" / "OFFLINE_LOWLIGHT_NOISE_20251110_055715_CPU_input_128.png"),
    ]
    return [(name, path) for name, path in items if path.exists()]


def load_image(path: Path, side: int = 128) -> np.ndarray:
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        raise FileNotFoundError(path)
    if image.shape[:2] != (side, side):
        image = cv2.resize(image, (side, side), interpolation=cv2.INTER_CUBIC)
    return image


def quantize_if_needed(x: np.ndarray, tensor: dict) -> np.ndarray:
    if tensor["dtype"] == np.float32:
        return x.astype(np.float32)
    scale, zero_point = tensor["quantization"]
    info = np.iinfo(tensor["dtype"])
    return np.clip(np.round(x / scale + zero_point), info.min, info.max).astype(tensor["dtype"])


def dequantize_if_needed(y: np.ndarray, tensor: dict) -> np.ndarray:
    if tensor["dtype"] == np.float32:
        return y.astype(np.float32)
    scale, zero_point = tensor["quantization"]
    return (y.astype(np.float32) - zero_point) * scale


def run_tflite(model_path: Path, image_bgr: np.ndarray, runs: int) -> tuple[np.ndarray, float, float]:
    interpreter = Interpreter(model_path=str(model_path))
    interpreter.allocate_tensors()
    inp = interpreter.get_input_details()[0]
    out = interpreter.get_output_details()[0]
    rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    x = quantize_if_needed(rgb[None, ...], inp)
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
    return out_bgr, float(np.median(timings)), float(np.percentile(timings, 95))


def psnr(reference: np.ndarray, candidate: np.ndarray) -> float:
    mse = np.mean((reference.astype(np.float64) - candidate.astype(np.float64)) ** 2)
    return 99.0 if mse == 0 else float(10.0 * np.log10((255.0 * 255.0) / mse))


def sharpness(image: np.ndarray) -> float:
    return float(cv2.Laplacian(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY), cv2.CV_64F).var())


def panel(image: np.ndarray, title: str, width: int = 220) -> np.ndarray:
    body = cv2.resize(image, (width, width), interpolation=cv2.INTER_AREA)
    header = np.full((34, width, 3), 30, dtype=np.uint8)
    cv2.putText(header, title[:24], (8, 23), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
    return np.vstack([header, body])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", default="20260721_quicksrnet_curve")
    parser.add_argument("--runs", type=int, default=5)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    out_dir = repo_root / "RB5_SR_lab" / "results" / "quicksrnet_curve" / args.run_id
    image_dir = out_dir / "images"
    image_dir.mkdir(parents=True, exist_ok=True)
    models = [(name, find_model(repo_root, name)) for name in ["small", "medium", "large"]]
    rows: list[dict[str, object]] = []
    for case_id, input_path in fixed_inputs(repo_root):
        image = load_image(input_path)
        bicubic = cv2.resize(image, (512, 512), interpolation=cv2.INTER_CUBIC)
        outputs: dict[str, np.ndarray] = {}
        for model_name, model_path in models:
            sr, p50, p95 = run_tflite(model_path, image, args.runs)
            outputs[model_name] = sr
            cv2.imwrite(str(image_dir / f"{case_id}_{model_name}_512.png"), sr)
            rows.append(
                {
                    "case_id": case_id,
                    "model": model_name,
                    "model_path": str(model_path),
                    "model_size_bytes": model_path.stat().st_size,
                    "host_tflite_p50_ms": f"{p50:.3f}",
                    "host_tflite_p95_ms": f"{p95:.3f}",
                    "psnr_vs_bicubic": f"{psnr(bicubic, sr):.3f}",
                    "sharpness": f"{sharpness(sr):.3f}",
                    "boundary": "Host LiteRT/XNNPACK curve only; not RB5 QNN app e2e.",
                }
            )
        cv2.imwrite(
            str(image_dir / f"{case_id}_contact_sheet.png"),
            np.hstack([panel(image, "input"), panel(bicubic, "bicubic"), panel(outputs["small"], "small"), panel(outputs["medium"], "medium"), panel(outputs["large"], "large")]),
        )
    csv_path = out_dir / "metrics.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    summary = [
        "# QuickSRNet Curve Summary",
        "",
        f"- run_id: `{args.run_id}`",
        "- models: small / medium / large W8A8 TFLite",
        "- boundary: host LiteRT curve only, not RB5 app evidence",
        "",
        "## Outputs",
        "",
        f"- metrics: `{csv_path}`",
        f"- images: `{image_dir}`",
        "",
        "## Next",
        "",
        "Promote a larger QuickSRNet to Android only if contact sheets show a visible quality gain worth the app packaging and RB5 QNN e2e validation cost.",
    ]
    (out_dir / "SUMMARY.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
    print(f"[ok] wrote {out_dir}")


if __name__ == "__main__":
    main()
