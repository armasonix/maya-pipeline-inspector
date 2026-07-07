# ADR 0006: Native Maya plugin (.mll) strategy

## Status

Accepted

## Date

2026-07-07

## Context

v0.3 ships Shader Health Inspector as a **Python OpenMayaMPx plugin** ([`maya_module/plug-ins/shader_health_inspector.py`](../../maya_module/plug-ins/shader_health_inspector.py)) plus a `userSetup.py` fallback that calls [`shader_health_inspector_bootstrap.install_ui()`](../../maya_module/scripts/shader_health_inspector_bootstrap.py). This works for development and small-studio rollout, but production facilities often expect:

- a **native compiled plugin** visible in Maya **Plug-in Manager** with a clear vendor/version;
- **per-Maya-year binaries** (2024 / 2025 / 2026) built against the matching Autodesk devkit;
- predictable **load / unload** hooks for menu, shelf, and dockable panel lifecycle;
- a **fallback path** when a matching `.mll` is missing (open-source checkout, unsupported OS, or contributor machines without a C++ toolchain).

ADR 0001 requires the validation engine to remain pure Python and snapshot-first. ADR 0005 names the dockable panel as the primary product surface and explicitly rejects rewriting the rule engine in C++. Any native plugin work must therefore stay a **thin bootstrap** — not a second implementation of validation, UI, or rule evaluation.

