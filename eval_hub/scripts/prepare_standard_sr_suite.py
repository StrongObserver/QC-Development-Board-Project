"""Prepare a standard SR x4 EvalHub extension from SelfExSR assets.

This script reuses the local `SelfExSR-master.zip` that already contains
Set5, Set14, BSD100, and Urban100 x4 LR/HR pairs. It creates a derived manifest
with the same shape used by the current RB5 harness:

``lr_128.png | bicubic_512.png | hr_512.png``

It does not modify RB5_SR_Benchmark_v1.
"""

from __future__ import annotations

import argparse
import zipfile
from pathlib import Path

import cv2

from evalhub_common import DATA_ROOT, write_csv


DEFAULT_ZIP = Path(r"C:\Users\Admin\Videos\RB5 gen2\SelfExSR-master.zip")
OUT_ROOT = DATA_ROOT / "derived" / "standard_sr_x4_v1"
DATASETS = ["Set5", "Set14", "BSD100", "Urban100"]


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


def read_zip_image(zf: zipfile.ZipFile, name: str):
    data = zf.read(name)
    import numpy as np

    arr = np.frombuffer(data, dtype=np.uint8)
    image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"unreadable image in zip: {name}")
    return image


def collect_pairs(zf: zipfile.ZipFile) -> list[tuple[str, str, str]]:
    names = {entry.filename for entry in zf.infolist() if entry.filename.endswith(".png")}
    pairs: list[tuple[str, str, str]] = []
    for dataset in DATASETS:
        prefix = f"SelfExSR-master/data/{dataset}/image_SRF_4/"
        hrs = sorted(name for name in names if name.startswith(prefix) and name.endswith("_HR.png"))
        for hr_name in hrs:
            lr_name = hr_name.replace("_HR.png", "_LR.png")
            if lr_name in names:
                pairs.append((dataset, lr_name, hr_name))
    return pairs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--zip", type=Path, default=DEFAULT_ZIP)
    parser.add_argument("--limit-per-dataset", type=int, default=0, help="Optional limit for smoke/debug generation.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.zip.exists():
        raise FileNotFoundError(args.zip)

    rows: list[dict[str, str]] = []
    with zipfile.ZipFile(args.zip) as zf:
        pairs = collect_pairs(zf)
        per_dataset_count: dict[str, int] = {}
        for dataset, lr_name, hr_name in pairs:
            count = per_dataset_count.get(dataset, 0)
            if args.limit_per_dataset and count >= args.limit_per_dataset:
                continue
            per_dataset_count[dataset] = count + 1

            lr_full = read_zip_image(zf, lr_name)
            hr_full = read_zip_image(zf, hr_name)
            lr = center_crop_or_resize(lr_full, 128, 128)
            hr = center_crop_or_resize(hr_full, 512, 512)
            bicubic = cv2.resize(lr, (512, 512), interpolation=cv2.INTER_CUBIC)

            source_id = Path(hr_name).stem.replace("_SRF_4_HR", "")
            case_id = f"{dataset.lower()}_{source_id.lower()}"
            case_dir = OUT_ROOT / "cases" / dataset.lower() / case_id
            case_dir.mkdir(parents=True, exist_ok=True)
            lr_path = case_dir / "lr_128.png"
            bicubic_path = case_dir / "bicubic_512.png"
            hr_path = case_dir / "hr_512.png"
            cv2.imwrite(str(lr_path), lr)
            cv2.imwrite(str(bicubic_path), bicubic)
            cv2.imwrite(str(hr_path), hr)
            rows.append({
                "case_id": case_id,
                "category": f"standard_{dataset.lower()}",
                "dataset": dataset,
                "source_id": source_id,
                "lr_128": str(lr_path),
                "bicubic_512": str(bicubic_path),
                "hr_512": str(hr_path),
                "source_lr": lr_name,
                "source_hr": hr_name,
                "selection_reason": "standard SR x4 LR/HR pair from SelfExSR, center-cropped/resized to current RB5 harness shape",
            })

    manifest = OUT_ROOT / "manifest.csv"
    write_csv(manifest, rows)
    (OUT_ROOT / "README.md").write_text(
        "\n".join([
            "# Standard SR x4 EvalHub Extension",
            "",
            "Derived from local SelfExSR-master.zip.",
            "",
            "Datasets included:",
            "- Set5",
            "- Set14",
            "- BSD100",
            "- Urban100",
            "",
            "Each case contains `lr_128.png`, `bicubic_512.png`, and `hr_512.png`.",
            "",
            "This is a broader standard SR sanity layer. It does not replace",
            "`C:\\Users\\Admin\\Videos\\RB5 gen2\\RB5_SR_Benchmark_v1`.",
            "",
            f"Manifest: `{manifest}`",
            "",
        ]),
        encoding="utf-8",
    )
    print(f"[ok] wrote {manifest}")
    print(f"[ok] cases={len(rows)}")
    for dataset in DATASETS:
        print(f"{dataset}: {sum(1 for row in rows if row['dataset'] == dataset)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

