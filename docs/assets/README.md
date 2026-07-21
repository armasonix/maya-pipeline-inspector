# README media assets

Media files for Issue #047 (`README` screenshots and demo GIF). Capture these locally in Maya and drop them into this folder before updating the public README commit.

## Required files

| File | Acceptance criterion | Suggested capture |
|---|---|---|
| `ui-panel.png` | UI screenshot | Open `examples/vray_policy/vray_policy_scene.ma` or `examples/arnold_policy/arnold_policy_scene.ma` (load matching renderer), run **Validate Scene**, show issues table + Issue Details + health summary. Crop to the dockable panel only. |
| `html-report.png` | HTML report screenshot | Export HTML from the panel or open `examples/vray_policy/reports/validation/vray_policy_scene_pipeline_inspector_report.html` (or the Arnold equivalent) in a browser. Capture the hero metrics and at least one failed issue group. |
| `before-after-safe-fix.gif` | Before/after fix demo | Record on a policy demo scene: validate, select a safe colorspace fix in the queue, apply, re-validate, show the issue cleared. Keep the clip under ~15 seconds. |

Optional:

| File | Notes |
|---|---|
| `architecture.png` | Only if you prefer a raster diagram instead of the Mermaid block in `README.md`. |

## Capture checklist

1. Use a **renderer policy demo scene** (`examples/vray_policy/` or `examples/arnold_policy/`) so issue labels match current documentation.
2. Hide unrelated Maya UI chrome where possible; keep Pipeline Inspector panel text legible.
3. Prefer PNG for stills (lossless UI text) and GIF or WebP for the fix demo.
4. Avoid real usernames, studio paths, or confidential scene names in visible paths.
5. After export, open `README.md` locally and confirm image links render.

## Sanitizing report paths

If exported HTML/JSON still contains machine-specific absolute paths, regenerate from the repo demo scene or sanitize paths before committing report artifacts used in screenshots.
