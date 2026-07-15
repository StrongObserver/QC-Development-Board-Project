"""Convert Real-ESRGAN QNN uint8 raw output to PNG."""

from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np


OUTPUT_SCALE = 0.005237185396254063
OUTPUT_ZERO_POINT = 25


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("raw_path", type=Path)
    parser.add_argument("--out", type=Path, default=Path("upscaled.png"))
    args = parser.parse_args()

    raw = np.fromfile(args.raw_path, dtype=np.uint8)
    expected = 1 * 512 * 512 * 3
    if raw.size != expected:
        raise SystemExit(f"expected {expected} bytes, got {raw.size}: {args.raw_path}")

    y = raw.reshape(1, 512, 512, 3)[0]
    image = np.clip((y.astype(np.float32) - OUTPUT_ZERO_POINT) * OUTPUT_SCALE, 0.0, 1.0)
    rgb = (image * 255.0 + 0.5).astype(np.uint8)
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(args.out), bgr)
    print(f"[ok] wrote {args.out}")


if __name__ == "__main__":
    main()
