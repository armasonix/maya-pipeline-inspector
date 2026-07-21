# Maya v0.2 manual verification checklist

Use this checklist before tagging **v0.2.0**. Public CI does not launch Maya; these steps validate UI behavior that unit tests mock.

## Session 1 — Demo scene regression

Scene: [`vray_policy_scene.ma`](../examples/vray_policy/vray_policy_scene.ma) (V-Ray loaded) or [`arnold_policy_scene.ma`](../examples/arnold_policy/arnold_policy_scene.ma) (Arnold loaded)

1. Open the panel via **Pipeline Inspector** menu or shelf.
2. Profile `publish_strict` → **Validate Scene**.
3. Confirm six issue categories still appear (missing texture, colorSpace, UDIM, local path, displacement, orphan).
4. Issue filters are on **one horizontal row** above the issues table.
5. **Safe Auto-Fix Queue** should include at least:
   - `set_attr` / low — wrong colorSpace
   - `normalize_path` / medium — local drive path
   - `disable_feature` / high — displacement amount (if rule fires on scene setup)
6. Use **Select** buttons on rows (not YES/NO cells); apply low-risk fixes; undo in Maya.
7. Select medium/high rows → **Apply Selected** → confirm dialogs (strict profile = per-fix).

## Session 2 — Reference safety (reference edits)

1. Save a small source scene with one fixable colorSpace issue as `ref_source.ma`.
2. New scene → **File → Reference** `ref_source.ma`.
3. Validate → select the colorSpace issue.
4. Issue Details should show **Reference safety: referenced node (...). Fixes apply here as reference edits.**
5. Fix queue row should show **Blocked = NO** (unless the node is locked).
6. **Select** + **Apply Selected** should apply the fix in the current scene as a reference edit.

## Session 3 — Renderer policy packs

Requires V-Ray or Arnold loaded in Maya.

1. Set **Render Settings → Current Renderer** to `vray` or `arnold`.
2. Use a scene with `VRayMtl` / `aiStandardSurface` materials (not only lambert).
3. Validate → issues table should include `vray.*` or `arnold.*` rule ids.
4. For V-Ray: create `VRaySettingsNode` if `vray.scene.plugin_missing.error` fires; revalidate.

## Session 4 — Headless parity

```powershell
mayapy -m pipeline_inspector validate examples/vray_policy/vray_policy_scene.ma `
  --input-kind scene --profile-id publish_strict --report report.json
mayapy examples/publish/submit_preflight.py examples/vray_policy/vray_policy_scene.ma `
  --repo-root D:\...\maya-pipeline-inspector `
  --mayapy "C:\Program Files\Autodesk\Maya2025\bin\mayapy.exe"
```

## Session 5 — Export workflow (post-revalidate)

After fixes and final **Revalidate**:

1. **Export JSON Report** → automation / CI artifact.
2. **Export HTML Report** → supervisor review.
3. **Export Shader Manifest** → new approved baseline.
4. **Export Manifest Diff** → only when comparing against a previous manifest.
5. **Export Fix Plan** → optional audit before apply.

Record tested Maya version(s) in the GitHub Release notes.
