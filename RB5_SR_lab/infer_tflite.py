"""
A2 local verification — run the AI Hub float TFLite on PC and compare to the
PyTorch (A1) result. Also a reference for how B3 will feed the model on Android.

TFLite I/O (from the exported model):
  input  'image'          [1,H,W,3] float32  NHWC, RGB, /255
  output 'upscaled_image' [1,4H,4W,3] float32  NHWC, RGB, [0,1]

Usage:
  python infer_tflite.py --input inputs/flower.png --tflite export_assets/.../*.tflite
"""
import argparse
import os
import time

import cv2
import numpy as np
from ai_edge_litert.interpreter import Interpreter


def run_tflite(model_path, img_bgr):
    it = Interpreter(model_path=model_path)
    it.allocate_tensors()
    inp = it.get_input_details()[0]
    out = it.get_output_details()[0]
    in_shape = list(inp["shape"])
    # BGR uint8 -> RGB float[0,1], NHWC (add batch dim)
    if in_shape[-1] == 3:
        layout = "NHWC"
        in_h, in_w = in_shape[1], in_shape[2]
    elif in_shape[1] == 3:
        layout = "NCHW"
        in_h, in_w = in_shape[2], in_shape[3]
    elif in_shape[2] == 3:
        layout = "NHCW"
        in_h, in_w = in_shape[1], in_shape[3]
    else:
        raise ValueError(f"Unsupported input shape: {in_shape}")
    if img_bgr.shape[0] != in_h or img_bgr.shape[1] != in_w:
        img_bgr = cv2.resize(img_bgr, (in_w, in_h), interpolation=cv2.INTER_CUBIC)
    rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    if layout == "NHWC":
        x = rgb[None, ...]
    elif layout == "NCHW":
        x = rgb.transpose(2, 0, 1)[None, ...]
    else:  # NHCW, produced by one local ONNX->TFLite path
        x = rgb.transpose(0, 2, 1)[None, ...]
    if inp["dtype"] != np.float32:
        scale, zero_point = inp["quantization"]
        if scale == 0:
            raise ValueError(f"quantized input has invalid scale: {inp}")
        x = np.round(x / scale + zero_point)
        x = np.clip(x, np.iinfo(inp["dtype"]).min, np.iinfo(inp["dtype"]).max).astype(inp["dtype"])
    it.set_tensor(inp["index"], x)
    t0 = time.time()
    it.invoke()
    dt = time.time() - t0
    y = it.get_tensor(out["index"])
    if out["dtype"] != np.float32:
        scale, zero_point = out["quantization"]
        if scale == 0:
            raise ValueError(f"quantized output has invalid scale: {out}")
        y = (y.astype(np.float32) - zero_point) * scale
    y = y[0]
    if y.shape[0] == 3:
        y = y.transpose(1, 2, 0)
    y_bgr = cv2.cvtColor((np.clip(y, 0, 1) * 255).round().astype(np.uint8), cv2.COLOR_RGB2BGR)
    return y_bgr, dt


def psnr(a, b):
    mse = np.mean((a.astype(np.float64) - b.astype(np.float64)) ** 2)
    return 99.0 if mse == 0 else 10 * np.log10(255 * 255 / mse)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--tflite", required=True)
    ap.add_argument("--outdir", default="results")
    ap.add_argument("--compare", help="A1 PyTorch result to compare against (optional)")
    args = ap.parse_args()

    img = cv2.imread(args.input, cv2.IMREAD_COLOR)
    out, dt = run_tflite(args.tflite, img)
    os.makedirs(args.outdir, exist_ok=True)
    base = os.path.splitext(os.path.basename(args.input))[0]
    out_path = os.path.join(args.outdir, f"{base}_tflite_x4.png")
    cv2.imwrite(out_path, out)
    bicubic = cv2.resize(img, (out.shape[1], out.shape[0]), interpolation=cv2.INTER_CUBIC)
    bicubic_path = os.path.join(args.outdir, f"{base}_bicubic_x4.png")
    cv2.imwrite(bicubic_path, bicubic)
    print(f"[ok] {args.input} -> {out_path}  ({out.shape[1]}x{out.shape[0]}, {dt*1000:.0f} ms CPU/XNNPACK)")
    print(f"[ok] wrote {bicubic_path}  (bicubic baseline for comparison)")

    if args.compare and os.path.exists(args.compare):
        ref = cv2.imread(args.compare)
        print(f"[cmp] TFLite vs PyTorch(A1) PSNR = {psnr(out, ref):.2f} dB  (>40 ≈ effectively identical)")


if __name__ == "__main__":
    main()
