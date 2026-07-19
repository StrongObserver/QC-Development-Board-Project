# Harness And Loop Engineering Policy

Updated: 2026-07-19

## Purpose

This file fixes a recurring loop failure mode:

```text
Negative evidence must not be converted into project stagnation.
Stable progress must not be converted into project completion unless every
designed objective is either completed or has a verified hard blocker.
```

The project needs stable baselines and Git commits, but a committed stable
version is a checkpoint, not a ceiling. A result that says "not justified for
the current mainline" must not be rewritten as "never explore this direction".

## Core Rule

Every negative, conditional, no-go, or deferred decision must carry scope.

Use these scopes:

| scope | meaning | allowed next action |
| --- | --- | --- |
| `claim_gate` | Do not make this claim yet | Gather stronger evidence or narrow the claim |
| `mainline_gate` | Do not put this in the default path yet | Keep as an isolated experiment or backlog item |
| `implementation_gate` | Do not implement this large change in the current loop | Write a probe, design a smaller experiment, or defer with trigger |
| `dead_end` | Evidence proves the route is not viable | Stop only this route and record why |

Only `dead_end` means "do not continue exploring this route". Use it only when
there is direct evidence that the route cannot work or would violate a hard
project constraint.

## Negative Evidence Rules

| result type | correct interpretation | wrong interpretation |
| --- | --- | --- |
| lower PSNR | metric mismatch or fidelity loss to investigate | model is useless |
| conditional visual result | usable with caveat or needs focused review | stop all related work |
| no immediate latency gain | current patch is not enough | no more performance work |
| high switching cost | do not default to live routing yet | never compare or combine models |
| dependency/tooling cost too high | defer package integration | never add the metric |
| physical evidence missing | ask for capture or create capture protocol | replace it with benchmark evidence |

## Stable Baseline Rule

A stable commit means:

```text
This version is known-good and recoverable.
```

It does not mean:

```text
Future work must stay close to this version forever.
```

After a stable baseline is committed, the loop should usually open one of these
lanes:

| lane | purpose |
| --- | --- |
| `showcase_lane` | Turn current evidence into resume/demo material |
| `exploration_lane` | Try a bounded higher-upside idea without weakening the baseline |
| `quality_lane` | Investigate visible artifacts or model tradeoffs |
| `performance_lane` | Attack a measured latency/memory/power bottleneck |
| `product_lane` | Validate real-camera, sustained, or user-facing behavior |

## Full-Scope Completion Rule

The project design is the scope floor, not an optional menu. If the original
project plan lists an item, the loop must keep that item in one of these states:

| state | meaning |
| --- | --- |
| `done` | implemented and verified with evidence |
| `in_progress` | currently being executed |
| `queued` | not current step yet, but still required |
| `blocked_needs_user` | cannot proceed without a concrete user/device/action |
| `blocked_technical` | attempted and blocked by a concrete technical issue |
| `not_viable_with_evidence` | proven not viable under project constraints |

Do not use vague labels such as `optional`, `later`, `not needed`, or
`not current` to remove work from the project. Those labels can only affect
ordering, not whether the item remains in the task ledger.

Rules:

1. A checkpoint can close a milestone, not the whole project.
2. `mainline_gate` means "not default now"; it does not mean "do not try".
3. `implementation_gate` means "use a smaller probe first"; it does not mean
   "skip the feature".
4. A hard item can move to `blocked_technical` only after an actual attempt and
   evidence, not because it looks hard.
5. A route can move to `not_viable_with_evidence` only with direct evidence that
   it cannot work or would violate a hard constraint.
6. Every loop handoff must name the next unfinished design objective, not only
   the next documentation or stabilization task.

## Full-Scope Ledger Requirement

Maintain a project-wide task ledger for the original design goals. The current
ledger is:

```text
C:\Users\Admin\Desktop\QC-Development-Board-Project\PROJECT_FULL_SCOPE_LEDGER.md
```

Future agents must consult this ledger before declaring the project "done" or
stopping after a stable checkpoint. If live user instructions conflict with the
ledger, the live oral template wins, but the skipped ledger item must remain
visible for later.

## Exploration Contract

For any non-trivial exploration, define:

```text
Hypothesis:
Success metric:
Budget:
Rollback:
Baseline to compare against:
```

Examples:

```text
Hypothesis: YUV ROI conversion can save 2-3ms e2e without color/rotation regression.
Success metric: live ROI e2e p50 improves by at least 2ms and saved sample aligns visually.
Budget: one small Kotlin probe before native code.
Rollback: keep current toBitmap path and do not change default behavior.
Baseline: P5 postprocess/sample-copy live ROI run.
```

## Harness Responsibilities

The harness must:

1. Preserve stable evidence and commits.
2. Separate claim gates from exploration gates.
3. Keep failed or conditional experiments reviewable.
4. Prevent one outlier from damaging general performance.
5. Prevent one negative result from freezing the project.
6. Require before/after evidence for performance claims.
7. Keep human visual review as quality veto, not as a reason to stop all work.

## Loop State Language

Prefer:

```text
deferred_with_trigger
ready_for_bounded_experiment
mainline_not_justified_yet
claim_not_supported_yet
```

Avoid using vague labels such as:

```text
no-go
blocked
do not do this
not worth doing
```

unless the scope is explicit.

## Current Project Interpretation

Current route decisions mean:

```text
QuickSRNetSmall is the current live ROI workhorse candidate.
Real-ESRGAN remains the QNN/HTP milestone and perceptual comparison path.
Automatic dual-model live routing is not justified as the default path yet.
YUV ROI, perceptual metrics, AIMET, and real-camera expansion remain valid
future exploration lanes when their triggers are met.
```

They do not mean:

```text
Stop exploring new models.
Stop optimizing the data path.
Stop evaluating AIMET forever.
Stay only with the current stable demo.
```
