# Arnold policy demo scene

**Scene:** `arnold_policy_scene.ma`  
**Renderer:** Autodesk Arnold (load the Arnold plug-in before validating)

Deliberately broken lookdev scene for **Maya Pipeline Inspector** portfolio demos and onboarding. Issues are **pre-modeled** across common material checks and **Arnold-specific** production policy rules.

## What it exercises

### Common rules (`common.*`)

- missing or mis-pathed textures (albedo, roughness, UDIM sets);
- wrong colorspace on data vs color maps;
- local drive paths unsafe for farm;
- project-root path policy failures;
- displacement review signals;
- geometry duplicate-scan metadata (v0.6);
- shader complexity / expensive node budgets.

### Arnold rules (`arnold.*`)

- `arnold.scene.plugin_missing.error` — Arnold materials without `aiOptions` (until plug-in is loaded correctly);
- `arnold.material.transmission_depth.warning` — transmission depth over budget;
- `arnold.material.texture_budget.warning` — per-material texture counts;
- `arnold.material.displacement_review.warning` — displacement-linked Arnold shaders;
- `arnold.scene.stand_in_review.warning` — stand-in / proxy review (when present).

## Quick start

```text
1. MAYA_MODULE_PATH -> repo/maya_module
2. Launch Maya, load Arnold
3. Open arnold_policy_scene.ma
4. Pipeline Inspector -> Validate Scene (publish_strict or deadline_critical)
5. Compare with reports/validation/arnold_policy_scene_pipeline_inspector_report.html
```

## Checked-in artifacts

| File | Purpose |
| --- | --- |
| `reports/validation/arnold_policy_scene_pipeline_inspector_report.html` | Sample HTML validation report |
| `reports/farm/arnold_policy_scene_pipeline_inspector_farm.json` | Sample farm preflight JSON |

Texture paths may reference shared files under `examples/broken_scene/textures/`. Onboarding uses this scene and [`../vray_policy/vray_policy_scene.ma`](../vray_policy/vray_policy_scene.ma).
