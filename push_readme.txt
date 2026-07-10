# Git commit and push convention

This file is the required convention for people and AI agents working in this
repository. Its purpose is to keep every pushed change small, searchable, and
safe to revert.

## 1. One logical change per commit and push

Each commit and each push must represent one independently understandable
change. Do not combine implementation, refactoring, generated files, IDE
settings, and unrelated cleanup in the same commit. If two changes need
different rollback decisions, they must be separate commits.

## 2. Commit subject format

Use exactly this format:

    <type>(<scope>): <imperative summary>

Rules:

- Use lowercase English for `type` and `scope`.
- Keep the summary at 72 characters or fewer, use an imperative verb, and do
  not end it with a period.
- Choose one type only: `feat`, `fix`, `perf`, `refactor`, `test`, `build`,
  `ci`, `docs`, `chore`, or `revert`.
- Use a concrete scope such as `android`, `camera`, `native`, `sr-lab`,
  `model`, `gradle`, `docs`, or `repo`.

Examples:

    feat(camera): add center ROI capture for live super resolution
    fix(native): respect Y-plane row stride when creating cv::Mat
    perf(model): enable NNAPI delegate for TFLite inference
    docs(repo): record verified RB5 deployment procedure
    revert(camera): disable unstable frame analyzer

## 3. Required commit body

For every code, configuration, model, dependency, or behavior change, add a
body after a blank line. It must state:

    Why: <problem or goal>
    Change: <what changed and its boundary>
    Verify: <exact command/device result, or "not run: <reason>">
    Rollback: git revert <this-commit-sha>; <side effect or migration note>

`Rollback` must name any data migration, model asset, or device behavior that
cannot be undone by a plain revert. Do not claim verification that was not run.

## 4. Pre-push checklist

Before every push:

1. Stage explicit paths; do not use a blind `git add .`.
2. Review `git diff --cached` and confirm there are no credentials, generated
   artifacts, APKs, local IDE files, virtual environments, or unrelated files.
3. Run the smallest relevant verification (for example Gradle build, unit test,
   device test, Python inference check) and record its result in the body.
4. Confirm the commit list with `git log --oneline origin/main..HEAD`.
5. Push only the reviewed commits to `main`.

## 5. Standard rollback procedure

To undo a pushed change without rewriting shared history:

    git revert <commit-sha>
    git push origin main

Do not force-push `main`. A force-push is allowed only after explicit owner
approval and must be documented in the replacement commit body.

## 6. This bootstrap commit

The initial workspace import uses the same format:

    chore(repo): bootstrap QC development board workspace

Its body records that it imports the Android and host-side SR workspaces,
excludes local/generated files, and did not run a new build. Revert it only if
the entire initial import must be removed.

## 7. Managed-workspace Git command

In this managed directory only, the top-level `.git` path is a read-only
mount. The active repository metadata is therefore kept in the ignored
`.qc-development-board.git/` directory. From the repository root, use:

    git --git-dir=.qc-development-board.git --work-tree=. status
    git --git-dir=.qc-development-board.git --work-tree=. log --oneline
    git --git-dir=.qc-development-board.git --work-tree=. revert <commit-sha>
    git --git-dir=.qc-development-board.git --work-tree=. push origin main

A normal clone of the GitHub repository has a standard writable `.git`
directory and should use ordinary `git` commands.
