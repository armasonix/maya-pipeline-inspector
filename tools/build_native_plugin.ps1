param(
    [ValidateSet(2024, 2025, 2026)]
    [int]$MayaVersion = 2025
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$devkit = $env:MAYA_DEVKIT_ROOT
if (-not $devkit) {
    $devkit = "C:\Program Files\Autodesk\Maya$MayaVersion"
}
$buildDir = Join-Path $repoRoot "native\build\maya$MayaVersion"
$logPath = Join-Path $repoRoot "debug-ee1eca.log"

function Write-BuildDebugLog {
    param(
        [string]$Message,
        [hashtable]$Data,
        [string]$HypothesisId
    )
    # region agent log
    try {
        $entry = @{
            sessionId = "ee1eca"
            runId     = "build-native-plugin"
            hypothesisId = $HypothesisId
            location  = "tools/build_native_plugin.ps1"
            message   = $Message
            data      = $Data
            timestamp = [int64]([DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds())
        } | ConvertTo-Json -Compress
        Add-Content -LiteralPath $logPath -Value $entry -Encoding utf8
    } catch {
        # Best-effort debug logging only.
    }
    # endregion
}

function Resolve-CMakeExecutable {
    $cmakeCmd = Get-Command cmake -ErrorAction SilentlyContinue
    if ($cmakeCmd) {
        return $cmakeCmd.Source
    }

    $vsCmakeCandidates = @(
        "${env:ProgramFiles}\Microsoft Visual Studio\2022\Community\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe",
        "${env:ProgramFiles}\Microsoft Visual Studio\2022\Professional\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe",
        "${env:ProgramFiles}\Microsoft Visual Studio\2022\Enterprise\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe",
        "${env:ProgramFiles(x86)}\Microsoft Visual Studio\2019\Community\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe"
    )
    foreach ($candidate in $vsCmakeCandidates) {
        if (Test-Path -LiteralPath $candidate) {
            return $candidate
        }
    }

    throw "cmake not found in PATH and no Visual Studio bundled CMake was detected."
}

function Resolve-VcVarsBatch {
    $vcvarsCandidates = @(
        "${env:ProgramFiles}\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat",
        "${env:ProgramFiles}\Microsoft Visual Studio\2022\Professional\VC\Auxiliary\Build\vcvars64.bat",
        "${env:ProgramFiles}\Microsoft Visual Studio\2022\Enterprise\VC\Auxiliary\Build\vcvars64.bat",
        "${env:ProgramFiles(x86)}\Microsoft Visual Studio\2019\Community\VC\Auxiliary\Build\vcvars64.bat"
    )
    foreach ($candidate in $vcvarsCandidates) {
        if (Test-Path -LiteralPath $candidate) {
            return $candidate
        }
    }

    throw "vcvars64.bat not found. Install Visual Studio Build Tools with the C++ workload."
}

function Invoke-NativeBuildStep {
    param(
        [string]$VcVars,
        [string]$CMake,
        [string]$Command
    )

    cmd /c "`"$VcVars`" && `"$CMake`" $Command"
    if ($LASTEXITCODE -ne 0) {
        throw "Native plug-in build step failed (exit $LASTEXITCODE): $Command"
    }
}

$cmake = Resolve-CMakeExecutable
$vcvars = Resolve-VcVarsBatch
Write-BuildDebugLog -Message "build_start" -Data @{
    mayaVersion = $MayaVersion
    devkit      = $devkit
    cmake       = $cmake
    vcvars      = $vcvars
    buildDir    = $buildDir
} -HypothesisId "H-CMAKE"

$nativeDir = Join-Path $repoRoot "native"
Invoke-NativeBuildStep -VcVars $vcvars -CMake $cmake -Command (
    "-S `"$nativeDir`" -B `"$buildDir`" -DMAYA_VERSION=$MayaVersion -DMAYA_DEVKIT_ROOT=`"$devkit`""
)
Invoke-NativeBuildStep -VcVars $vcvars -CMake $cmake -Command "--build `"$buildDir`" --config Release"
Invoke-NativeBuildStep -VcVars $vcvars -CMake $cmake -Command "--install `"$buildDir`" --config Release"

$artifact = Join-Path $repoRoot "maya_module\plug-ins\$MayaVersion\shader_health_inspector.mll"
$managerArtifact = Join-Path $repoRoot "maya_module\plug-ins\shader_health_inspector.mll"
if (Test-Path -LiteralPath $artifact) {
    Copy-Item -LiteralPath $artifact -Destination $managerArtifact -Force
    Write-Host "Plug-in Manager copy: $managerArtifact"
}
Write-BuildDebugLog -Message "build_complete" -Data @{
    artifact        = $artifact
    managerArtifact = $managerArtifact
    exists          = (Test-Path -LiteralPath $artifact)
    managerExists   = (Test-Path -LiteralPath $managerArtifact)
} -HypothesisId "H-INSTALL"

Write-Host "Installed plug-in for Maya $MayaVersion from $devkit"
Write-Host "Artifact: $artifact"
