"""Tile quality comparison across benchmark scenes.

For each selected still input, this runner creates one comparable row:

Input 512 | Bicubic x4 | QuickSR tile x4 | Real-ESRGAN tile x4

It is host-side evidence only. The output is for visual review and route
selection before expanding Android app tile behavior.
"""

from __future__ import annotations

import argparse
import csv
import json
import time
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

from tile_still_mvp import (
    BENCHMARK_ROOT,
    REPO_ROOT,
    TfliteSrModel,
    git_revision,
    model_path_for,
    read_image,
    run_tiled_sr,
    seam_score,
    write_csv,
)


def load_manifest() -> dict[str, dict[str, str]]:
    with (BENCHMARK_ROOT / "manifest.csv").open("r", encoding="utf-8-sig", newline="") as f:
        return {row["case_id"]: row for row in csv.DictReader(f)}


def load_case_ids(input_set: str) -> list[str]:
    if input_set == "smoke":
        with (BENCHMARK_ROOT / "qa" / "smoke_subset.csv").open("r", encoding="utf-8-sig", newline="") as f:
            return [row["case_id"] for row in csv.DictReader(f)]
    if input_set == "structure_text_lowlight":
        return [
            "structure_edges_urban040",
            "structure_edges_urban041",
            "text_signage_div2k0891",
            "text_signage_urban076",
            "low_light_div2k0852",
            "natural_texture_div2k0889",
        ]
    raise ValueError(f"unsupported input set: {input_set}")