v0.4 Milestone 24 (issues #096–#097) will add CMake scaffolding and the first `.mll` build. This ADR defines the strategy those issues must follow.

## Decision

Shader Health Inspector adopts a **phased native-plugin strategy**:

1. **Thin C++ bootstrap only** — The `.mll` (Windows), `.so` (Linux), or `.bundle` (macOS) plugin registers with the Maya API and delegates all product behavior to existing Python modules. No validation, rule loading, Qt UI, or scene mutation logic lives in C++.
2. **Python remains authoritative** — `shader_health.maya.commands`, `shader_health.maya.ui_launcher`, and `shader_health.maya.validation_pipeline` stay the implementation. The native plugin's `initializePlugin` / `uninitializePlugin` call the same bootstrap functions the `.py` plugin uses today.
3. **Dual delivery with explicit fallback** — Installers and `maya_module/` ship **both** native binaries (when built for the target Maya year) and the existing `.py` plugin. Runtime load order prefers the native plugin; if load fails, fall back to `.py`; if that fails, fall back to direct `install_ui()` from `userSetup.py` (current v0.3 behavior).
4. **Per-year artifacts** — Each supported Maya release gets its own compiled binary linked against that release's devkit. Binaries are **not** portable across Maya years.
5. **CMake as the single build entrypoint** — Issue #096 introduces `native/CMakeLists.txt` (or equivalent) with devkit discovery, Maya version selection, and install/copy rules. Issue #097 implements the minimal `MPxPlugin` source.
6. **Open-source build expectations** — Prebuilt `.mll` files may ship in GitHub Releases for supported Maya versions. Contributors build locally when they have a licensed Maya devkit installed. Public CI does **not** gate merges on compiling the native plugin (Maya devkit + MSVC are maintainer/self-hosted concerns).

### Native plugin responsibilities (in scope)

| Responsibility | Owner |
|---|---|
| `MFnPlugin` registration (name, vendor, version) | C++ `.mll` |
| `initializePlugin` → defer UI install | C++ → Python `shader_health_inspector_bootstrap.install_ui()` |
| `uninitializePlugin` → remove menu/shelf/panel | C++ → Python `shader_health_inspector_bootstrap.uninstall_ui()` |
| Menu, shelf, dockable panel, validation | Python (`shader_health.*`) |

### Native plugin non-responsibilities (out of scope for v0.4 and foreseeable releases)

- GraphSnapshot scanning, rule evaluation, scoring, fix planning, or report generation in C++;
- Renderer adapter logic (V-Ray / Arnold) in C++;
- Duplicating Qt UI in C++;
- Replacing `mayapy` headless CLI with a C++ executable.

### Runtime load priority

```text
Maya startup (maya_module/scripts/userSetup.py)
  1. Resolve Maya year (e.g. 2024 / 2025 / 2026)
  2. Try cmds.loadPlugin("<year>/shader_health_inspector.mll")  [preferred]
  3. Else try cmds.loadPlugin("shader_health_inspector.py")       [fallback]
  4. Else shader_health_inspector_bootstrap.install_ui()          [last resort]
```

The year-qualified path keeps multiple prebuilt binaries in one module tree without filename collisions. Exact folder names are defined in **Implementation Notes** below.

### Build matrix (v0.4 Phase 1)

Phase 1 targets **Windows x64** first (matches current self-hosted Maya CI runner). Linux and macOS are documented for parity; binary publication can trail Windows by one milestone when devkit hosts are unavailable.

| Maya year | Platform | Toolchain (documented) | Devkit input | Output artifact | CI / release |
|---|---|---|---|---|---|
| 2024 | Windows x64 | MSVC 2019+ (VS 2019/2022) | `MAYA_DEVKIT_ROOT` → Maya 2024 | `shader_health_inspector.mll` | Release asset; optional self-hosted build |
| 2025 | Windows x64 | MSVC 2019+ | Maya 2025 devkit | `shader_health_inspector.mll` | Release asset; optional self-hosted build |
| 2026 | Windows x64 | MSVC 2022+ (per Autodesk release notes) | Maya 2026 devkit | `shader_health_inspector.mll` | Release asset when devkit available |
| 2024–2026 | Linux x64 | GCC 11+ (studio-dependent) | Matching devkit | `shader_health_inspector.so` | Best-effort; not a v0.4.0 blocker |
| 2024–2026 | macOS arm64 / x64 | Xcode / clang per devkit | Matching devkit | `shader_health_inspector.bundle` | Best-effort; not a v0.4.0 blocker |

**Devkit requirements (all platforms):**

- Licensed Autodesk Maya installation for the target year (devkit headers/libs ship with Maya).
- Environment variable `MAYA_DEVKIT_ROOT` pointing at the devkit root (CMake module resolves `include/` and `lib/`).
- CMake ≥ 3.20.
- Python development headers are **not** required in the `.mll` for Phase 1 — the bootstrap calls into Maya's embedded Python via `MGlobal::executePythonCommand` (or equivalent) to import existing modules.

**Version coupling:**

- Plugin `kApiVersion` / `maya_useAPIVersion` must match the devkit used at compile time.
- `PLUGIN_VERSION` in C++ must track the package version in `pyproject.toml` for supportability.

## Alternatives Considered

### 1. Keep Python-only OpenMayaMPx plugin permanently

Pros:

- no devkit/MSVC maintenance;
- one source file, easy contributor onboarding;
- identical behavior on all platforms Maya Python supports.

Cons:

- some studios distrust or block `.py` plug-ins in Plug-in Manager;
- harder to align with facility packaging that expects `.mll` in `bin/plug-ins`;
- no path to optional future C++ hooks (e.g. custom DG nodes) without a later breaking migration.

Rejected as the long-term sole delivery mode. Retained as **fallback** per this ADR.

### 2. Full C++ rewrite of scanner / validator

Pros:

- potentially faster scene traversal for huge scenes;
- single binary artifact per Maya year.

Cons:

- violates ADR 0001 snapshot-first testability;
- duplicates rule JSON schema, profiles, waivers, and fix policy in a second language;
- blocks open-source contributors without C++ and Maya API expertise;
- guarantees GUI/headless parity bugs.

Rejected. Explicitly out of scope per ADR 0005 non-goals.

### 3. Single universal `.mll` binary across Maya 2024–2026

Pros:

- one build artifact to publish.

Cons:

- Maya plug-in ABI and devkit APIs change per year;
- Autodesk does not support cross-year binary compatibility;
- support burden when studios mix Maya versions.

Rejected. Per-year binaries are required.

### 4. Separate Maya module package per year (no shared tree)

Pros:

- simple `plug-ins/` folder per `.mod` file;
- no year subfolder loader logic.

Cons:

- duplicates `scripts/`, `shelves/`, and Python package wiring three times;
- harder to document one `MAYA_MODULE_PATH` entry for developers.

Rejected for the open-source repo layout. Studios may still repackage per year in internal deployments.

## Consequences

### Positive

- Facilities can deploy a familiar native plug-in while keeping the testable Python core unchanged.
- Plug-in Manager shows vendor, version, and load state — easier TD support.
- `userSetup.py` and `.py` fallback preserve contributor and CI workflows without devkit installs.
- CMake scaffolding creates a clear home for optional future C++ extensions that still delegate to Python.

### Negative / Tradeoffs

- Maintainers must build or CI-produce **N binaries per release** (at least three Windows years in v0.4 scope).
- Devkit + MSVC toolchain is a barrier for some contributors; documentation must keep the Python path first-class.
- Load-order bugs (native vs Python vs bootstrap) require explicit integration tests on real Maya (#097, manual checklist #094).
- Native binaries increase release artifact size and signing/notarization work on macOS (deferred).

## Implementation Notes

### Target repository layout (issues #096–#097)

```text
native/
├── CMakeLists.txt              # MAYA_VERSION, MAYA_DEVKIT_ROOT, output dir
├── cmake/
│   └── FindMayaDevkit.cmake
└── src/
    └── shader_health_inspector_plugin.cpp

maya_module/
├── plug-ins/
│   ├── shader_health_inspector.py          # fallback (existing)
│   ├── 2024/
│   │   └── shader_health_inspector.mll     # built artifact copied here
│   ├── 2025/
│   │   └── shader_health_inspector.mll
│   └── 2026/
│       └── shader_health_inspector.mll
└── scripts/
    ├── userSetup.py                        # year-aware load order (update in #097)
    └── shader_health_inspector_bootstrap.py
```

### C++ bootstrap sketch (illustrative — implemented in #097)

```cpp
MStatus initializePlugin(MObject obj) {
    MFnPlugin plugin(obj, "Shader Health Inspector", "0.4.0", "Any");
    MGlobal::executePythonCommand(
        "import maya.utils; maya.utils.executeDeferred("
        "'import shader_health_inspector_bootstrap; "
        "shader_health_inspector_bootstrap.install_ui()')"
    );
    return MStatus::kSuccess;
}
```

Unload must call `shader_health_inspector_bootstrap.uninstall_ui()` synchronously (no defer) so menu/shelf/panel teardown completes before the plug-in unloads.

### Bootstrap contract (unchanged)

[`shader_health_inspector_bootstrap.py`](../../maya_module/scripts/shader_health_inspector_bootstrap.py) continues to:

- prepend `repo_root/src` to `sys.path` when present;
- delegate to `shader_health.maya.commands` for menu, shelf, panel, and uninstall;
- remain importable from both `.mll` and `.py` plug-in entrypoints.

### Testing expectations

| Layer | Coverage |
|---|---|
| Bootstrap Python | Existing `tests/unit/test_maya_module_bootstrap.py` |
| Load-order logic | Extend unit tests for year-path resolution in `userSetup.py` (#097) |
| Native binary | Manual Maya checklist (#094); optional self-hosted smoke loading `.mll` |
| Validation parity | No new parity dimension — native plugin does not change `validation_pipeline` |

### Release packaging

- GitHub Release `v0.4.0` may attach `shader_health_inspector-maya{YEAR}-win64.zip` per supported year.
- Source checkout without built `.mll` files continues to work via `.py` fallback (documented in `MAYA_INSTALL.md`).

## Related

- Issue: `#095 - ADR 0006 native Maya plugin (.mll) strategy` (GitHub #123)
- Issue: `#096 - CMake scaffold + shader_health_inspector.mll bootstrap` (GitHub #124)
- Issue: `#097 - Dual install docs + detection in userSetup` (GitHub #125)
- ADR: `0001-snapshot-first-core.md`
- ADR: `0005-gui-first-product-philosophy.md`
- Document: `docs/ARCHITECTURE.md`
- Document: `docs/MAYA_INSTALL.md`
- Module: `maya_module/plug-ins/shader_health_inspector.py`
- Module: `maya_module/scripts/shader_health_inspector_bootstrap.py`
