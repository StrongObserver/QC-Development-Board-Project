# Tools

## RB5 oral-template guard

Use this before acting on a newly updated oral template:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools\read_rb5_oral_template_guard.ps1
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
