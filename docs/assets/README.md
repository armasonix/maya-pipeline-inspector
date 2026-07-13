# README media assets

Media files for Issue #047 (`README` screenshots and demo GIF). Capture these locally in Maya and drop them into this folder before updating the public README commit.

## Required files

| File | Acceptance criterion | Suggested capture |
|---|---|---|
| `ui-panel.png` | UI screenshot | Open `examples/broken_scene/pipeline_inspector_demo_broken.ma`, run **Validate Scene**, show issues table + Issue Details + health summary. Crop to the dockable panel only. |
| `html-report.png` | HTML report screenshot | Export HTML from the panel or open `examples/broken_scene/pipeline_inspector_demo_broken_pipeline_inspector_report.html` in a browser. Capture the hero metrics and at least one failed issue group. |
| `before-after-safe-fix.gif` | Before/after fix demo | Record a short GIF: validate scene, select a safe colorspace fix in the queue, apply it, re-validate, show the issue cleared. Keep the clip under ~15 seconds. |

Optional:

| File | Notes |
|---|---|
| `architecture.png` | Only if you prefer a raster diagram instead of the Mermaid block in `README.md`. |

## Capture checklist

1. Use the broken demo scene so issue labels stay readable and match documentation.
2. Hide unrelated Maya UI chrome where possible; keep Pipeline Inspector panel text legible.
3. Prefer PNG for stills (lossless UI text) and GIF or WebP for the fix demo.
4. Avoid real usernames, studio paths, or confidential scene names in visible paths.
5. After export, open `README.md` locally and confirm image links render.

## Sanitizing report paths

If exported HTML/JSON still contains machine-specific absolute paths, regenerate from the repo demo scene or sanitize paths before committing report artifacts used in screenshots.
