"""Compare AIMET-Torch simulated INT8 before/after CLE on fixed inputs."""

from __future__ import annotations

import argparse
import copy
import csv
import os
from pathlib import Path

import cv2
import numpy as np
import torch

from infer_realesrgan import load_model


def psnr(a: np.ndarray, b: np.ndarray) -> float:
    mse = np.mean((a.astype(np.float64) - b.astype(np.float64)) ** 2)
    return 99.0 if mse == 0 else float(10.0 * np.log10((255.0 * 255.0) / mse))


def mad(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.mean(np.abs(a.astype(np.float32) - b.astype(np.float32))))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def load_input(path: Path, side: int) -> tuple[np.ndarray, torch.Tensor]:
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        raise FileNotFoundError(path)
    if image.shape[:2] != (side, side):
        image = cv2.resize(image, (side, side), interpolation=cv2.INTER_CUBIC)
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    tensor = torch.from_numpy(rgb).permute(2, 0, 1).unsqueeze(0)
    return image, tensor


def tensor_to_bgr(y: torch.Tensor) -> np.ndarray:
    arr = y.detach().clamp(0, 1).squeeze(0).permute(1, 2, 0).cpu().numpy()
    return cv2.cvtColor((arr * 255.0).round().astype(np.uint8), cv2.COLOR_RGB2BGR)


def default_cases(repo_root: Path) -> list[tuple[str, Path]]:
    candidates = [
        ("flower", repo_root / "RB5_SR_lab" / "inputs" / "flower.png"),
        ("photo", repo_root / "RB5_SR_lab" / "inputs" / "photo.png"),
        (
            "offline_text_edge",
            repo_root / "project_assets" / "offline_eval" / "OFFLINE_TEXT_EDGE_20251110_055715_CPU_input_128.png",
        ),
        (
            "offline_lowlight_noise",
            repo_root / "project_assets" / "offline_eval" / "OFFLINE_LOWLIGHT_NOISE_20251110_055715_CPU_input_128.png",
        ),
    ]
    return [(name, path) for name, path in candidates if path.exists()]


def run_quantsim(model: torch.nn.Module, calibration_inputs: list[torch.Tensor], eval_input: torch.Tensor) -> torch.Tensor:
    from aimet_common.defs import QuantScheme
    from aimet_torch.quantsim import QuantizationSimModel

    dummy = torch.rand_like(eval_input)
    sim = QuantizationSimModel(
        model,
        dummy,
        quant_scheme=QuantScheme.post_training_tf_enhanced,
        default_output_bw=8,
        default_param_bw=8,
        in_place=False,
    )

    def forward_pass(qmodel: torch.nn.Module, inputs: list[torch.Tensor]) -> None:
        qmodel.eval()
        with torch.no_grad():
            for item in inputs:
                _ = qmodel(item)

    sim.compute_encodings(forward_pass, calibration_inputs)
    sim.model.eval()
    with torch.no_grad():
        return sim.model(eval_input)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--weights", default="RB5_SR_lab/weights/realesr-general-x4v3.pth")
    parser.add_argument("--side", type=int, default=128)
    parser.add_argument("--outdir", default="RB5_SR_lab/results/aimet_torch_quantsim_compare/20260721_realesrgan128")
    return parser.parse_args()


