"""Compare Real-ESRGAN W8A8 and QuickSRNetSmall W8A8 on RB5_SR_Benchmark_v1.

This is a host-side model comparison runner. It does not claim RB5 app e2e
latency. Its purpose is to create a first, fixed-input quality/latency/size
comparison for the D9 lightweight SR direction.
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
from ai_edge_litert.interpreter import Interpreter


REPO_ROOT = Path(__file__).resolve().parents[1]
BENCHMARK_ROOT = Path(r"C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1")


@dataclass(frozen=True)
class BenchmarkCase:
    case_id: str
    category: str
    dataset: str
    source_id: str
    lr_128: Path
    bicubic_512: Path
    hr_512: Path
    selection_note: str


def git_revision(repo_root: Path) -> str:
    try:
        head = subprocess.check_output(
            ["git", "-C", str(repo_root), "rev-parse", "--short", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        status = subprocess.check_output(
            ["git", "-C", str(repo_root), "status", "--short"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        return head + ("-dirty" if status else "")
    except Exception:
        return ""


def load_cases(input_set: str) -> list[BenchmarkCase]:
    manifest: dict[str, dict[str, str]] = {}
    with (BENCHMARK_ROOT / "manifest.csv").open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            manifest[row["case_id"]] = row

    if input_set == "smoke":
        cases: list[BenchmarkCase] = []
        with (BENCHMARK_ROOT / "qa" / "smoke_subset.csv").open("r", encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                m = manifest[row["case_id"]]
                cases.append(
                    BenchmarkCase(
                        case_id=row["case_id"],
                        category=row["category"],
                        dataset=row["dataset"],
                        source_id=row["source_id"],
                        lr_128=Path(m["lr_128"]),
                        bicubic_512=Path(m["bicubic_512"]),
                        hr_512=Path(m["hr_512"]),
                        selection_note=row.get("why_in_smoke", ""),
                    )
                )
        return cases

    if input_set == "full":
        return [
            BenchmarkCase(
                case_id=row["case_id"],
                category=row["category"],
                dataset=row["dataset"],
                source_id=row["source_id"],
                lr_128=Path(row["lr_128"]),
                bicubic_512=Path(row["bicubic_512"]),
                hr_512=Path(row["hr_512"]),
                selection_note=row.get("selection_reason", ""),
            )
            for row in manifest.values()
        ]

    raise ValueError(f"unsupported input_set: {input_set}")


def first_existing(paths: list[Path]) -> Path:
    for path in paths:
        if path.exists():
            return path
    raise FileNotFoundError("none of these paths exists: " + ", ".join(str(p) for p in paths))


def read_image(path: Path) -> np.ndarray:
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        raise FileNotFoundError(path)
    return image


def quantize_if_needed(x: np.ndarray, tensor: dict) -> np.ndarray:
    if tensor["dtype"] == np.float32:
        return x.astype(np.float32)
    scale, zero_point = tensor["quantization"]
    if scale == 0:
        raise ValueError(f"invalid quantization params: {tensor}")
    info = np.iinfo(tensor["dtype"])
    q = np.round(x / scale + zero_point)
    return np.clip(q, info.min, info.max).astype(tensor["dtype"])


def dequantize_if_needed(y: np.ndarray, tensor: dict) -> np.ndarray:
    if tensor["dtype"] == np.float32:
        return y.astype(np.float32)
    scale, zero_point = tensor["quantization"]
    if scale == 0:
        raise ValueError(f"invalid quantization params: {tensor}")
    return (y.astype(np.float32) - zero_point) * scale


def run_tflite(model_path: Path, image_bgr: np.ndarray, warmup: int, runs: int) -> tuple[np.ndarray, float, float, float]:
    interpreter = Interpreter(model_path=str(model_path))
    interpreter.allocate_tensors()
    inp = interpreter.get_input_details()[0]
    out = interpreter.get_output_details()[0]
    if image_bgr.shape[:2] != (128, 128):
        raise ValueError(f"expected 128x128, got {image_bgr.shape[:2]}")

    rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    x = quantize_if_needed(rgb[None, ...], inp)

    for _ in range(warmup):
        interpreter.set_tensor(inp["index"], x)
        interpreter.invoke()

    timings: list[float] = []
    for _ in range(runs):
        interpreter.set_tensor(inp["index"], x)
        t0 = time.perf_counter()
        interpreter.invoke()
        timings.append((time.perf_counter() - t0) * 1000.0)

    y = dequantize_if_needed(interpreter.get_tensor(out["index"]), out)[0]
    out_bgr = cv2.cvtColor((np.clip(y, 0, 1) * 255.0).round().astype(np.uint8), cv2.COLOR_RGB2BGR)
    return out_bgr, float(np.mean(timings)), float(np.median(timings)), float(np.percentile(timings, 95))


def psnr(reference: np.ndarray, candidate: np.ndarray) -> float:
    mse = np.mean((reference.astype(np.float64) - candidate.astype(np.float64)) ** 2)
    return 99.0 if mse == 0 else float(10.0 * np.log10((255.0 * 255.0) / mse))


def ssim(reference: np.ndarray, candidate: np.ndarray) -> float:
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


def sharpness(image: np.ndarray) -> float:
    return float(cv2.Laplacian(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY), cv2.CV_64F).var())


def mean_abs_diff(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.mean(np.abs(a.astype(np.float64) - b.astype(np.float64))))


def panel(image: np.ndarray, title: str, width: int = 220) -> np.ndarray:
    body = cv2.resize(image, (width, width), interpolation=cv2.INTER_AREA)
    header = np.full((34, width, 3), 25, dtype=np.uint8)
    cv2.putText(header, title[:24], (8, 23), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
    return np.vstack([header, body])


def write_case_sheet(path: Path, lr: np.ndarray, bicubic: np.ndarray, realesrgan: np.ndarray, quicksr: np.ndarray, hr: np.ndarray) -> None:
    sheet = np.hstack(
        [
            panel(lr, "LR 128"),
            panel(bicubic, "bicubic 512"),
            panel(realesrgan, "RealESRGAN W8A8"),
            panel(quicksr, "QuickSR Small"),
            panel(hr, "HR 512"),
        ]
    )
    cv2.imwrite(str(path), sheet)


def write_contact_sheet(rows: list[dict[str, str]], out_path: Path) -> None:
    panels: list[np.ndarray] = []
    for row in rows:
        image = cv2.imread(row["case_contact_sheet"], cv2.IMREAD_COLOR)
        if image is None:
            continue
        thumb = cv2.resize(image, (900, 180), interpolation=cv2.INTER_AREA)
        header = np.full((34, 900, 3), 245, dtype=np.uint8)
        text = (
            f"{row['case_id']} | {row['category']} | "
            f"Real {row['realesrgan_w8a8_p50_ms']}ms PSNR {row['psnr_realesrgan_vs_hr']} | "
            f"Quick {row['quicksr_w8a8_p50_ms']}ms PSNR {row['psnr_quicksr_vs_hr']}"
        )
        cv2.putText(header, text[:125], (8, 23), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (20, 20, 20), 1, cv2.LINE_AA)
        panels.append(np.vstack([header, thumb]))
    if panels:
        cv2.imwrite(str(out_path), np.vstack(panels))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def average(rows: list[dict[str, str]], key: str) -> float:
    values = [float(row[key]) for row in rows if row.get(key)]
    return float(np.mean(values)) if values else float("nan")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-set", choices=["smoke", "full"], default="smoke")
    parser.add_argument("--run-id", default="")
    parser.add_argument("--warmup", type=int, default=1)
    parser.add_argument("--runs", type=int, default=5)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    realesrgan_model = REPO_ROOT / "RB5VisionLab" / "app" / "src" / "main" / "assets" / "real_esrgan_general_x4v3_w8a8.tflite"
    quicksr_model = first_existing(
        [
            REPO_ROOT
            / "RB5_SR_lab"
            / "export_assets"
            / "quicksrnetsmall-tflite-w8a8"
            / "quicksrnetsmall-tflite-w8a8"
            / "quicksrnetsmall.tflite",
        ]
    )
    for path in [realesrgan_model, quicksr_model]:
        if not path.exists():
            raise FileNotFoundError(path)

    run_id = args.run_id or datetime.now().strftime(f"%Y%m%d_%H%M%S_quicksrnet_small_vs_realesrgan_w8a8_{args.input_set}_host")
    out_root = BENCHMARK_ROOT / "results" / run_id
    case_root = out_root / "by_category"
    out_root.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, str]] = []
    for index, case in enumerate(load_cases(args.input_set), start=1):
        print(f"[{index}] {case.case_id}")
        lr = read_image(case.lr_128)
        bicubic = read_image(case.bicubic_512)
        hr = read_image(case.hr_512)
        realesrgan_out, real_mean, real_p50, real_p95 = run_tflite(realesrgan_model, lr, args.warmup, args.runs)
        quicksr_out, quick_mean, quick_p50, quick_p95 = run_tflite(quicksr_model, lr, args.warmup, args.runs)

        case_dir = case_root / case.category / case.case_id
        case_dir.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(case_dir / "lr_128.png"), lr)
        cv2.imwrite(str(case_dir / "bicubic_512.png"), bicubic)
        cv2.imwrite(str(case_dir / "realesrgan_w8a8_512.png"), realesrgan_out)
        cv2.imwrite(str(case_dir / "quicksrnet_small_w8a8_512.png"), quicksr_out)
        cv2.imwrite(str(case_dir / "hr_512.png"), hr)
        case_sheet = case_dir / "case_contact_sheet.png"
        write_case_sheet(case_sheet, lr, bicubic, realesrgan_out, quicksr_out, hr)

        bicubic_psnr = psnr(hr, bicubic)
        real_psnr = psnr(hr, realesrgan_out)
        quick_psnr = psnr(hr, quicksr_out)
        bicubic_sharp = sharpness(bicubic)
        rows.append(
            {
                "case_id": case.case_id,
                "category": case.category,
                "dataset": case.dataset,
                "source_id": case.source_id,
                "backend": "host_cpu_litert",
                "main_variable": "model family: Real-ESRGAN W8A8 vs QuickSRNetSmall W8A8",
                "frozen_variables": f"{args.input_set} input set; 128x128 RGB input; 512x512 output; host LiteRT CPU; warmup={args.warmup}; runs={args.runs}",
                "realesrgan_model_bytes": str(realesrgan_model.stat().st_size),
                "quicksr_model_bytes": str(quicksr_model.stat().st_size),
                "realesrgan_w8a8_mean_ms": f"{real_mean:.3f}",
                "realesrgan_w8a8_p50_ms": f"{real_p50:.3f}",
                "realesrgan_w8a8_p95_ms": f"{real_p95:.3f}",
                "quicksr_w8a8_mean_ms": f"{quick_mean:.3f}",
                "quicksr_w8a8_p50_ms": f"{quick_p50:.3f}",
                "quicksr_w8a8_p95_ms": f"{quick_p95:.3f}",
                "host_speedup_realesrgan_over_quicksr": f"{real_p50 / quick_p50:.3f}" if quick_p50 > 0 else "",
                "psnr_bicubic_vs_hr": f"{bicubic_psnr:.2f}",
                "ssim_bicubic_vs_hr": f"{ssim(hr, bicubic):.4f}",
                "psnr_realesrgan_vs_hr": f"{real_psnr:.2f}",
                "ssim_realesrgan_vs_hr": f"{ssim(hr, realesrgan_out):.4f}",
                "psnr_quicksr_vs_hr": f"{quick_psnr:.2f}",
                "ssim_quicksr_vs_hr": f"{ssim(hr, quicksr_out):.4f}",
                "psnr_delta_realesrgan_minus_bicubic": f"{real_psnr - bicubic_psnr:.2f}",
                "psnr_delta_quicksr_minus_bicubic": f"{quick_psnr - bicubic_psnr:.2f}",
                "psnr_quicksr_minus_realesrgan": f"{quick_psnr - real_psnr:.2f}",
                "mad_quicksr_vs_realesrgan": f"{mean_abs_diff(quicksr_out, realesrgan_out):.3f}",
                "sharpness_realesrgan_over_bicubic": f"{sharpness(realesrgan_out) / bicubic_sharp:.3f}" if bicubic_sharp > 0 else "",
                "sharpness_quicksr_over_bicubic": f"{sharpness(quicksr_out) / bicubic_sharp:.3f}" if bicubic_sharp > 0 else "",
                "case_contact_sheet": str(case_sheet),
                "review_hint": "Compare quality visually; QuickSRNet may be faster and more conservative, not GAN-like.",
                "metric_role": "Latency/model size are hard facts; PSNR/SSIM/sharpness are supporting evidence; contact sheet review owns quality.",
            }
        )

    write_csv(out_root / "metrics.csv", rows)
    write_contact_sheet(rows, out_root / "contact_sheet.png")
    category_rows: list[dict[str, str]] = []
    for category in sorted({row["category"] for row in rows}):
        group = [row for row in rows if row["category"] == category]
        category_rows.append(
            {
                "category": category,
                "count": str(len(group)),
                "realesrgan_p50_avg_ms": f"{average(group, 'realesrgan_w8a8_p50_ms'):.3f}",
                "quicksr_p50_avg_ms": f"{average(group, 'quicksr_w8a8_p50_ms'):.3f}",
                "speedup_avg": f"{average(group, 'host_speedup_realesrgan_over_quicksr'):.3f}",
                "psnr_realesrgan_avg": f"{average(group, 'psnr_realesrgan_vs_hr'):.2f}",
                "psnr_quicksr_avg": f"{average(group, 'psnr_quicksr_vs_hr'):.2f}",
                "psnr_quicksr_minus_realesrgan_avg": f"{average(group, 'psnr_quicksr_minus_realesrgan'):.2f}",
            }
        )
    write_csv(out_root / "category_summary.csv", category_rows)

    run_log = {
        "run_id": run_id,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M +0800"),
        "device": "Windows host",
        "app_or_script_commit": git_revision(REPO_ROOT),
        "backend": "host_cpu_litert",
        "input_set": args.input_set,
        "output_dir": str(out_root),
        "num_cases": str(len(rows)),
        "main_variable": "model family: Real-ESRGAN W8A8 vs QuickSRNetSmall W8A8",
        "frozen_variables": f"same benchmark inputs; host LiteRT CPU; warmup={args.warmup}; runs={args.runs}",
        "realesrgan_model_bytes": str(realesrgan_model.stat().st_size),
        "quicksr_model_bytes": str(quicksr_model.stat().st_size),
        "realesrgan_p50_avg_ms": f"{average(rows, 'realesrgan_w8a8_p50_ms'):.3f}",
        "quicksr_p50_avg_ms": f"{average(rows, 'quicksr_w8a8_p50_ms'):.3f}",
        "speedup_avg": f"{average(rows, 'host_speedup_realesrgan_over_quicksr'):.3f}",
        "notes": "Host-side first-pass model comparison; not RB5 QNN/app e2e.",
    }
    write_csv(out_root / "run_log.csv", [run_log])
    loop_state = {
        "run_id": run_id,
        "status": "quicksrnet_smoke_completed" if args.input_set == "smoke" else "quicksrnet_full_completed",
        "stop_reason": "model_comparison_completed",
        "next_priority_task": "human_review_contact_sheet_then_choose_app_or_full_quicksrnet_followup",
        "requires_human_review": True,
        "blocked_by": "",
        "notes": "QuickSRNetSmall W8A8 and Real-ESRGAN W8A8 were compared on the same fixed inputs. This is host LiteRT evidence only.",
        "required_next_read": [
            str(out_root / "SUMMARY.md"),
            str(out_root / "metrics.csv"),
            str(out_root / "category_summary.csv"),
            str(out_root / "contact_sheet.png"),
            str(out_root / "NEXT_ACTION.md"),
        ],
    }
    (out_root / "loop_state.json").write_text(json.dumps(loop_state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = [
        "# QuickSRNetSmall vs Real-ESRGAN W8A8 Host Comparison",
        "",
        f"- run_id: `{run_id}`",
        f"- input_set: `{args.input_set}`",
        f"- cases: {len(rows)}",
        "- backend: Windows host LiteRT CPU",
        "- boundary: not RB5 QNN/app e2e",
        "",
        "## Key Numbers",
        "",
        f"- Real-ESRGAN W8A8 model size: {realesrgan_model.stat().st_size} bytes",
        f"- QuickSRNetSmall W8A8 model size: {quicksr_model.stat().st_size} bytes",
        f"- Real-ESRGAN W8A8 average p50: {average(rows, 'realesrgan_w8a8_p50_ms'):.3f} ms",
        f"- QuickSRNetSmall W8A8 average p50: {average(rows, 'quicksr_w8a8_p50_ms'):.3f} ms",
        f"- Host speedup average: {average(rows, 'host_speedup_realesrgan_over_quicksr'):.3f}x",
        f"- Average PSNR QuickSRNet minus Real-ESRGAN: {average(rows, 'psnr_quicksr_minus_realesrgan'):.2f} dB",
        "",
        "## Outputs",
        "",
        f"- metrics: `{out_root / 'metrics.csv'}`",
        f"- category summary: `{out_root / 'category_summary.csv'}`",
        f"- contact sheet: `{out_root / 'contact_sheet.png'}`",
        f"- loop state: `{out_root / 'loop_state.json'}`",
        "",
        "## Boundary",
        "",
        "Use this as a first-pass model-family comparison. Visual review owns the final quality conclusion.",
        "",
    ]
    (out_root / "SUMMARY.md").write_text("\n".join(summary), encoding="utf-8")
    next_action = [
        "# Next Action",
        "",
        "## 当前结论",
        "",
        f"`{run_id}` 已完成 QuickSRNetSmall W8A8 与 Real-ESRGAN W8A8 的 host LiteRT `{args.input_set}` 对比。",
        "",
        "## 当前阻塞",
        "",
        "无功能阻塞。当前边界是：这不是 RB5 QNN/app e2e 证据。",
        "",
        "## 下一步最高优先级任务",
        "",
        "下一步优先做：【人工查看 contact_sheet.png，再决定 full benchmark 或 Android app 接入】",
        "",
        "## 不要做什么",
        "",
        "- 不要把 host LiteRT latency 当成 RB5 app latency。",
        "- 不要用 QuickSRNet 替代已打通的 QNN Delegate 主线。",
        "- 不要只看 PSNR；必须看 contact sheet。",
        "",
    ]
    (out_root / "NEXT_ACTION.md").write_text("\n".join(next_action), encoding="utf-8")
    print(f"[ok] wrote {out_root}")


if __name__ == "__main__":
    main()
