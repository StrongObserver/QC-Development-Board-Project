"""Shared helpers for RB5 EvalHub scripts."""

from __future__ import annotations

import csv
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
EVAL_HUB = REPO_ROOT / "eval_hub"
DATA_ROOT = REPO_ROOT / "evalhub_data"
DATASET_REGISTRY = EVAL_HUB / "registries" / "dataset_registry.csv"
METRIC_POLICY = EVAL_HUB / "registries" / "metric_policy.csv"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = []
        for row in rows:
            for key in row:
                if key not in fieldnames:
                    fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def dataset_local_dir(row: dict[str, str]) -> Path:
    return DATA_ROOT / "raw" / row["local_subdir"]


def dataset_is_present(row: dict[str, str]) -> bool:
    if row["status"] == "existing":
        source = Path(row["source_url"])
        if source.exists():
            return True
    local = dataset_local_dir(row)
    if row["dataset_id"] == "csiq":
        archives = local / "archives"
        required = [
            archives / "src_imgs.zip",
            archives / "dst_imgs.zip",
            archives / "csiq.DMOS.xlsx",
        ]
        return all(path.exists() and path.stat().st_size > 0 for path in required)
    if row["dataset_id"] == "set14_hf":
        archive = local / "archives" / "Set14_HR.tar.gz"
        return archive.exists() and archive.stat().st_size > 0
    if row["dataset_id"] == "set5_set14_bsd100_urban100":
        manifest = DATA_ROOT / "derived" / "standard_sr_x4_v1" / "manifest.csv"
        return manifest.exists() and manifest.stat().st_size > 0
    if row["dataset_id"] == "realsr":
        manifest = DATA_ROOT / "derived" / "realsr_v3_x4_test_128x4_v1" / "manifest.csv"
        return manifest.exists() and manifest.stat().st_size > 0
    if row["dataset_id"] == "textzoom":
        manifest = DATA_ROOT / "derived" / "textzoom_test_128x4_v1" / "manifest.csv"
        return manifest.exists() and manifest.stat().st_size > 0
    return local.exists() and any(local.iterdir())

