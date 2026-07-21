# 5-minute quick start

Hands-on path for **Technical Artists** — from zero to first validation.

## Prerequisites

- Maya 2024 or 2025 with Pipeline Inspector installed ([Installation](Installation))
- Demo scene: `examples/broken_scene/broken_scene.ma` (or any lookdev scene)

## Steps

### 1. Open the panel

- Menu: **Pipeline Inspector → Open Pipeline Inspector**
- Or shelf tab **PipelineInspector → Pipeline Inspector**

### 2. Choose workflow profile

On the **Validate** tab:

| Control | Pick |
| --- | --- |
| **Workflow** | `artist_relaxed` (daily) or `publish_strict` (gate) |
| **Asset class** | `None` (or Hero/Prop/Background for resolution rules) |

### 3. Validate

Click **Validate Scene**. Wait for the async job to finish.

You should see:

- **Health** score (0–100)
- Severity counts (Critical / Error / Warning / Info)
- **Publish Block** / **Deadline Block** flags
- Issue table with rule id, message, owner

### 4. Triage one issue

1. Click a row in the issue table.
2. Read **Issue Details** (why it matters).
3. Use **Select Node**, **Open in Hypershade**, **Copy Path**, or **Reveal File**.

### 5. Apply a safe fix (if offered)

1. Switch to **Fixes** tab (or use fix queue on Validate).
2. Check safe fixes → **Apply Safe Fixes**.
3. Return to **Validate** → **Validate Scene** again.

### 6. Export a report (optional)

**Reports** tab → **Export JSON** or **Export HTML** for supervisor review.

## What you learned

| Concept | Where to go deeper |
| --- | --- |
| Profiles | [Profiles & asset class](Profiles-and-Asset-Classes) |
| Issue table & filters | [Validate tab](Validate-Tab) |
| Safe fixes | [Safe fixes](Safe-Fixes) |
| Blocking flags | [Publish preflight](Publish-Preflight) |

## Next tutorial

→ [First validation tutorial](First-Validation-Tutorial) (structured walkthrough with broken scene)
