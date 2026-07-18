"""Loop policy helpers for RB5 SR benchmark runs.

This module is deliberately small and machine-readable. It keeps the current
task priorities, hard gates, and stop reasons close to the runner scripts
without turning the benchmark QA files into another long planning document.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Iterable


TASK_PRIORITY = [
    {
        "priority": "P0",
        "task": "follow_current_oral_template",
        "boundary": "The user's latest RB5 oral-template request always wins over old NEXT_ACTION.md files.",
    },
    {
        "priority": "P1",
        "task": "qnn_w8a8_repeat_smoke_p50_p95",
        "boundary": "Use the existing 6-case smoke set and QNN context binary; only claim local qnn-net-run runner timing, not Android app e2e.",
    },
    {
        "priority": "P2",
        "task": "qnn_w8a8_full_24_case_benchmark",
        "boundary": "Use the fixed 24-case manifest after smoke is stable; do not rebuild or overwrite cases.",
    },
    {
        "priority": "P3",
        "task": "qnn_delegate_app_stabilization_and_evidence",
        "boundary": "Path B mainline is the QNN TFLite Delegate app route; direct QNN context-binary app execution is a non-blocking deeper experiment.",
    },
    {
        "priority": "P4",
        "task": "targeted_l2_quality_investigation",
        "boundary": "Run only for a repeated category failure; do not let one conditional low-light case derail the QNN mainline.",
    },
]

HARNESS_LOOP_SCOPE_POLICY = {
    "rule": "Negative evidence must include scope. A stable baseline is a checkpoint, not a ceiling.",
    "scopes": {
        "claim_gate": "Do not make this claim yet; gather stronger evidence or narrow the claim.",
        "mainline_gate": "Do not put this in the default path yet; bounded exploration is still allowed.",
        "implementation_gate": "Do not implement the large change in the current loop; use a smaller probe or trigger.",
        "dead_end": "Stop this route only when direct evidence proves it cannot work or violates a hard constraint.",
    },
    "exploration_lanes": [
        "showcase_lane",
        "exploration_lane",
        "quality_lane",
        "performance_lane",
        "product_lane",
    ],
}


METRIC_ROLE_POLICY = {
    "hard_gate": [
        "output_size",
        "raw_output_bytes",
        "output_stddev",
        "netrun_execute_us",
        "qnn_execute_us",
        "qnn_accelerator_execute_us",
    ],
    "supporting_evidence": [
        "psnr_bicubic_vs_hr",
        "ssim_bicubic_vs_hr",
        "psnr_qnn_vs_hr",
        "ssim_qnn_vs_hr",
        "psnr_delta_qnn_minus_bicubic",
        "sharpness_qnn_over_bicubic",
    ],
    "diagnostic_not_hard_gate": [
        "LPIPS",
        "NR-IQA",
        "Ringing",
        "Visual Noise",
        "MLLM labels",
    ],
    "rule": "Only hard_gate fields can block runner validity automatically. Supporting and diagnostic metrics require side-by-side human review before quality claims.",
}


KNOWLEDGE_BASE_RULES = [
    {
        "trigger": "evaluation_system_expansion",
        "progressive_disclosure": "Use EvalHub registries before downloading data or adding metrics; do not replace RB5_SR_Benchmark_v1 silently.",
        "internal_first": [
            r"C:\Users\Admin\Desktop\QC-Development-Board-Project\eval_hub\README.md",
            r"C:\Users\Admin\Desktop\QC-Development-Board-Project\eval_hub\registries\lifecycle_matrix.md",
            r"C:\Users\Admin\Desktop\QC-Development-Board-Project\eval_hub\registries\dataset_registry.csv",
            r"C:\Users\Admin\Desktop\QC-Development-Board-Project\eval_hub\registries\metric_policy.csv",
        ],
        "external_if_needed": [],
    },
    {
        "trigger": "quality_failure_or_conditional",
        "progressive_disclosure": "Read only RB5/Harness summaries first; open full docs only if the summary matches the failure.",
        "internal_first": [
            r"C:\Users\Admin\Nutstore\1\Typora_save\字节_嵌入式camera实习\丁大均\超分.md",
            r"C:\Users\Admin\Nutstore\1\Typora_save\字节_嵌入式camera实习\丁大均\客观化评测方法.md",
            r"C:\Users\Admin\Nutstore\1\Typora_save\字节_嵌入式camera实习\丁大均\自然细腻的细节质感效果表现及客观分析（含 RAW 噪声回叠）.md",
        ],
        "external_if_needed": [
            r"C:\Users\Admin\Desktop\QC-Development-Board-Project\knowledge_base\external_research\super_resolution\realesrgan\RESOURCE_CARD.md",
            r"C:\Users\Admin\Desktop\QC-Development-Board-Project\knowledge_base\external_research\text_fidelity_sr\tpgsr\RESOURCE_CARD.md",
            r"C:\Users\Admin\Desktop\QC-Development-Board-Project\knowledge_base\external_research\text_fidelity_sr\sgenet\RESOURCE_CARD.md",
        ],
    },
    {
        "trigger": "qnn_or_android_integration_failure",
        "progressive_disclosure": "Read runner logs and hard gates first; then read QNN/HTP summaries before full docs or source.",
        "internal_first": [
            r"C:\Users\Admin\Nutstore\1\Typora_save\字节_嵌入式camera实习\万钰臻\高通NPU集成分析.md",
            r"C:\Users\Admin\Nutstore\1\Typora_save\字节_嵌入式camera实习\万钰臻\端侧大模型 LiteRT 与高通 HTP 算子执行机制与量化管线分析.md",
        ],
        "external_if_needed": [
            r"C:\Users\Admin\Desktop\QC-Development-Board-Project\knowledge_base\external_research\qnn_android\qualcomm_ai_hub_apps\RESOURCE_CARD.md",
            r"C:\Users\Admin\Desktop\QC-Development-Board-Project\knowledge_base\external_research\qnn_android\edgeimpulse_qnn_android\RESOURCE_CARD.md",
        ],
    },
    {
        "trigger": "lightweight_fallback_needed",
        "progressive_disclosure": "Read resource cards before opening code; compare on the fixed benchmark before changing app code.",
        "internal_first": [
            r"C:\Users\Admin\Nutstore\1\Typora_save\字节_嵌入式camera实习\超分\FastSR：一种超快速的图像超分辨率方法.md",
        ],
        "external_if_needed": [
            r"C:\Users\Admin\Desktop\QC-Development-Board-Project\knowledge_base\external_research\super_resolution\quicksrnet\RESOURCE_CARD.md",
        ],
    },
    {
        "trigger": "real_camera_or_raw_pipeline_failure",
        "progressive_disclosure": "Do not use these docs for fixed-image QNN smoke; use them only after the task enters real camera/RAW/video.",
        "internal_first": [
            r"C:\Users\Admin\Nutstore\1\Typora_save\字节_嵌入式camera实习\丁大均\AI ISP.md",
            r"C:\Users\Admin\Nutstore\1\Typora_save\字节_嵌入式camera实习\丁大均\噪声标定.md",
            r"C:\Users\Admin\Nutstore\1\Typora_save\字节_嵌入式camera实习\丁大均\计算光学.md",
        ],
        "external_if_needed": [
            r"C:\Users\Admin\Desktop\QC-Development-Board-Project\knowledge_base\external_research\super_resolution\bsrgan_real_degradation\RESOURCE_CARD.md",
        ],
    },
]


CATEGORY_REVIEW_FOCUS = {
    "structure_edges": "line geometry, edge clarity, jagged edges, ringing or halo",
    "repeating_patterns": "checkerboard artifacts, fake periodic texture, pattern stability",
    "natural_texture": "texture naturalness, detail loss, fake texture, over-sharpening, color naturalness",
    "low_light_noise": "noise amplification, dark detail clumping, luma/contrast shift, under-enhancement",
    "text_signage": "text readability, character shape correctness, double strokes, ringing or halo",
    "people_scene": "skin, face/body edges, clothing texture, unnatural detail, color or luma shift",
}


HARD_GATE_RULES = {
    "expected_cases": 6,
    "expected_output_size": "512x512",
    "expected_raw_bytes": 786432,
    "required_profile_fields": [
        "netrun_execute_us",
        "qnn_execute_us",
        "qnn_accelerator_execute_us",
    ],
}


INPUT_SET_EXPECTED_CASES = {
    "smoke": 6,
    "full": 24,
}


def hard_gate_rules(expected_cases: int) -> dict[str, object]:
    rules = dict(HARD_GATE_RULES)
    rules["expected_cases"] = expected_cases
    return rules


def _to_float(value: object, default: float = float("nan")) -> float:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def percentile(values: Iterable[float], q: float) -> float:
    ordered = sorted(v for v in values if v == v)
    if not ordered:
        return float("nan")
    if len(ordered) == 1:
        return ordered[0]
    pos = (len(ordered) - 1) * q
    lower = int(pos)
    upper = min(lower + 1, len(ordered) - 1)
    weight = pos - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def hard_gate_failures(row: dict[str, str]) -> list[str]:
    failures: list[str] = []
    if row.get("output_size") != HARD_GATE_RULES["expected_output_size"]:
        failures.append("BAD_OUTPUT_SIZE")
    raw_bytes = _to_float(row.get("raw_output_bytes"), -1)
    if raw_bytes != raw_bytes or int(raw_bytes) != HARD_GATE_RULES["expected_raw_bytes"]:
        failures.append("BAD_RAW_OUTPUT_BYTES")
    if _to_float(row.get("output_stddev"), 0.0) < 1.0:
        failures.append("BLANK_OR_NEAR_BLANK_OUTPUT")
    for field in HARD_GATE_RULES["required_profile_fields"]:
        if not row.get(field):
            failures.append(f"MISSING_{field.upper()}")
    return failures


def annotate_rows(rows: list[dict[str, str]]) -> dict[str, int]:
    counts = {"pass": 0, "conditional": 0, "fail": 0}
    for row in rows:
        failures = hard_gate_failures(row)
        row["hard_gate"] = "fail" if failures else "pass"
        row["failure_code"] = ";".join(failures)
        if failures:
            decision = "fail"
            hint = "Hard gate failed; fix runner or output validity before discussing visual quality."
        else:
            psnr_delta = _to_float(row.get("psnr_delta_qnn_minus_bicubic"), 0.0)
            category = row.get("category", "")
            if category == "low_light_noise" and psnr_delta < 0.3:
                decision = "conditional"
                row["failure_code"] = "UNDER_ENHANCED_LOW_LIGHT"
                hint = "Treat as low-light/model-boundary evidence unless human review finds a blocking artifact."
            else:
                decision = "pass"
                hint = "Hard gates pass; visual review still owns the final quality claim."
        row["auto_loop_decision"] = decision
        row["review_focus"] = CATEGORY_REVIEW_FOCUS.get(row.get("category", ""), "general visual artifacts")
        row["metric_role"] = "hard_gate=runner validity; psnr/ssim/sharpness=supporting evidence; human side-by-side review owns quality"
        row["loop_hint"] = hint
        row.setdefault("human_decision", "")
        row.setdefault("human_notes", "")
        counts[decision] += 1
    return counts


@dataclass(frozen=True)
class LoopState:
    status: str
    stop_reason: str
    next_priority_task: str
    requires_human_review: bool
    blocked_by: str
    notes: str


def environment_blocked_payload(
    *,
    run_id: str,
    output_dir: Path,
    repeat_count: int,
    blocked_by: str,
    notes: str,
    input_set: str = "smoke",
    expected_cases: int | None = None,
) -> dict[str, object]:
    expected_count = expected_cases if expected_cases is not None else INPUT_SET_EXPECTED_CASES.get(input_set, 6)
    next_task = (
        "fix_environment_then_rerun_qnn_full_benchmark"
        if input_set == "full"
        else "fix_environment_then_rerun_qnn_smoke"
    )
    return {
        "run_id": run_id,
        "input_set": input_set,
        "status": "environment_blocked",
        "stop_reason": "preflight_failed",
        "decision_scope": "implementation_gate",
        "next_priority_task": next_task,
        "requires_human_review": False,
        "blocked_by": blocked_by,
        "notes": notes + " This blocks the current run only; it is not a project dead end.",
        "case_count_warning": "",
        "task_priority": TASK_PRIORITY,
        "harness_loop_scope_policy": HARNESS_LOOP_SCOPE_POLICY,
        "hard_gate_rules": hard_gate_rules(expected_count),
        "metric_role_policy": METRIC_ROLE_POLICY,
        "knowledge_base_rules": KNOWLEDGE_BASE_RULES,
        "knowledge_base_triggered": [],
        "auto_decision_counts": {"pass": 0, "conditional": 0, "fail": 0},
        "repeat_count": repeat_count,
        "timing_summary_us": {
            "netrun_execute": {"avg": None, "p50": None, "p95": None},
            "qnn_accelerator_execute": {"avg": None, "p50": None, "p95": None},
        },
        "required_next_read": [
            str(output_dir / "SUMMARY.md"),
            str(output_dir / "NEXT_ACTION.md"),
            str(output_dir / "run_log.csv"),
            str(output_dir / "loop_state.json"),
            str(output_dir / "preflight_stdout.txt"),
        ],
    }


def decide_loop_state(rows: list[dict[str, str]], repeat_count: int, input_set: str = "smoke") -> LoopState:
    counts = {"pass": 0, "conditional": 0, "fail": 0}
    for row in rows:
        counts[row.get("auto_loop_decision", "fail")] = counts.get(row.get("auto_loop_decision", "fail"), 0) + 1

    if counts["fail"] > 0:
        return LoopState(
            status="blocked",
            stop_reason="hard_gate_failed",
            next_priority_task="fix_qnn_runner_or_output_validity",
            requires_human_review=False,
            blocked_by=";".join(sorted({row.get("failure_code", "") for row in rows if row.get("auto_loop_decision") == "fail"})),
            notes="Claim gate: do not make quality or performance claims until hard gates pass. This is not a dead end for the broader project.",
        )

    if input_set == "full":
        if counts["conditional"] > 0:
            return LoopState(
                status="full_benchmark_completed_with_quality_boundary",
                stop_reason="full_benchmark_completed_with_conditional_cases",
                next_priority_task="human_review_full_contact_sheet_then_qnn_delegate_app_evidence",
                requires_human_review=True,
                blocked_by="",
                notes="Claim gate: full benchmark completed with conditional cases; review the contact sheet, then continue QNN Delegate app evidence or bounded quality exploration if no visual blocker is found.",
            )
        return LoopState(
            status="ready_for_path_b_integration",
            stop_reason="full_benchmark_completed",
            next_priority_task="qnn_delegate_app_stabilization_and_evidence",
            requires_human_review=True,
            blocked_by="",
            notes="Full benchmark hard gates passed; review the full contact sheet, then continue QNN Delegate app stabilization and keep bounded exploration lanes open.",
        )

    if repeat_count < 3:
        return LoopState(
            status="ready_for_repeated_smoke",
            stop_reason="single_smoke_completed",
            next_priority_task="qnn_w8a8_repeat_smoke_p50_p95",
            requires_human_review=counts["conditional"] > 0,
            blocked_by="",
            notes="Single smoke proves the runner path; repeated smoke is needed before stable p50/p95 claims. This is a claim gate, not an exploration stop.",
        )

    if counts["conditional"] > 0:
        return LoopState(
            status="ready_with_quality_boundary",
            stop_reason="repeated_smoke_completed_with_conditional_cases",
            next_priority_task="qnn_w8a8_full_24_case_benchmark",
            requires_human_review=True,
            blocked_by="",
            notes="Conditional cases should be reviewed, but they do not block the main QNN path unless human review marks fail. They may open a bounded quality exploration lane.",
        )

    return LoopState(
        status="ready_for_full_benchmark",
        stop_reason="repeated_smoke_completed",
        next_priority_task="qnn_w8a8_full_24_case_benchmark",
        requires_human_review=False,
        blocked_by="",
        notes="Runner hard gates passed across repeated smoke; move to the fixed 24-case benchmark before app integration and preserve exploration lanes separately.",
    )


def numeric_summary(rows: list[dict[str, str]], key: str) -> dict[str, float]:
    values = [_to_float(row.get(key)) for row in rows]
    values = [v for v in values if v == v]
    if not values:
        return {"avg": float("nan"), "p50": float("nan"), "p95": float("nan")}
    return {
        "avg": mean(values),
        "p50": percentile(values, 0.50),
        "p95": percentile(values, 0.95),
    }


def make_loop_state_payload(
    *,
    run_id: str,
    output_dir: Path,
    rows: list[dict[str, str]],
    repeat_count: int,
    input_set: str = "smoke",
    expected_cases: int | None = None,
) -> dict[str, object]:
    expected_count = expected_cases if expected_cases is not None else INPUT_SET_EXPECTED_CASES.get(input_set, 6)
    counts = annotate_rows(rows)
    case_count_warning = ""
    if len(rows) != expected_count:
        case_count_warning = f"expected {expected_count} {input_set} cases, got {len(rows)}"
        counts["fail"] += 1
    state = decide_loop_state(rows, repeat_count, input_set)
    if case_count_warning and state.status != "blocked":
        state = LoopState(
            status="blocked",
            stop_reason="case_count_mismatch",
            next_priority_task="fix_benchmark_input_or_runner_case_selection",
            requires_human_review=False,
            blocked_by="CASE_COUNT_MISMATCH",
            notes="Implementation gate: case count is wrong; do not compare this run against the fixed protocol. Fix the run, but do not treat the project route as blocked.",
        )
    return {
        "run_id": run_id,
        "input_set": input_set,
        "status": state.status,
        "stop_reason": state.stop_reason,
        "next_priority_task": state.next_priority_task,
        "requires_human_review": state.requires_human_review,
        "blocked_by": state.blocked_by,
        "notes": state.notes,
        "decision_scope": decision_scope_for_state(state),
        "case_count_warning": case_count_warning,
        "task_priority": TASK_PRIORITY,
        "harness_loop_scope_policy": HARNESS_LOOP_SCOPE_POLICY,
        "hard_gate_rules": hard_gate_rules(expected_count),
        "metric_role_policy": METRIC_ROLE_POLICY,
        "knowledge_base_rules": KNOWLEDGE_BASE_RULES,
        "knowledge_base_triggered": knowledge_base_triggers(rows, state),
        "auto_decision_counts": counts,
        "repeat_count": repeat_count,
        "timing_summary_us": {
            "netrun_execute": numeric_summary(rows, "netrun_execute_p50_us" if repeat_count > 1 else "netrun_execute_us"),
            "qnn_accelerator_execute": numeric_summary(
                rows,
                "qnn_accelerator_execute_p50_us" if repeat_count > 1 else "qnn_accelerator_execute_us",
            ),
        },
        "required_next_read": [
            str(output_dir / "SUMMARY.md"),
            str(output_dir / "HUMAN_REVIEW_GUIDE.md"),
            str(output_dir / "metrics.csv"),
            str(output_dir / "run_log.csv"),
            str(output_dir / "loop_state.json"),
            str(output_dir / "contact_sheet.png"),
        ],
    }


def knowledge_base_triggers(rows: list[dict[str, str]], state: LoopState) -> list[str]:
    triggers: list[str] = []
    if state.status == "blocked":
        triggers.append("qnn_or_android_integration_failure")
    if any(row.get("auto_loop_decision") in {"conditional", "fail"} for row in rows):
        triggers.append("quality_failure_or_conditional")
    return triggers


def decision_scope_for_state(state: LoopState) -> str:
    if state.stop_reason in {"hard_gate_failed", "case_count_mismatch", "preflight_failed"}:
        return "implementation_gate"
    if "conditional" in state.stop_reason:
        return "claim_gate"
    return "ready_for_next_lane"
