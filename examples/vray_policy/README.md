# V-Ray policy demo scene

**Scene:** `vray_policy_scene.ma`  
**Renderer:** Chaos V-Ray (load the V-Ray plug-in before validating)

Deliberately broken lookdev scene for **Maya Pipeline Inspector** portfolio demos and onboarding. Geometry and material names stay readable; issues are **pre-modeled** so validation, reports, and the Fixes tab show a realistic V-Ray production policy mix.

## What it exercises

### Common rules (`common.*`)

- missing displacement / albedo / normal / roughness textures;
- wrong colorspace on data maps;
- missing UDIM tiles;
- local drive and user-folder texture paths;
- paths outside approved project roots (when studio path policy is active);
- displacement texture missing;
- shader complexity / farm cost signals.

### V-Ray rules (`vray.*`)

- `vray.scene.plugin_missing.error` — V-Ray materials without a settings node (until plug-in is loaded correctly);
- `vray.material.trace_depth.warning` — reflection trace depth over budget;
- `vray.material.displacement_force.warning` — force displacement enabled;
- `vray.material.displacement_review.warning` — displacement-linked materials;
- `vray.material.texture_budget.warning` — texture count budgets.

## Quick start

```text
1. MAYA_MODULE_PATH -> repo/maya_module
2. Launch Maya, load V-Ray
3. Open vray_policy_scene.ma
4. Pipeline Inspector -> Validate Scene (publish_strict or deadline_critical)
5. Compare with reports/validation/vray_policy_scene_pipeline_inspector_report.html
```

## Checked-in artifacts

| File | Purpose |
| --- | --- |
| `reports/validation/vray_policy_scene_pipeline_inspector_report.html` | Sample HTML validation report |
| `reports/farm/vray_policy_scene_deadline_farm_report.html` | Sample farm-oriented HTML export |

Texture paths may reference shared files under `examples/broken_scene/textures/`. Onboarding and docs use this scene and [`../arnold_policy/arnold_policy_scene.ma`](../arnold_policy/arnold_policy_scene.ma) only.
