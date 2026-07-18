"""Fetch directly downloadable EvalHub data sources.

This script intentionally downloads only sources marked ``auto_download=yes`` in
``eval_hub/registries/dataset_registry.csv``. Large, form-gated, or
license-sensitive datasets stay registered but manual.
"""

from __future__ import annotations

import argparse
import tarfile
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path

from evalhub_common import DATA_ROOT, DATASET_REGISTRY, dataset_local_dir, read_csv


CSIQ_FILES = {
    "src_imgs.zip": "https://s2.smu.edu/~eclarson/csiq/src_imgs.zip",
    "dst_imgs.zip": "https://s2.smu.edu/~eclarson/csiq/dst_imgs.zip",
    "csiq.DMOS.xlsx": "https://s2.smu.edu/~eclarson/csiq/csiq.DMOS.xlsx",
}

SET14_URL = "https://huggingface.co/datasets/eugenesiow/Set14/resolve/main/data/Set14_HR.tar.gz"


def download(url: str, out_path: Path, *, force: bool) -> None:
    if out_path.exists() and not force:
        print(f"[skip] {out_path}")
        return
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_path.with_suffix(out_path.suffix + ".tmp")
    print(f"[download] {url}")
    with urllib.request.urlopen(url, timeout=60) as response, tmp.open("wb") as f:
        shutil.copyfileobj(response, f)
    tmp.replace(out_path)
    print(f"[ok] {out_path} ({out_path.stat().st_size} bytes)")


def extract_zip(zip_path: Path, out_dir: Path, *, force: bool) -> None:
    marker = out_dir / ".extracted"
    if marker.exists() and not force:
        print(f"[skip] extracted {out_dir}")
        return
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"[extract] {zip_path}")
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(out_dir)
    marker.write_text(f"source={zip_path.name}\n", encoding="utf-8")


def extract_tar_gz(tar_path: Path, out_dir: Path, *, force: bool) -> None:
    marker = out_dir / ".extracted"
    if marker.exists() and not force:
        print(f"[skip] extracted {out_dir}")
        return
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"[extract] {tar_path}")
    with tarfile.open(tar_path, "r:gz") as tf:
        tf.extractall(out_dir)
    marker.write_text(f"source={tar_path.name}\n", encoding="utf-8")


def fetch_csiq(root: Path, *, force: bool, extract: bool) -> None:
    archives = root / "archives"
    for name, url in CSIQ_FILES.items():
        download(url, archives / name, force=force)
    if extract:
        extract_zip(archives / "src_imgs.zip", root / "src_imgs", force=force)
        extract_zip(archives / "dst_imgs.zip", root / "dst_imgs", force=force)
    readme = root / "README_EVALHUB.md"
    readme.write_text(
        "\n".join(
            [
                "# CSIQ Local Copy",
                "",
                "Source: https://s2.smu.edu/~eclarson/csiq/",
                "",
                "Downloaded files:",
                "- archives/src_imgs.zip",
                "- archives/dst_imgs.zip",
                "- archives/csiq.DMOS.xlsx",
                "",
                "Use this as an IQA metric calibration/sanity dataset only.",
                "It is not an SR lifecycle benchmark and must not replace RB5_SR_Benchmark_v1.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def fetch_set14(root: Path, *, force: bool, extract: bool) -> None:
    archives = root / "archives"
    tar_path = archives / "Set14_HR.tar.gz"
    download(SET14_URL, tar_path, force=force)
    if extract:
        extract_tar_gz(tar_path, root / "hr", force=force)
    (root / "README_EVALHUB.md").write_text(
        "\n".join(
            [
                "# Set14 Local Copy",
                "",
                f"Source: {SET14_URL}",
                "",
                "Use this as a small standard SR sanity source.",
                "Derive project-compatible 128->512 cases with:",
                "",
                "```bat",
                "python -B eval_hub\\scripts\\prepare_set14_extension.py",
                "```",
                "",
            ]
        ),
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="auto", help="Dataset id or 'auto'. Currently supports csiq for direct download.")
    parser.add_argument("--force", action="store_true", help="Re-download existing files.")
    parser.add_argument("--extract", action="store_true", help="Extract downloaded zip files.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rows = read_csv(DATASET_REGISTRY)
    selected = [
        row for row in rows
        if (args.dataset == "auto" and row["auto_download"].lower() == "yes")
        or row["dataset_id"] == args.dataset
    ]
    if not selected:
        print(f"No dataset matched: {args.dataset}", file=sys.stderr)
        return 2
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    for row in selected:
        dataset_id = row["dataset_id"]
        root = dataset_local_dir(row)
        if dataset_id == "csiq":
            fetch_csiq(root, force=args.force, extract=args.extract)
        elif dataset_id == "set14_hf":
            fetch_set14(root, force=args.force, extract=args.extract)
        else:
            print(f"[manual] {dataset_id}: {row['source_url']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

