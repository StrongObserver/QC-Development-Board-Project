"""Dry-run checks for RB5 loop policy behavior.

These tests do not touch the RB5 device. They exercise loop states that are
hard to validate reliably through a single hardware run.
"""

from __future__ import annotations

import json
from pathlib import Path

from loop_policy import environment_blocked_payload, make_loop_state_payload


def valid_row(case_id: str, category: str, psnr_delta: str = "1.0") -> dict[str, str]:
    return {
        "case_id": case_id,
        "category": category,
        "output_size": "512x512",
        "raw_output_bytes": "786432",
        "output_stddev": "12.3",
        "netrun_execute_us": "13000",
        "qnn_execute_us": "12000",
        "qnn_accelerator_execute_us": "9000",
        "netrun_execute_p50_us": "13000",
        "qnn_accelerator_execute_p50_us": "9000",
        "psnr_delta_qnn_minus_bicubic": psnr_delta,
    }


def six_rows(low_light_delta: str = "1.0") -> list[dict[str, str]]:
    categories = [
        "structure_edges",
        "repeating_patterns",
        "natural_texture",
        "low_light_noise",
        "text_signage",
        "people_scene",
    ]
    rows = []
    for index, category in enumerate(categories):
        delta = low_light_delta if category == "low_light_noise" else "1.0"
        rows.append(valid_row(f"case_{index}", category, delta))
    return rows


def full_rows(low_light_delta: str = "1.0") -> list[dict[str, str]]:
    rows = []
    categories = [
        "structure_edges",
        "repeating_patterns",
        "natural_texture",
        "low_light_noise",
        "text_signage",
        "people_scene",
    ]
    for index in range(24):
        category = categories[index % len(categories)]
        delta = low_light_delta if category == "low_light_noise" else "1.0"
        rows.append(valid_row(f"full_case_{index:02d}", category, delta))
    return rows


def assert_strict_json(payload: dict[str, object]) -> None:
    json.loads(json.dumps(payload, allow_nan=False))


def main() -> None:
    out = Path("dryrun")

    env = environment_blocked_payload(
        run_id="env",
        output_dir=out,
        repeat_count=3,
        blocked_by="ADB_OR_REQUIRED_FILE_PREFLIGHT_FAILED",
        notes="dry run",
    )
    assert env["status"] == "environment_blocked"
    assert env["knowledge_base_triggered"] == []
    assert_strict_json(env)

    hard_fail_rows = six_rows()
    hard_fail_rows[0]["raw_output_bytes"] = "1"
    hard_fail = make_loop_state_payload(run_id="hard", output_dir=out, rows=hard_fail_rows, repeat_count=3)
    assert hard_fail["status"] == "blocked"
    assert "qnn_or_android_integration_failure" in hard_fail["knowledge_base_triggered"]
    assert_strict_json(hard_fail)

    single = make_loop_state_payload(run_id="single", output_dir=out, rows=six_rows(), repeat_count=1)
    assert single["status"] == "ready_for_repeated_smoke"
    assert single["next_priority_task"] == "qnn_w8a8_repeat_smoke_p50_p95"
    assert single["knowledge_base_triggered"] == []
    assert_strict_json(single)

    conditional = make_loop_state_payload(run_id="cond", output_dir=out, rows=six_rows("0.1"), repeat_count=3)
    assert conditional["status"] == "ready_with_quality_boundary"
    assert "quality_failure_or_conditional" in conditional["knowledge_base_triggered"]
    assert conditional["requires_human_review"] is True
    assert_strict_json(conditional)

    count_bad = make_loop_state_payload(run_id="count", output_dir=out, rows=six_rows()[:5], repeat_count=3)
    assert count_bad["status"] == "blocked"
    assert count_bad["stop_reason"] == "case_count_mismatch"
    assert_strict_json(count_bad)

    full_ok = make_loop_state_payload(run_id="full", output_dir=out, rows=full_rows(), repeat_count=1, input_set="full")
    assert full_ok["input_set"] == "full"
    assert full_ok["hard_gate_rules"]["expected_cases"] == 24
    assert full_ok["status"] == "ready_for_path_b_integration"
    assert full_ok["next_priority_task"] == "qnn_delegate_app_stabilization_and_evidence"
    assert full_ok["requires_human_review"] is True
    assert_strict_json(full_ok)

    full_conditional = make_loop_state_payload(
        run_id="full_cond",
        output_dir=out,
        rows=full_rows("0.1"),
        repeat_count=1,
        input_set="full",
    )
    assert full_conditional["status"] == "full_benchmark_completed_with_quality_boundary"
    assert full_conditional["next_priority_task"] == "human_review_full_contact_sheet_then_qnn_delegate_app_evidence"
    assert "quality_failure_or_conditional" in full_conditional["knowledge_base_triggered"]
    assert_strict_json(full_conditional)

    full_count_bad = make_loop_state_payload(
        run_id="full_count",
        output_dir=out,
        rows=full_rows()[:23],
        repeat_count=1,
        input_set="full",
    )
    assert full_count_bad["status"] == "blocked"
    assert full_count_bad["case_count_warning"] == "expected 24 full cases, got 23"
    assert_strict_json(full_count_bad)

    print("loop policy dry-run checks passed")


if __name__ == "__main__":
    main()
