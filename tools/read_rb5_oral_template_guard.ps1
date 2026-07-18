param(
    [string]$Path = "",
    [string]$PreviousHash = "",
    [string]$StateFile = "",
    [int]$ExcerptChars = 1400,
    [switch]$RequireChanged,
    [switch]$UpdateState
)

$ErrorActionPreference = "Stop"

function Join-Codepoints([int[]]$Codes) {
    return -join ($Codes | ForEach-Object { [char]$_ })
}

if ($Path -eq "") {
    $ownProjectDir = Join-Codepoints @(0x81EA, 0x5DF1, 0x7684, 0x9879, 0x76EE)
    $templateName = "RB5 Gen2 " + (Join-Codepoints @(0x9879, 0x76EE, 0x53E3, 0x64AD, 0x6A21, 0x677F)) + ".md"
    $Path = Join-Path $env:USERPROFILE ("Nutstore\1\Typora_save\" + $ownProjectDir + "\" + $templateName)
}

if ($StateFile -eq "") {
    $repoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
    $stateDir = Join-Path $repoRoot ".state"
    $StateFile = Join-Path $stateDir "rb5_oral_template_hash.txt"
}

if (-not (Test-Path -LiteralPath $Path)) {
    throw "Template file not found: $Path"
}

$item = Get-Item -LiteralPath $Path
$hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash
$content = Get-Content -Raw -Encoding UTF8 -LiteralPath $Path
$stateHash = ""
if (Test-Path -LiteralPath $StateFile) {
    $stateHash = (Get-Content -Raw -Encoding ASCII -LiteralPath $StateFile).Trim()
}
if ($PreviousHash -eq "" -and $stateHash -ne "") {
    $PreviousHash = $stateHash
}

Write-Host "TEMPLATE_PATH=$($item.FullName)"
Write-Host "LENGTH=$($item.Length)"
Write-Host "LAST_WRITE_TIME=$($item.LastWriteTime.ToString('yyyy-MM-dd HH:mm:ss'))"
Write-Host "ATTRIBUTES=$($item.Attributes)"
Write-Host "SHA256=$hash"
Write-Host "STATE_FILE=$StateFile"

if ($PreviousHash -ne "") {
    if ($hash -eq $PreviousHash) {
        Write-Host "HASH_STATUS=UNCHANGED_FROM_PREVIOUS"
        if ($RequireChanged) {
            Write-Error "Template hash is unchanged. If the user says the template was updated, stop and ask them to save/sync the file before continuing."
            exit 2
        }
    } else {
        Write-Host "HASH_STATUS=CHANGED_FROM_PREVIOUS"
    }
} else {
    Write-Host "HASH_STATUS=NO_PREVIOUS_HASH"
}

$marker = "## " + (Join-Codepoints @(0x6211, 0x9700, 0x8981, 0x4F60, 0x505A, 0x3010, 0x6A21, 0x5757, 0x002F, 0x529F, 0x80FD, 0x3011))
$index = $content.IndexOf($marker)
if ($index -ge 0) {
    $excerpt = $content.Substring($index, [Math]::Min($ExcerptChars, $content.Length - $index))
    Write-Host "TASK_EXCERPT_BEGIN"
    Write-Output $excerpt
    Write-Host "TASK_EXCERPT_END"
} else {
    Write-Host "TASK_EXCERPT_BEGIN"
    Write-Output $content.Substring(0, [Math]::Min($ExcerptChars, $content.Length))
    Write-Host "TASK_EXCERPT_END"
}

if ($UpdateState) {
    $stateParent = Split-Path -Parent $StateFile
    if (-not (Test-Path -LiteralPath $stateParent)) {
        New-Item -ItemType Directory -Force -Path $stateParent | Out-Null
    }
    Set-Content -Encoding ASCII -NoNewline -LiteralPath $StateFile -Value $hash
    Write-Host "STATE_UPDATED=1"
}
