"""Run RB5_SR_Benchmark_v1 smoke cases with local RB5 QNN context binary.

This script stages QAIRT qnn-net-run under /data/local/tmp/qnn_sr, runs the
six smoke cases from RB5_SR_Benchmark_v1, converts QNN raw outputs to PNG, and
creates metrics plus contact sheets for quick human review.
"""

from __future__ import annotations

import csv
import shutil
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[1]
BENCHMARK_ROOT = Path(r"C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1")
QAIRT_ROOT = Path(r"C:\Qualcomm\QAIRT\v2.45.0.260326\qairt\2.45.0.260326")
QNN_LOCAL_RUN = REPO_ROOT / "RB5_SR_lab" / "qnn_local_run"
DEVICE_SERIAL = "ff5d3ab4"
DEVICE_DIR = "/data/local/tmp/qnn_sr"
CONTEXT_BINARY = (
    REPO_ROOT
    / "RB5_SR_lab"
    / "export_assets"
    / "real_esrgan_general_x4v3-qnn-w8a8-qcs8550-20260715"
    / "real_esrgan_general_x4v3-qnn_context_binary-w8a8-qualcomm_qcs8550_proxy"
    / "real_esrgan_general_x4v3.bin"
)

OUTPUT_SCALE = 0.005237185396254063
OUTPUT_ZERO_POINT = 25


@dataclass(frozen=True)
class SmokeCase:
    case_id: str
    category: str
    dataset: str
    source_id: str
    lr_128: Path
    bicubic_512: Path
    hr_512: Path
    why_in_smoke: str


