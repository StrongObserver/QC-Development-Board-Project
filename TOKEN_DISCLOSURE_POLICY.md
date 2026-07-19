# RB5 Token Disclosure Policy

Updated: 2026-07-20

## Purpose

This file keeps RB5 onboarding from consuming a large share of the conversation
window before useful engineering work starts.

The rule is:

```text
Load the smallest source that can answer the current question.
Escalate to longer documents only when a task, failure, or user instruction
requires that extra detail.
```

The user's current oral template remains P0. If it explicitly says to read a
file in full, do that full read. Otherwise use the progressive disclosure levels
below.

## Token Cost Findings

| source | observed cost driver | default handling |
| --- | --- | --- |
| `RB5 Gen2_AI上下文.md` | 1451 lines / about 111KB; full reads dominate onboarding cost | read heading index and relevant sections first |
| internal camera/SR/QNN Markdown folders | broad keyword search can return thousands of lines from long docs | read only `RB5/Harness 读取摘要` first |
| `MainActivity.kt` and large Kotlin files | full-file reads mix many unrelated app paths | read targeted functions or symbols first |
| benchmark result folders | raw logs, metrics, and review guides can be large and repetitive | read `loop_state.json` first, then `SUMMARY.md` |
| contact sheets / images | visual evidence is high value but not textual context | open only when visual review is required |

## Disclosure Levels

### L0: Route

Use at the start of almost every RB5 turn:

```text
1. Full-read the current oral template.
2. Read PROJECT_ENTRYPOINTS.md.
3. Read LOOP_TASK_QUEUE.md.
4. Read PROJECT_FULL_SCOPE_LEDGER.md.
5. Read latest loop_state.json if the task depends on benchmark/app evidence.
```

L0 should normally be enough to choose the next loop task.

### L1: Summaries

Use when the task needs project background but not exact historical details:

```text
RB5 Gen2_AI上下文.md:
  - heading index
  - 当前总状态（给失忆 AI 先看）
  - 当前 Android Studio 工程
  - 当前项目结构
  - 暂未开始
  - the relevant subsection under 下一步计划

Internal knowledge documents:
  - only `RB5/Harness 读取摘要`

External research:
  - knowledge_base/external_research/README.md
  - relevant RESOURCE_CARD.md
```

### L2: Task Evidence

Use when implementing or debugging a specific lane:

```text
tile:
  - tile-related plan/output files
  - image I/O and model inference scripts

QNN / app runtime:
  - QNN Delegate code path
  - latest app/QNN loop_state and SUMMARY
  - relevant QNN internal-document summaries

evaluation:
  - eval_hub README/freeze only when expanding EvalHub
  - metric policy only when adding or changing metrics
```

### L3: Full Detail

Full-read long documents only when one of these is true:

```text
- the user explicitly asks for full reading
- editing that exact document
- a contradiction cannot be resolved from summaries
- a bug requires exact historical commands or error text
- final closeout needs exact evidence wording
```

## Search Rules

- Prefer precise headings, filenames, symbols, and run IDs over broad keyword
  scans.
- For long Markdown files, first get headings and line ranges, then read the
  smallest relevant range.
- For source files, search symbol names first, then read the surrounding
  function.
- For result folders, read `loop_state.json` before `SUMMARY.md`; read metrics
  only after the loop state says the run is valid.

## Loop Rule

The loop queue is controlled by:

```text
C:\Users\Admin\Desktop\QC-Development-Board-Project\LOOP_TASK_QUEUE.md
```

Do not re-open completed tasks just because their evidence is easy to read.
Use the queue and ledger to decide what is still unfinished.
