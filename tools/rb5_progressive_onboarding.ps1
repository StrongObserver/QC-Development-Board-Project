param(
    [switch]$IncludeLatestResult
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)

function Join-Codepoints([int[]]$Codes) {
    return -join ($Codes | ForEach-Object { [char]$_ })
}

function Write-FileStat([string]$Label, [string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) {
        Write-Host "$Label=missing|$Path"
        return
    }
    $item = Get-Item -LiteralPath $Path
    $lines = (Get-Content -LiteralPath $Path -Encoding UTF8 | Measure-Object -Line).Lines
    Write-Host "$Label=present|lines=$lines|bytes=$($item.Length)|path=$Path"
}

Write-Host "RB5_PROGRESSIVE_ONBOARDING=1"
Write-Host "REPO_ROOT=$repoRoot"

$oralTemplateName = "RB5 Gen2" + (Join-Codepoints @(0x9879, 0x76EE, 0x53E3, 0x64AD, 0x6A21, 0x677F)) + ".txt"
$projectDirName = Join-Codepoints @(0x81EA, 0x5DF1, 0x7684, 0x9879, 0x76EE)
$contextFileName = "RB5 Gen2_AI" + (Join-Codepoints @(0x4E0A, 0x4E0B, 0x6587)) + ".md"
$longContextPath = Join-Path $env:USERPROFILE ("Nutstore\1\Typora_save\" + $projectDirName + "\" + $contextFileName)

Write-FileStat "ORAL_TEMPLATE" (Join-Path $repoRoot $oralTemplateName)
Write-FileStat "ENTRYPOINT" (Join-Path $repoRoot "PROJECT_ENTRYPOINTS.md")
Write-FileStat "TOKEN_POLICY" (Join-Path $repoRoot "TOKEN_DISCLOSURE_POLICY.md")
Write-FileStat "LOOP_QUEUE" (Join-Path $repoRoot "LOOP_TASK_QUEUE.md")
Write-FileStat "FULL_SCOPE_LEDGER" (Join-Path $repoRoot "PROJECT_FULL_SCOPE_LEDGER.md")
Write-FileStat "LONG_CONTEXT" $longContextPath

Write-Host "READ_ORDER_BEGIN"
Write-Host "1. Full-read ORAL_TEMPLATE because it is P0."
Write-Host "2. Read ENTRYPOINT."
Write-Host "3. Read TOKEN_POLICY."
Write-Host "4. Read LOOP_QUEUE."
Write-Host "5. Read FULL_SCOPE_LEDGER."
Write-Host "6. Read latest loop_state.json only when evidence state matters."
Write-Host "7. Read LONG_CONTEXT sections only when triggered by TOKEN_POLICY."
Write-Host "READ_ORDER_END"

if ($IncludeLatestResult) {
    $resultsRoot = "C:\Users\Admin\Videos\RB5 gen2\RB5_SR_Benchmark_v1\results"
    if (Test-Path -LiteralPath $resultsRoot) {
        $latest = Get-ChildItem -LiteralPath $resultsRoot -Directory |
            Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName "loop_state.json") } |
            Sort-Object LastWriteTime -Descending |
            Select-Object -First 1
        if ($null -ne $latest) {
            Write-Host "LATEST_RESULT=$($latest.FullName)"
            Write-FileStat "LATEST_LOOP_STATE" (Join-Path $latest.FullName "loop_state.json")
            Write-FileStat "LATEST_SUMMARY" (Join-Path $latest.FullName "SUMMARY.md")
            Write-FileStat "LATEST_NEXT_ACTION" (Join-Path $latest.FullName "NEXT_ACTION.md")
        } else {
            Write-Host "LATEST_RESULT=none_with_loop_state"
        }
    } else {
        Write-Host "RESULTS_ROOT=missing|$resultsRoot"
    }
}
