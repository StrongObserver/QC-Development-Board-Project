"""Print EvalHub dataset and metric coverage status."""

from __future__ import annotations

from collections import Counter

from evalhub_common import DATA_ROOT, DATASET_REGISTRY, METRIC_POLICY, dataset_is_present, dataset_local_dir, read_csv, write_csv


def main() -> int:
    datasets = read_csv(DATASET_REGISTRY)
    metrics = read_csv(METRIC_POLICY)

    rows: list[dict[str, str]] = []
    counts = Counter()
    for row in datasets:
        present = dataset_is_present(row)
        counts[f"present={present}"] += 1
        counts[f"layer={row['layer']}"] += 1
        rows.append({
            "dataset_id": row["dataset_id"],
            "layer": row["layer"],
            "priority": row["priority"],
            "status": row["status"],
            "auto_download": row["auto_download"],
            "present": "yes" if present else "no",
            "local_dir": str(dataset_local_dir(row)),
            "why_needed": row["why_needed"],
            "boundary": row["boundary"],
        })

    out = DATA_ROOT / "manifests" / "evalhub_dataset_status.csv"
    write_csv(out, rows)

    print("# EvalHub Dataset Status")
    print(f"data_root={DATA_ROOT}")
    print(f"registered={len(datasets)}")
    print(f"present={counts['present=True']}")
    print(f"missing={counts['present=False']}")
    print(f"status_csv={out}")
    print()
    for row in rows:
        print(f"{row['present']:>3} | {row['priority']} | {row['layer']} | {row['dataset_id']} | {row['boundary']}")

    print()
    print("# Metric Policy")
    for role, count in sorted(Counter(row["role"] for row in metrics).items()):
        print(f"{role}: {count}")
    print()
    print("# Priority Gaps")
    for row in rows:
        if row["present"] == "no" and row["priority"] in {"P1", "P0"}:
            print(f"- {row['priority']} missing: {row['dataset_id']} ({row['layer']}) -> {row['boundary']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

