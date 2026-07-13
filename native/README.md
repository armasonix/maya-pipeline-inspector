# Native Maya plug-in build

Thin C++ bootstrap that registers in Plug-in Manager and calls the existing Python module `pipeline_inspector_bootstrap`. Validation, UI, and rules stay in `src/pipeline_inspector/`.

Architecture: [docs/adr/0006-native-mll-plugin-strategy.md](../docs/adr/0006-native-mll-plugin-strategy.md)

## Requirements

- Licensed Autodesk Maya for the target year (2024 / 2025 / 2026)
- CMake ≥ 3.20 (standalone install **or** the copy bundled with Visual Studio 2022)
- **Windows:** Visual Studio 2019 or 2022 (MSVC)
- **Linux:** GCC 11+ (best-effort)
- **macOS:** Xcode / clang per Maya devkit (best-effort)

Set the devkit root to your Maya installation (headers and libs ship with Maya):

```text
MAYA_DEVKIT_ROOT=C:\Program Files\Autodesk\Maya2025
```

`MAYA_LOCATION` is accepted as a fallback.

## Windows build (recommended)

PowerShell from the repository root:

```powershell
$year = 2025
$devkit = "C:\Program Files\Autodesk\Maya$year"
cmake -S native -B "native/build/maya$year" `
  -DMAYA_VERSION=$year `
  -DMAYA_DEVKIT_ROOT=$devkit
cmake --build "native/build/maya$year" --config Release
cmake --install "native/build/maya$year" --config Release
```

Or use the helper script (auto-detects Visual Studio `cmake` and `vcvars64` when `cmake` is not on `PATH`):

```powershell
.\tools\build_native_plugin.ps1 -MayaVersion 2024
```

Output is copied to:

```text
maya_module/plug-ins/{year}/pipeline_inspector.mll
```

## Linux / macOS

```bash
year=2025
devkit="/usr/autodesk/maya2025"
cmake -S native -B "native/build/maya${year}" \
  -DMAYA_VERSION="${year}" \
  -DMAYA_DEVKIT_ROOT="${devkit}"
cmake --build "native/build/maya${year}" --config Release
cmake --install "native/build/maya${year}" --config Release
```

Artifact suffix: `.so` (Linux) or `.bundle` (macOS).

## Runtime load order

`maya_module/scripts/userSetup.py` calls `pipeline_inspector_bootstrap.plugin_load_candidates()`:

1. `plug-ins/{year}/pipeline_inspector.mll` when the year-specific binary exists (absolute path load)
2. `plug-ins/pipeline_inspector.mll` when the Plug-in Manager copy exists
3. `pipeline_inspector.py` (Python fallback)
4. `pipeline_inspector_bootstrap.install_ui()` when all plug-in loads fail

Use `describe_dual_install()` in Script Editor to inspect detection output. See [docs/MAYA_INSTALL.md](../docs/MAYA_INSTALL.md).

## Version string

`PIPELINE_INSPECTOR_PLUGIN_VERSION` in `native/CMakeLists.txt` should match `version` in `pyproject.toml` at release time.

## CI note

Public GitHub Actions does **not** compile the native plug-in (devkit + MSVC are maintainer-local). Maya integration smoke tests use the Python fallback unless a self-hosted runner publishes prebuilt binaries.
