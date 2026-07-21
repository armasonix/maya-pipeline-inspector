# Arnold policy walkthrough

Hands-on with **`examples/arnold_policy/arnold_policy_scene.ma`**.

## Prerequisites

- Maya 2024 or 2025
- **Arnold** plug-in loaded
- Pipeline Inspector installed

Read first: [`examples/arnold_policy/README.md`](../../../examples/arnold_policy/README.md)

## 1. Load scene

```text
MAYA_MODULE_PATH → repo/maya_module
Open → examples/arnold_policy/arnold_policy_scene.ma
Load Arnold if prompted
```

## 2. Validate

| Setting | Value |
| --- | --- |
| Workflow | `publish_strict` |
| Asset class | `asset_class_hero` |

**Validate Scene**.

## 3. Issue categories to expect

| Category | Notes |
| --- | --- |
| Common | Texture path / missing maps |
| Arnold policy | `aiStandardSurface`, transmission, specular roughness |
| Scene plugin | Arnold plug-in presence rules |
| Geometry (v0.6) | Duplicate scan metadata on shapes |

## 4. Complexity triage

Filter issues mentioning **farm cost** or **expensive nodes**. Open Hypershade — look for `aiLayerShader`, mix stacks.

See [Shader farm cost score](../../USER_GUIDE.md#shader-farm-cost-score) in user guide.

## 5. Export manifest

**Reports → Export Manifest** — use as teaching example for publish baseline workflow.

→ [Publish preflight](../Workflows/Publish-Preflight)

## 6. Compare sample output

```text
examples/arnold_policy/sample_report.html
```

## Next

→ [V-Ray walkthrough](V-Ray-Policy-Walkthrough) · [`RULE_AUTHORING.md`](../../RULE_AUTHORING.md)
