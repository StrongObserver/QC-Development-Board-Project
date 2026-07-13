"""P0 evaluation baseline for the RB5 Gen2 super-resolution project.

This script intentionally stays small and dependency-light. It reuses existing
host-side and RB5-captured artifacts, then writes a single CSV table with the
metrics that are safe to automate now:

- reference metrics when a real reference exists (for example TFLite vs PyTorch)
- no-reference proxy metrics for camera samples (sharpness, color difference)
- explicit notes that camera samples still require visual pass/fail review

The goal is not to declare final image quality from one number. The goal is to
standardize inputs, comparisons, fields, and boundaries before D8 quantization.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import cv2
import numpy as np


@dataclass(frozen=True)
class EvalCase:
    case_id: str
    scenario: str
    input_path: Optional[Path]
    bicubic_path: Optional[Path]
    candidate_path: Path
    candidate_role: str
    reference_path: Optional[Path]
    reference_role: str
    notes: str


def read_image(path: Optional[Path]) -> Optional[np.ndarray]:
    if path is None:
        return None
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        raise FileNotFoundError(path)
    return image


def rel(root: Path, path: Optional[Path]) -> str:
    if path is None:
        return ""
    try:
        return str(path.relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(path)


def image_size(image: Optional[np.ndarray]) -> str:
    if image is None:
        return ""
    height, width = image.shape[:2]
    return f"{width}x{height}"


def psnr(reference: np.ndarray, candidate: np.ndarray) -> float:
    if reference.shape != candidate.shape:
        raise ValueError(f"shape mismatch: {reference.shape} vs {candidate.shape}")
    mse = np.mean((reference.astype(np.float64) - candidate.astype(np.float64)) ** 2)
    if mse == 0:
        return 99.0
    return float(10.0 * np.log10((255.0 * 255.0) / mse))


def ssim(reference: np.ndarray, candidate: np.ndarray) -> float:
    """Compute a compact global SSIM over grayscale images.

    This is sufficient for consistency checks. It is not a perceptual SR score.
    """
    if reference.shape != candidate.shape:
        raise ValueError(f"shape mismatch: {reference.shape} vs {candidate.shape}")
    ref = cv2.cvtColor(reference, cv2.COLOR_BGR2GRAY).astype(np.float64)
    cand = cv2.cvtColor(candidate, cv2.COLOR_BGR2GRAY).astype(np.float64)
    c1 = (0.01 * 255) ** 2
    c2 = (0.03 * 255) ** 2
    mu_ref = cv2.GaussianBlur(ref, (11, 11), 1.5)
    mu_cand = cv2.GaussianBlur(cand, (11, 11), 1.5)
    sigma_ref = cv2.GaussianBlur(ref * ref, (11, 11), 1.5) - mu_ref * mu_ref
    sigma_cand = cv2.GaussianBlur(cand * cand, (11, 11), 1.5) - mu_cand * mu_cand
    sigma_ref_cand = cv2.GaussianBlur(ref * cand, (11, 11), 1.5) - mu_ref * mu_cand
    numerator = (2 * mu_ref * mu_cand + c1) * (2 * sigma_ref_cand + c2)
    denominator = (mu_ref * mu_ref + mu_cand * mu_cand + c1) * (sigma_ref + sigma_cand + c2)
    return float(np.mean(numerator / np.maximum(denominator, 1e-12)))


def laplacian_variance(image: Optional[np.ndarray]) -> Optional[float]:
    if image is None:
        return None
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def mean_abs_diff(a: np.ndarray, b: np.ndarray) -> float:
    if a.shape != b.shape:
        b = cv2.resize(b, (a.shape[1], a.shape[0]), interpolation=cv2.INTER_CUBIC)
    return float(np.mean(np.abs(a.astype(np.float64) - b.astype(np.float64))))


def resize_keep_aspect(image: np.ndarray, width: int = 360) -> np.ndarray:
    height = max(1, int(image.shape[0] * width / image.shape[1]))
    return cv2.resize(image, (width, height), interpolation=cv2.INTER_AREA)


def panel(image: Optional[np.ndarray], title: str, width: int = 360) -> np.ndarray:
    if image is None:
        body = np.full((width, width, 3), 245, dtype=np.uint8)
        cv2.putText(body, "N/A", (width // 2 - 35, width // 2), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (80, 80, 80), 2)
    else:
        body = resize_keep_aspect(image, width=width)
    header = np.full((44, body.shape[1], 3), 25, dtype=np.uint8)
    cv2.putText(header, title[:34], (10, 29), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (255, 255, 255), 1, cv2.LINE_AA)
    return np.vstack([header, body])


def stack_panels(panels: list[np.ndarray]) -> np.ndarray:
    max_height = max(p.shape[0] for p in panels)
    padded = []
    for p in panels:
        if p.shape[0] < max_height:
            pad = np.full((max_height - p.shape[0], p.shape[1], 3), 245, dtype=np.uint8)
            p = np.vstack([p, pad])
        padded.append(p)
    return np.hstack(padded)


def write_contact_sheet(
    output_dir: Path,
    case: EvalCase,
    input_image: Optional[np.ndarray],
    bicubic: Optional[np.ndarray],
    candidate: np.ndarray,
    reference: Optional[np.ndarray],
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    panels = [
        panel(input_image, "input"),
        panel(bicubic, "bicubic"),
        panel(candidate, case.candidate_role),
    ]
    if reference is not None:
        panels.append(panel(reference, case.reference_role))
    sheet = stack_panels(panels)
    out_path = output_dir / f"{case.case_id}_comparison.png"
    cv2.imwrite(str(out_path), sheet)
    return out_path


def fmt(value: Optional[float], digits: int = 4) -> str:
    if value is None:
        return ""
    return f"{value:.{digits}f}"


def existing_case(case: EvalCase) -> bool:
    paths = [case.input_path, case.bicubic_path, case.candidate_path, case.reference_path]
    return all(path is None or path.exists() for path in paths)


def build_cases(root: Path) -> list[EvalCase]:
    sr_lab = root / "RB5_SR_lab"
    assets = root / "project_assets"
    return [
        EvalCase(
            case_id="host_flower_tflite_vs_pytorch",
            scenario="host_static_consistency",
            input_path=sr_lab / "inputs" / "flower.png",
            bicubic_path=sr_lab / "results" / "flower_bicubic_x4.png",
            candidate_path=sr_lab / "results" / "flower_tflite_x4.png",
            candidate_role="float_tflite",
            reference_path=sr_lab / "results" / "flower_x4.png",
            reference_role="pytorch_float_reference",
            notes="Use PSNR/SSIM only as conversion consistency checks, not subjective quality.",
        ),
        EvalCase(
            case_id="host_photo_tflite_vs_pytorch",
            scenario="host_static_consistency",
            input_path=sr_lab / "inputs" / "photo.png",
            bicubic_path=sr_lab / "results" / "photo_bicubic_x4.png",
            candidate_path=sr_lab / "results" / "photo_tflite_x4.png",
            candidate_role="float_tflite",
            reference_path=sr_lab / "results" / "photo_x4.png",
            reference_role="pytorch_float_reference",
            notes="Use PSNR/SSIM only as conversion consistency checks, not subjective quality.",
        ),
        EvalCase(
            case_id="d7_cpu_camera_roi",
            scenario="rb5_camera_128_roi_no_reference",
            input_path=assets / "D7_backend_compare" / "D7_20251110_054147_CPU_roi_128.png",
            bicubic_path=assets / "D7_backend_compare" / "D7_20251110_054147_CPU_baseline_resize_512.png",
            candidate_path=assets / "D7_backend_compare" / "D7_20251110_054147_CPU_sr_512.png",
            candidate_role="android_tflite_cpu_float",
            reference_path=None,
            reference_role="none",
            notes="No ground truth. Requires visual review for artifacts/readability; metrics are proxies only.",
        ),
        EvalCase(
            case_id="d7_gpu_camera_roi",
            scenario="rb5_camera_128_roi_no_reference",
            input_path=assets / "D7_backend_compare" / "D7_20251110_055113_GPU_roi_128.png",
            bicubic_path=assets / "D7_backend_compare" / "D7_20251110_055113_GPU_baseline_resize_512.png",
            candidate_path=assets / "D7_backend_compare" / "D7_20251110_055113_GPU_sr_512.png",
            candidate_role="android_tflite_gpu_float",
            reference_path=None,
            reference_role="none",
            notes="No ground truth. Requires visual review for artifacts/readability; metrics are proxies only.",
        ),
        EvalCase(
            case_id="d75_highres_256_still",
            scenario="rb5_camera_256_still_no_reference",
            input_path=assets / "D75_256_highres" / "RB5_camerax_up" / "D75_256_20251110_093929_input_256.png",
            bicubic_path=assets / "D75_256_highres" / "RB5_camerax_up" / "D75_256_20251110_093929_baseline_resize_1024.png",
            candidate_path=assets / "D75_256_highres" / "RB5_camerax_up" / "D75_256_20251110_093929_sr_1024.png",
            candidate_role="android_tflite_cpu_256_float",
            reference_path=None,
            reference_role="none",
            notes="Still-quality evidence only; not a real-time target. Requires visual artifact review.",
        ),
        EvalCase(
            case_id="offline_text_edge_cpu",
            scenario="rb5_offline_text_edge_128_no_reference",
            input_path=assets / "offline_eval" / "OFFLINE_TEXT_EDGE_20251110_055715_CPU_input_128.png",
            bicubic_path=assets / "offline_eval" / "OFFLINE_TEXT_EDGE_20251110_055715_CPU_baseline_resize_512.png",
            candidate_path=assets / "offline_eval" / "OFFLINE_TEXT_EDGE_20251110_055715_CPU_sr_512.png",
            candidate_role="android_tflite_cpu_float_offline",
            reference_path=None,
            reference_role="none",
            notes="Offline public-domain text/edge asset. Main gate: SR must improve edge clarity without making letters less readable or deforming geometry.",
        ),
        EvalCase(
            case_id="offline_lowlight_noise_cpu",
            scenario="rb5_offline_lowlight_noise_128_no_reference",
            input_path=assets / "offline_eval" / "OFFLINE_LOWLIGHT_NOISE_20251110_055715_CPU_input_128.png",
            bicubic_path=assets / "offline_eval" / "OFFLINE_LOWLIGHT_NOISE_20251110_055715_CPU_baseline_resize_512.png",
            candidate_path=assets / "offline_eval" / "OFFLINE_LOWLIGHT_NOISE_20251110_055715_CPU_sr_512.png",
            candidate_role="android_tflite_cpu_float_offline",
            reference_path=None,
            reference_role="none",
            notes="Offline public-domain low-light/noise asset. Main gate: SR must not amplify noise, invent fake texture, or introduce visible color shift.",
        ),
    ]


def evaluate_case(root: Path, case: EvalCase, contact_dir: Path) -> dict[str, str]:
    input_image = read_image(case.input_path)
    bicubic = read_image(case.bicubic_path)
    candidate = read_image(case.candidate_path)
    reference = read_image(case.reference_path)

    candidate_sharpness = laplacian_variance(candidate)
    bicubic_sharpness = laplacian_variance(bicubic)
    sharpness_ratio = None
    if candidate_sharpness is not None and bicubic_sharpness not in (None, 0):
        sharpness_ratio = candidate_sharpness / bicubic_sharpness

    psnr_value = None
    ssim_value = None
    diff_role = "bicubic" if reference is None else case.reference_role
    diff_base = bicubic if reference is None else reference
    diff_value = mean_abs_diff(candidate, diff_base) if diff_base is not None else None
    pass_fail_hint = "visual_review_required"
    if reference is not None:
        psnr_value = psnr(reference, candidate)
        ssim_value = ssim(reference, candidate)
        pass_fail_hint = "candidate_close_to_reference" if psnr_value >= 40.0 else "inspect_reference_delta"

    contact_sheet_path = write_contact_sheet(contact_dir, case, input_image, bicubic, candidate, reference)

    return {
        "case_id": case.case_id,
        "scenario": case.scenario,
        "input_path": rel(root, case.input_path),
        "bicubic_path": rel(root, case.bicubic_path),
        "candidate_path": rel(root, case.candidate_path),
        "candidate_role": case.candidate_role,
        "reference_path": rel(root, case.reference_path),
        "reference_role": case.reference_role,
        "input_size": image_size(input_image),
        "candidate_size": image_size(candidate),
        "psnr_vs_reference": fmt(psnr_value, 2),
        "ssim_vs_reference": fmt(ssim_value, 4),
        "sharpness_laplacian_bicubic": fmt(bicubic_sharpness, 2),
        "sharpness_laplacian_candidate": fmt(candidate_sharpness, 2),
        "sharpness_ratio_candidate_over_bicubic": fmt(sharpness_ratio, 3),
        "mean_abs_diff_vs_" + diff_role: fmt(diff_value, 3),
        "quality_boundary": (
            "PSNR/SSIM check only" if reference is not None
            else "No reference: use visual checklist for text/edges/texture/color/geometry/artifacts"
        ),
        "pass_fail_hint": pass_fail_hint,
        "contact_sheet_path": rel(root, contact_sheet_path),
        "notes": case.notes,
    }


def review_template_row(row: dict[str, str]) -> dict[str, str]:
    manual = {
        "host_flower_tflite_vs_pytorch": {
            "preliminary_decision": "pass",
            "preliminary_reason": "TFLite output is effectively identical to PyTorch float reference; this checks conversion consistency only.",
            "text_readability": "not_applicable",
            "edge_clarity": "pass_consistency_only",
            "texture_naturalness": "pass_consistency_only",
            "color_shift": "pass_no_obvious_shift_vs_reference",
            "geometry_or_rotation": "pass_same_as_reference",
            "ringing_or_halo": "not_judged_for_subjective_quality",
            "fake_texture_or_noise": "not_judged_for_subjective_quality",
            "final_decision": "pass",
            "human_notes": "Use this case to verify float TFLite conversion, not to prove real camera quality.",
        },
        "host_photo_tflite_vs_pytorch": {
            "preliminary_decision": "pass",
            "preliminary_reason": "TFLite output is effectively identical to PyTorch float reference; this checks conversion consistency only.",
            "text_readability": "not_applicable",
            "edge_clarity": "pass_consistency_only",
            "texture_naturalness": "pass_consistency_only",
            "color_shift": "pass_no_obvious_shift_vs_reference",
            "geometry_or_rotation": "pass_same_as_reference",
            "ringing_or_halo": "not_judged_for_subjective_quality",
            "fake_texture_or_noise": "not_judged_for_subjective_quality",
            "final_decision": "pass",
            "human_notes": "Use this case to verify float TFLite conversion, not to prove real camera quality.",
        },
        "d7_cpu_camera_roi": {
            "preliminary_decision": "conditional",
            "preliminary_reason": "No real HR reference; automated metrics are only proxies. Human visual review is required before using as quality evidence.",
            "text_readability": "not_applicable_or_unreadable_source",
            "edge_clarity": "pass_sharper_than_bicubic",
            "texture_naturalness": "conditional_possible_oversharpening",
            "color_shift": "pass_no_major_shift_seen",
            "geometry_or_rotation": "pass_same_orientation_as_input",
            "ringing_or_halo": "conditional_high_contrast_edges_need_caution",
            "fake_texture_or_noise": "conditional_not_enough_scene_coverage",
            "final_decision": "conditional",
            "human_notes": "SR is visibly sharper than bicubic and geometry is consistent, but this scene lacks readable text/ground truth; use as visual sanity evidence only.",
        },
        "d7_gpu_camera_roi": {
            "preliminary_decision": "conditional",
            "preliminary_reason": "No real HR reference; automated metrics are only proxies. Human visual review is required before using as quality evidence.",
            "text_readability": "conditional_chart_is_clearer_but_not_full_text_test",
            "edge_clarity": "pass_sharper_than_bicubic",
            "texture_naturalness": "conditional_possible_oversharpening",
            "color_shift": "pass_no_major_shift_seen",
            "geometry_or_rotation": "pass_same_orientation_as_input",
            "ringing_or_halo": "conditional_high_contrast_edges_need_caution",
            "fake_texture_or_noise": "conditional_not_enough_scene_coverage",
            "final_decision": "conditional",
            "human_notes": "Good current demo evidence: GPU output is sharper than bicubic and keeps geometry, but still needs a dedicated text/low-light set before final quality claims.",
        },
        "d75_highres_256_still": {
            "preliminary_decision": "fail",
            "preliminary_reason": "No real HR reference; visual review found geometry/orientation mismatch against bicubic/input.",
            "text_readability": "fail_text_like_card_is_not_reliable",
            "edge_clarity": "conditional_sharper_but_not_valid_due_geometry",
            "texture_naturalness": "fail_not_judged_because_geometry_mismatch",
            "color_shift": "conditional_no_primary_issue",
            "geometry_or_rotation": "fail_candidate_is_horizontally_mismatched_vs_bicubic",
            "ringing_or_halo": "not_judged_because_geometry_mismatch",
            "fake_texture_or_noise": "not_judged_because_geometry_mismatch",
            "final_decision": "fail",
            "human_notes": "Do not use this D75 256 sample as a quality pass. It is useful bug evidence: candidate SR does not match the bicubic/input geometry, likely layout/rotation/mirroring handling needs fixing before 256 still evidence is trusted.",
        },
        "offline_text_edge_cpu": {
            "preliminary_decision": "conditional",
            "preliminary_reason": "Dedicated offline text/edge case now exists and is reproducible; final decision still needs human visual review on the contact sheet.",
            "text_readability": "todo_review_letters_are_not_deformed",
            "edge_clarity": "todo_compare_against_bicubic",
            "texture_naturalness": "not_primary_for_this_case",
            "color_shift": "todo_check_no_obvious_shift",
            "geometry_or_rotation": "todo_check_same_orientation_as_input",
            "ringing_or_halo": "todo_check_high_contrast_edges",
            "fake_texture_or_noise": "todo_check_no_false_strokes",
            "final_decision": "todo",
            "human_notes": "Use this as the mandatory text/edge acceptance case before D8 quantization. A sharper result is not enough if letters become less readable.",
        },
        "offline_lowlight_noise_cpu": {
            "preliminary_decision": "conditional",
            "preliminary_reason": "Dedicated offline low-light/noise case now exists and is reproducible; final decision still needs human visual review on the contact sheet.",
            "text_readability": "not_applicable",
            "edge_clarity": "todo_check_useful_detail_vs_noise",
            "texture_naturalness": "todo_check_natural_scene_texture",
            "color_shift": "todo_check_no_obvious_shift",
            "geometry_or_rotation": "todo_check_same_orientation_as_input",
            "ringing_or_halo": "todo_check_bright_edge_halo",
            "fake_texture_or_noise": "todo_check_noise_not_amplified_or_hallucinated",
            "final_decision": "todo",
            "human_notes": "Use this as the mandatory low-light/noise acceptance case before D8 quantization. Reject candidates that look sharper only because noise is amplified.",
        },
    }
    if row["case_id"] in manual:
        result = {
            "case_id": row["case_id"],
            "scenario": row["scenario"],
            "contact_sheet_path": row["contact_sheet_path"],
            "candidate_role": row["candidate_role"],
        }
        result.update(manual[row["case_id"]])
        return result

    has_reference = bool(row.get("reference_path"))
    if has_reference and row.get("pass_fail_hint") == "candidate_close_to_reference":
        preliminary_decision = "pass"
        preliminary_reason = "TFLite output is effectively identical to PyTorch float reference; this checks conversion consistency only."
    else:
        preliminary_decision = "conditional"
        preliminary_reason = "No real HR reference; automated metrics are only proxies. Human visual review is required before using as quality evidence."
    return {
        "case_id": row["case_id"],
        "scenario": row["scenario"],
        "contact_sheet_path": row["contact_sheet_path"],
        "candidate_role": row["candidate_role"],
        "preliminary_decision": preliminary_decision,
        "preliminary_reason": preliminary_reason,
        "text_readability": "todo_if_text_present",
        "edge_clarity": "todo",
        "texture_naturalness": "todo",
        "color_shift": "todo",
        "geometry_or_rotation": "todo",
        "ringing_or_halo": "todo",
        "fake_texture_or_noise": "todo",
        "final_decision": "todo",
        "human_notes": "todo",
    }


def write_csv(rows: list[dict[str, str]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    for row in rows:
        for key in row.keys():
            if key not in fieldnames:
                fieldnames.append(key)
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Repository root. Defaults to the parent of RB5_SR_lab.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parent / "results" / "eval_baseline" / "baseline_metrics.csv",
        help="CSV output path.",
    )
    parser.add_argument(
        "--review-output",
        type=Path,
        default=Path(__file__).resolve().parent / "results" / "eval_baseline" / "acceptance_review_template.csv",
        help="CSV template for human visual acceptance review.",
    )
    parser.add_argument(
        "--contact-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "results" / "eval_baseline" / "contact_sheets",
        help="Directory for side-by-side comparison images.",
    )
    args = parser.parse_args()

    root = args.repo_root.resolve()
    rows: list[dict[str, str]] = []
    skipped: list[str] = []
    for case in build_cases(root):
        if existing_case(case):
            rows.append(evaluate_case(root, case, args.contact_dir))
        else:
            skipped.append(case.case_id)

    if not rows:
        raise SystemExit("No eval cases found. Check project_assets and RB5_SR_lab/results.")

    write_csv(rows, args.output)
    write_csv([review_template_row(row) for row in rows], args.review_output)
    print(f"[ok] wrote {args.output}")
    print(f"[ok] wrote {args.review_output}")
    print(f"[ok] wrote contact sheets under {args.contact_dir}")
    print(f"[ok] evaluated {len(rows)} cases")
    if skipped:
        print(f"[warn] skipped missing cases: {', '.join(skipped)}")


if __name__ == "__main__":
    main()
