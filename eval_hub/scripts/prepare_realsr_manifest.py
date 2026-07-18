"""Prepare a RealSR V3 x4 EvalHub extension from the downloaded tarball.

The script uses the Test/4 split from RealSR(V3). It extracts only x4 test
pairs into EvalHub's derived area and creates project-compatible
`lr_128.png | bicubic_512.png | hr_512.png` triplets.

This derived layer is for real-degradation SR evaluation. It does not replace
RB5_SR_Benchmark_v1.
"""

from __future__ import annotations

import argparse
import re
import tarfile
from pathlib import Path

import cv2
import numpy as np

from evalhub_common import DATA_ROOT, write_csv


REALSR_ROOT = DATA_ROOT / "raw" / "realsr"
OUT_ROOT = DATA_ROOT / "derived" / "realsr_v3_x4_test_128x4_v1"
FILE_RE = re.compile(r"^(Canon|Nikon)_(\d+)_(HR|LR4)\.png$")


def find_tar(root: Path) -> Path:
    candidates = sorted(root.glob("*.tar.gz"))
    if not candidates:
        raise FileNotFoundError(f"No .tar.gz file under {root}")
    return candidates[0]


def read_tar_image(tf: tarfile.TarFile, member_name: str):
    member = tf.getmember(member_name)
    with tf.extractfile(member) as f:
        if f is None:
            raise FileNotFoundError(member_name)
        data = np.frombuffer(f.read(), dtype=np.uint8)
    image = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"unreadable image in tar: {member_name}")
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


def collect_pairs(tf: tarfile.TarFile) -> dict[tuple[str, str], dict[str, str]]:
    pairs: dict[tuple[str, str], dict[str, str]] = {}
    for member in tf.getmembers():
        if not member.isfile():
            continue
        parts = member.name.split("/")
        if len(parts) != 5 or parts[0] != "RealSR(V3)" or parts[2] != "Test" or parts[3] != "4":
            continue
        camera_dir = parts[1]
        match = FILE_RE.match(parts[4])
        if not match:
            continue
        camera, scene_id, kind = match.groups()
        if camera != camera_dir:
            continue
        key = (camera, scene_id)
        pairs.setdefault(key, {})[kind] = member.name
    return {key: value for key, value in pairs.items() if "HR" in value and "LR4" in value}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tar", type=Path, default=None)
    parser.add_argument("--limit", type=int, default=0, help="Optional limit for smoke/debug generation.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    tar_path = args.tar or find_tar(REALSR_ROOT)
    rows: list[dict[str, str]] = []
    with tarfile.open(tar_path, "r:gz") as tf:
        pairs = collect_pairs(tf)
        for index, ((camera, scene_id), files) in enumerate(sorted(pairs.items()), start=1):
            if args.limit and len(rows) >= args.limit:
                break
            lr_full = read_tar_image(tf, files["LR4"])
            hr_full = read_tar_image(tf, files["HR"])
            lr = center_crop_or_resize(lr_full, 128, 128)
            hr = center_crop_or_resize(hr_full, 512, 512)
            bicubic = cv2.resize(lr, (512, 512), interpolation=cv2.INTER_CUBIC)

            case_id = f"realsr_v3_{camera.lower()}_{scene_id}"
            case_dir = OUT_ROOT / "cases" / camera.lower() / case_id
            case_dir.mkdir(parents=True, exist_ok=True)
            lr_path = case_dir / "lr_128.png"
            bicubic_path = case_dir / "bicubic_512.png"
            hr_path = case_dir / "hr_512.png"
            cv2.imwrite(str(lr_path), lr)
            cv2.imwrite(str(bicubic_path), bicubic)
            cv2.imwrite(str(hr_path), hr)
            rows.append({
                "case_id": case_id,
                "category": f"realsr_{camera.lower()}",
                "dataset": "RealSR_V3_x4_Test",
                "source_id": f"{camera}_{scene_id}",
                "lr_128": str(lr_path),
                "bicubic_512": str(bicubic_path),
                "hr_512": str(hr_path),
                "source_lr": files["LR4"],
                "source_hr": files["HR"],
                "selection_reason": "RealSR V3 x4 Test real-degradation pair, center-cropped/resized to current RB5 harness shape",
            })

    manifest = OUT_ROOT / "manifest.csv"
    write_csv(manifest, rows)
    (OUT_ROOT / "README.md").write_text(
        "\n".join([
            "# RealSR V3 x4 Test EvalHub Extension",
            "",
            f"Source archive: `{tar_path}`",
            "",
            "This is a real-degradation SR layer derived from RealSR V3 Test/4.",
            "It does not replace `RB5_SR_Benchmark_v1`.",
            "",
            "Each case contains `lr_128.png`, `bicubic_512.png`, and `hr_512.png`.",
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

