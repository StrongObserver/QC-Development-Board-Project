"""Create a lightweight CSIQ manifest without extracting image archives."""

from __future__ import annotations

import zipfile
from pathlib import Path

from evalhub_common import DATA_ROOT, write_csv


CSIQ_ROOT = DATA_ROOT / "raw" / "csiq"
ARCHIVES = CSIQ_ROOT / "archives"


def zip_count(path: Path) -> int:
    if not path.exists():
        return 0
    with zipfile.ZipFile(path) as zf:
        return len([name for name in zf.namelist() if not name.endswith("/")])


def main() -> int:
    src_zip = ARCHIVES / "src_imgs.zip"
    dst_zip = ARCHIVES / "dst_imgs.zip"
    dmos = ARCHIVES / "csiq.DMOS.xlsx"
    rows = [
        {
            "dataset_id": "csiq",
            "component": "source_images",
            "path": str(src_zip),
            "present": "yes" if src_zip.exists() else "no",
            "bytes": str(src_zip.stat().st_size) if src_zip.exists() else "",
            "file_count_in_zip": str(zip_count(src_zip)),
            "use": "reference images for IQA metric sanity",
        },
        {
            "dataset_id": "csiq",
            "component": "distorted_images",
            "path": str(dst_zip),
            "present": "yes" if dst_zip.exists() else "no",
            "bytes": str(dst_zip.stat().st_size) if dst_zip.exists() else "",
            "file_count_in_zip": str(zip_count(dst_zip)),
            "use": "distorted images for IQA metric sanity",
        },
        {
            "dataset_id": "csiq",
            "component": "dmos",
            "path": str(dmos),
            "present": "yes" if dmos.exists() else "no",
            "bytes": str(dmos.stat().st_size) if dmos.exists() else "",
            "file_count_in_zip": "",
            "use": "subjective quality labels",
        },
    ]
    out = DATA_ROOT / "manifests" / "csiq_manifest.csv"
    write_csv(out, rows)
    print(f"[ok] wrote {out}")
    for row in rows:
        print(f"{row['component']}: present={row['present']} bytes={row['bytes']} files={row['file_count_in_zip']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

