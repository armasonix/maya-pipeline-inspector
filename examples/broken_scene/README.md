# Broken demo scene

This folder contains the v0.1 broken demo scene for Maya Pipeline Inspector.

The final scene should be created manually in Maya and saved as:

```text
examples/broken_scene/pipeline_inspector_demo_broken.ma
```

The goal is not to create a beautiful render scene. The goal is to create a compact, readable portfolio/demo scene that exercises the validator, Maya UI, JSON/HTML reports, safe-fix queue, and Deadline preflight path.

## Acceptance coverage

The scene must contain the following intentional issues:

- missing texture;
- wrong colorSpace;
- missing UDIM tile;
- local path;
- displacement risk;
- orphan material.

## Recommended scene layout

Use simple named geometry so screenshots and reports are easy to understand:

```text
mesh_missing_texture_GEO
mesh_wrong_colorspace_GEO
mesh_missing_udim_GEO
mesh_local_path_GEO
mesh_displacement_risk_GEO
```

Use simple primitives such as planes, cubes, or spheres. Place them side-by-side and freeze transforms after layout if desired.

## Recommended materials

```text
demo_missing_texture_MTL
demo_wrong_colorspace_MTL
demo_missing_udim_MTL
demo_local_path_MTL
demo_displacement_risk_MTL
demo_orphan_unused_MTL
```

Assign every material except `demo_orphan_unused_MTL` to one visible mesh. Leave `demo_orphan_unused_MTL` unassigned so the orphan/dead shader network rule can report it.

## Texture folder

Recommended folder:

```text
examples/broken_scene/textures/
```

Recommended files:

```text
demo_albedo_v001.1001.exr
demo_roughness_v001.1001.exr
demo_roughness_v001.1003.exr
demo_normal_v001.1001.exr
demo_displacement_v001.1001.exr
```

The missing UDIM case intentionally omits:

```text
demo_roughness_v001.1002.exr
```

Small placeholder images are enough for the demo as long as Maya can load them and the path validator can see them on disk. Avoid proprietary production textures.

## Intentional issue setup

### 1. Missing texture

Create a file texture node connected to `demo_missing_texture_MTL`.

Suggested node name:

```text
file_demo_missing_texture
```

Set its path to a file that does not exist, for example:

```text
examples/broken_scene/textures/DOES_NOT_EXIST_missing_albedo.exr
```

Expected validator behavior:

```text
common.texture.missing => failed
```

### 2. Wrong colorSpace

Create a roughness/data texture connected to `demo_wrong_colorspace_MTL`.

Suggested node name:

```text
file_demo_wrong_colorspace_roughness
```

Set the texture to an existing data map and intentionally set colorSpace to a color-managed value instead of Raw:

```text
fileTextureName = examples/broken_scene/textures/demo_roughness_v001.1001.exr
colorSpace = ACEScg or sRGB
```

Expected validator behavior:

```text
common.texture.colorspace.data_raw => failed
safe low-risk set_attr fix available
```

### 3. Missing UDIM tile

Create a UDIM texture connected to `demo_missing_udim_MTL`.

Suggested node name:

```text
file_demo_missing_udim_roughness
```

Set the path to:

```text
examples/broken_scene/textures/demo_roughness_v001.<UDIM>.exr
```

Create tiles `1001` and `1003`, but intentionally do not create `1002`.

Expected validator behavior:

```text
common.udim.missing_tile => failed
```

### 4. Local path

Create a file texture connected to `demo_local_path_MTL`.

Suggested node name:

```text
file_demo_local_path
```

Set the path to a local user-style path that should be unsafe for render farm submission. Use a sanitized fake path rather than a real private path:

```text
C:/Users/demo/Desktop/local_only_texture.exr
```

Expected validator behavior:

```text
common.texture.path.local_drive or user-location path policy => failed
```

### 5. Displacement risk

Create a displacement setup connected to `demo_displacement_risk_MTL`.

Suggested nodes:

```text
file_demo_displacement
shader_demo_displacement
```

Use an existing displacement file:

```text
examples/broken_scene/textures/demo_displacement_v001.1001.exr
```

Set at least one risky property:

```text
colorSpace = ACEScg or sRGB instead of Raw
high displacement amount above the configured threshold
```

Expected validator behavior:

```text
displacement risk rule(s) => failed
```

### 6. Orphan material

Create `demo_orphan_unused_MTL` and optionally one disconnected file node. Do not assign it to any mesh.

Expected validator behavior:

```text
common.shader.unassigned_material or orphan/dead shader network rule => failed
```

## Manual Maya build checklist

1. Create a new Maya scene.
2. Create five simple visible meshes and name them as listed above.
3. Create the six demo materials and assign five of them.
4. Create the texture folder and placeholder image files.
5. Wire file nodes into the materials.
6. Set the intentional bad paths/colorSpace/UDIM/displacement values.
7. Leave the orphan material unassigned.
8. Save as Maya ASCII:

```text
examples/broken_scene/pipeline_inspector_demo_broken.ma
```

## Local validation checklist

From Maya:

1. Launch Pipeline Inspector.
2. Validate Scene.
3. Confirm all six acceptance categories appear in the issues table.
4. Select each issue and confirm the details panel shows message, why, current/expected values, and graph trace where available.
5. Confirm the wrong colorSpace issue appears as safe auto-fixable.
6. Export JSON report.
7. Export HTML report.

Headless smoke:

```bash
mayapy -m pipeline_inspector validate examples/broken_scene/pipeline_inspector_demo_broken.ma \
  --input-kind scene \
  --profile src/pipeline_inspector/rules/profiles/deadline_critical.json \
  --report examples/broken_scene/reports/pipeline_inspector_demo_broken_deadline.json
```

If the packaged `deadline_critical` profile does not exist yet, use the current local profile path or a temporary profile matching the [Deadline integration guide](../../docs/integrations/deadline_submit_preflight.md).

## Commit checklist

Commit these artifacts when the scene is ready:

```text
examples/broken_scene/pipeline_inspector_demo_broken.ma
examples/broken_scene/pipeline_inspector_demo_broken_headless.ma
examples/broken_scene/textures/*
examples/broken_scene/README.md
```

Optional **curated** report artifacts for README screenshots (regenerate after rule-pack changes):

```text
examples/broken_scene/pipeline_inspector_demo_broken_pipeline_inspector_report.html
examples/broken_scene/pipeline_inspector_demo_broken_pipeline_inspector_report.json
examples/broken_scene/pipeline_inspector_demo_broken_pipeline_inspector_manifest.json
```

Do **not** commit machine-local outputs (covered by `.gitignore`):

```text
examples/broken_scene/*.pipeline_inspector_fix_audit.json
examples/broken_scene/*_pipeline_inspector_manifest_diff.*
examples/broken_scene/*_pipeline_inspector_deadline_command.txt
examples/broken_scene/*_fixed.ma
examples/broken_scene/reports/
```