def main() -> None:
    os.environ.setdefault("PYTHONUTF8", "1")
    from aimet_torch.cross_layer_equalization import equalize_model

    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    out_dir = Path(args.outdir)
    image_dir = out_dir / "images"
    image_dir.mkdir(parents=True, exist_ok=True)

    cases = default_cases(repo_root)
    if not cases:
        raise RuntimeError("no fixed input cases found")
    loaded = [(case_id, *load_input(path, args.side), path) for case_id, path in cases]
    calibration_inputs = [item[2] for item in loaded]

    base_model = load_model(args.weights, torch.device("cpu")).eval()
    cle_model = copy.deepcopy(base_model).eval()
    equalize_model(cle_model, dummy_input=torch.rand(1, 3, args.side, args.side))

    rows: list[dict[str, object]] = []
    for case_id, input_bgr, eval_input, input_path in loaded:
        with torch.no_grad():
            float_before = base_model(eval_input)
            float_after_cle = cle_model(eval_input)
        quant_before = run_quantsim(base_model, calibration_inputs, eval_input)
        quant_after_cle = run_quantsim(cle_model, calibration_inputs, eval_input)

        float_bgr = tensor_to_bgr(float_before)
        cle_float_bgr = tensor_to_bgr(float_after_cle)
        quant_before_bgr = tensor_to_bgr(quant_before)
        quant_after_bgr = tensor_to_bgr(quant_after_cle)
        bicubic = cv2.resize(input_bgr, (args.side * 4, args.side * 4), interpolation=cv2.INTER_CUBIC)

        for suffix, image in [
            ("input_128", input_bgr),
            ("bicubic_512", bicubic),
            ("float_512", float_bgr),
            ("cle_float_512", cle_float_bgr),
            ("quantsim_512", quant_before_bgr),
            ("cle_quantsim_512", quant_after_bgr),
        ]:
            cv2.imwrite(str(image_dir / f"{case_id}_{suffix}.png"), image)
        cv2.imwrite(
            str(image_dir / f"{case_id}_contact_sheet.png"),
            np.hstack([bicubic, float_bgr, quant_before_bgr, quant_after_bgr]),
        )
        before_psnr = psnr(float_bgr, quant_before_bgr)
        after_psnr = psnr(float_bgr, quant_after_bgr)
        before_mad = mad(float_bgr, quant_before_bgr)
        after_mad = mad(float_bgr, quant_after_bgr)
        rows.append(
            {
                "case_id": case_id,
                "input_path": str(input_path),
                "psnr_float_vs_quantsim": f"{before_psnr:.3f}",
                "psnr_float_vs_cle_quantsim": f"{after_psnr:.3f}",
                "psnr_delta_cle_minus_base": f"{after_psnr - before_psnr:.3f}",
                "mad_float_vs_quantsim": f"{before_mad:.6f}",
                "mad_float_vs_cle_quantsim": f"{after_mad:.6f}",
                "mad_delta_base_minus_cle": f"{before_mad - after_mad:.6f}",
                "psnr_float_vs_cle_float": f"{psnr(float_bgr, cle_float_bgr):.3f}",
                "boundary": "AIMET-Torch QuantSim only; not Android TFLite/QNN output.",
            }
        )

    write_csv(out_dir / "metrics.csv", rows)
    avg_delta = float(np.mean([float(row["psnr_delta_cle_minus_base"]) for row in rows]))
    summary = [
        "# AIMET-Torch QuantSim Compare",
        "",
        f"- cases: {len(rows)}",
        f"- avg PSNR delta CLE-minus-base: `{avg_delta:.3f}` dB",
        "- boundary: simulated INT8 only, not exported TFLite/QNN evidence",
        "",
        "## Decision",
        "",
    ]
    if avg_delta > 0.05:
        summary.append("CLE shows a measurable simulated-quantization improvement and is worth trying in the export path.")
    elif avg_delta < -0.05:
        summary.append("CLE hurts the simulated quantization result on this small slice; do not promote without more evidence.")
    else:
        summary.append("CLE is effectively neutral on this small simulated quantization slice; keep it as evidence but do not expect a large recovery.")
    summary.extend(
        [
            "",
            "## Outputs",
            "",
            f"- metrics: `{out_dir / 'metrics.csv'}`",
            f"- images: `{image_dir}`",
        ]
    )
    (out_dir / "SUMMARY.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
    print(f"[ok] wrote {out_dir}")
    print(f"[cmp] avg_delta={avg_delta:.3f}dB")


if __name__ == "__main__":
    main()
