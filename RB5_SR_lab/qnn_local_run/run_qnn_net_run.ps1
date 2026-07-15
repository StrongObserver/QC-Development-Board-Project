param(
    [string]$QairtRoot = $env:QAIRT_SDK_ROOT,
    [string]$DeviceSerial = "ff5d3ab4",
    [string]$DeviceDir = "/data/local/tmp/qnn_sr",
    [string]$ContextBinary = "C:\Users\Admin\Desktop\QC-Development-Board-Project\RB5_SR_lab\export_assets\real_esrgan_general_x4v3-qnn-w8a8-qcs8550-20260715\real_esrgan_general_x4v3-qnn_context_binary-w8a8-qualcomm_qcs8550_proxy\real_esrgan_general_x4v3.bin"
)

$ErrorActionPreference = "Stop"

function Require-File([string]$Path, [string]$Label) {
    if (-not (Test-Path -LiteralPath $Path)) {
        throw "Missing $Label`: $Path"
    }
}

if ([string]::IsNullOrWhiteSpace($QairtRoot)) {
    throw "QAIRT SDK path is missing. Pass -QairtRoot or set QAIRT_SDK_ROOT. Expected QAIRT 2.45.x to match the context binary."
}

$QairtRoot = (Resolve-Path -LiteralPath $QairtRoot).Path
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$LocalInput = Join-Path $ScriptDir "input.raw"
$LocalInputList = Join-Path $ScriptDir "input_list.txt"
$LocalHtpConfig = Join-Path $ScriptDir "HtpConfigFile.json"
$LocalPerfSetting = Join-Path $ScriptDir "PerfSetting.conf"
$LocalDeviceScript = Join-Path $ScriptDir "run_on_device.sh"

$QnnNetRun = Join-Path $QairtRoot "bin\aarch64-android\qnn-net-run"
$QnnProfileViewer = Join-Path $QairtRoot "bin\aarch64-android\qnn-profile-viewer"
$LibRoot = Join-Path $QairtRoot "lib\aarch64-android"
$Skel = Join-Path $QairtRoot "lib\hexagon-v73\unsigned\libQnnHtpV73Skel.so"

Require-File $QnnNetRun "qnn-net-run"
Require-File $QnnProfileViewer "qnn-profile-viewer"
Require-File (Join-Path $LibRoot "libQnnHtp.so") "libQnnHtp.so"
Require-File (Join-Path $LibRoot "libQnnHtpNetRunExtensions.so") "libQnnHtpNetRunExtensions.so"
Require-File (Join-Path $LibRoot "libQnnHtpV73Stub.so") "libQnnHtpV73Stub.so"
Require-File (Join-Path $LibRoot "libQnnHtpPrepare.so") "libQnnHtpPrepare.so"
Require-File (Join-Path $LibRoot "libQnnSystem.so") "libQnnSystem.so"
Require-File $Skel "libQnnHtpV73Skel.so"
Require-File $ContextBinary "QNN context binary"
Require-File $LocalInput "input.raw"
Require-File $LocalInputList "input_list.txt"
Require-File $LocalHtpConfig "HtpConfigFile.json"
Require-File $LocalPerfSetting "PerfSetting.conf"
Require-File $LocalDeviceScript "run_on_device.sh"

$InputSize = (Get-Item -LiteralPath $LocalInput).Length
if ($InputSize -ne 49152) {
    throw "input.raw must be 49152 bytes for [1,128,128,3] uint8, got $InputSize"
}

adb -s $DeviceSerial root | Out-Host
adb -s $DeviceSerial shell "mkdir -p $DeviceDir/output" | Out-Host

adb -s $DeviceSerial push $QnnNetRun "$DeviceDir/qnn-net-run" | Out-Host
adb -s $DeviceSerial push $QnnProfileViewer "$DeviceDir/qnn-profile-viewer" | Out-Host
adb -s $DeviceSerial push (Join-Path $LibRoot "libQnnHtp.so") "$DeviceDir/libQnnHtp.so" | Out-Host
adb -s $DeviceSerial push (Join-Path $LibRoot "libQnnHtpNetRunExtensions.so") "$DeviceDir/libQnnHtpNetRunExtensions.so" | Out-Host
adb -s $DeviceSerial push (Join-Path $LibRoot "libQnnHtpV73Stub.so") "$DeviceDir/libQnnHtpV73Stub.so" | Out-Host
adb -s $DeviceSerial push (Join-Path $LibRoot "libQnnHtpPrepare.so") "$DeviceDir/libQnnHtpPrepare.so" | Out-Host
adb -s $DeviceSerial push (Join-Path $LibRoot "libQnnSystem.so") "$DeviceDir/libQnnSystem.so" | Out-Host
adb -s $DeviceSerial push $Skel "$DeviceDir/libQnnHtpV73Skel.so" | Out-Host
adb -s $DeviceSerial push $ContextBinary "$DeviceDir/real_esrgan_general_x4v3.bin" | Out-Host
adb -s $DeviceSerial push $LocalInput "$DeviceDir/input.raw" | Out-Host
adb -s $DeviceSerial push $LocalInputList "$DeviceDir/input_list.txt" | Out-Host
adb -s $DeviceSerial push $LocalHtpConfig "$DeviceDir/HtpConfigFile.json" | Out-Host
adb -s $DeviceSerial push $LocalPerfSetting "$DeviceDir/PerfSetting.conf" | Out-Host
adb -s $DeviceSerial push $LocalDeviceScript "$DeviceDir/run_on_device.sh" | Out-Host

adb -s $DeviceSerial shell "chmod 755 $DeviceDir/qnn-net-run $DeviceDir/qnn-profile-viewer $DeviceDir/run_on_device.sh" | Out-Host

adb -s $DeviceSerial shell "$DeviceDir/run_on_device.sh" | Tee-Object -FilePath (Join-Path $ScriptDir "qnn_net_run_device.log")

$PullDir = Join-Path $ScriptDir "pulled_output"
New-Item -ItemType Directory -Force -Path $PullDir | Out-Null
adb -s $DeviceSerial pull "$DeviceDir/output" $PullDir | Out-Host

$RawCandidates = Get-ChildItem -Path $PullDir -Recurse -File -Filter "*.raw" | Sort-Object Length -Descending
if ($RawCandidates.Count -eq 0) {
    throw "No .raw output pulled from $DeviceDir/output"
}

$RawOut = $RawCandidates[0].FullName
Write-Host "[ok] raw output: $RawOut ($((Get-Item -LiteralPath $RawOut).Length) bytes)"
$Python = "python"
$VenvPython = "C:\Users\Admin\Desktop\QC-Development-Board-Project\RB5_SR_lab\.venv-eval\Scripts\python.exe"
if (Test-Path -LiteralPath $VenvPython) {
    $Python = $VenvPython
}
$PngOut = Join-Path $PullDir "upscaled.png"
& $Python (Join-Path $ScriptDir "convert_qnn_output.py") $RawOut --out $PngOut | Out-Host
Write-Host "[ok] png output: $PngOut"
