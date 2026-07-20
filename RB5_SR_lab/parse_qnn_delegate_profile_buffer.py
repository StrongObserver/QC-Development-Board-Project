"""Best-effort diagnostic parser for QNN TFLite Delegate profile buffers.

The QNN Delegate Java API returns a raw byte buffer. `qnn-profile-viewer` expects
the SDK profiling log file format and may reject this buffer. This script does
not claim official per-op decoding; it extracts readable event names and nearby
little-endian timing-like integers so the evidence is at least inspectable.
"""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path


KNOWN_EVENTS = [
    b"QNN (execute) time",
    b"Accelerator (execute excluding wait) time",
    b"Accelerator (execute) time",
    b"QNN accelerator (execute) time",
    b"RPC (execute) time",
    b"Number of HVX threads used",
    b"QNN (finalize) time",
    b"Accelerator (finalize) time",
    b"QNN accelerator (finalize) time",
    b"RPC (finalize) time",
]


def parse_events(data: bytes) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for event in KNOWN_EVENTS:
        start = data.find(event)
        if start < 0:
            continue
        window_start = max(0, start - 64)
        prefix = data[window_start:start]
        ints = []
        for i in range(0, max(0, len(prefix) - 3), 4):
            value = int.from_bytes(prefix[i : i + 4], "little", signed=False)
            if 0 < value < 10_000_000:
                ints.append(value)
        rows.append(
            {
                "event": event.decode("ascii"),
                "offset": start,
                "candidate_values_little_endian": ";".join(str(v) for v in ints[-6:]),
                "note": "best-effort diagnostic; value units/fields are not officially decoded",
            }
        )
    return rows


def printable_strings(data: bytes) -> list[str]:
    return [
        match.group(0).decode("ascii", errors="ignore")
        for match in re.finditer(rb"[ -~]{4,}", data)
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True)
    parser.add_argument("--outdir", default="")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    profile = Path(args.profile)
    out_dir = Path(args.outdir) if args.outdir else profile.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    data = profile.read_bytes()
    rows = parse_events(data)
    with (out_dir / "profile_events_diagnostic.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["event", "offset", "candidate_values_little_endian", "note"],
        )
        writer.writeheader()
        writer.writerows(rows)
    (out_dir / "profile_strings.txt").write_text("\n".join(printable_strings(data)) + "\n", encoding="utf-8")
    summary = [
        "# QNN Delegate Profile Buffer Diagnostic",
        "",
        f"- profile: `{profile}`",
        f"- bytes: {len(data)}",
        f"- recognized_events: {len(rows)}",
        "- boundary: best-effort event/string extraction; qnn-profile-viewer rejected this raw delegate buffer",
        "",
        "## Outputs",
        "",
        f"- events: `{out_dir / 'profile_events_diagnostic.csv'}`",
        f"- strings: `{out_dir / 'profile_strings.txt'}`",
    ]
    (out_dir / "PROFILE_DIAGNOSTIC_SUMMARY.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
    print(f"[ok] wrote {out_dir}")


if __name__ == "__main__":
    main()
