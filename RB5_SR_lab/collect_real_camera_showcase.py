"""Pull and organize RB5VisionLab real-camera showcase captures.

The Android app saves one standard set per scene:

    REALCAM_<session>_<scene>_input_128.png
    REALCAM_<session>_<scene>_bicubic_512.png
    REALCAM_<session>_<scene>_quicksr_qnn_512.png
    REALCAM_<session>_<scene>_realesrgan_qnn_512.png

This script pulls one session from the RB5, writes a manifest/review template,
and creates a contact sheet when OpenCV is available.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
from datetime import datetime
from pathlib import Path


DEVICE_SERIAL = "ff5d3ab4"
REMOTE_DIR = "/sdcard/Pictures/RB5VisionLab"
LOCAL_ROOT = Path(r"C:\Users\Admin\Videos\RB5 gen2\real_camera_showcase")
KIND_ORDER = ["input_128", "bicubic_512", "quicksr_qnn_512", "realesrgan_qnn_512"]
KIND_LABEL = {
    "input_128": "Input ROI 128",
    "bicubic_512": "Bicubic 512",
    "quicksr_qnn_512": "QuickSR QNN 512",
    "realesrgan_qnn_512": "Real-ESRGAN QNN 512",
}
SCENE_RE = re.compile(
    r"^REALCAM_(?P<session>\d{8}_\d{6})_(?P<scene>.+?)_"
    r"(?P<kind>input_128|bicubic_512|quicksr_qnn_512|realesrgan_qnn_512)"
    r"(?: \((?P<variant_index>\d+)\))?\.png$"
)


def run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, check=check, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


def adb(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return run(["adb", "-s", DEVICE_SERIAL, *args], check=check)


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


def list_remote_realcam_files() -> list[str]:
    result = adb("shell", f"ls -1 {REMOTE_DIR}/REALCAM_*.png", check=False)
    if result.returncode != 0:
        return []
    files: list[str] = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if line.startswith(REMOTE_DIR) and line.endswith(".png"):
            files.append(line)
    return sorted(files)


def parse_remote_files(files: list[str]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for remote_path in files:
        name = Path(remote_path).name
        match = SCENE_RE.match(name)
        if not match:
            continue
        group = match.groupdict()
        group["variant_index"] = group.get("variant_index") or "0"
        rows.append({"remote_path": remote_path, "file_name": name, **group})
    return rows


def latest_session(rows: list[dict[str, str]]) -> str:
    sessions = sorted({row["session"] for row in rows})
    if not sessions:
        raise RuntimeError("No REALCAM session found on the RB5 device.")
    return sessions[-1]


def pull_session(rows: list[dict[str, str]], session: str, out_dir: Path) -> list[dict[str, object]]:
    out_dir.mkdir(parents=True, exist_ok=True)
    pulled: list[dict[str, object]] = []
    selected: dict[tuple[str, str], dict[str, str]] = {}
    for row in rows:
        if row["session"] != session:
            continue
        key = (row["scene"], row["kind"])
        old = selected.get(key)
        if old is None or int(row["variant_index"]) > int(old["variant_index"]):
            selected[key] = row
    for row in sorted(selected.values(), key=lambda item: (item["scene"], item["kind"])):
        local_path = out_dir / row["file_name"]
        adb("pull", row["remote_path"], str(local_path))
        pulled.append(
            {
                "session": session,
                "scene_id": row["scene"],
                "kind": row["kind"],
                "variant_index": int(row["variant_index"]),
                "remote_path": row["remote_path"],
                "local_path": str(local_path),
                "file_name": row["file_name"],
            }
        )
    return pulled


def write_review_template(out_dir: Path, manifest_rows: list[dict[str, object]]) -> None:
    review_path = out_dir / "review_template.csv"
    if review_path.exists():
        with review_path.open("r", newline="", encoding="utf-8-sig") as f:
            if any((row.get("decision") or "").strip() for row in csv.DictReader(f)):
                return
    scenes = sorted({str(row["scene_id"]) for row in manifest_rows})
    rows = [
        {
            "scene_id": scene,
            "decision": "",
            "text_readability": "",
            "edge_geometry": "",
            "texture_naturalness": "",
            "noise_or_halo": "",
            "preferred_output": "",
            "one_line_reason": "",
            "route_impact": "",
        }
        for scene in scenes
    ]
    write_csv(review_path, rows)


def write_contact_sheet(out_dir: Path, manifest_rows: list[dict[str, object]]) -> bool:
    try:
        import cv2
        import numpy as np
    except Exception:
        return False

    by_scene: dict[str, dict[str, Path]] = {}
    for row in manifest_rows:
        by_scene.setdefault(str(row["scene_id"]), {})[str(row["kind"])] = Path(str(row["local_path"]))

    rows_img = []
    tile_w, tile_h = 220, 220
    header_h, scene_h = 32, 28
    for scene in sorted(by_scene):
        tiles = []
        for kind in KIND_ORDER:
            path = by_scene[scene].get(kind)
            image = cv2.imread(str(path), cv2.IMREAD_COLOR) if path else None
            if image is None:
                image = np.full((tile_h, tile_w, 3), 235, dtype=np.uint8)
            else:
                image = cv2.resize(image, (tile_w, tile_h), interpolation=cv2.INTER_AREA)
            header = np.full((header_h, tile_w, 3), 245, dtype=np.uint8)
            cv2.putText(header, KIND_LABEL[kind], (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (20, 20, 20), 1, cv2.LINE_AA)
            tiles.append(np.vstack([header, image]))
        row_img = np.hstack(tiles)
        scene_header = np.full((scene_h, row_img.shape[1], 3), 230, dtype=np.uint8)
        cv2.putText(scene_header, scene, (8, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (0, 0, 0), 1, cv2.LINE_AA)
        rows_img.append(np.vstack([scene_header, row_img]))
    if not rows_img:
        return False
    sheet = np.vstack(rows_img)
    cv2.imwrite(str(out_dir / "contact_sheet.png"), sheet)
    return True


def write_summary(out_dir: Path, session: str, manifest_rows: list[dict[str, object]], contact_sheet: bool) -> None:
    scenes = sorted({str(row["scene_id"]) for row in manifest_rows})
    complete = []
    incomplete = []
    by_scene: dict[str, set[str]] = {}
    for row in manifest_rows:
        by_scene.setdefault(str(row["scene_id"]), set()).add(str(row["kind"]))
    for scene in scenes:
        missing = [kind for kind in KIND_ORDER if kind not in by_scene.get(scene, set())]
        if missing:
            incomplete.append(f"{scene}: missing {', '.join(missing)}")
        else:
            complete.append(scene)
    lines = [
        "# Real Camera Showcase Summary",
        "",
        f"- session: `{session}`",
        "- device: RB5 Gen2 / QCS8550 / Android 13",
        "- app path: CameraX real scene -> center ROI -> bicubic / QuickSRNet QNN / Real-ESRGAN QNN",
        f"- complete scenes: {len(complete)}",
        f"- output_dir: `{out_dir}`",
        "- boundary: real-camera showcase evidence; not a training set and not a full product-quality dataset",
        "",
        "## Files",
        "",
        f"- manifest: `{out_dir / 'manifest.csv'}`",
        f"- review template: `{out_dir / 'review_template.csv'}`",
        f"- contact sheet: `{out_dir / 'contact_sheet.png' if contact_sheet else 'not generated: OpenCV unavailable or no complete rows'}`",
        f"- loop state: `{out_dir / 'loop_state.json'}`",
        "",
        "## Complete Scenes",
        "",
    ]
    lines.extend([f"- `{scene}`" for scene in complete] or ["- none"])
    if incomplete:
        lines.extend(["", "## Incomplete Scenes", ""])
        lines.extend([f"- {item}" for item in incomplete])
    lines.extend(
        [
            "",
            "## Review Rule",
            "",
            "Use `pass`, `conditional`, or `fail` in `review_template.csv`.",
            "Do not claim QuickSRNet is globally better only from this set; use it to support or reject the real-camera showcase route.",
        ]
    )
    (out_dir / "SUMMARY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_loop_state(out_dir: Path, session: str, manifest_rows: list[dict[str, object]], contact_sheet: bool) -> None:
    scenes = {str(row["scene_id"]) for row in manifest_rows}
    state = {
        "schema_version": 1,
        "run_id": f"{session}_real_camera_showcase",
        "output_dir": str(out_dir),
        "status": "requires_human_review" if scenes else "environment_blocked",
        "stop_reason": "real_camera_assets_pulled" if scenes else "no_real_camera_assets_found",
        "next_priority_task": "Fill review_template.csv with pass/conditional/fail labels, then decide app default model route.",
        "session": session,
        "scene_count": len(scenes),
        "image_count": len(manifest_rows),
        "contact_sheet_generated": contact_sheet,
        "requires_human_review": True,
        "blocked_by": "" if scenes else "No REALCAM files were pulled.",
        "required_next_read": [
            str(out_dir / "SUMMARY.md"),
            str(out_dir / "manifest.csv"),
            str(out_dir / "review_template.csv"),
            str(out_dir / "contact_sheet.png"),
        ],
    }
    (out_dir / "loop_state.json").write_text(json.dumps(state, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def write_next_action(out_dir: Path, session: str) -> None:
    lines = [
        "# Next Action",
        "",
        "## Current Conclusion",
        "",
        f"Real-camera showcase session `{session}` has been pulled and organized.",
        "",
        "## Next Priority",
        "",
        "Review `contact_sheet.png` and fill `review_template.csv` with pass / conditional / fail labels.",
        "",
        "## Boundary",
        "",
        "Use this set as real-camera showcase evidence. Do not treat it as a training set or as proof that one model is globally better.",
    ]
    (out_dir / "NEXT_ACTION.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--session", default="", help="REALCAM session id, for example 20260719_153000. Defaults to latest.")
    parser.add_argument("--out-root", type=Path, default=LOCAL_ROOT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    devices = run(["adb", "devices"], check=False).stdout
    expected = f"{DEVICE_SERIAL}\tdevice"
    if expected not in devices:
        raise SystemExit(f"[blocked] {expected} not found")

    parsed = parse_remote_files(list_remote_realcam_files())
    if not parsed:
        raise SystemExit(f"[blocked] no REALCAM captures found under {REMOTE_DIR}")
    session = args.session or latest_session(parsed)
    out_dir = args.out_root / f"{session}_minimal_real_camera_set"
    manifest_rows = pull_session(parsed, session, out_dir)
    if not manifest_rows:
        raise SystemExit(f"[blocked] no files found for session {session}")

    write_csv(out_dir / "manifest.csv", manifest_rows)
    write_review_template(out_dir, manifest_rows)
    contact_sheet = write_contact_sheet(out_dir, manifest_rows)
    write_summary(out_dir, session, manifest_rows, contact_sheet)
    write_loop_state(out_dir, session, manifest_rows, contact_sheet)
    write_next_action(out_dir, session)
    write_csv(
        out_dir / "run_log.csv",
        [
            {
                "run_id": f"{session}_real_camera_showcase",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M +0800"),
                "device": "RB5 Gen2 QCS8550",
                "remote_dir": REMOTE_DIR,
                "output_dir": str(out_dir),
                "scene_count": len({row["scene_id"] for row in manifest_rows}),
                "image_count": len(manifest_rows),
                "status": "requires_human_review",
            }
        ],
    )
    print(f"[ok] pulled session {session} to {out_dir}")


if __name__ == "__main__":
    main()
