"""Search for W8A8-vs-float local crops that could trigger AIMET work.

This is a trigger search, not an AIMET run. It scans an existing
float-vs-W8A8 benchmark result and finds local regions where float Real-ESRGAN is
closer to HR than W8A8 by a meaningful margin.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np


DEFAULT_BENCHMARK_ROOT = Path(r"C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1")
DEFAULT_SOURCE_RUN = DEFAULT_BENCHMARK_ROOT / "results" / "20260715_1950_realesrgan_host_float_vs_w8a8_full_v2"


@dataclass(frozen=True)
class Candidate:
    case_id: str
    category: str
    x: int
    y: int
    patch_size: int
    psnr_float_hr: float
    psnr_w8a8_hr: float
    psnr_delta_float_minus_w8a8: float
    mad_float_w8a8: float
    sharpness_float: float
    sharpness_w8a8: float
    score: float
    float_path: Path
    w8a8_path: Path
    hr_path: Path
    sheet_path: Path


def resolve_path(benchmark_root: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return benchmark_root / path


def read_image(path: Path) -> np.ndarray:
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        raise FileNotFoundError(path)
    return image


def psnr(reference: np.ndarray, candidate: np.ndarray) -> float:
    mse = np.mean((reference.astype(np.float64) - candidate.astype(np.float64)) ** 2)
    return 99.0 if mse == 0 else float(10.0 * np.log10((255.0 * 255.0) / mse))


def mean_abs_diff(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.mean(np.abs(a.astype(np.float64) - b.astype(np.float64))))


def sharpness(image: np.ndarray) -> float:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def panel(image: np.ndarray, title: str, width: int = 220) -> np.ndarray:
    body = cv2.resize(image, (width, width), interpolation=cv2.INTER_AREA)
    header = np.full((36, width, 3), 24, dtype=np.uint8)
    cv2.putText(header, title[:26], (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 255, 255), 1, cv2.LINE_AA)
    return np.vstack([header, body])


def diff_heatmap(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    diff = np.mean(np.abs(a.astype(np.float32) - b.astype(np.float32)), axis=2)
    norm = np.clip(diff * 6.0, 0, 255).astype(np.uint8)
    return cv2.applyColorMap(norm, cv2.COLORMAP_INFERNO)


def write_candidate_sheet(candidate: Candidate, float_img: np.ndarray, w8a8_img: np.ndarray, hr_img: np.ndarray) -> None:
    x = candidate.x
    y = candidate.y
    size = candidate.patch_size
    float_crop = float_img[y : y + size, x : x + size]
    w8a8_crop = w8a8_img[y : y + size, x : x + size]
    hr_crop = hr_img[y : y + size, x : x + size]
    sheet = np.hstack(
        [
            panel(hr_crop, "HR crop"),
            panel(float_crop, f"float {candidate.psnr_float_hr:.2f}"),
            panel(w8a8_crop, f"W8A8 {candidate.psnr_w8a8_hr:.2f}"),
            panel(diff_heatmap(float_crop, w8a8_crop), f"diff MAD {candidate.mad_float_w8a8:.2f}"),
        ]
    )
    candidate.sheet_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(candidate.sheet_path), sheet)


def scan_case(
    row: dict[str, str],
    benchmark_root: Path,
    out_dir: Path,
    patch_size: int,
    stride: int,
    min_delta_db: float,
    min_mad: float,
) -> list[Candidate]:
    case_id = row["case_id"]
    category = row["category"]
    float_path = resolve_path(benchmark_root, row["float_output"])
    w8a8_path = resolve_path(benchmark_root, row["w8a8_output"])
    hr_path = resolve_path(benchmark_root, row["hr_512"])
    float_img = read_image(float_path)
    w8a8_img = read_image(w8a8_path)
    hr_img = read_image(hr_path)
    height, width = hr_img.shape[:2]
    candidates: list[Candidate] = []
    for y in range(0, height - patch_size + 1, stride):
        for x in range(0, width - patch_size + 1, stride):
            hr_crop = hr_img[y : y + patch_size, x : x + patch_size]
            float_crop = float_img[y : y + patch_size, x : x + patch_size]
            w8a8_crop = w8a8_img[y : y + patch_size, x : x + patch_size]
            psnr_float = psnr(hr_crop, float_crop)
            psnr_w8a8 = psnr(hr_crop, w8a8_crop)
            delta = psnr_float - psnr_w8a8
            mad = mean_abs_diff(float_crop, w8a8_crop)
            if delta < min_delta_db or mad < min_mad:
                continue
            sharp_float = sharpness(float_crop)
            sharp_w8a8 = sharpness(w8a8_crop)
            score = delta + 0.08 * mad + 0.0005 * max(0.0, sharp_float - sharp_w8a8)
            sheet_path = out_dir / "candidates" / f"{case_id}_x{x}_y{y}.png"
            candidate = Candidate(
                case_id=case_id,
                category=category,
                x=x,
                y=y,
                patch_size=patch_size,
                psnr_float_hr=psnr_float,
                psnr_w8a8_hr=psnr_w8a8,
                psnr_delta_float_minus_w8a8=delta,
                mad_float_w8a8=mad,
                sharpness_float=sharp_float,
                sharpness_w8a8=sharp_w8a8,
                score=score,
                float_path=float_path,
                w8a8_path=w8a8_path,
                hr_path=hr_path,
                sheet_path=sheet_path,
            )
            candidates.append(candidate)
    candidates.sort(key=lambda item: item.score, reverse=True)
    for candidate in candidates[:2]:
        write_candidate_sheet(candidate, float_img, w8a8_img, hr_img)
    return candidates[:2]


def write_csv(path: Path, candidates: list[Candidate], benchmark_root: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "rank",
        "case_id",
        "category",
        "x",
        "y",
        "patch_size",
        "psnr_float_hr",
        "psnr_w8a8_hr",
        "psnr_delta_float_minus_w8a8",
        "mad_float_w8a8",
        "sharpness_float",
        "sharpness_w8a8",
        "score",
        "trigger_strength",
        "sheet_path",
        "review_note",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for rank, candidate in enumerate(candidates, start=1):
            trigger_strength = "strong" if candidate.psnr_delta_float_minus_w8a8 >= 1.0 and candidate.mad_float_w8a8 >= 3.0 else "weak"
            writer.writerow(
                {
                    "rank": rank,
                    "case_id": candidate.case_id,
                    "category": candidate.category,
                    "x": candidate.x,
                    "y": candidate.y,
                    "patch_size": candidate.patch_size,
                    "psnr_float_hr": f"{candidate.psnr_float_hr:.3f}",
                    "psnr_w8a8_hr": f"{candidate.psnr_w8a8_hr:.3f}",
                    "psnr_delta_float_minus_w8a8": f"{candidate.psnr_delta_float_minus_w8a8:.3f}",
                    "mad_float_w8a8": f"{candidate.mad_float_w8a8:.3f}",
                    "sharpness_float": f"{candidate.sharpness_float:.2f}",
                    "sharpness_w8a8": f"{candidate.sharpness_w8a8:.2f}",
                    "score": f"{candidate.score:.3f}",
                    "trigger_strength": trigger_strength,
                    "sheet_path": str(candidate.sheet_path).replace("\\", "/"),
                    "review_note": "Human review must confirm visible W8A8-only degradation before AIMET starts.",
                }
            )


def write_overview(out_path: Path, candidates: list[Candidate]) -> None:
    sheets = []
    for candidate in candidates[:12]:
        if candidate.sheet_path.exists():
            image = read_image(candidate.sheet_path)
            header = np.full((34, image.shape[1], 3), 245, dtype=np.uint8)
            label = f"{candidate.case_id} d={candidate.psnr_delta_float_minus_w8a8:.2f} mad={candidate.mad_float_w8a8:.2f}"
            cv2.putText(header, label[:90], (8, 23), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (20, 20, 20), 1, cv2.LINE_AA)
            sheets.append(np.vstack([header, image]))
    if sheets:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(out_path), np.vstack(sheets))


def write_summary(out_dir: Path, candidates: list[Candidate], source_run: Path) -> None:
    strong = [c for c in candidates if c.psnr_delta_float_minus_w8a8 >= 1.0 and c.mad_float_w8a8 >= 3.0]
    lines = [
        "# AIMET Trigger Crop Search",
        "",
        f"- source_run: `{source_run}`",
        f"- candidates: {len(candidates)}",
        f"- strong_candidates: {len(strong)}",
        "- boundary: this is an automated trigger search, not proof that AIMET should start",
        "",
        "## Decision",
        "",
    ]
    if strong:
        lines.append("Potential AIMET trigger crops exist. Human review should inspect `candidate_overview.png` before starting CLE/Bias Correction.")
    else:
        lines.append("No strong automated W8A8-vs-float failure crop was found under the current thresholds.")
    lines.extend(
        [
            "",
            "## Outputs",
            "",
            f"- candidates: `{out_dir / 'candidate_metrics.csv'}`",
            f"- overview: `{out_dir / 'candidate_overview.png'}`",
            f"- crop sheets: `{out_dir / 'candidates'}`",
            "",
            "## Review Rule",
            "",
            "Start AIMET only if a crop shows visible W8A8-only degradation that float does not have.",
        ]
    )
    (out_dir / "SUMMARY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark-root", type=Path, default=DEFAULT_BENCHMARK_ROOT)
    parser.add_argument("--source-run", type=Path, default=DEFAULT_SOURCE_RUN)
    parser.add_argument("--run-id", default="")
    parser.add_argument("--patch-size", type=int, default=96)
    parser.add_argument("--stride", type=int, default=48)
    parser.add_argument("--min-delta-db", type=float, default=0.45)
    parser.add_argument("--min-mad", type=float, default=2.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    benchmark_root = args.benchmark_root.resolve()
    source_run = args.source_run.resolve()
    run_id = args.run_id or datetime.now().strftime("aimet_trigger_search_%Y%m%d_%H%M%S")
    out_dir = Path(__file__).resolve().parent / "results" / "aimet_trigger_search" / run_id
    rows: list[dict[str, str]] = []
    with (source_run / "metrics.csv").open("r", newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    candidates: list[Candidate] = []
    for row in rows:
        candidates.extend(
            scan_case(
                row=row,
                benchmark_root=benchmark_root,
                out_dir=out_dir,
                patch_size=args.patch_size,
                stride=args.stride,
                min_delta_db=args.min_delta_db,
                min_mad=args.min_mad,
            )
        )
    candidates.sort(key=lambda item: item.score, reverse=True)
    candidates = candidates[:20]
    write_csv(out_dir / "candidate_metrics.csv", candidates, benchmark_root)
    write_overview(out_dir / "candidate_overview.png", candidates)
    write_summary(out_dir, candidates, source_run)
    print(f"[ok] wrote {out_dir}")
    print(f"[ok] candidates={len(candidates)}")


if __name__ == "__main__":
    main()
