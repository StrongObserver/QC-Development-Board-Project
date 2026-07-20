"""Run RB5VisionLab fixed sample QNN replay through the Android app."""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path

from app_e2e_export import git_commit_label, mirror_app_e2e_log, write_app_e2e_log


REPO_ROOT = Path(__file__).resolve().parents[1]
RESULTS_ROOT = Path(r"C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results")
DEVICE_SERIAL = "ff5d3ab4"
APP_COMPONENT = "com.cyf.rb5visionlab/.MainActivity"
PACKAGE_NAME = "com.cyf.rb5visionlab"
REMOTE_PICTURES_DIR = "/sdcard/Pictures/RB5VisionLab"

FIXED_RE = re.compile(
    r"fixed sample QNN Delegate OK model=(?P<model>\w+) asset=(?P<asset>\S+) "
    r"pre=(?P<pre_ms>\d+) inf=(?P<inf_ms>\d+) post=(?P<post_ms>\d+) "
    r"total=(?P<total_ms>\d+) "
    r"(?:profileBytes=(?P<profile_bytes>\d+) profileHex16=(?P<profile_hex16>[0-9a-fA-F]*) (?:profileHex=(?P<profile_hex>[0-9a-fA-F]*) )?)?"
    r"saved=(?P<saved>.*)"
)


def run(cmd: list[str], *, check: bool = True, timeout: int | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, check=check, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)


def adb(*args: str, check: bool = True, timeout: int | None = None) -> subprocess.CompletedProcess[str]:
    return run(["adb", "-s", DEVICE_SERIAL, *args], check=check, timeout=timeout)


def prepare_device_interactive() -> None:
    adb("shell", "input", "keyevent", "KEYCODE_WAKEUP", check=False)
    adb("shell", "wm", "dismiss-keyguard", check=False)
    adb("shell", "cmd", "statusbar", "collapse", check=False)
    time.sleep(0.3)


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


def parse_fixed_rows(log_text: str) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for line in log_text.splitlines():
        match = FIXED_RE.search(line)
        if not match:
            continue
        values = match.groupdict()
        saved_paths = [item.strip() for item in values["saved"].split(",") if item.strip()]
        rows.append(
            {
                "index": len(rows) + 1,
                "model": values["model"],
                "asset": values["asset"],
                "pre_ms": int(values["pre_ms"]),
                "inf_ms": int(values["inf_ms"]),
                "post_ms": int(values["post_ms"]),
                "total_ms": int(values["total_ms"]),
                "profile_bytes": int(values["profile_bytes"]) if values.get("profile_bytes") else "",
                "profile_hex16": values.get("profile_hex16") or "",
                "profile_hex": values.get("profile_hex") or "",
                "saved_paths": "|".join(saved_paths),
                "raw_log_prefix": line[:18],
            }
        )
    return rows


def collect_fixed_sample(asset: str, model: str, timeout_s: int) -> tuple[str, list[dict[str, object]]]:
    prepare_device_interactive()
    adb("shell", "am", "force-stop", PACKAGE_NAME, check=False)
    adb("logcat", "-c", check=False)
    prepare_device_interactive()
    started = adb(
        "shell",
        "am",
        "start",
        "-n",
        APP_COMPONENT,
        "--ez",
        "run_qnn_fixed",
        "true",
        "--es",
        "sr_model",
        model,
        "--es",
        "sr_asset",
        asset,
        check=False,
    )
    if started.returncode != 0:
        raise RuntimeError(started.stdout)
    deadline = time.time() + timeout_s
    final_log = ""
    rows: list[dict[str, object]] = []
    while time.time() < deadline:
        time.sleep(1)
        final_log = adb(
            "logcat",
            "-d",
            "-v",
            "time",
            "RB5_QNN:D",
            "RB5_SR:D",
            "AndroidRuntime:E",
            "*:S",
            check=False,
        ).stdout
        rows = parse_fixed_rows(final_log)
        if rows:
            break
    adb("shell", "am", "force-stop", PACKAGE_NAME, check=False)
    return final_log, rows


def pull_saved_outputs(rows: list[dict[str, object]], out_dir: Path) -> list[dict[str, object]]:
    pulled: list[dict[str, object]] = []
    image_dir = out_dir / "images"
    image_dir.mkdir(exist_ok=True)
    for row in rows:
        for remote_path in str(row.get("saved_paths", "")).split("|"):
            if not remote_path:
                continue
            local_path = image_dir / Path(remote_path).name
            adb("pull", remote_path, str(local_path), check=False, timeout=60)
            if local_path.exists() and local_path.stat().st_size > 0:
                pulled.append(
                    {
                        "asset": row["asset"],
                        "remote_path": remote_path,
                        "local_path": str(local_path),
                        "file_name": local_path.name,
                        "bytes": local_path.stat().st_size,
                    }
                )
    return pulled


