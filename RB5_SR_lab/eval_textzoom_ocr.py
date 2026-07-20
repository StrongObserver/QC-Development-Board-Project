"""Small TextZoom OCR/readability evaluation for RB5 SR outputs.

This script keeps the scope deliberately small: sample a few easy/medium/hard
TextZoom cases, run bicubic/float/W8A8 outputs, and compare OCR text against the
TextZoom label. It is diagnostic evidence, not a hard quality gate.
"""

from __future__ import annotations

import argparse
import csv
import shutil
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
from ai_edge_litert.interpreter import Interpreter


REPO_ROOT = Path(__file__).resolve().parents[1]
TEXTZOOM_MANIFEST = REPO_ROOT / "evalhub_data" / "derived" / "textzoom_test_128x4_v1" / "manifest.csv"
RESULTS_ROOT = REPO_ROOT / "RB5_SR_lab" / "results" / "textzoom_ocr"
TESSERACT_CANDIDATES = [
    Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
    Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"),
]
TESSERACT_SEARCH_ROOTS = [
    Path.home() / "AppData" / "Local" / "Doubao" / "User Data" / "Default" / "sandbox_envs_dir" / "envs",
]


@dataclass(frozen=True)
class TextZoomCase:
    case_id: str
    category: str
    lr_128: Path
    bicubic_512: Path
    hr_512: Path
    text_label: str


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
        raise ValueError(f"invalid input quantization: {tensor}")
    info = np.iinfo(tensor["dtype"])
    q = np.round(x / scale + zero_point)
    return np.clip(q, info.min, info.max).astype(tensor["dtype"])


def dequantize_if_needed(y: np.ndarray, tensor: dict) -> np.ndarray:
    if tensor["dtype"] == np.float32:
        return y.astype(np.float32)
    scale, zero_point = tensor["quantization"]
    if scale == 0:
        raise ValueError(f"invalid output quantization: {tensor}")
    return (y.astype(np.float32) - zero_point) * scale


def run_model(model_path: Path, image_bgr: np.ndarray) -> tuple[np.ndarray, float]:
    interpreter = Interpreter(model_path=str(model_path))
    interpreter.allocate_tensors()
    inp = interpreter.get_input_details()[0]
    out = interpreter.get_output_details()[0]
    rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    x = quantize_if_needed(rgb[None, ...], inp)
    interpreter.set_tensor(inp["index"], x)
    interpreter.invoke()
    timings = []
    for _ in range(2):
        interpreter.set_tensor(inp["index"], x)
        t0 = time.perf_counter()
        interpreter.invoke()
        timings.append((time.perf_counter() - t0) * 1000.0)
    y = dequantize_if_needed(interpreter.get_tensor(out["index"]), out)[0]
    out_bgr = cv2.cvtColor((np.clip(y, 0, 1) * 255.0).round().astype(np.uint8), cv2.COLOR_RGB2BGR)
    return out_bgr, float(np.median(timings))


def normalize_text(text: str) -> str:
    return "".join(ch.lower() for ch in text.strip() if ch.isalnum())


def edit_distance(a: str, b: str) -> int:
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        cur = [i]
        for j, cb in enumerate(b, start=1):
            cost = 0 if ca == cb else 1
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost))
        prev = cur
    return prev[-1]


def similarity(label: str, pred: str) -> float:
    a = normalize_text(label)
    b = normalize_text(pred)
    denom = max(len(a), len(b), 1)
    return max(0.0, 1.0 - edit_distance(a, b) / denom)


def run_ocr(tesseract: Path, image_path: Path) -> str:
    cmd = [
        str(tesseract),
        str(image_path),
        "stdout",
        "--psm",
        "7",
        "-l",
        "eng",
        "-c",
        "tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_.:,/()@'",
    ]
    result = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    return " ".join(result.stdout.split())


def resolve_tesseract(user_path: str) -> Path:
    if user_path:
        path = Path(user_path)
        if path.exists():
            return path
        raise FileNotFoundError(f"tesseract not found: {path}")
    path_from_env = shutil.which("tesseract")
    if path_from_env:
        return Path(path_from_env)
    for path in TESSERACT_CANDIDATES:
        if path.exists():
            return path
    for root in TESSERACT_SEARCH_ROOTS:
        if root.exists():
            matches = sorted(root.glob("*/tesseract-ocr/tesseract.exe"))
            if matches:
                return matches[0]
    raise FileNotFoundError("tesseract not found. Pass --tesseract <path-to-tesseract.exe>.")


