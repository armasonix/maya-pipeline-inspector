# Native Maya plug-in build

Thin C++ bootstrap that registers in Plug-in Manager and calls the existing Python module `shader_health_inspector_bootstrap`. Validation, UI, and rules stay in `src/shader_health/`.

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
maya_module/plug-ins/{year}/shader_health_inspector.mll
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

`maya_module/scripts/userSetup.py` tries, in order:

1. `{year}/shader_health_inspector.mll` (or `.so` / `.bundle`)
2. `shader_health_inspector.py` (Python fallback)
3. `shader_health_inspector_bootstrap.install_ui()` (module-only fallback)

Source checkouts without a built `.mll` continue to work via the `.py` path.

## Version string

`SHADER_HEALTH_PLUGIN_VERSION` in `native/CMakeLists.txt` should match `version` in `pyproject.toml` at release time.

## CI note

Public GitHub Actions does **not** compile the native plug-in (devkit + MSVC are maintainer-local). Maya integration smoke tests use the Python fallback unless a self-hosted runner publishes prebuilt binaries.