def write_profile_outputs(rows: list[dict[str, object]], out_dir: Path) -> list[dict[str, object]]:
    profile_dir = out_dir / "profiles"
    profile_dir.mkdir(exist_ok=True)
    outputs: list[dict[str, object]] = []
    viewer = Path(r"C:\Qualcomm\QAIRT\v2.45.0.260326\qairt\2.45.0.260326\bin\x86_64-windows-msvc\qnn-profile-viewer.exe")
    for row in rows:
        profile_hex = str(row.get("profile_hex") or "")
        if not profile_hex:
            continue
        profile_path = profile_dir / f"{row['asset']}_{row['model']}_profile.bin".replace("/", "_")
        profile_path.write_bytes(bytes.fromhex(profile_hex))
        viewer_stdout = ""
        viewer_status = "not_run"
        csv_path = profile_path.with_suffix(".csv")
        if viewer.exists():
            result = run(
                [str(viewer), "--input_log", str(profile_path), "--output", str(csv_path)],
                check=False,
                timeout=30,
            )
            viewer_stdout = result.stdout
            viewer_status = "ok" if result.returncode == 0 else f"failed_{result.returncode}"
            profile_path.with_suffix(".viewer.txt").write_text(viewer_stdout, encoding="utf-8")
        outputs.append(
            {
                "asset": row["asset"],
                "model": row["model"],
                "profile_path": str(profile_path),
                "profile_bytes": profile_path.stat().st_size,
                "viewer_status": viewer_status,
                "viewer_csv": str(csv_path) if csv_path.exists() else "",
                "viewer_stdout": str(profile_path.with_suffix(".viewer.txt")) if viewer_stdout else "",
            }
        )
    write_csv(out_dir / "profile_outputs.csv", outputs)
    return outputs


