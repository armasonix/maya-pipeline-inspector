param(
    [ValidateSet(2024, 2025, 2026)]
    [int]$MayaVersion = 2024
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$mayaModule = Join-Path $repoRoot "maya_module"
$mayaExe = Join-Path ${env:ProgramFiles} "Autodesk\Maya$MayaVersion\bin\maya.exe"

if (-not (Test-Path -LiteralPath $mayaModule)) {
    throw "maya_module not found: $mayaModule"
}
if (-not (Test-Path -LiteralPath $mayaExe)) {
    throw "Maya executable not found: $mayaExe"
}

$env:MAYA_MODULE_PATH = $mayaModule
Write-Host "MAYA_MODULE_PATH=$mayaModule"
Write-Host "Launching: $mayaExe"
& $mayaExe
