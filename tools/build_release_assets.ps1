param(
    [int[]]$MayaVersions = @(2024, 2025, 2026),
    [switch]$SkipNativeBuild,
    [string]$OutputDir = ""
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$buildScript = Join-Path $repoRoot "tools\build_native_plugin.ps1"
$packageScript = Join-Path $repoRoot "tools\build_release_package.py"

if (-not $SkipNativeBuild) {
    $builtYears: [System.Collections.Generic.List[int]] = @()
    foreach ($year in $MayaVersions) {
        $mayaRoot = Join-Path ${env:ProgramFiles} "Autodesk\Maya$year"
        $mayapy = Join-Path $mayaRoot "bin\mayapy.exe"
        if (-not (Test-Path -LiteralPath $mayapy)) {
            Write-Host "Skipping Maya $year native build (not installed): $mayapy"
            continue
        }
        Write-Host "Building native plug-in for Maya $year"
        & $buildScript -MayaVersion $year
        $builtYears.Add($year) | Out-Null
    }

    if ($builtYears.Count -eq 0) {
        throw "No Maya installations found for native plug-in build. Install Maya 2024/2025/2026 or pass -SkipNativeBuild for zip-only packaging."
    }
    Write-Host "Built native plug-ins for Maya year(s): $($builtYears -join ', ')"
}

$packageArgs = @("$packageScript", "--require-native")
if ($OutputDir) {
    $packageArgs += @("--output-dir", $OutputDir)
}
python @packageArgs
if ($LASTEXITCODE -ne 0) {
    throw "Release package build failed (exit $LASTEXITCODE)."
}
