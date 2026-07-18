"""Validate SR manifests for RB5 EvalHub/Harness compatibility."""

from __future__ import annotations

import argparse
from pathlib import Path

try:
    import cv2
except Exception:  # pragma: no cover - allows path-only validation on minimal Python
    cv2 = None

from evalhub_common import read_csv


REQUIRED_COLUMNS = [
    "case_id",
    "category",
    "dataset",
    "source_id",
    "lr_128",
    "bicubic_512",
    "hr_512",
]


def check_image(path: Path, expected_size: tuple[int, int] | None) -> str:
    if not path.exists():
        return "missing"
    if expected_size is None or cv2 is None:
        return "ok"
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        return "unreadable"
    height, width = image.shape[:2]
    if (width, height) != expected_size:
        return f"bad_size:{width}x{height}"
    return "ok"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--check-size", action="store_true", help="Require lr=128x128 and bicubic/hr=512x512.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rows = read_csv(args.manifest)
    if not rows:
        print(f"[fail] empty manifest: {args.manifest}")
        return 1
    missing_columns = [column for column in REQUIRED_COLUMNS if column not in rows[0]]
    if missing_columns:
        print(f"[fail] missing columns: {', '.join(missing_columns)}")
        return 1

    failures: list[str] = []
    seen: set[str] = set()
    for row in rows:
        case_id = row["case_id"]
        if case_id in seen:
            failures.append(f"{case_id}: duplicate case_id")
        seen.add(case_id)
        lr_status = check_image(Path(row["lr_128"]), (128, 128) if args.check_size else None)
        bicubic_status = check_image(Path(row["bicubic_512"]), (512, 512) if args.check_size else None)
        hr_status = check_image(Path(row["hr_512"]), (512, 512) if args.check_size else None)
        if lr_status != "ok" or bicubic_status != "ok" or hr_status != "ok":
            failures.append(
                f"{case_id}: lr={lr_status}, bicubic={bicubic_status}, hr={hr_status}"
            )

    if failures:
        print(f"[fail] {args.manifest}")
        for item in failures[:20]:
            print(f"- {item}")
        if len(failures) > 20:
            print(f"- ... {len(failures) - 20} more")
        return 1

    print(f"[ok] {args.manifest}")
    print(f"cases={len(rows)}")
    print(f"size_check={'enabled' if args.check_size else 'disabled'}")
    print(f"cv2={'available' if cv2 is not None else 'not_available'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

