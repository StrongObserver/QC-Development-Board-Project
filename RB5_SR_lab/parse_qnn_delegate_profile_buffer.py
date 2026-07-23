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
        window_start = max(0, start - 64)
        prefix = data[window_start:start] if start >= 0 else b""
        ints = []
        for i in range(0, max(0, len(prefix) - 3), 4):
            value = int.from_bytes(prefix[i : i + 4], "little", signed=False)
            if 0 < value < 10_000_000:
                ints.append(value)
        rows.append(
            {
                "event": event.decode("ascii"),
                "present": start >= 0,
                "offset": start if start >= 0 else "",
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
    strings = printable_strings(data)
    present_rows = [row for row in rows if row["present"]]
    with (out_dir / "profile_events_diagnostic.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["event", "present", "offset", "candidate_values_little_endian", "note"],
        )
        writer.writeheader()
        writer.writerows(rows)
    (out_dir / "profile_strings.txt").write_text("\n".join(strings) + "\n", encoding="utf-8")
    with (out_dir / "diagnostic_summary.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "profile",
                "bytes",
                "known_events",
                "recognized_events",
                "printable_strings",
                "viewer_boundary",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "profile": str(profile),
                "bytes": len(data),
                "known_events": len(KNOWN_EVENTS),
                "recognized_events": len(present_rows),
                "printable_strings": len(strings),
                "viewer_boundary": "qnn-profile-viewer rejected Java raw delegate buffer; this is diagnostic-only, not official per-op decode",
            }
        )
    summary = [
        "# QNN Delegate Profile Buffer Diagnostic",
        "",
        f"- profile: `{profile}`",
        f"- bytes: {len(data)}",
        f"- known_events: {len(KNOWN_EVENTS)}",
        f"- recognized_events: {len(present_rows)}",
        f"- printable_strings: {len(strings)}",
        "- boundary: best-effort event/string extraction; qnn-profile-viewer rejected this raw delegate buffer",
        "",
        "## Outputs",
        "",
        f"- summary: `{out_dir / 'diagnostic_summary.csv'}`",
        f"- events: `{out_dir / 'profile_events_diagnostic.csv'}`",
        f"- strings: `{out_dir / 'profile_strings.txt'}`",
    ]
    (out_dir / "PROFILE_DIAGNOSTIC_SUMMARY.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
    print(f"[ok] wrote {out_dir}")


if __name__ == "__main__":
    main()