def write_contact_sheet(out_dir: Path, pulled_rows: list[dict[str, object]]) -> bool:
    try:
        import cv2
        import numpy as np
    except Exception:
        return False
    by_asset: dict[str, list[Path]] = {}
    for row in pulled_rows:
        by_asset.setdefault(str(row["asset"]), []).append(Path(str(row["local_path"])))
    strips = []
    tile = 220
    header_h = 32
    for asset, paths in sorted(by_asset.items()):
        panels = []
        for path in sorted(paths):
            image = cv2.imread(str(path), cv2.IMREAD_COLOR)
            if image is None:
                image = np.full((tile, tile, 3), 230, dtype=np.uint8)
            else:
                image = cv2.resize(image, (tile, tile), interpolation=cv2.INTER_AREA)
            header = np.full((header_h, tile, 3), 245, dtype=np.uint8)
            label = path.name.split("_")[-2] if "_" in path.name else path.name[:16]
            cv2.putText(header, label[:20], (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (20, 20, 20), 1, cv2.LINE_AA)
            panels.append(np.vstack([header, image]))
        if panels:
            strip = np.hstack(panels)
            asset_header = np.full((header_h, strip.shape[1], 3), 230, dtype=np.uint8)
            cv2.putText(asset_header, asset, (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 1, cv2.LINE_AA)
            strips.append(np.vstack([asset_header, strip]))
    if not strips:
        return False
    cv2.imwrite(str(out_dir / "contact_sheet.png"), np.vstack(strips))
    return True


def write_summary(out_dir: Path, run_id: str, rows: list[dict[str, object]], pulled_rows: list[dict[str, object]], profile_rows: list[dict[str, object]], app_e2e_path: Path, app_e2e_mirror: Path, contact_sheet: bool) -> None:
    lines = [
        "# App Fixed-Sample Replay Summary",
        "",
        f"- run_id: `{run_id}`",
        f"- cases: {len(rows)}",
        f"- pulled images: {len(pulled_rows)}",
        f"- max profile bytes: {max((int(row.get('profile_bytes') or 0) for row in rows), default=0)}",
        f"- decoded profile files: {len(profile_rows)}",
        "- boundary: Android app fixed-sample replay evidence, not live camera visual quality",
        "",
        "## Timing",
        "",
        "| asset | model | pre ms | inf ms | post ms | total ms | profile bytes |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(f"| `{row['asset']}` | `{row['model']}` | {row['pre_ms']} | {row['inf_ms']} | {row['post_ms']} | {row['total_ms']} | {row.get('profile_bytes', '')} |")
    lines.extend(
        [
            "",
            "## Outputs",
            "",
            f"- metrics: `{out_dir / 'metrics.csv'}`",
            f"- pulled images: `{out_dir / 'images'}`",
            f"- contact sheet: `{out_dir / 'contact_sheet.png' if contact_sheet else 'not generated'}`",
            f"- EvalHub app e2e row: `{app_e2e_path}`",
            f"- EvalHub ignored mirror: `{app_e2e_mirror}`",
            f"- raw logcat: `{out_dir / 'raw_logcat.txt'}`",
            f"- profile outputs: `{out_dir / 'profile_outputs.csv'}`",
        ]
    )
    (out_dir / "SUMMARY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--assets",
        nargs="+",
        default=["offline_text_edge_128.png", "case_text_signage_urban076.png", "case_people_scene_div2k0832.png"],
    )
    parser.add_argument("--model", default="QUICKSR_W8A8", choices=["QUICKSR_W8A8", "W8A8"])
    parser.add_argument("--run-id", default="")
    parser.add_argument("--timeout-s", type=int, default=30)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_id = args.run_id or datetime.now().strftime("app_fixed_sample_replay_%Y%m%d_%H%M%S")
    out_dir = RESULTS_ROOT / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    devices = run(["adb", "devices"], check=False).stdout
    expected = f"{DEVICE_SERIAL}\tdevice"
    if expected not in devices:
        raise SystemExit(f"[blocked] {expected} not found")
    all_rows: list[dict[str, object]] = []
    raw_logs = []
    for asset in args.assets:
        log_text, rows = collect_fixed_sample(asset, args.model, args.timeout_s)
        raw_logs.append(f"===== {asset} =====\n{log_text}")
        all_rows.extend(rows)
    (out_dir / "raw_logcat.txt").write_text("\n".join(raw_logs), encoding="utf-8")
    write_csv(out_dir / "metrics.csv", all_rows)
    pulled_rows = pull_saved_outputs(all_rows, out_dir)
    write_csv(out_dir / "pulled_images.csv", pulled_rows)
    profile_rows = write_profile_outputs(all_rows, out_dir)
    contact_sheet = write_contact_sheet(out_dir, pulled_rows)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M +0800")
    totals = [float(row["total_ms"]) for row in all_rows]
    infs = [float(row["inf_ms"]) for row in all_rows]
    p50_total = sorted(totals)[len(totals) // 2] if totals else ""
    p50_inf = sorted(infs)[len(infs) // 2] if infs else ""
    app_e2e_path = out_dir / "app_e2e_log.csv"
    write_app_e2e_log(
        app_e2e_path,
        {
            "run_id": run_id,
            "timestamp": timestamp,
            "device": "RB5 Gen2 QCS8550",
            "android_version": "Android 13",
            "app_commit": git_commit_label(REPO_ROOT),
            "model_name": "QuickSRNetSmall" if "QUICKSR" in args.model else "Real-ESRGAN general x4v3",
            "model_variant": args.model.lower(),
            "backend": "QNN TFLite Delegate / HTP",
            "input_source": "app_fixed_assets",
            "input_size": "128x128",
            "output_size": "512x512",
            "inference_ms": p50_inf,
            "e2e_ms": p50_total,
            "steady_state_window": f"{len(all_rows)} fixed assets",
            "p50_e2e_ms": p50_total,
            "npu_or_dsp_note": "QNN Delegate configured for HTP backend; fixed assets executed inside Android app",
            "fallback_code": "none" if all_rows else "no_fixed_rows",
            "failure_code": "none" if all_rows else "no_fixed_rows",
            "human_decision": "not_reviewed",
            "notes": "Fixed-sample app replay for regression evidence; not live camera visual quality.",
        },
    )
    app_e2e_mirror = mirror_app_e2e_log(REPO_ROOT, run_id, app_e2e_path)
    write_csv(
        out_dir / "run_log.csv",
        [
            {
                "run_id": run_id,
                "timestamp": timestamp,
                "assets": "|".join(args.assets),
                "model": args.model,
                "cases": len(all_rows),
                "pulled_images": len(pulled_rows),
                "contact_sheet": contact_sheet,
                "status": "app_fixed_sample_replay_collected" if all_rows else "environment_blocked",
                "max_profile_bytes": max((int(row.get("profile_bytes") or 0) for row in all_rows), default=0),
                "profile_files": len(profile_rows),
            }
        ],
    )
    (out_dir / "loop_state.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "run_id": run_id,
                "output_dir": str(out_dir),
                "status": "app_fixed_sample_replay_collected" if all_rows else "environment_blocked",
                "stop_reason": "fixed_assets_collected" if all_rows else "no_fixed_rows",
                "next_priority_task": "Use this as fixed app replay evidence; review contact_sheet.png before making visual claims.",
                "requires_human_review": bool(all_rows),
                "cases": len(all_rows),
                "pulled_images": len(pulled_rows),
                "max_profile_bytes": max((int(row.get("profile_bytes") or 0) for row in all_rows), default=0),
                "profile_files": len(profile_rows),
                "boundary": "QNN Delegate profile buffer presence confirms app-side profiling API access; format is raw delegate bytes and is not yet per-op decoded.",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    write_summary(out_dir, run_id, all_rows, pulled_rows, profile_rows, app_e2e_path, app_e2e_mirror, contact_sheet)
    print(f"[ok] wrote {out_dir}")


if __name__ == "__main__":
    main()