def panel(image: np.ndarray, title: str, width: int = 220) -> np.ndarray:
    body = cv2.resize(image, (width, width), interpolation=cv2.INTER_AREA)
    header = np.full((44, width, 3), 24, dtype=np.uint8)
    cv2.putText(header, title[:25], (8, 27), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
    return np.vstack([header, body])


def write_case_sheet(path: Path, lr: np.ndarray, bicubic: np.ndarray, float_out: np.ndarray, w8a8_out: np.ndarray, hr: np.ndarray, label: str) -> None:
    sheet = np.hstack([
        panel(lr, f"LR {label}"),
        panel(bicubic, "bicubic"),
        panel(float_out, "float"),
        panel(w8a8_out, "W8A8"),
        panel(hr, "HR"),
    ])
    cv2.imwrite(str(path), sheet)


def load_cases(manifest: Path, per_split: int) -> list[TextZoomCase]:
    selected: list[TextZoomCase] = []
    counts = {"textzoom_easy": 0, "textzoom_medium": 0, "textzoom_hard": 0}
    with manifest.open("r", newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            category = row["category"]
            label = row.get("text_label", "")
            if category not in counts or counts[category] >= per_split:
                continue
            if len(normalize_text(label)) < 3:
                continue
            selected.append(
                TextZoomCase(
                    case_id=row["case_id"],
                    category=category,
                    lr_128=Path(row["lr_128"]),
                    bicubic_512=Path(row["bicubic_512"]),
                    hr_512=Path(row["hr_512"]),
                    text_label=label,
                )
            )
            counts[category] += 1
            if all(count >= per_split for count in counts.values()):
                break
    return selected


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_summary(out_dir: Path, rows: list[dict[str, str]]) -> None:
    variants = ["bicubic", "float", "w8a8", "hr"]
    averages = {}
    for variant in variants:
        values = [float(row[f"{variant}_ocr_similarity"]) for row in rows]
        averages[variant] = sum(values) / len(values) if values else 0.0
    lines = [
        "# TextZoom OCR Mini Evaluation",
        "",
        f"- cases: {len(rows)}",
        "- scope: TextZoom easy/medium/hard mini sample",
        "- boundary: diagnostic OCR/readability evidence, not a hard quality gate",
        "",
        "## Average OCR Similarity",
        "",
        "| variant | similarity |",
        "| --- | ---: |",
    ]
    for variant in variants:
        lines.append(f"| `{variant}` | {averages[variant]:.3f} |")
    lines.extend(
        [
            "",
            "## Outputs",
            "",
            f"- metrics: `{out_dir / 'ocr_metrics.csv'}`",
            f"- contact sheets: `{out_dir / 'cases'}`",
            "",
            "## Interpretation Rule",
            "",
            "Use this only as text-fidelity diagnostic evidence. If OCR disagrees with visual review, visual review owns the final decision.",
        ]
    )
    (out_dir / "SUMMARY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=TEXTZOOM_MANIFEST)
    parser.add_argument("--run-id", default="")
    parser.add_argument("--per-split", type=int, default=5)
    parser.add_argument("--tesseract", default="")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    tesseract = resolve_tesseract(args.tesseract)
    run_id = args.run_id or datetime.now().strftime("textzoom_ocr_%Y%m%d_%H%M%S")
    out_dir = RESULTS_ROOT / run_id
    case_dir = out_dir / "cases"
    case_dir.mkdir(parents=True, exist_ok=True)
    float_model = REPO_ROOT / "RB5_SR_lab" / "export_assets" / "real_esrgan_general_x4v3-tflite-float" / "real_esrgan_general_x4v3.tflite"
    w8a8_model = REPO_ROOT / "RB5VisionLab" / "app" / "src" / "main" / "assets" / "real_esrgan_general_x4v3_w8a8.tflite"
    cases = load_cases(args.manifest, args.per_split)
    rows: list[dict[str, str]] = []
    for index, case in enumerate(cases, start=1):
        print(f"[{index}/{len(cases)}] {case.case_id} {case.text_label}")
        lr = read_image(case.lr_128)
        bicubic = read_image(case.bicubic_512)
        hr = read_image(case.hr_512)
        float_out, float_ms = run_model(float_model, lr)
        w8a8_out, w8a8_ms = run_model(w8a8_model, lr)
        current_dir = case_dir / case.case_id
        current_dir.mkdir(parents=True, exist_ok=True)
        image_paths = {
            "lr": current_dir / "lr_128.png",
            "bicubic": current_dir / "bicubic_512.png",
            "float": current_dir / "float_512.png",
            "w8a8": current_dir / "w8a8_512.png",
            "hr": current_dir / "hr_512.png",
        }
        cv2.imwrite(str(image_paths["lr"]), lr)
        cv2.imwrite(str(image_paths["bicubic"]), bicubic)
        cv2.imwrite(str(image_paths["float"]), float_out)
        cv2.imwrite(str(image_paths["w8a8"]), w8a8_out)
        cv2.imwrite(str(image_paths["hr"]), hr)
        sheet_path = current_dir / "case_contact_sheet.png"
        write_case_sheet(sheet_path, lr, bicubic, float_out, w8a8_out, hr, case.text_label)
        ocr = {variant: run_ocr(tesseract, path) for variant, path in image_paths.items() if variant != "lr"}
        rows.append(
            {
                "case_id": case.case_id,
                "category": case.category,
                "text_label": case.text_label,
                "bicubic_ocr": ocr["bicubic"],
                "float_ocr": ocr["float"],
                "w8a8_ocr": ocr["w8a8"],
                "hr_ocr": ocr["hr"],
                "bicubic_ocr_similarity": f"{similarity(case.text_label, ocr['bicubic']):.3f}",
                "float_ocr_similarity": f"{similarity(case.text_label, ocr['float']):.3f}",
                "w8a8_ocr_similarity": f"{similarity(case.text_label, ocr['w8a8']):.3f}",
                "hr_ocr_similarity": f"{similarity(case.text_label, ocr['hr']):.3f}",
                "float_ms": f"{float_ms:.1f}",
                "w8a8_ms": f"{w8a8_ms:.1f}",
                "contact_sheet": str(sheet_path),
                "metric_role": "diagnostic_only",
            }
        )
    write_csv(out_dir / "ocr_metrics.csv", rows)
    write_summary(out_dir, rows)
    print(f"[ok] wrote {out_dir}")


if __name__ == "__main__":
    main()
