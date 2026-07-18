"""Prepare a small Set14 128->512 EvalHub extension.

This does not modify RB5_SR_Benchmark_v1. It creates a derived dataset under
``evalhub_data/derived/set14_128x4_v1`` with the same image triplet shape:

``lr_128.png | bicubic_512.png | hr_512.png``
"""

from __future__ import annotations

import csv
import tarfile
from pathlib import Path

import cv2

from evalhub_common import DATA_ROOT, write_csv


SET14_ROOT = DATA_ROOT / "raw" / "set14_hf"
TAR_PATH = SET14_ROOT / "archives" / "Set14_HR.tar.gz"
EXTRACT_DIR = SET14_ROOT / "hr"
OUT_ROOT = DATA_ROOT / "derived" / "set14_128x4_v1"


def ensure_extracted() -> Path:
    if not TAR_PATH.exists():
        raise FileNotFoundError(f"Missing {TAR_PATH}. Run fetch_evalhub_sources.py --dataset set14_hf --extract")
    marker = EXTRACT_DIR / ".extracted"
    if not marker.exists():
        EXTRACT_DIR.mkdir(parents=True, exist_ok=True)
        with tarfile.open(TAR_PATH, "r:gz") as tf:
            tf.extractall(EXTRACT_DIR)
        marker.write_text(f"source={TAR_PATH.name}\n", encoding="utf-8")
    pngs = sorted(EXTRACT_DIR.rglob("*.png"))
    if not pngs:
        raise FileNotFoundError(f"No PNG images under {EXTRACT_DIR}")
    return EXTRACT_DIR


def center_crop_512(image):
    height, width = image.shape[:2]
    if height < 512 or width < 512:
        scale = max(512 / height, 512 / width)
        new_w = int(round(width * scale))
        new_h = int(round(height * scale))
        image = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
        height, width = image.shape[:2]
    x0 = max(0, (width - 512) // 2)
    y0 = max(0, (height - 512) // 2)
    return image[y0:y0 + 512, x0:x0 + 512]


def main() -> int:
    ensure_extracted()
    rows: list[dict[str, str]] = []
    for index, image_path in enumerate(sorted(EXTRACT_DIR.rglob("*.png")), start=1):
        image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
        if image is None:
            continue
        hr = center_crop_512(image)
        lr = cv2.resize(hr, (128, 128), interpolation=cv2.INTER_CUBIC)
        bicubic = cv2.resize(lr, (512, 512), interpolation=cv2.INTER_CUBIC)

        case_id = f"set14_{image_path.stem.lower()}"
        case_dir = OUT_ROOT / "cases" / "set14_standard" / case_id
        case_dir.mkdir(parents=True, exist_ok=True)
        lr_path = case_dir / "lr_128.png"
        bicubic_path = case_dir / "bicubic_512.png"
        hr_path = case_dir / "hr_512.png"
        cv2.imwrite(str(lr_path), lr)
        cv2.imwrite(str(bicubic_path), bicubic)
        cv2.imwrite(str(hr_path), hr)
        rows.append({
            "case_id": case_id,
            "category": "set14_standard",
            "dataset": "Set14",
            "source_id": image_path.stem,
            "lr_128": str(lr_path),
            "bicubic_512": str(bicubic_path),
            "hr_512": str(hr_path),
            "source_hr": str(image_path),
            "selection_reason": "standard Set14 image center-cropped/resized to current RB5 128->512 harness shape",
        })

    manifest = OUT_ROOT / "manifest.csv"
    write_csv(manifest, rows)
    readme = OUT_ROOT / "README.md"
    readme.write_text(
        "\n".join([
            "# Set14 128x4 EvalHub Extension",
            "",
            "Derived from Set14 HR images downloaded from Hugging Face.",
            "",
            "This is a small standard-SR sanity layer. It does not replace",
            "`C:\\Users\\Admin\\Videos\\RB5 gen2\\RB5_SR_Benchmark_v1`.",
            "",
            "Each case contains:",
            "",
            "```text",
            "lr_128.png",
            "bicubic_512.png",
            "hr_512.png",
            "```",
            "",
            f"Manifest: `{manifest}`",
            "",
        ]),
        encoding="utf-8",
    )
    print(f"[ok] wrote {manifest}")
    print(f"[ok] cases={len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

