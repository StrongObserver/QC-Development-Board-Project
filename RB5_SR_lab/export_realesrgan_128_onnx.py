"""Export Real-ESRGAN-General-x4v3 128x128->512x512 to ONNX."""

from __future__ import annotations

import argparse
import os

import torch

from export_realesrgan_256_onnx import RealEsrganNhwcWrapper
from infer_realesrgan import load_model


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--weights", default="RB5_SR_lab/weights/realesr-general-x4v3.pth")
    parser.add_argument(
        "--output",
        default="RB5_SR_lab/export_assets/real_esrgan_general_x4v3_128-local/real_esrgan_general_x4v3_128.onnx",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    model = load_model(args.weights, torch.device("cpu"))
    wrapped = RealEsrganNhwcWrapper(model).eval()
    example = torch.rand(1, 128, 128, 3, dtype=torch.float32)
    torch.onnx.export(
        wrapped,
        example,
        args.output,
        input_names=["image"],
        output_names=["upscaled_image"],
        opset_version=17,
        dynamo=False,
        do_constant_folding=True,
    )
    print(f"[ok] wrote {args.output}")


if __name__ == "__main__":
    main()
