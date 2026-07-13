param(
    [string]$RepoRoot = "",
    [int[]]$MayaVersions = @(2024, 2025, 2026)
)

$ErrorActionPreference = "Stop"
if (-not $RepoRoot) {
    $RepoRoot = Split-Path -Parent $PSScriptRoot
}
$mayaModule = (Resolve-Path -LiteralPath (Join-Path $RepoRoot "maya_module")).Path
$entry = "MAYA_MODULE_PATH = $mayaModule"
$documents = [Environment]::GetFolderPath("MyDocuments")

function Update-MayaEnvFile {
    param(
        [string]$Path,
        [string]$Line
    )

    $lines = @()
    if (Test-Path -LiteralPath $Path) {
        $lines = Get-Content -LiteralPath $Path -Encoding UTF8
        $lines = $lines | Where-Object { $_ -notmatch '^\s*MAYA_MODULE_PATH\s*=' }
    }
    $lines += $Line
    $parent = Split-Path -Parent $Path
    if (-not (Test-Path -LiteralPath $parent)) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }
    Set-Content -LiteralPath $Path -Value $lines -Encoding UTF8
}

$updated = @()
foreach ($year in $MayaVersions) {
    $mayaEnv = Join-Path $documents "maya\$year\Maya.env"
    $mayaRoot = Join-Path ${env:ProgramFiles} "Autodesk\Maya$year"
    if (-not (Test-Path -LiteralPath $mayaRoot)) {
        Write-Host "Skipping Maya $year (not installed): $mayaRoot"
        continue
    }
    Update-MayaEnvFile -Path $mayaEnv -Line $entry
    $updated += $mayaEnv
    Write-Host "Updated $mayaEnv"
}

if ($updated.Count -eq 0) {
    throw "No installed Maya versions found to update Maya.env"
}

Write-Host ""
Write-Host "Configured module path:"
Write-Host "  $entry"
Write-Host "Restart Maya completely so Plug-in Manager picks up the module."
