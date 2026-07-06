# Maya v0.2 manual verification checklist

Use this checklist before tagging **v0.2.0**. Public CI does not launch Maya; these steps validate UI behavior that unit tests mock.

## Session 1 — Demo scene regression

Scene: [`shader_health_demo_broken.ma`](../examples/broken_scene/shader_health_demo_broken.ma)

1. Open the panel via **Shader Health** menu or shelf.
2. Profile `publish_strict` → **Validate Scene**.
3. Confirm six issue categories still appear (missing texture, colorSpace, UDIM, local path, displacement, orphan).
4. Issue filters are on **one horizontal row** above the issues table.
5. **Safe Auto-Fix Queue** should include at least:
   - `set_attr` / low — wrong colorSpace
   - `normalize_path` / medium — local drive path
   - `disable_feature` / high — displacement amount (if rule fires on scene setup)
6. Apply Safe Fixes for low risk only; undo in Maya.
7. Select medium/high rows → **Apply Selected** → confirm dialogs (strict profile = per-fix).

## Session 2 — Reference safety

1. Save a small source scene with one fixable colorSpace issue as `ref_source.ma`.
2. New scene → **File → Reference** `ref_source.ma`.
3. Validate → select the colorSpace issue.
4. Issue Details should show **Reference safety: referenced node (...)**.
5. Fix queue row for that fix should show **Blocked = YES**.
6. Apply Selected must not change the referenced node.

## Session 3 — Renderer policy packs

Requires V-Ray or Arnold loaded in Maya.

1. Set **Render Settings → Current Renderer** to `vray` or `arnold`.
2. Use a scene with `VRayMtl` / `aiStandardSurface` materials (not only lambert).
3. Validate → issues table should include `vray.*` or `arnold.*` rule ids.
4. No separate renderer panel is expected; rules appear in the main issues table.

## Session 4 — Headless parity

```powershell
mayapy -m shader_health validate examples/broken_scene/shader_health_demo_broken.ma `
  --input-kind scene --profile-id publish_strict --report report.json
mayapy examples/publish/submit_preflight.py examples/broken_scene/shader_health_demo_broken.ma `
  --repo-root D:\Workspace\portfolio\maya-shader-health-inspector `
  --mayapy "C:\Program Files\Autodesk\Maya2025\bin\mayapy.exe"
```

## Debug log (optional)

After **Validate Scene**, check [`debug-ee1eca.log`](../debug-ee1eca.log) at repo root for:

- `fix_action_types` containing `set_attr`, `normalize_path`, `disable_feature` (and `relink_path` when version siblings exist on disk)
- `requires_confirmation_count` > 0 when high-risk fixes are queued

Record tested Maya version(s) in release notes.
