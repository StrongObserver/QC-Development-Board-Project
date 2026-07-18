"""Prepare TextZoom test splits for EvalHub.

TextZoom is stored as LMDB with keys like:

``image_lr-000000001``
``image_hr-000000001``
``label-000000001``

This script extracts the test easy/medium/hard splits into a derived manifest
compatible with the current RB5 SR harness, while preserving text labels.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import lmdb
import numpy as np

from evalhub_common import DATA_ROOT, write_csv


TEXTZOOM_ROOT = DATA_ROOT / "raw" / "textzoom" / "已加速- textzoom"
OUT_ROOT = DATA_ROOT / "derived" / "textzoom_test_128x4_v1"
SPLITS = ["easy", "medium", "hard"]


def decode_image(data: bytes):
    arr = np.frombuffer(data, dtype=np.uint8)
    image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("unreadable image bytes")
    return image


def center_crop_or_resize(image, width: int, height: int):
    h, w = image.shape[:2]
    if h < height or w < width:
        scale = max(height / h, width / w)
        new_w = int(round(w * scale))
        new_h = int(round(h * scale))
        image = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
        h, w = image.shape[:2]
    x0 = max(0, (w - width) // 2)
    y0 = max(0, (h - height) // 2)
    return image[y0:y0 + height, x0:x0 + width]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=TEXTZOOM_ROOT)
    parser.add_argument("--limit-per-split", type=int, default=0, help="Optional limit for smoke/debug generation.")
    parser.add_argument("--splits", nargs="*", default=SPLITS, choices=SPLITS)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rows: list[dict[str, str]] = []
    for split in args.splits:
        lmdb_dir = args.root / "test" / split
        if not lmdb_dir.exists():
            raise FileNotFoundError(lmdb_dir)
        env = lmdb.open(str(lmdb_dir), readonly=True, lock=False, readahead=False)
        with env.begin() as txn:
            raw_count = txn.get(b"num-samples")
            if raw_count is None:
                raise ValueError(f"missing num-samples in {lmdb_dir}")
            count = int(raw_count.decode("ascii"))
            if args.limit_per_split:
                count = min(count, args.limit_per_split)
            for index in range(1, count + 1):
                key = f"{index:09d}"
                lr_bytes = txn.get(f"image_lr-{key}".encode("ascii"))
                hr_bytes = txn.get(f"image_hr-{key}".encode("ascii"))
                label_bytes = txn.get(f"label-{key}".encode("ascii"))
                if lr_bytes is None or hr_bytes is None:
                    continue
                lr_full = decode_image(lr_bytes)
                hr_full = decode_image(hr_bytes)
                label = label_bytes.decode("utf-8", "replace") if label_bytes else ""

                lr = center_crop_or_resize(lr_full, 128, 128)
                hr = center_crop_or_resize(hr_full, 512, 512)
                bicubic = cv2.resize(lr, (512, 512), interpolation=cv2.INTER_CUBIC)

                case_id = f"textzoom_{split}_{index:06d}"
                case_dir = OUT_ROOT / "cases" / split / case_id
                case_dir.mkdir(parents=True, exist_ok=True)
                lr_path = case_dir / "lr_128.png"
                bicubic_path = case_dir / "bicubic_512.png"
                hr_path = case_dir / "hr_512.png"
                cv2.imwrite(str(lr_path), lr)
                cv2.imwrite(str(bicubic_path), bicubic)
                cv2.imwrite(str(hr_path), hr)
                rows.append({
                    "case_id": case_id,
                    "category": f"textzoom_{split}",
                    "dataset": "TextZoom",
                    "source_id": f"{split}_{index:09d}",
                    "lr_128": str(lr_path),
                    "bicubic_512": str(bicubic_path),
                    "hr_512": str(hr_path),
                    "text_label": label,
                    "source_lmdb": str(lmdb_dir),
                    "selection_reason": "TextZoom real scene text SR test pair, resized/cropped to current RB5 harness shape",
                })

    manifest = OUT_ROOT / "manifest.csv"
    write_csv(manifest, rows)
    (OUT_ROOT / "README.md").write_text(
        "\n".join([
            "# TextZoom Test EvalHub Extension",
            "",
            f"Source root: `{args.root}`",
            "",
            "This is a text-fidelity SR layer derived from TextZoom test splits.",
            "It does not replace `RB5_SR_Benchmark_v1`.",
            "",
            "Each case contains `lr_128.png`, `bicubic_512.png`, and `hr_512.png`.",
            "The manifest also keeps `text_label` for future OCR/readability checks.",
            "",
            f"Manifest: `{manifest}`",
            "",
        ]),
        encoding="utf-8",
    )
    print(f"[ok] wrote {manifest}")
    print(f"[ok] cases={len(rows)}")
    for split in args.splits:
        print(f"{split}: {sum(1 for row in rows if row['category'] == 'textzoom_' + split)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

