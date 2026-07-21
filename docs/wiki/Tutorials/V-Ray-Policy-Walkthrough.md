# V-Ray policy walkthrough

Hands-on with **`examples/vray_policy/vray_policy_scene.ma`**.

## Prerequisites

- Maya 2024 or 2025
- **V-Ray** plug-in loaded
- Pipeline Inspector installed

Read first: [`examples/vray_policy/README.md`](../../../examples/vray_policy/README.md)

## 1. Load scene

```text
MAYA_MODULE_PATH → repo/maya_module
Open → examples/vray_policy/vray_policy_scene.ma
Load V-Ray if prompted
```

## 2. Validate

| Setting | Value |
| --- | --- |
| Workflow | `publish_strict` or `deadline_critical` |
| Asset class | `asset_class_hero` (optional — texture budget) |

**Validate Scene**.

## 3. Issue categories to expect

| Category | Example rule area |
| --- | --- |
| Common textures | Missing files, local paths |
| V-Ray policy | Plugin missing, transmission depth, displacement |
| Complexity | Expensive V-Ray blend/layer nodes |
| Geometry (v0.6) | Polycount / duplicate metadata |

Use **Owner** filter to separate `shader_td` vs `technical_artist` issues.

## 4. Renderer-specific triage

1. Select a V-Ray rule failure.
2. **Hypershade** → inspect VRayMtl / blend stack.
3. Compare with rule message threshold in [`rules/vray/`](../../../src/pipeline_inspector/rules/vray/).

## 5. Farm preflight

Switch workflow to **`deadline_critical`** → revalidate → confirm **Deadline Block** reflects farm policy.

Optional: **Farm tab → Run Farm Preflight**.

## 6. Sample report

Pre-generated report beside scene — diff against your export:

```text
examples/vray_policy/sample_report.html
```

## Next

→ [Arnold walkthrough](Arnold-Policy-Walkthrough) · [Authoring rules](Authoring-Rules)
