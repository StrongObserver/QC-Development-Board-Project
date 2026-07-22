# Tools

## RB5 oral-template guard

Use this before acting on a newly updated oral template. The default output
prints the full template text because the final section controls whether the
agent should execute immediately or align first:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools\read_rb5_oral_template_guard.ps1
```

Do not act from a task excerpt alone. If you only need a quick human-readable
preview, use the explicit summary mode:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools\read_rb5_oral_template_guard.ps1 -SummaryOnly
```

After confirming the template is the version you acted on, update the local
state hash:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools\read_rb5_oral_template_guard.ps1 -UpdateState
```

If the user says the template has been updated, use:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools\read_rb5_oral_template_guard.ps1 -RequireChanged
```

If `HASH_STATUS=UNCHANGED_FROM_PREVIOUS`, stop. Ask the user to save or sync the
Typora/Nutstore file before continuing. This prevents accidentally executing an
older oral-template version.

## RB5 progressive onboarding

Use this to check the minimal RB5 read order and the token-heavy files without
dumping long documents into the conversation:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools\rb5_progressive_onboarding.ps1
```

Include latest result metadata when the current task depends on existing
benchmark/app evidence:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools\rb5_progressive_onboarding.ps1 -IncludeLatestResult
```
