"""Create zoom-friendly review packs for tile SR outputs.

The default overview sheets shrink 2048x2048 outputs too much. This script
creates 1:1 crops, 2x crops, small patch zooms, and difference maps so visual
review does not depend on laptop zoom limits.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import cv2
import numpy as np


def read_image(path: Path) -> np.ndarray:
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        raise FileNotFoundError(path)
    return image


def panel(image: np.ndarray, title: str, width: int | None = None) -> np.ndarray:
    body = image if width is None else cv2.resize(image, (width, width), interpolation=cv2.INTER_NEAREST)
    header = np.full((42, body.shape[1], 3), 25, dtype=np.uint8)
    cv2.putText(header, title[:50], (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (255, 255, 255), 1, cv2.LINE_AA)
    return np.vstack([header, body])


def crop_center(image: np.ndarray, size: int) -> np.ndarray:
    h, w = image.shape[:2]
    size = min(size, h, w)
    y = max(0, h // 2 - size // 2)
    x = max(0, w // 2 - size // 2)
    return image[y : y + size, x : x + size]


def crop_quadrant_detail(image: np.ndarray, size: int) -> np.ndarray:
    h, w = image.shape[:2]
    # Slightly above center usually catches structure in the current benchmark crops.
    cx = w // 2
    cy = h // 2 - h // 8
    half = size // 2
    x0 = max(0, min(w - size, cx - half))
    y0 = max(0, min(h - size, cy - half))
    return image[y0 : y0 + size, x0 : x0 + size]


def diff_heatmap(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    diff = np.mean(np.abs(a.astype(np.float32) - b.astype(np.float32)), axis=2)
    norm = np.clip(diff * 8.0, 0, 255).astype(np.uint8)
    return cv2.applyColorMap(norm, cv2.COLORMAP_TURBO)


def color_stats(image: np.ndarray) -> dict[str, float]:
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    bgr_mean = np.mean(image.reshape(-1, 3), axis=0)
    return {
        "mean_b": float(bgr_mean[0]),
        "mean_g": float(bgr_mean[1]),
        "mean_r": float(bgr_mean[2]),
        "mean_luma": float(np.mean(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY))),
        "mean_saturation": float(np.mean(hsv[:, :, 1])),
        "std": float(np.std(image)),
    }


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--case-id", default="low_light_div2k0852")
    parser.add_argument("--crop-size", type=int, default=512)
    parser.add_argument("--patch-size", type=int, default=192)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    case_dir = args.run_dir / "cases" / args.case_id
    out_dir = args.run_dir / "review_packs" / args.case_id
    out_dir.mkdir(parents=True, exist_ok=True)

    input_img = read_image(case_dir / "input_512.png")
    bicubic = read_image(case_dir / "bicubic_2048.png")
    quick = read_image(case_dir / "quicksr_tile_2048.png")
    real = read_image(case_dir / "realesrgan_tile_2048.png")

    center_images = [
        ("Input 512", cv2.resize(input_img, (args.crop_size, args.crop_size), interpolation=cv2.INTER_CUBIC)),
        ("Bicubic 1:1", crop_center(bicubic, args.crop_size)),
        ("QuickSR 1:1", crop_center(quick, args.crop_size)),
        ("RealESRGAN 1:1", crop_center(real, args.crop_size)),
    ]
    center_sheet = np.hstack([panel(img, title) for title, img in center_images])
    cv2.imwrite(str(out_dir / "center_crop_1x.png"), center_sheet)

    center_2x = np.hstack([panel(img, title + " 2x", width=args.crop_size * 2) for title, img in center_images[1:]])
    cv2.imwrite(str(out_dir / "center_crop_2x.png"), center_2x)

    patch_images = [
        ("Bicubic patch", crop_quadrant_detail(bicubic, args.patch_size)),
        ("QuickSR patch", crop_quadrant_detail(quick, args.patch_size)),
        ("RealESRGAN patch", crop_quadrant_detail(real, args.patch_size)),
    ]
    patch_sheet = np.hstack([panel(img, title, width=args.patch_size * 4) for title, img in patch_images])
    cv2.imwrite(str(out_dir / "detail_patch_4x.png"), patch_sheet)

    quick_real_diff = diff_heatmap(quick, real)
    bicubic_quick_diff = diff_heatmap(bicubic, quick)
    bicubic_real_diff = diff_heatmap(bicubic, real)
    diff_sheet = np.hstack(
        [
            panel(crop_center(bicubic_quick_diff, args.crop_size), "Diff Bicubic vs QuickSR"),
            panel(crop_center(bicubic_real_diff, args.crop_size), "Diff Bicubic vs RealESRGAN"),
            panel(crop_center(quick_real_diff, args.crop_size), "Diff QuickSR vs RealESRGAN"),
        ]
    )
    cv2.imwrite(str(out_dir / "difference_heatmaps.png"), diff_sheet)

    rows = []
    for name, image in [
        ("input", input_img),
        ("bicubic", bicubic),
        ("quicksr", quick),
        ("realesrgan", real),
    ]:
        stats = color_stats(image)
        stats["image"] = name
        rows.append(stats)
    write_csv(out_dir / "color_stats.csv", rows)
    print(f"[ok] wrote {out_dir}")


if __name__ == "__main__":
    main()
