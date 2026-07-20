"""Run an AIMET-Torch CLE feasibility probe for Real-ESRGAN SRVGG."""

from __future__ import annotations

import argparse
import csv
import os
import time
from pathlib import Path

import cv2
import numpy as np
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


def load_input(path: str, side: int) -> tuple[np.ndarray, torch.Tensor]:
    bgr = cv2.imread(path, cv2.IMREAD_COLOR)
    if bgr is None:
        raise FileNotFoundError(path)
    if bgr.shape[:2] != (side, side):
        bgr = cv2.resize(bgr, (side, side), interpolation=cv2.INTER_CUBIC)
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    tensor = torch.from_numpy(rgb).permute(2, 0, 1).unsqueeze(0)
    return bgr, tensor


def tensor_to_bgr(y: torch.Tensor) -> np.ndarray:
    arr = y.detach().clamp(0, 1).squeeze(0).permute(1, 2, 0).cpu().numpy()
    return cv2.cvtColor((arr * 255.0).round().astype(np.uint8), cv2.COLOR_RGB2BGR)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--weights", default="RB5_SR_lab/weights/realesr-general-x4v3.pth")
    parser.add_argument("--input", default="RB5_SR_lab/inputs/flower.png")
    parser.add_argument("--side", type=int, default=128)
    parser.add_argument("--outdir", default="RB5_SR_lab/results/aimet_torch_cle_probe/20260721_realesrgan128_flower")
    return parser.parse_args()


def export_onnx(model: torch.nn.Module, output_path: Path, side: int) -> None:
    wrapped = RealEsrganNhwcWrapper(model).eval()
    example = torch.rand(1, side, side, 3, dtype=torch.float32)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    torch.onnx.export(
        wrapped,
        example,
        str(output_path),
        input_names=["image"],
        output_names=["upscaled_image"],
        opset_version=17,
        dynamo=False,
        do_constant_folding=True,
    )


def main() -> None:
    # AIMET import on Windows needs UTF-8 mode because torch inductor templates
    # may contain non-GBK bytes even when we only use CPU-side CLE.
    os.environ.setdefault("PYTHONUTF8", "1")
    from aimet_torch.cross_layer_equalization import equalize_model

    args = parse_args()
    out_dir = Path(args.outdir)
    out_dir.mkdir(parents=True, exist_ok=True)

    input_bgr, x = load_input(args.input, args.side)
    model = load_model(args.weights, torch.device("cpu")).eval()

    with torch.no_grad():
        t0 = time.time()
        before = model(x)
        before_ms = (time.time() - t0) * 1000.0

    t_cle0 = time.time()
    equalize_model(model, dummy_input=torch.rand(1, 3, args.side, args.side))
    cle_ms = (time.time() - t_cle0) * 1000.0

    with torch.no_grad():
        t1 = time.time()
        after = model(x)
        after_ms = (time.time() - t1) * 1000.0

    before_bgr = tensor_to_bgr(before)
    after_bgr = tensor_to_bgr(after)
    bicubic = cv2.resize(input_bgr, (args.side * 4, args.side * 4), interpolation=cv2.INTER_CUBIC)
    cv2.imwrite(str(out_dir / "input_128.png"), input_bgr)
    cv2.imwrite(str(out_dir / "bicubic_512.png"), bicubic)
    cv2.imwrite(str(out_dir / "torch_before_cle_512.png"), before_bgr)
    cv2.imwrite(str(out_dir / "torch_after_cle_512.png"), after_bgr)
    cv2.imwrite(str(out_dir / "contact_sheet.png"), np.hstack([bicubic, before_bgr, after_bgr]))

    max_abs = float(torch.max(torch.abs(before - after)).item())
    mad = float(np.mean(np.abs(before_bgr.astype(np.float32) - after_bgr.astype(np.float32))))
    rows = [
        {
            "input": args.input,
            "side": args.side,
            "cle_ms": f"{cle_ms:.3f}",
            "before_ms": f"{before_ms:.3f}",
            "after_ms": f"{after_ms:.3f}",
            "psnr_before_after": f"{psnr(before_bgr, after_bgr):.3f}",
            "mad_before_after": f"{mad:.6f}",
            "max_abs_float_before_after": f"{max_abs:.8f}",
        }
    ]
    write_csv(out_dir / "metrics.csv", rows)

    state_path = out_dir / "cle_state_dict.pt"
    torch.save(model.state_dict(), state_path)
    export_onnx(model, out_dir / "real_esrgan_general_x4v3_128_cle.onnx", args.side)

    summary = [
        "# AIMET-Torch CLE Probe Summary",
        "",
        f"- input: `{args.input}`",
        f"- status: `{'passed' if max_abs < 1e-3 else 'changed_output_review_required'}`",
        f"- CLE runtime: `{rows[0]['cle_ms']}` ms",
        f"- before/after PSNR: `{rows[0]['psnr_before_after']}` dB",
        f"- before/after MAD: `{rows[0]['mad_before_after']}`",
        f"- max abs float diff: `{rows[0]['max_abs_float_before_after']}`",
        f"- CLE state dict: `{state_path}`",
        f"- CLE ONNX: `{out_dir / 'real_esrgan_general_x4v3_128_cle.onnx'}`",
        "",
        "## Boundary",
        "",
        "This proves AIMET-Torch CLE can run on the local PyTorch FP source model. It does not prove W8A8 recovery yet and does not replace Android assets.",
    ]
    (out_dir / "SUMMARY.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
    print(f"[ok] wrote {out_dir}")
    print(f"[cmp] PSNR={rows[0]['psnr_before_after']}dB MAD={rows[0]['mad_before_after']} max_abs={rows[0]['max_abs_float_before_after']}")


if __name__ == "__main__":
    main()