def run(cmd: list[str], *, cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, check=check, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


def adb(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return run(["adb", "-s", DEVICE_SERIAL, *args], check=check)


def require_file(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(path)


def load_smoke_cases() -> list[SmokeCase]:
    manifest: dict[str, dict[str, str]] = {}
    with (BENCHMARK_ROOT / "manifest.csv").open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            manifest[row["case_id"]] = row

    cases: list[SmokeCase] = []
    with (BENCHMARK_ROOT / "qa" / "smoke_subset.csv").open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            m = manifest[row["case_id"]]
            cases.append(
                SmokeCase(
                    case_id=row["case_id"],
                    category=row["category"],
                    dataset=row["dataset"],
                    source_id=row["source_id"],
                    lr_128=Path(m["lr_128"]),
                    bicubic_512=Path(m["bicubic_512"]),
                    hr_512=Path(m["hr_512"]),
                    why_in_smoke=row["why_in_smoke"],
                )
            )
    return cases


def image_to_raw_rgb(path: Path, raw_path: Path) -> None:
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        raise FileNotFoundError(path)
    if image.shape[:2] != (128, 128):
        raise ValueError(f"expected 128x128 image, got {image.shape[:2]}: {path}")
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    raw_path.write_bytes(rgb.tobytes())


def qnn_raw_to_bgr(raw_path: Path) -> np.ndarray:
    raw = np.fromfile(raw_path, dtype=np.uint8)
    expected = 1 * 512 * 512 * 3
    if raw.size != expected:
        raise ValueError(f"expected {expected} bytes, got {raw.size}: {raw_path}")
    y = raw.reshape(1, 512, 512, 3)[0]
    rgb_f32 = np.clip((y.astype(np.float32) - OUTPUT_ZERO_POINT) * OUTPUT_SCALE, 0.0, 1.0)
    rgb_u8 = (rgb_f32 * 255.0 + 0.5).astype(np.uint8)
    return cv2.cvtColor(rgb_u8, cv2.COLOR_RGB2BGR)


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


def parse_profile(profile_csv: Path) -> dict[str, str]:
    result = {
        "netrun_execute_us": "",
        "qnn_execute_us": "",
        "qnn_accelerator_execute_us": "",
        "rpc_execute_us": "",
        "accelerator_execute_us": "",
        "ips": "",
    }
    if not profile_csv.exists():
        return result
    lines = profile_csv.read_text(encoding="utf-8").splitlines()
    header_index = next((i for i, line in enumerate(lines) if line.startswith("Msg Timestamp,")), None)
    if header_index is None:
        return result
    with profile_csv.open("r", encoding="utf-8", newline="") as f:
        for _ in range(header_index):
            next(f)
        for raw_row in csv.DictReader(f):
            row = {
                key.strip(): value.strip()
                for key, value in raw_row.items()
                if isinstance(key, str) and isinstance(value, str)
            }
            event = row.get("Event Identifier", "")
            msg = row.get("Message", "")
            time_value = row.get("Time", "")
            if event == "Graph 0: real_esrgan_general_x4v3" and msg == "EXECUTE":
                result["netrun_execute_us"] = time_value
            elif event == "QNN (execute) time":
                result["qnn_execute_us"] = time_value
            elif event == "QNN accelerator (execute) time":
                result["qnn_accelerator_execute_us"] = time_value
            elif event == "RPC (execute) time":
                result["rpc_execute_us"] = time_value
            elif event == "Accelerator (execute) time":
                result["accelerator_execute_us"] = time_value
            elif msg == "EXECUTE IPS":
                result["ips"] = time_value
    return result


def panel(image: np.ndarray, title: str, width: int = 220) -> np.ndarray:
    body = cv2.resize(image, (width, width), interpolation=cv2.INTER_AREA)
    header = np.full((36, width, 3), 25, dtype=np.uint8)
    cv2.putText(header, title[:26], (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
    return np.vstack([header, body])


def write_case_sheet(path: Path, lr: np.ndarray, bicubic: np.ndarray, qnn: np.ndarray, hr: np.ndarray) -> None:
    sheet = np.hstack([
        panel(lr, "LR 128"),
        panel(bicubic, "bicubic 512"),
        panel(qnn, "QNN W8A8"),
        panel(hr, "HR reference"),
    ])
    cv2.imwrite(str(path), sheet)


def write_contact_sheet(rows: list[dict[str, str]], out_path: Path) -> None:
    panels: list[np.ndarray] = []
    for row in rows:
        sheet = cv2.imread(row["case_contact_sheet"], cv2.IMREAD_COLOR)
        if sheet is None:
            continue
        thumb = cv2.resize(sheet, (880, 236), interpolation=cv2.INTER_AREA)
        header = np.full((34, 880, 3), 245, dtype=np.uint8)
        text = f"{row['case_id']} | {row['category']} | QNN {row['netrun_execute_us']} us | PSNR {row['psnr_qnn_vs_hr']}"
        cv2.putText(header, text[:115], (8, 23), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (20, 20, 20), 1, cv2.LINE_AA)
        panels.append(np.vstack([header, thumb]))
    cv2.imwrite(str(out_path), np.vstack(panels))


def average_number(rows: list[dict[str, str]], key: str) -> float:
    values = [float(row[key]) for row in rows if row.get(key)]
    return float(np.mean(values)) if values else float("nan")


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
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


def write_summary(out_root: Path, run_id: str, rows: list[dict[str, str]], by_category: Path) -> None:
    summary_lines = [
        "# RB5 QNN W8A8 Smoke Summary",
        "",
        f"- run_id: {run_id}",
        f"- cases: {len(rows)}",
        "- device: RB5 Gen2 / QCS8550 / Android 13",
        "- runtime: QAIRT qnn-net-run 2.45.0.260326154327",
        "- context: real_esrgan_general_x4v3 QNN context binary W8A8",
        "- important: ADSP_LIBRARY_PATH is intentionally unset in run_on_device.sh",
        "",
        "## Outputs",
        "",
        f"- metrics: `{out_root / 'metrics.csv'}`",
        f"- contact sheet: `{out_root / 'contact_sheet.png'}`",
        f"- human review guide: `{out_root / 'HUMAN_REVIEW_GUIDE.md'}`",
        f"- next action: `{out_root / 'NEXT_ACTION.md'}`",
        f"- by category: `{by_category}`",
        "",
        "## Quick Result Table",
        "",
        "| case | category | NetRun us | QNN accel us | PSNR QNN-HR | PSNR delta vs bicubic |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        summary_lines.append(
            f"| {row['case_id']} | {row['category']} | {row['netrun_execute_us']} | "
            f"{row['qnn_accelerator_execute_us']} | {row['psnr_qnn_vs_hr']} | "
            f"{row['psnr_delta_qnn_minus_bicubic']} |"
        )
    summary_lines.extend(
        [
            "",
            "## Boundary",
            "",
            "This is local RB5 `qnn-net-run` smoke evidence, not Android app end-to-end timing.",
            "For performance claims, run repeated inputs and report p50/p95 separately.",
        ]
    )
    (out_root / "SUMMARY.md").write_text("\n".join(summary_lines) + "\n", encoding="utf-8")


def write_human_review_guide(out_root: Path, rows: list[dict[str, str]]) -> None:
    avg_netrun = average_number(rows, "netrun_execute_us") / 1000.0
    avg_accel = average_number(rows, "qnn_accelerator_execute_us") / 1000.0
    guide = [
        "# 人工 Review 指南",
        "",
        "这次结果用于验证：本地 RB5 能否通过 `qnn-net-run` 跑通 Real-ESRGAN W8A8 QNN context binary，并在 6 个 smoke case 上产出可看的超分结果。",
        "",
        "## 已经通过的点",
        "",
        "- 6 个 smoke case 都已经在本地 RB5 上通过 `qnn-net-run` 执行成功。",
        "- 每个 case 都生成了 512x512 的 QNN 输出图。",
        "- 优先查看 `contact_sheet.png`，确认是否有空图、旋转、镜像、裁剪错位。",
        "- 输出风格应与 Real-ESRGAN / W8A8 一致：通常比 bicubic 更锐，但低光自然纹理可能出现 conditional 情况。",
        "",
        "## 怎么看总览图",
        "",
        f"优先打开：`{out_root / 'contact_sheet.png'}`",
        "",
        "每一行对应一个测试 case，排列顺序是：",
        "",
        "```text",
        "LR 128 | bicubic 512 | QNN W8A8 | HR reference",
        "```",
        "",
        "行标题里包含：",
        "",
        "```text",
        "case_id | 场景类别 | QNN NetRun 执行时间 | PSNR vs HR",
        "```",
        "",
        "## 每类重点看什么",
        "",
        "| 类别 | 重点看什么 |",
        "| --- | --- |",
        "| `structure_edges` | 线条是否锐利但不过度 halo，几何是否变形 |",
        "| `repeating_patterns` | 是否出现棋盘格、假周期纹理、彩色边缘异常 |",
        "| `natural_texture` | 纹理是否自然，是否变成假细节 |",
        "| `low_light_noise` | 是否放大噪声，暗部细节是否糊成一团 |",
        "| `text_signage` | 字是否更清楚，字形是否变形 |",
        "| `people_scene` | 人脸/皮肤/人体边缘是否不自然 |",
        "",
        "## 时延边界",
        "",
        "这里的时延是本地 RB5 上 `qnn-net-run` 的时延，不是 Android app 端到端时延。",
        "",
        f"- 平均 NetRun execute: 约 {avg_netrun:.2f} ms",
        f"- 平均 QNN accelerator execute: 约 {avg_accel:.2f} ms",
        "",
        "后续如果要写正式性能结论，需要重复多次运行并统计 p50 / p95。",
        "",
        "## 当前建议",
        "",
        "如果 contact sheet 未见阻断问题，可以进入下一步：多次运行统计稳定 p50/p95，或开始 Path B native runner / Android app 接入。用户当前口播模板的最新要求优先于这里的建议。",
    ]
    (out_root / "HUMAN_REVIEW_GUIDE.md").write_text("\n".join(guide) + "\n", encoding="utf-8")


def write_next_action(out_root: Path, run_id: str, rows: list[dict[str, str]]) -> None:
    avg_netrun = average_number(rows, "netrun_execute_us") / 1000.0
    avg_accel = average_number(rows, "qnn_accelerator_execute_us") / 1000.0
    next_action = [
        "# Next Action",
        "",
        "## 当前结论",
        "",
        f"本轮 `{run_id}` 已完成本地 RB5 QNN W8A8 smoke benchmark。6 个 smoke case 均通过 `qnn-net-run --retrieve_context` 生成 512x512 QNN 输出；本轮平均 NetRun execute 约 "
        f"{avg_netrun:.2f} ms，平均 QNN accelerator execute 约 {avg_accel:.2f} ms。",
        "",
        "## 当前阻塞",
        "",
        "无阻塞。",
        "",
        "## 下一步最高优先级任务",
        "",
        "下一步优先做：【根据用户当前口播模板选择：多次运行统计 p50/p95，或进入 Path B native runner / Android app 接入】",
        "",
        "## 为什么是这个任务",
        "",
        "本轮已经证明 Path A 本地 QNN smoke 可跑通。下一步要么把性能数据从单次 smoke 升级为稳定 p50/p95，要么把已验证的 QNN context binary 接到更接近产品形态的 native/app 路径。",
        "",
        "## 下轮 AI 开始前必须先读",
        "",
        "```text",
        r"C:\Users\Admin\Desktop\QC-Development-Board-Project\PROJECT_ENTRYPOINTS.md",
        r"C:\Users\Admin\Nutstore\1\Typora_save\自己的项目\RB5 Gen2_AI上下文.md",
        r"C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\qa\RESULT_SOP.md",
        str(out_root / "SUMMARY.md"),
        str(out_root / "HUMAN_REVIEW_GUIDE.md"),
        str(out_root / "metrics.csv"),
        str(out_root / "contact_sheet.png"),
        "```",
        "",
        "## 不要做什么",
        "",
        "- 不要把生成结果写回 `cases/`。",
        "- 不要把 AI Hub hosted profile 当成本地 app 端到端。",
        "- 不要把本轮 qnn-net-run 单次时延当成稳态 p50/p95。",
        "- 不要让本文件覆盖用户当前口播模板；用户最新要求永远优先。",
        "",
        "## 需要用户人工判断的点",
        "",
        "需要用户优先查看 `contact_sheet.png`。如果发现某个 case 视觉失败，应先定位问题来源，再决定是否继续性能统计或 Path B。",
    ]
    (out_root / "NEXT_ACTION.md").write_text("\n".join(next_action) + "\n", encoding="utf-8")


def stage_common_files() -> None:
    adb("root")
    adb("shell", f"mkdir -p {DEVICE_DIR}")
    pushes = [
        (QAIRT_ROOT / "bin" / "aarch64-android" / "qnn-net-run", f"{DEVICE_DIR}/qnn-net-run"),
        (QAIRT_ROOT / "bin" / "aarch64-android" / "qnn-profile-viewer", f"{DEVICE_DIR}/qnn-profile-viewer"),
        (QAIRT_ROOT / "lib" / "aarch64-android" / "libQnnHtp.so", f"{DEVICE_DIR}/libQnnHtp.so"),
        (QAIRT_ROOT / "lib" / "aarch64-android" / "libQnnHtpNetRunExtensions.so", f"{DEVICE_DIR}/libQnnHtpNetRunExtensions.so"),
        (QAIRT_ROOT / "lib" / "aarch64-android" / "libQnnHtpV73Stub.so", f"{DEVICE_DIR}/libQnnHtpV73Stub.so"),
        (QAIRT_ROOT / "lib" / "aarch64-android" / "libQnnHtpPrepare.so", f"{DEVICE_DIR}/libQnnHtpPrepare.so"),
        (QAIRT_ROOT / "lib" / "aarch64-android" / "libQnnSystem.so", f"{DEVICE_DIR}/libQnnSystem.so"),
        (CONTEXT_BINARY, f"{DEVICE_DIR}/real_esrgan_general_x4v3.bin"),
        (QNN_LOCAL_RUN / "HtpConfigFile.json", f"{DEVICE_DIR}/HtpConfigFile.json"),
        (QNN_LOCAL_RUN / "PerfSetting.conf", f"{DEVICE_DIR}/PerfSetting.conf"),
        (QNN_LOCAL_RUN / "run_on_device.sh", f"{DEVICE_DIR}/run_on_device.sh"),
    ]
    for local, remote in pushes:
        require_file(local)
        adb("push", str(local), remote)
    adb("shell", f"chmod 755 {DEVICE_DIR}/qnn-net-run {DEVICE_DIR}/qnn-profile-viewer {DEVICE_DIR}/run_on_device.sh")


def main() -> None:
    for path in [QAIRT_ROOT, CONTEXT_BINARY, QNN_LOCAL_RUN / "run_on_device.sh"]:
        require_file(path)

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S_qnn_w8a8_smoke_rb5")
    out_root = BENCHMARK_ROOT / "results" / run_id
    by_category = out_root / "by_category"
    raw_inputs = out_root / "raw_inputs"
    out_root.mkdir(parents=True, exist_ok=True)
    raw_inputs.mkdir(parents=True, exist_ok=True)

    print(f"[stage] {DEVICE_DIR}")
    stage_common_files()

    rows: list[dict[str, str]] = []
    for index, case in enumerate(load_smoke_cases(), start=1):
        print(f"[{index}/6] {case.case_id}")
        case_dir = by_category / case.category / case.case_id
        case_dir.mkdir(parents=True, exist_ok=True)
        local_raw = raw_inputs / f"{case.case_id}.raw"
        image_to_raw_rgb(case.lr_128, local_raw)
        adb("push", str(local_raw), f"{DEVICE_DIR}/input.raw")
        (raw_inputs / "input_list.txt").write_text("input.raw\n", encoding="ascii")
        adb("push", str(raw_inputs / "input_list.txt"), f"{DEVICE_DIR}/input_list.txt")

        t0 = time.perf_counter()
        completed = adb("shell", f"{DEVICE_DIR}/run_on_device.sh", check=False)
        wall_ms = (time.perf_counter() - t0) * 1000.0
        (case_dir / "qnn_net_run_stdout.txt").write_text(completed.stdout, encoding="utf-8")
        if completed.returncode != 0:
            raise RuntimeError(f"qnn-net-run failed for {case.case_id}:\n{completed.stdout}")

        pull_dir = case_dir / "pulled_output"
        if pull_dir.exists():
            shutil.rmtree(pull_dir)
        pull_dir.mkdir(parents=True)
        adb("pull", f"{DEVICE_DIR}/output", str(pull_dir))
        raw_out = pull_dir / "output" / "Result_0" / "upscaled_image_native.raw"
        require_file(raw_out)
        qnn_bgr = qnn_raw_to_bgr(raw_out)

        lr = cv2.imread(str(case.lr_128), cv2.IMREAD_COLOR)
        bicubic = cv2.imread(str(case.bicubic_512), cv2.IMREAD_COLOR)
        hr = cv2.imread(str(case.hr_512), cv2.IMREAD_COLOR)
        if lr is None or bicubic is None or hr is None:
            raise FileNotFoundError(case.case_id)

        cv2.imwrite(str(case_dir / "lr_128.png"), lr)
        cv2.imwrite(str(case_dir / "bicubic_512.png"), bicubic)
        cv2.imwrite(str(case_dir / "qnn_w8a8_512.png"), qnn_bgr)
        cv2.imwrite(str(case_dir / "hr_512.png"), hr)
        write_case_sheet(case_dir / "case_contact_sheet.png", lr, bicubic, qnn_bgr, hr)

        profile = parse_profile(pull_dir / "output" / "profile_viewer.csv")
        rows.append({
            "case_id": case.case_id,
            "category": case.category,
            "dataset": case.dataset,
            "source_id": case.source_id,
            "wall_ms": f"{wall_ms:.1f}",
            **profile,
            "psnr_bicubic_vs_hr": f"{psnr(hr, bicubic):.2f}",
            "ssim_bicubic_vs_hr": f"{ssim(hr, bicubic):.4f}",
            "psnr_qnn_vs_hr": f"{psnr(hr, qnn_bgr):.2f}",
            "ssim_qnn_vs_hr": f"{ssim(hr, qnn_bgr):.4f}",
            "psnr_delta_qnn_minus_bicubic": f"{psnr(hr, qnn_bgr) - psnr(hr, bicubic):.2f}",
            "sharpness_bicubic": f"{sharpness(bicubic):.2f}",
            "sharpness_qnn": f"{sharpness(qnn_bgr):.2f}",
            "sharpness_qnn_over_bicubic": f"{sharpness(qnn_bgr) / sharpness(bicubic):.3f}" if sharpness(bicubic) > 0 else "",
            "case_contact_sheet": str(case_dir / "case_contact_sheet.png"),
            "qnn_png": str(case_dir / "qnn_w8a8_512.png"),
            "why_in_smoke": case.why_in_smoke,
            "review_hint": "Check QNN image against bicubic and HR; metrics are supporting evidence, not final visual judgment.",
        })

    write_csv(out_root / "metrics.csv", rows)
    write_contact_sheet(rows, out_root / "contact_sheet.png")
    write_summary(out_root, run_id, rows, by_category)
    write_human_review_guide(out_root, rows)
    write_next_action(out_root, run_id, rows)
    print(f"[ok] wrote {out_root}")


if __name__ == "__main__":
    main()
