"""Verify local Real-ESRGAN PyTorch source against exported ONNX."""

from __future__ import annotations

import argparse
import csv
import os
import time
from pathlib import Path

import cv2
import numpy as np
import onnxruntime as ort
import torch

from export_realesrgan_256_onnx import RealEsrganNhwcWrapper
from infer_realesrgan import load_model


def psnr(a: np.ndarray, b: np.ndarray) -> float:
    mse = np.mean((a.astype(np.float64) - b.astype(np.float64)) ** 2)
    return 99.0 if mse == 0 else float(10 * np.log10(255 * 255 / mse))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def load_input(path: str, side: int) -> tuple[np.ndarray, np.ndarray]:
    bgr = cv2.imread(path, cv2.IMREAD_COLOR)
    if bgr is None:
        raise FileNotFoundError(path)
    if bgr.shape[:2] != (side, side):
        bgr = cv2.resize(bgr, (side, side), interpolation=cv2.INTER_CUBIC)
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    return bgr, rgb[None, ...]


def tensor_to_bgr(y: np.ndarray) -> np.ndarray:
    y = np.clip(y[0], 0.0, 1.0)
    return cv2.cvtColor((y * 255.0).round().astype(np.uint8), cv2.COLOR_RGB2BGR)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--onnx", required=True)
    parser.add_argument("--input", default="RB5_SR_lab/inputs/flower.png")
    parser.add_argument("--weights", default="RB5_SR_lab/weights/realesr-general-x4v3.pth")
    parser.add_argument("--side", type=int, default=128)
    parser.add_argument("--outdir", default="RB5_SR_lab/results/onnx_fp_source_check/20260721_realesrgan128")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = Path(args.outdir)
    out_dir.mkdir(parents=True, exist_ok=True)
    input_bgr, x = load_input(args.input, args.side)

    model = RealEsrganNhwcWrapper(load_model(args.weights, torch.device("cpu"))).eval()
    with torch.no_grad():
        t0 = time.time()
        torch_out = model(torch.from_numpy(x)).numpy()
        torch_ms = (time.time() - t0) * 1000.0

    session = ort.InferenceSession(args.onnx, providers=["CPUExecutionProvider"])
    input_name = session.get_inputs()[0].name
    t1 = time.time()
    onnx_out = session.run(None, {input_name: x})[0]
    onnx_ms = (time.time() - t1) * 1000.0

    torch_bgr = tensor_to_bgr(torch_out)
    onnx_bgr = tensor_to_bgr(onnx_out)
    bicubic = cv2.resize(input_bgr, (args.side * 4, args.side * 4), interpolation=cv2.INTER_CUBIC)
    cv2.imwrite(str(out_dir / "input_128.png"), input_bgr)
    cv2.imwrite(str(out_dir / "bicubic_512.png"), bicubic)
    cv2.imwrite(str(out_dir / "torch_512.png"), torch_bgr)
    cv2.imwrite(str(out_dir / "onnx_512.png"), onnx_bgr)
    sheet = np.hstack([bicubic, torch_bgr, onnx_bgr])
    cv2.imwrite(str(out_dir / "contact_sheet.png"), sheet)

    mad = float(np.mean(np.abs(torch_bgr.astype(np.float32) - onnx_bgr.astype(np.float32))))
    max_abs = float(np.max(np.abs(torch_out.astype(np.float32) - onnx_out.astype(np.float32))))
    rows = [
        {
            "input": args.input,
            "onnx": args.onnx,
            "side": args.side,
            "torch_ms": f"{torch_ms:.3f}",
            "onnx_ms": f"{onnx_ms:.3f}",
            "psnr_torch_vs_onnx": f"{psnr(torch_bgr, onnx_bgr):.3f}",
            "mad_torch_vs_onnx": f"{mad:.6f}",
            "max_abs_float": f"{max_abs:.8f}",
        }
    ]
    write_csv(out_dir / "metrics.csv", rows)
    summary = [
        "# Real-ESRGAN ONNX FP Source Check",
        "",
        f"- input: `{args.input}`",
        f"- onnx: `{args.onnx}`",
        f"- torch vs onnx PSNR: `{rows[0]['psnr_torch_vs_onnx']}` dB",
        f"- torch vs onnx MAD: `{rows[0]['mad_torch_vs_onnx']}`",
        f"- max abs float diff: `{rows[0]['max_abs_float']}`",
        "",
        "## Boundary",
        "",
        "This validates that the local PyTorch source model can export to ONNX consistently. It does not run AIMET yet and does not change Android assets.",
    ]
    (out_dir / "SUMMARY.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
    print(f"[ok] wrote {out_dir}")
    print(f"[cmp] PSNR={rows[0]['psnr_torch_vs_onnx']}dB MAD={rows[0]['mad_torch_vs_onnx']} max_abs={rows[0]['max_abs_float']}")


if __name__ == "__main__":
    main()
