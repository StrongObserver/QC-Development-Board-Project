"""Compare two qnn-net-run result folders case by case."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


def read_rows(path: Path) -> dict[str, dict[str, str]]:
    with (path / "metrics.csv").open("r", encoding="utf-8-sig", newline="") as f:
        return {row["case_id"]: row for row in csv.DictReader(f)}


def f(row: dict[str, str], key: str) -> float:
    value = row.get(key, "")
    return float(value) if value not in ("", None) else 0.0


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def avg(rows: list[dict[str, object]], key: str) -> float:
    values = [float(row[key]) for row in rows if row.get(key) not in ("", None)]
    return sum(values) / len(values) if values else 0.0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--outdir", type=Path, required=True)
    parser.add_argument("--baseline-label", default="baseline")
    parser.add_argument("--candidate-label", default="candidate")
    args = parser.parse_args()

    args.outdir.mkdir(parents=True, exist_ok=True)
    baseline = read_rows(args.baseline)
    candidate = read_rows(args.candidate)
    rows: list[dict[str, object]] = []
    for case_id in sorted(set(baseline) & set(candidate)):
        b = baseline[case_id]
        c = candidate[case_id]
        rows.append(
            {
                "case_id": case_id,
                "category": c.get("category") or b.get("category"),
                "baseline_psnr": f"{f(b, 'psnr_qnn_vs_hr'):.3f}",
                "candidate_psnr": f"{f(c, 'psnr_qnn_vs_hr'):.3f}",
                "delta_psnr": f"{f(c, 'psnr_qnn_vs_hr') - f(b, 'psnr_qnn_vs_hr'):.3f}",
                "baseline_ssim": f"{f(b, 'ssim_qnn_vs_hr'):.5f}",
                "candidate_ssim": f"{f(c, 'ssim_qnn_vs_hr'):.5f}",
                "delta_ssim": f"{f(c, 'ssim_qnn_vs_hr') - f(b, 'ssim_qnn_vs_hr'):.5f}",
                "baseline_qnn_accel_us": f"{f(b, 'qnn_accelerator_execute_p50_us') or f(b, 'qnn_accelerator_execute_us'):.1f}",
                "candidate_qnn_accel_us": f"{f(c, 'qnn_accelerator_execute_p50_us') or f(c, 'qnn_accelerator_execute_us'):.1f}",
                "delta_qnn_accel_us": f"{(f(c, 'qnn_accelerator_execute_p50_us') or f(c, 'qnn_accelerator_execute_us')) - (f(b, 'qnn_accelerator_execute_p50_us') or f(b, 'qnn_accelerator_execute_us')):.1f}",
                "baseline_netrun_us": f"{f(b, 'netrun_execute_p50_us') or f(b, 'netrun_execute_us'):.1f}",
                "candidate_netrun_us": f"{f(c, 'netrun_execute_p50_us') or f(c, 'netrun_execute_us'):.1f}",
                "delta_netrun_us": f"{(f(c, 'netrun_execute_p50_us') or f(c, 'netrun_execute_us')) - (f(b, 'netrun_execute_p50_us') or f(b, 'netrun_execute_us')):.1f}",
                "baseline_decision": b.get("auto_loop_decision", ""),
                "candidate_decision": c.get("auto_loop_decision", ""),
            }
        )

    write_csv(args.outdir / "comparison_metrics.csv", rows)
    avg_delta_psnr = avg(rows, "delta_psnr")
    avg_delta_ssim = avg(rows, "delta_ssim")
    avg_delta_accel = avg(rows, "delta_qnn_accel_us")
    improved = sum(1 for row in rows if float(row["delta_psnr"]) > 0.0)
    worsened = sum(1 for row in rows if float(row["delta_psnr"]) < 0.0)
    summary = [
        "# QNN Run Comparison",
        "",
        f"- baseline: `{args.baseline}`",
        f"- candidate: `{args.candidate}`",
        f"- baseline_label: `{args.baseline_label}`",
        f"- candidate_label: `{args.candidate_label}`",
        f"- cases compared: {len(rows)}",
        "",
        "## Aggregate",
        "",
        f"- average delta PSNR(candidate-baseline): `{avg_delta_psnr:.3f} dB`",
        f"- average delta SSIM(candidate-baseline): `{avg_delta_ssim:.5f}`",
        f"- average delta QNN accelerator execute: `{avg_delta_accel:.1f} us`",
        f"- PSNR improved / worsened: `{improved}/{worsened}`",
        "",
        "## Decision Boundary",
        "",
        "Use this as numeric evidence only. Contact sheets and human review still own final visual quality claims.",
    ]
    (args.outdir / "SUMMARY.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
    print(f"[ok] wrote {args.outdir}")


if __name__ == "__main__":
    main()
