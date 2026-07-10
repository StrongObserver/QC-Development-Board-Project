"""
A2 local verification — run the AI Hub float TFLite on PC and compare to the
PyTorch (A1) result. Also a reference for how B3 will feed the model on Android.

TFLite I/O (from the exported model):
  input  'image'          [1,128,128,3] float32  NHWC, RGB, /255
  output 'upscaled_image' [1,512,512,3] float32  NHWC, RGB, [0,1]

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
    # BGR uint8 -> RGB float[0,1], NHWC (add batch dim)
    rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    x = rgb[None, ...]  # [1,H,W,3]
    it.set_tensor(inp["index"], x)
    t0 = time.time()
    it.invoke()
    dt = time.time() - t0
    y = it.get_tensor(out["index"])[0]  # [512,512,3] RGB [0,1]
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
    print(f"[ok] {args.input} -> {out_path}  ({out.shape[1]}x{out.shape[0]}, {dt*1000:.0f} ms CPU/XNNPACK)")

    if args.compare and os.path.exists(args.compare):
        ref = cv2.imread(args.compare)
        print(f"[cmp] TFLite vs PyTorch(A1) PSNR = {psnr(out, ref):.2f} dB  (>40 ≈ effectively identical)")


if __name__ == "__main__":
    main()