def panel(image: np.ndarray, title: str, width: int = 260) -> np.ndarray:
    body = cv2.resize(image, (width, width), interpolation=cv2.INTER_AREA)
    header = np.full((38, width, 3), 25, dtype=np.uint8)
    cv2.putText(header, title[:28], (8, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.54, (255, 255, 255), 1, cv2.LINE_AA)
    return np.vstack([header, body])


def row_sheet(case_id: str, input_bgr: np.ndarray, bicubic: np.ndarray, quicksr: np.ndarray, real: np.ndarray) -> np.ndarray:
    header = np.full((34, 260 * 4, 3), 245, dtype=np.uint8)
    cv2.putText(header, case_id[:80], (8, 23), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (20, 20, 20), 1, cv2.LINE_AA)
    body = np.hstack(
        [
            panel(input_bgr, "Input 512"),
            panel(bicubic, "Bicubic x4"),
            panel(quicksr, "QuickSR tile x4"),
            panel(real, "Real-ESRGAN tile x4"),
        ]
    )
    return np.vstack([header, body])


def center_crop_row(case_id: str, bicubic: np.ndarray, quicksr: np.ndarray, real: np.ndarray) -> np.ndarray:
    def crop(image: np.ndarray) -> np.ndarray:
        size = min(512, image.shape[0], image.shape[1])
        y = max(0, image.shape[0] // 2 - size // 2)
        x = max(0, image.shape[1] // 2 - size // 2)
        return image[y : y + size, x : x + size]

    header = np.full((34, 260 * 3, 3), 245, dtype=np.uint8)
    cv2.putText(header, (case_id + " center crop")[:80], (8, 23), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (20, 20, 20), 1, cv2.LINE_AA)
    body = np.hstack(
        [
            panel(crop(bicubic), "Bicubic center"),
            panel(crop(quicksr), "QuickSR center"),
            panel(crop(real), "RealESRGAN center"),
        ]
    )
    blank = np.full((body.shape[0] + header.shape[0], 260, 3), 255, dtype=np.uint8)
    return np.hstack([np.vstack([header, body]), blank])


def mean_abs_diff(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.mean(np.abs(a.astype(np.float32) - b.astype(np.float32))))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-set", choices=["smoke", "structure_text_lowlight"], default="smoke")
    parser.add_argument("--overlap", type=int, default=32)
    parser.add_argument("--run-id", default="")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_id = args.run_id or datetime.now().strftime(f"%Y%m%d_%H%M%S_tile_eval_{args.input_set}")
    out_dir = REPO_ROOT / "RB5_SR_lab" / "results" / "tile_eval" / run_id
    case_dir = out_dir / "cases"
    out_dir.mkdir(parents=True, exist_ok=True)
    case_dir.mkdir(parents=True, exist_ok=True)

    manifest = load_manifest()
    quick_model = TfliteSrModel(model_path_for("quicksr"))
    real_model = TfliteSrModel(model_path_for("realesrgan"))
    rows: list[dict[str, object]] = []
    full_rows: list[np.ndarray] = []
    crop_rows: list[np.ndarray] = []

    for case_id in load_case_ids(args.input_set):
        row = manifest[case_id]
        input_path = Path(row["hr_512"])
        image = read_image(input_path)
        bicubic = cv2.resize(image, (image.shape[1] * 4, image.shape[0] * 4), interpolation=cv2.INTER_CUBIC)

        print(f"[tile-eval] {case_id} QuickSR")
        q0 = time.perf_counter()
        quick = run_tiled_sr(image, quick_model, args.overlap)
        quick_wall = (time.perf_counter() - q0) * 1000.0

        print(f"[tile-eval] {case_id} Real-ESRGAN")
        r0 = time.perf_counter()
        real = run_tiled_sr(image, real_model, args.overlap)
        real_wall = (time.perf_counter() - r0) * 1000.0

        one_case = case_dir / case_id
        one_case.mkdir(parents=True, exist_ok=True)
        input_out = one_case / "input_512.png"
        bicubic_out = one_case / "bicubic_2048.png"
        quick_out = one_case / "quicksr_tile_2048.png"
        real_out = one_case / "realesrgan_tile_2048.png"
        sheet_out = one_case / "method_comparison.png"
        crop_out = one_case / "center_crop_comparison.png"
        cv2.imwrite(str(input_out), image)
        cv2.imwrite(str(bicubic_out), bicubic)
        cv2.imwrite(str(quick_out), quick.image)
        cv2.imwrite(str(real_out), real.image)
        sheet = row_sheet(case_id, image, bicubic, quick.image, real.image)
        crops = center_crop_row(case_id, bicubic, quick.image, real.image)
        cv2.imwrite(str(sheet_out), sheet)
        cv2.imwrite(str(crop_out), crops)
        full_rows.append(sheet)
        crop_rows.append(crops)

        quick_tiles = np.array(quick.tile_ms, dtype=np.float64)
        real_tiles = np.array(real.tile_ms, dtype=np.float64)
        rows.append(
            {
                "case_id": case_id,
                "category": row["category"],
                "input_path": str(input_path),
                "tile_count": quick.tile_count,
                "overlap_px_lr": args.overlap,
                "quicksr_tile_p50_ms": f"{np.percentile(quick_tiles, 50):.3f}",
                "quicksr_tile_p95_ms": f"{np.percentile(quick_tiles, 95):.3f}",
                "quicksr_wall_ms": f"{quick_wall:.3f}",
                "quicksr_seam_mad": f"{seam_score(quick.image, image.shape[1], image.shape[0], 128, args.overlap):.3f}",
                "quicksr_mad_vs_bicubic": f"{mean_abs_diff(quick.image, bicubic):.3f}",
                "realesrgan_tile_p50_ms": f"{np.percentile(real_tiles, 50):.3f}",
                "realesrgan_tile_p95_ms": f"{np.percentile(real_tiles, 95):.3f}",
                "realesrgan_wall_ms": f"{real_wall:.3f}",
                "realesrgan_seam_mad": f"{seam_score(real.image, image.shape[1], image.shape[0], 128, args.overlap):.3f}",
                "realesrgan_mad_vs_bicubic": f"{mean_abs_diff(real.image, bicubic):.3f}",
                "method_comparison": str(sheet_out),
                "center_crop_comparison": str(crop_out),
                "review_hint": "Check seams, edge sharpness, text/face distortion, fake texture, and low-light noise.",
            }
        )

    overview = np.vstack(full_rows)
    crop_overview = np.vstack(crop_rows)
    cv2.imwrite(str(out_dir / "tile_method_overview.png"), overview)
    cv2.imwrite(str(out_dir / "tile_center_crop_overview.png"), crop_overview)
    write_csv(out_dir / "metrics.csv", rows)
    write_csv(
        out_dir / "run_log.csv",
        [
            {
                "run_id": run_id,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M +0800"),
                "app_or_script_commit": git_revision(REPO_ROOT),
                "device": "Windows host",
                "backend": "host_cpu_litert",
                "task": "tile-eval",
                "status": "tile_eval_completed_needs_visual_review",
                "output_dir": str(out_dir),
                "notes": "Host-side multi-scene tile comparison; not Android app e2e.",
            }
        ],
    )
    (out_dir / "loop_state.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "run_id": run_id,
                "status": "tile_eval_completed_needs_visual_review",
                "stop_reason": "visual_review_required",
                "next_priority_task": "Review tile_method_overview.png and tile_center_crop_overview.png; then decide whether Real-ESRGAN tile should be the post-capture default candidate.",
                "requires_human_review": True,
                "blocked_by": "visual_review",
                "required_next_read": [
                    str(out_dir / "metrics.csv"),
                    str(out_dir / "tile_method_overview.png"),
                    str(out_dir / "tile_center_crop_overview.png"),
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"[ok] wrote {out_dir}")


if __name__ == "__main__":
    main()
