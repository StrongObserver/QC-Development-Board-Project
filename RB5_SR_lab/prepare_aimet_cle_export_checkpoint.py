"""Prepare a Real-ESRGAN checkpoint that QAI Hub Models can load.

The AIMET-Torch CLE probe saves a raw PyTorch state_dict. Qualcomm AI Hub
Models' Real-ESRGAN exporter expects a checkpoint dict with a `params` or
`params_ema` key. This script wraps the CLE state_dict in that format and
verifies the official model wrapper can load it and serialize to ONNX.

This is a deployability check only. It does not submit AI Hub quantize/compile
jobs and does not replace Android assets.
"""

from __future__ import annotations

import argparse
import csv
import os
import subprocess
from pathlib import Path

import torch


REPO_ROOT = Path(__file__).resolve().parents[1]


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def run(cmd: list[str], *, cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=cwd,
        env=env,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--cle-state-dict",
        default="RB5_SR_lab/results/aimet_torch_cle_probe/20260721_realesrgan128_flower/cle_state_dict.pt",
    )
    parser.add_argument(
        "--qai-python",
        default="RB5_SR_lab/.venv_qai/Scripts/python.exe",
    )
    parser.add_argument(
        "--run-id",
        default="20260722_aimet_cle_export_checkpoint",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = REPO_ROOT / "RB5_SR_lab" / "results" / "aimet_deployability" / args.run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    cle_state_path = REPO_ROOT / args.cle_state_dict
    checkpoint_path = out_dir / "real_esrgan_general_x4v3_128_cle_qaihub_checkpoint.pth"
    onnx_path = out_dir / "real_esrgan_general_x4v3_128_cle_qaihub.onnx"
    helper_path = out_dir / "verify_qaihub_load_and_export.py"

    state = torch.load(cle_state_path, map_location="cpu")
    if not isinstance(state, dict) or not state:
        raise RuntimeError(f"unexpected CLE state_dict: {cle_state_path}")
    torch.save({"params": state}, checkpoint_path)

    helper_path.write_text(
        "\n".join(
            [
                "from pathlib import Path",
                "import sys",
                "import torch",
                "from qai_hub_models.models.real_esrgan_general_x4v3.model import Real_ESRGAN_General_x4v3",
                f"checkpoint = Path(r'{checkpoint_path}')",
                f"onnx_path = Path(r'{onnx_path}')",
                "model = Real_ESRGAN_General_x4v3.from_pretrained(str(checkpoint))",
                "spec = model.get_input_spec(height=128, width=128)",
                "serialized = model.serialize(str(onnx_path.parent), spec)",
                "Path(serialized).replace(onnx_path)",
                "print(f'loaded=1 input_spec={spec} onnx={onnx_path} bytes={onnx_path.stat().st_size}')",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONPATH"] = str(REPO_ROOT / "RB5_SR_lab")
    result = run([str(REPO_ROOT / args.qai_python), str(helper_path)], cwd=REPO_ROOT, env=env)
    (out_dir / "qaihub_export_stdout.txt").write_text(result.stdout, encoding="utf-8")

    status = "passed" if result.returncode == 0 and onnx_path.exists() else "blocked"
    rows = [
        {
            "status": status,
            "cle_state_dict": str(cle_state_path),
            "checkpoint": str(checkpoint_path),
            "checkpoint_bytes": checkpoint_path.stat().st_size if checkpoint_path.exists() else "",
            "onnx": str(onnx_path),
            "onnx_bytes": onnx_path.stat().st_size if onnx_path.exists() else "",
            "returncode": result.returncode,
            "boundary": "QAI Hub Models local wrapper/export check only; no remote quantize/compile/profile job submitted.",
        }
    ]
    write_csv(out_dir / "metrics.csv", rows)
    summary = [
        "# AIMET CLE Export Checkpoint",
        "",
        f"- status: `{status}`",
        f"- CLE state dict: `{cle_state_path}`",
        f"- QAI Hub checkpoint: `{checkpoint_path}`",
        f"- ONNX export: `{onnx_path if onnx_path.exists() else 'not generated'}`",
        "",
        "## Boundary",
        "",
        "This proves the AIMET-Torch CLE state_dict can be wrapped into the checkpoint shape expected by Qualcomm AI Hub Models and locally serialized through its Real-ESRGAN wrapper.",
        "It does not prove W8A8 TFLite/QNN recovery yet, because no AI Hub quantize/compile/profile job was submitted in this script.",
        "",
        "## Next",
        "",
        "If deployable CLE evidence is needed, the next step is an explicit AI Hub export using this checkpoint as `--weight-path`, with `--quantize w8a8` and the target runtime selected by the current route.",
    ]
    (out_dir / "SUMMARY.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
    print(f"[{status}] wrote {out_dir}")
    if status != "passed":
        raise SystemExit(result.returncode or 1)


if __name__ == "__main__":
    main()
