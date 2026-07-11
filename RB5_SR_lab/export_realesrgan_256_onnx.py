"""Export Real-ESRGAN-General-x4v3 256x256->1024x1024 to ONNX.

This is a local fallback when AI Hub custom TFLite export is unavailable on the
current Windows machine. The exported ONNX keeps Android-friendly NHWC I/O:
  input  image          [1,256,256,3] float32 RGB [0,1]
  output upscaled_image [1,1024,1024,3] float32 RGB, unclamped
"""
import argparse
import os

import torch

from infer_realesrgan import load_model


class RealEsrganNhwcWrapper(torch.nn.Module):
    def __init__(self, model: torch.nn.Module):
        super().__init__()
        self.model = model

    def forward(self, image: torch.Tensor) -> torch.Tensor:
        # Android/TFLite-friendly NHWC -> PyTorch NCHW -> NHWC.
        x = image.permute(0, 3, 1, 2)
        y = self.model(x)
        return y.permute(0, 2, 3, 1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--weights", default="weights/realesr-general-x4v3.pth")
    parser.add_argument("--output", default="export_assets/real_esrgan_general_x4v3_256-local/real_esrgan_general_x4v3_256.onnx")
    args = parser.parse_args()

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    model = load_model(args.weights, torch.device("cpu"))
    wrapped = RealEsrganNhwcWrapper(model).eval()
    example = torch.rand(1, 256, 256, 3, dtype=torch.float32)

    torch.onnx.export(
        wrapped,
        example,
        args.output,
        input_names=["image"],
        output_names=["upscaled_image"],
        opset_version=17,
        do_constant_folding=True,
    )
    print(f"[ok] wrote {args.output}")


if __name__ == "__main__":
    main()
