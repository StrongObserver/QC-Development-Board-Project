"""Post-capture tiled still-image SR MVP.

This host-side runner proves the tile path before Android app integration:

large still image -> 128x128 LR tiles -> 4x TFLite SR per tile -> stitched output

It writes artifacts under RB5_SR_lab/results by default. Do not write generated
SR outputs back into the fixed benchmark cases.
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
class TileRun:
    image: np.ndarray
    tile_ms: list[float]
    tile_count: int
    padded_width: int
    padded_height: int
    output_width: int
    output_height: int


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


def read_image(path: Path) -> np.ndarray:
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        raise FileNotFoundError(path)
    return image


def first_existing(paths: list[Path]) -> Path:
    for path in paths:
        if path.exists():
            return path
    raise FileNotFoundError("none of these paths exists: " + ", ".join(str(p) for p in paths))


def load_case_input(benchmark_root: Path, case_id: str) -> tuple[np.ndarray, str, Path]:
    manifest = benchmark_root / "manifest.csv"
    with manifest.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise ValueError(f"empty manifest: {manifest}")
    row = next((item for item in rows if item["case_id"] == case_id), rows[0])
    path = Path(row["hr_512"])
    return read_image(path), row["case_id"], path


def model_path_for(name: str) -> Path:
    assets = REPO_ROOT / "RB5VisionLab" / "app" / "src" / "main" / "assets"
    if name == "quicksr":
        return assets / "quicksrnetsmall_w8a8.tflite"
    if name == "realesrgan":
        return assets / "real_esrgan_general_x4v3_w8a8.tflite"
    raise ValueError(f"unsupported model: {name}")


def quantize_if_needed(x: np.ndarray, tensor: dict) -> np.ndarray:
    if tensor["dtype"] == np.float32:
        return x.astype(np.float32)
    scale, zero_point = tensor["quantization"]
    if scale == 0:
        raise ValueError(f"invalid input quantization params: {tensor}")
    info = np.iinfo(tensor["dtype"])
    q = np.round(x / scale + zero_point)
    return np.clip(q, info.min, info.max).astype(tensor["dtype"])


def dequantize_if_needed(y: np.ndarray, tensor: dict) -> np.ndarray:
    if tensor["dtype"] == np.float32:
        return y.astype(np.float32)
    scale, zero_point = tensor["quantization"]
    if scale == 0:
        raise ValueError(f"invalid output quantization params: {tensor}")
    return (y.astype(np.float32) - zero_point) * scale


class TfliteSrModel:
    def __init__(self, model_path: Path) -> None:
        self.model_path = model_path
        self.interpreter = Interpreter(model_path=str(model_path))
        self.interpreter.allocate_tensors()
        self.input = self.interpreter.get_input_details()[0]
        self.output = self.interpreter.get_output_details()[0]
        shape = list(self.input["shape"])
        if shape[-1] == 3:
            self.layout = "NHWC"
            self.input_h = int(shape[1])
            self.input_w = int(shape[2])
        elif shape[1] == 3:
            self.layout = "NCHW"
            self.input_h = int(shape[2])
            self.input_w = int(shape[3])
        elif shape[2] == 3:
            self.layout = "NHCW"
            self.input_h = int(shape[1])
            self.input_w = int(shape[3])
        else:
            raise ValueError(f"unsupported input shape: {shape}")
        if self.input_h != 128 or self.input_w != 128:
            raise ValueError(f"tile MVP expects 128x128 model input, got {self.input_w}x{self.input_h}")

    def run(self, tile_bgr: np.ndarray) -> tuple[np.ndarray, float]:
        if tile_bgr.shape[:2] != (self.input_h, self.input_w):
            raise ValueError(f"expected {self.input_w}x{self.input_h}, got {tile_bgr.shape[:2]}")
        rgb = cv2.cvtColor(tile_bgr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        if self.layout == "NHWC":
            x = rgb[None, ...]
        elif self.layout == "NCHW":
            x = rgb.transpose(2, 0, 1)[None, ...]
        else:
            x = rgb.transpose(0, 2, 1)[None, ...]
        x = quantize_if_needed(x, self.input)
        self.interpreter.set_tensor(self.input["index"], x)
        t0 = time.perf_counter()
        self.interpreter.invoke()
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        y = dequantize_if_needed(self.interpreter.get_tensor(self.output["index"]), self.output)[0]
        if y.shape[0] == 3:
            y = y.transpose(1, 2, 0)
        out = cv2.cvtColor((np.clip(y, 0, 1) * 255.0).round().astype(np.uint8), cv2.COLOR_RGB2BGR)
        return out, elapsed_ms


def starts_for(length: int, tile: int, stride: int) -> list[int]:
    if length <= tile:
        return [0]
    starts = list(range(0, max(1, length - tile + 1), stride))
    final = length - tile
    if starts[-1] != final:
        starts.append(final)
    return starts


def pad_to_cover(image: np.ndarray, tile: int) -> np.ndarray:
    height, width = image.shape[:2]
    pad_h = max(0, tile - height)
    pad_w = max(0, tile - width)
    if pad_h == 0 and pad_w == 0:
        return image
    return cv2.copyMakeBorder(image, 0, pad_h, 0, pad_w, cv2.BORDER_REFLECT_101)


def blend_window(size: int, overlap: int) -> np.ndarray:
    if overlap <= 0:
        return np.ones((size, size, 1), dtype=np.float32)
    ramp = np.ones(size, dtype=np.float32)
    edge = max(1, min(size // 2, overlap * 4))
    values = np.linspace(0.08, 1.0, edge, dtype=np.float32)
    ramp[:edge] = values
    ramp[-edge:] = values[::-1]
    weight = np.outer(ramp, ramp).astype(np.float32)
    return weight[:, :, None]


def run_tiled_sr(image: np.ndarray, model: TfliteSrModel, overlap: int) -> TileRun:
    tile = 128
    scale = 4
    stride = tile - overlap
    if stride <= 0:
        raise ValueError("overlap must be smaller than tile size")
    source = pad_to_cover(image, tile)
    height, width = source.shape[:2]
    x_starts = starts_for(width, tile, stride)
    y_starts = starts_for(height, tile, stride)
    out_h = height * scale
    out_w = width * scale
    acc = np.zeros((out_h, out_w, 3), dtype=np.float32)
    weights = np.zeros((out_h, out_w, 1), dtype=np.float32)
    window = blend_window(tile * scale, overlap)
    tile_ms: list[float] = []
    for y in y_starts:
        for x in x_starts:
            sr_tile, elapsed = model.run(source[y : y + tile, x : x + tile])
            tile_ms.append(elapsed)
            oy = y * scale
            ox = x * scale
            acc[oy : oy + sr_tile.shape[0], ox : ox + sr_tile.shape[1]] += sr_tile.astype(np.float32) * window
            weights[oy : oy + sr_tile.shape[0], ox : ox + sr_tile.shape[1]] += window
    stitched = acc / np.maximum(weights, 1e-6)
    target_h = image.shape[0] * scale
    target_w = image.shape[1] * scale
    out = np.clip(stitched[:target_h, :target_w], 0, 255).round().astype(np.uint8)
    return TileRun(
        image=out,
        tile_ms=tile_ms,
        tile_count=len(tile_ms),
        padded_width=width,
        padded_height=height,
        output_width=target_w,
        output_height=target_h,
    )


def seam_score(image: np.ndarray, input_width: int, input_height: int, tile: int, overlap: int) -> float:
    scale = 4
    stride = tile - overlap
    if stride <= 0:
        return 0.0
    scores: list[float] = []
    for x in range(stride, input_width, stride):
        ox = x * scale
        if 1 <= ox < image.shape[1]:
            scores.append(float(np.mean(np.abs(image[:, ox].astype(np.float32) - image[:, ox - 1].astype(np.float32)))))
    for y in range(stride, input_height, stride):
        oy = y * scale
        if 1 <= oy < image.shape[0]:
            scores.append(float(np.mean(np.abs(image[oy, :].astype(np.float32) - image[oy - 1, :].astype(np.float32)))))
    return float(np.mean(scores)) if scores else 0.0


def panel(image: np.ndarray, title: str, width: int = 420) -> np.ndarray:
    body = cv2.resize(image, (width, width), interpolation=cv2.INTER_AREA)
    header = np.full((42, width, 3), 25, dtype=np.uint8)
    cv2.putText(header, title[:34], (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (255, 255, 255), 1, cv2.LINE_AA)
    return np.vstack([header, body])


def write_contact_sheet(path: Path, input_bgr: np.ndarray, bicubic: np.ndarray, sr: np.ndarray) -> None:
    full = np.hstack([panel(input_bgr, "input still"), panel(bicubic, "bicubic x4"), panel(sr, "tiled SR x4")])
    crop_size = min(512, sr.shape[0], sr.shape[1])
    y0 = max(0, sr.shape[0] // 2 - crop_size // 2)
    x0 = max(0, sr.shape[1] // 2 - crop_size // 2)
    bicrop = bicubic[y0 : y0 + crop_size, x0 : x0 + crop_size]
    srcrop = sr[y0 : y0 + crop_size, x0 : x0 + crop_size]
    detail = np.hstack([panel(bicrop, "bicubic center crop"), panel(srcrop, "SR center crop")])
    blank = np.full((detail.shape[0], full.shape[1] - detail.shape[1], 3), 255, dtype=np.uint8)
    cv2.imwrite(str(path), np.vstack([full, np.hstack([detail, blank])]))


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=None, help="Optional still image path. Defaults to benchmark HR image.")
    parser.add_argument("--case-id", default="structure_edges_urban040")
    parser.add_argument("--model", choices=["quicksr", "realesrgan"], default="quicksr")
    parser.add_argument("--overlap", type=int, default=32)
    parser.add_argument("--run-id", default="")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.input:
        input_path = args.input
        case_id = input_path.stem
        image = read_image(input_path)
    else:
        image, case_id, input_path = load_case_input(BENCHMARK_ROOT, args.case_id)
    model_path = first_existing([model_path_for(args.model)])
    model = TfliteSrModel(model_path)
    run_id = args.run_id or datetime.now().strftime(f"%Y%m%d_%H%M%S_tile_mvp_{args.model}_{case_id}")
    out_dir = REPO_ROOT / "RB5_SR_lab" / "results" / "tile_mvp" / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    t0 = time.perf_counter()
    tile_run = run_tiled_sr(image, model, args.overlap)
    total_ms = (time.perf_counter() - t0) * 1000.0
    bicubic = cv2.resize(image, (image.shape[1] * 4, image.shape[0] * 4), interpolation=cv2.INTER_CUBIC)
    seam = seam_score(tile_run.image, image.shape[1], image.shape[0], 128, args.overlap)
    mad_vs_bicubic = float(np.mean(np.abs(tile_run.image.astype(np.float32) - bicubic.astype(np.float32))))

    input_out = out_dir / "input_still.png"
    bicubic_out = out_dir / "bicubic_x4.png"
    sr_out = out_dir / "tile_sr_x4.png"
    sheet_out = out_dir / "contact_sheet.png"
    cv2.imwrite(str(input_out), image)
    cv2.imwrite(str(bicubic_out), bicubic)
    cv2.imwrite(str(sr_out), tile_run.image)
    write_contact_sheet(sheet_out, image, bicubic, tile_run.image)

    tile_values = np.array(tile_run.tile_ms, dtype=np.float64)
    metrics = {
        "run_id": run_id,
        "model": args.model,
        "model_path": str(model_path),
        "input_path": str(input_path),
        "input_width": image.shape[1],
        "input_height": image.shape[0],
        "output_width": tile_run.output_width,
        "output_height": tile_run.output_height,
        "tile_input": "128x128",
        "tile_output": "512x512",
        "overlap_px_lr": args.overlap,
        "tile_count": tile_run.tile_count,
        "tile_p50_ms": f"{np.percentile(tile_values, 50):.3f}",
        "tile_p95_ms": f"{np.percentile(tile_values, 95):.3f}",
        "tile_sum_ms": f"{float(np.sum(tile_values)):.3f}",
        "wall_total_ms": f"{total_ms:.3f}",
        "seam_boundary_mad": f"{seam:.3f}",
        "mad_vs_bicubic": f"{mad_vs_bicubic:.3f}",
        "input_still": str(input_out),
        "bicubic_x4": str(bicubic_out),
        "tile_sr_x4": str(sr_out),
        "contact_sheet": str(sheet_out),
        "boundary": "host-side tile MVP; not Android app e2e; visual review required",
    }
    write_csv(out_dir / "metrics.csv", [metrics])
    write_csv(
        out_dir / "run_log.csv",
        [
            {
                "run_id": run_id,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M +0800"),
                "app_or_script_commit": git_revision(REPO_ROOT),
                "device": "Windows host",
                "backend": "host_cpu_litert",
                "task": "tile-mvp",
                "status": "tile_mvp_completed",
                "output_dir": str(out_dir),
                "notes": "Host-side still image tile path. Does not change Android live ROI.",
            }
        ],
    )
    (out_dir / "loop_state.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "run_id": run_id,
                "status": "tile_mvp_completed",
                "stop_reason": "host_tile_path_validated",
                "next_priority_task": "tile-eval: inspect contact_sheet and decide whether to run Real-ESRGAN tile or Android app tile entry",
                "requires_human_review": True,
                "blocked_by": "",
                "task_queue_update": "tile-mvp can move to done after artifacts are reviewed; tile-eval should become in_progress",
                "required_next_read": [
                    str(out_dir / "SUMMARY.md"),
                    str(out_dir / "metrics.csv"),
                    str(sheet_out),
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    summary = [
        "# Tile Still MVP Summary",
        "",
        f"- run_id: `{run_id}`",
        f"- task: `tile-mvp`",
        f"- model: `{args.model}`",
        f"- input: `{input_path}`",
        "- boundary: host-side tile path, not Android app e2e",
        "",
        "## Key Results",
        "",
        f"- input size: {image.shape[1]}x{image.shape[0]}",
        f"- output size: {tile_run.output_width}x{tile_run.output_height}",
        f"- tile count: {tile_run.tile_count}",
        f"- overlap: {args.overlap}px on LR tiles",
        f"- tile p50/p95: {metrics['tile_p50_ms']} / {metrics['tile_p95_ms']} ms",
        f"- total wall time: {metrics['wall_total_ms']} ms",
        f"- seam boundary MAD: {metrics['seam_boundary_mad']}",
        f"- MAD vs bicubic: {metrics['mad_vs_bicubic']}",
        "",
        "## Outputs",
        "",
        f"- input: `{input_out}`",
        f"- bicubic: `{bicubic_out}`",
        f"- tile SR: `{sr_out}`",
        f"- contact sheet: `{sheet_out}`",
        f"- metrics: `{out_dir / 'metrics.csv'}`",
        "",
        "## Next",
        "",
        "Review the contact sheet. If the tile output has no obvious stitch/geometry failure, move `tile-mvp` to done and start `tile-eval`.",
        "",
    ]
    (out_dir / "SUMMARY.md").write_text("\n".join(summary), encoding="utf-8")
    (out_dir / "NEXT_ACTION.md").write_text(
        "\n".join(
            [
                "# Next Action",
                "",
                "## Current Conclusion",
                "",
                "Host-side post-capture tile MVP generated input, bicubic, tile SR, metrics, and contact sheet.",
                "",
                "## Next Priority",
                "",
                "Run tile-eval: inspect contact_sheet.png and decide whether to validate Real-ESRGAN tile output or move toward Android app tile entry.",
                "",
                "## Boundary",
                "",
                "Do not claim Android app e2e or product quality from this host-only MVP.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"[ok] wrote {out_dir}")
    print(f"[ok] tile_count={tile_run.tile_count} output={tile_run.output_width}x{tile_run.output_height} total_ms={total_ms:.1f}")


if __name__ == "__main__":
    main()
