# First validation tutorial

Structured walkthrough using the **broken scene** demo.

## Goal

Open a scene with known defects, validate, fix at least one issue, revalidate, export HTML report.

## 1. Setup

```text
MAYA_MODULE_PATH → repo/maya_module
Open → examples/broken_scene/broken_scene.ma
Panel → Pipeline Inspector
```

→ [Demo scenes](Demo-Scenes)

## 2. Baseline validation

| Setting | Value |
| --- | --- |
| Workflow | `publish_strict` |
| Asset class | None |

Click **Validate Scene**.

**Expected:** Health below 100, **Publish Block: YES**, multiple Critical/Error rows (missing textures, paths, etc.).

## 3. Triage

1. Filter **Severity → Critical**.
2. Select first row — read **Issue Details** (rule id + remediation).
3. Click **Reveal File** or **Select Node** to confirm in scene.

Write down the **rule id** (e.g. `common.texture.missing`) for your studio wiki notes.

## 4. Safe fix attempt

1. Open **Fixes** tab.
2. If fixable rows exist, select safe items only.
3. **Apply Safe Fixes**.
4. Return to **Validate** → **Validate Scene**.

**Expected:** Health improves; some issues remain (not everything is auto-fixable).

## 5. Waiver (optional)

If one remaining issue is approved by supervisor:

1. **Waivers** tab → select issue → **Make Waive**.
2. Revalidate — blocking may clear per policy.

## 6. Export

**Reports** → **Export HTML**. Open in browser — compare with [`docs/assets/html-report.png`](../../assets/html-report.png).

## 7. Headless echo (TD)

```bash
mayapy -m pipeline_inspector validate examples/broken_scene/broken_scene.ma \
  --profile-id publish_strict \
  --report /tmp/broken_report.json
```

Same issue set as panel (same pipeline).

## Learn more

→ [Validate tab](Validate-Tab) · [Safe fixes](Safe-Fixes)
