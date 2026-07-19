"""Low-cost diagnostic metrics for tile SR comparison outputs.

These metrics are supporting evidence only. They help explain visual review
questions such as "which output is sharper" and "did sharpening introduce edge
or clipping risk". They are not hard gates.
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


def sharpness(image: np.ndarray) -> float:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def edge_mask(image: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # Data-driven thresholds keep this usable across dark and bright cases.
    median = float(np.median(gray))
    low = int(max(0, 0.66 * median))
    high = int(min(255, 1.33 * median + 20))
    mask = cv2.Canny(gray, low, high)
    return mask > 0


def edge_delta(reference: np.ndarray, candidate: np.ndarray) -> float:
    mask = edge_mask(reference)
    if not np.any(mask):
        return 0.0
    ref_gray = cv2.cvtColor(reference, cv2.COLOR_BGR2GRAY).astype(np.float32)
    cand_gray = cv2.cvtColor(candidate, cv2.COLOR_BGR2GRAY).astype(np.float32)
    return float(np.mean(np.abs(cand_gray[mask] - ref_gray[mask])))


def clipping_ratio(image: np.ndarray) -> float:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    clipped = (gray <= 2) | (gray >= 253)
    return float(np.mean(clipped))


def local_contrast(image: np.ndarray) -> float:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY).astype(np.float32)
    blur = cv2.GaussianBlur(gray, (0, 0), 3.0)
    return float(np.mean(np.abs(gray - blur)))


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
    parser.add_argument(
        "--run-dir",
        type=Path,
        required=True,
        help="Tile eval run directory containing cases/<case_id> outputs.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_dir = args.run_dir
    cases_dir = run_dir / "cases"
    rows: list[dict[str, object]] = []
    for case_dir in sorted(p for p in cases_dir.iterdir() if p.is_dir()):
        bicubic = read_image(case_dir / "bicubic_2048.png")
        quick = read_image(case_dir / "quicksr_tile_2048.png")
        real = read_image(case_dir / "realesrgan_tile_2048.png")

        bicubic_sharp = sharpness(bicubic)
        quick_sharp = sharpness(quick)
        real_sharp = sharpness(real)
        bicubic_contrast = local_contrast(bicubic)
        quick_contrast = local_contrast(quick)
        real_contrast = local_contrast(real)
        rows.append(
            {
                "case_id": case_dir.name,
                "sharpness_bicubic": f"{bicubic_sharp:.3f}",
                "sharpness_quicksr": f"{quick_sharp:.3f}",
                "sharpness_realesrgan": f"{real_sharp:.3f}",
                "sharpness_quicksr_over_bicubic": f"{quick_sharp / bicubic_sharp:.3f}" if bicubic_sharp > 0 else "",
                "sharpness_realesrgan_over_bicubic": f"{real_sharp / bicubic_sharp:.3f}" if bicubic_sharp > 0 else "",
                "sharpness_realesrgan_over_quicksr": f"{real_sharp / quick_sharp:.3f}" if quick_sharp > 0 else "",
                "edge_delta_quicksr_vs_bicubic": f"{edge_delta(bicubic, quick):.3f}",
                "edge_delta_realesrgan_vs_bicubic": f"{edge_delta(bicubic, real):.3f}",
                "local_contrast_bicubic": f"{bicubic_contrast:.3f}",
                "local_contrast_quicksr": f"{quick_contrast:.3f}",
                "local_contrast_realesrgan": f"{real_contrast:.3f}",
                "clipping_ratio_bicubic": f"{clipping_ratio(bicubic):.6f}",
                "clipping_ratio_quicksr": f"{clipping_ratio(quick):.6f}",
                "clipping_ratio_realesrgan": f"{clipping_ratio(real):.6f}",
                "metric_role": "diagnostic_only_not_hard_gate",
                "review_hint": "Higher sharpness may mean clearer edges or oversharpening; final decision still requires visual review.",
            }
        )
    out_path = run_dir / "diagnostic_metrics.csv"
    write_csv(out_path, rows)
    print(f"[ok] wrote {out_path}")


if __name__ == "__main__":
    main()
