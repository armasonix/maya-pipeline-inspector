# Maya UI/UX Audit — v0.4

**Status:** Baseline audit (pre–Wave 1)  
**Date:** 2026-07-07  
**Plan issue:** #092 (GitHub [#120](https://github.com/armasonix/maya-shader-health-inspector/issues/120))  
**Philosophy:** [ADR 0005 — GUI-first product philosophy](adr/0005-gui-first-product-philosophy.md)  
**Code reviewed:** `src/shader_health/ui/main_window.py`, `src/shader_health/maya/ui_launcher.py`, `src/shader_health/ui/fix_queue.py`, `src/shader_health/ui/waiver_manager.py`, `maya_module/shelves/shelf_ShaderHealth.mel`

---

## Executive summary

The v0.3 dockable panel is **functionally complete** for validate → triage → fix → export, with shared `validation_pipeline` parity to CLI. For daily artist use, the **Validate tab is vertically overloaded**: summary, four action buttons, four filters, the issues table, a six-field details block, and a status line compete for the same scroll area. Pipeline actions (manifest gate, publish preflight) sit beside primary validate buttons without grouping, and farm/Deadline workflow is **absent from the panel** (CLI/example only).

This audit records **22 findings**. **Seven are P0** and map to M28 issues [#108](https://github.com/armasonix/maya-shader-health-inspector/issues/136) and [#109](https://github.com/armasonix/maya-shader-health-inspector/issues/137). **Farm tab work** (M26, #101) addresses a separate P0 gap.

**Wave 1 goal:** reduce validate → triage → select node from **5+ clicks / 2 tab switches** toward **≤3 clicks** on the Validate tab, with visible blocking state and non-blocking scan feedback.

---

## Methodology

| Step | Activity |
|------|----------|
| 1 | Static review of panel layout builders and `ui_launcher` callback flows |
| 2 | Map artist task flows against ADR 0005 (speed, clarity, delight, parity) |
| 3 | Score each finding: **Impact** (1–5, time saved or risk reduced) × **Effort** (1–5, implementation cost) |
| 4 | Assign priority: **P0** = Impact ≥ 4 and Effort ≤ 3, or blocks ADR 0005 acceptance; **P1** = high value, moderate effort; **P2** = polish / defer post–v0.4.0 |
| 5 | Assign P0 items to M28 GitHub issues |

Manual timing (before/after Wave 1) will be recorded in [MAYA_V04_MANUAL_CHECKLIST.md](MAYA_V04_MANUAL_CHECKLIST.md) when that doc ships (#094).

---

## Current panel inventory

| Tab | Primary widgets | Data source |
|-----|-----------------|-------------|
| **Validate** | Panel header, summary labels, workflow/asset class combos, 4 validate buttons, 4 filter combos, issues table, issue details + 4 nav buttons, status label | `ui_launcher._validate_from_ui`, `_populate_validation_result` |
| **Waivers** | Panel header, waiver table, Refresh / Make Waive / Revoke | `commands.list_waivers_action` |
| **Fixes** | Panel header, fix queue table, Apply Selected / Apply Safe / Export Fix Plan | `fix_plan` from last validation |
| **Reports** | Panel header, 7 export/gate buttons (3×3 grid) | Requires `_shader_health_snapshot` from prior validate |
| **Farm** | Connection status, scene readiness, eligibility, last report/job id; **Refresh Connection**, **Run Farm Preflight**, **Submit to Farm** | `shader_health.maya.farm_actions` → `integrations.deadline` |

**Shipped in v0.4 (#101):** Farm tab with Deadline connection status, in-panel preflight eligibility, and CommandScript submit with last job id.

---

## Task flows (baseline)

### Flow A — Open panel → validate scene → triage first issue

| Step | Action | Clicks | Notes |
|------|--------|--------|-------|
| 1 | Shelf **Shader Health** or menu | 1 | Shelf only opens panel; no validate shortcut |
| 2 | **Validate Scene** | 1 | Blocks UI thread; no progress bar (F-07) |
| 3 | Scroll to see issues table if summary + filters fill viewport | 0–1 | Vertical stack pushes table down (F-06) |
| 4 | Click issue row | 1 | Selection updates details below table |
| 5 | **Select Node** in details | 1 | **5 clicks**; no double-click shortcut (F-05) |

**Friction:** Issue details often below fold on laptop-sized docks. Status text is **below** details (`VALIDATE_STATUS_LABEL` last in layout).

### Flow B — Validate → apply safe fix → revalidate

| Step | Action | Clicks | Notes |
|------|--------|--------|-------|
| 1–2 | Open + Validate Scene | 2 | |
| 3 | Switch to **Fixes** tab | 1 | Queue not visible on Validate tab (F-14) |
| 4 | **Apply Safe Fixes** | 1 | May prompt per high-risk row on strict profiles (F-12) |
| 5 | Switch to **Validate** tab | 1 | |
| 6 | **Validate Scene** again | 1 | **6 clicks**, 2 tab switches |

**Target (ADR 0005):** ≤3 clicks for primary outcome; revalidate should be one action from summary chrome (F-02, F-04).

### Flow C — Publish preflight check

| Step | Action | Clicks | Notes |
|------|--------|--------|-------|
| 1 | Open panel | 1 | |
| 2 | **Publish Preflight** | 1 | Forces `publish_strict`; ignores workflow dropdown |
| 3 | Read **QMessageBox** modal | 0 | Duplicate of summary block state (F-11) |
| 4 | Dismiss modal | 1 | Modal spam for safe read-only action |

Blocking state is already in summary labels (`BLOCK_STATUS_LABEL`); modal adds friction.

### Flow D — Export JSON report

| Step | Action | Clicks | Notes |
|------|--------|--------|-------|
| 1 | Validate on **Validate** tab | 2 | |
| 2 | Switch to **Reports** tab | 1 | No “last validated” or stale warning (F-09) |
| 3 | **Export JSON Report** | 1 | Result only in Script Editor print (F-15) |

### Flow E — Manifest gate (artist)

| Step | Action | Clicks | Notes |
|------|--------|--------|-------|
| 1 | Validate | 2 | |
| 2 | **Manifest Gate** on Validate **or** Reports | 1 | Same action in two tabs (F-10) |
| 3 | If no sidecar: dialog → Reports → Export Manifest | 2+ | Cross-tab hop not guided in-panel |

### Flow F — Farm / Deadline preflight (v0.4 Farm tab)

| Step | Action | Clicks | Notes |
|------|--------|--------|-------|
| 1 | Open panel → **Farm** tab | 2 | Connection status pings `SHADER_HEALTH_DEADLINE_API_URL` (default `http://localhost:8081`) |
| 2 | **Validate Scene** on Validate tab (if not already run) | 1 | Farm preflight reads last validation summary |
| 3 | **Run Farm Preflight** | 1 | Evaluates `deadline_critical` eligibility + scene saved / renderer plug-in |
| 4 | **Submit to Farm** (when allowed) | 1 | Submits CommandScript utility job; shows last job id |

**Remaining:** shelf **Farm Check** (#102) — **shipped**: menu + shelf shortcut opens Farm tab and runs preflight.

---

## Friction inventory

| ID | Finding | Area | Impact | Effort | Priority | M28 / v0.4 issue |
|----|---------|------|--------|--------|----------|------------------|
| F-01 | **No unified action bar** — Validate Scene, Validate Selection, Publish Preflight, and Manifest Gate are four equal buttons in one row; pipeline actions not visually grouped | Validate | 5 | 2 | **P0** | #108 |
| F-02 | **Summary not sticky** — health, severities, block flags, and profile rows scroll away with tab content; ADR 0005 expects persistent blocking chrome | Validate | 5 | 2 | **P0** | #108 |
| F-03 | **No last-validated timestamp** — artist cannot tell if results are stale after external scene edits (only full reset on SceneOpened) | Validate | 4 | 2 | **P0** | #108 |
| F-04 | ~~**No Farm / Deadline affordance**~~ — **Resolved (#101):** Farm tab with connection status, preflight, submit | Global | 5 | 4 | **P0** | M26 #101 ✅ |
| F-05 | **No double-click triage** — must select row, then click **Select Node** (extra click vs. peer tools) | Validate | 4 | 2 | **P0** | #109 |
| F-06 | **Issue details below fold** — layout order: header → summary (3 lines) → asset hint → buttons → filters → table → details; details panel often off-screen on default dock height | Validate | 5 | 3 | **P0** | #108 (splitter / compact summary) |
| F-07 | **No progress feedback during validate** — `_validate_from_ui` runs synchronously on UI thread; Maya appears frozen on large scenes | Validate | 4 | 3 | **P0** | #109 |
| F-08 | **No keyboard shortcut** — no F5 / hotkey for Validate Scene despite Maya convention | Validate | 3 | 2 | **P1** | #108 (optional) |
| F-09 | **Reports tab disconnected** — exports do not show validation age, scene name, or stale-state warning | Reports | 4 | 2 | **P1** | #108 partial |
| F-10 | **Manifest Gate duplicated** — same control on Validate toolbar and Reports grid (`VALIDATE_MANIFEST_GATE_BUTTON` / export grid) | Validate / Reports | 3 | 2 | **P1** | #108 |
| F-11 | **Publish Preflight modal** — `_show_information_dialog` after summary already updated | Validate | 3 | 1 | **P1** | #108 |
| F-12 | **Strict profile fix confirm spam** — `publish_strict` uses per-fix `QMessageBox` (`confirm_risky_fixes` → `_confirm_single_risky_fix`) | Fixes | 4 | 3 | **P1** | defer batch UX polish |
| F-13 | **Duplicate panel header** — `build_panel_header()` on all four tabs (~14pt title + version) wastes ~40px × 4 | Global | 3 | 1 | **P1** | #108 (single header above tabs) |
| F-14 | **Fix queue on separate tab** — artist leaves Validate to inspect/apply fixes; no inline “N fixes available” chip | Fixes | 4 | 3 | **P1** | post–Wave 1 |
| F-15 | **Export feedback in Script Editor only** — no in-panel path label after JSON/HTML/manifest export | Reports | 3 | 2 | **P1** | #108 status line reuse |
| F-16 | **Filter row density** — Severity, Owner, View, Sort each with label + combo; wraps on narrow docks | Validate | 3 | 2 | **P1** | #109 |
| F-17 | **Filters reset on revalidate** — severity/owner filters repopulated; `setCurrentText(options[0])` clears user filter ( `_update_severity_filter_options`) | Validate | 4 | 2 | **P1** | #109 |
| F-18 | **Waive path indirect** — **Make Waive** on Waivers tab; no waive action on issue details row | Waivers | 3 | 3 | **P2** | v0.5+ |
| F-19 | **No scene name in chrome** — `DEVELOPMENT_PLAN.md` mockup shows scene + renderer; panel omits scene file name | Validate | 3 | 2 | **P2** | #108 optional |
| F-20 | **No severity color in table** — text-only severities; harder scan at a glance | Validate | 2 | 2 | **P2** | theme pass deferred |
| F-21 | **Asset class hint always expanded** — three-line hint under combos consumes vertical space | Validate | 2 | 1 | **P2** | collapsible hint |
| F-22 | ~~**Shelf single action**~~ — **Resolved (#102):** **Shader Health Farm Check** menu + shelf shortcut | Shelf | 3 | 2 | **P1** | M26 #102 ✅ |

---

## Prioritized backlog

### P0 — Must ship in v0.4.0 (M28 + M26)

| ID | Summary | Owner issue |
|----|---------|-------------|
| F-01 | Unified Validate tab action bar (primary vs pipeline groups) | [#108](https://github.com/armasonix/maya-shader-health-inspector/issues/136) |
| F-02 | Sticky summary header (health, blocks, profile chips) | #108 |
| F-03 | Last-validated timestamp in summary | #108 |
| F-04 | Farm tab + Deadline status — **shipped (#101)** | [#101](https://github.com/armasonix/maya-shader-health-inspector/issues/129) M26 ✅ |
| F-05 | Double-click issue row → select node | [#109](https://github.com/armasonix/maya-shader-health-inspector/issues/137) |
| F-06 | Reduce vertical overload (compact summary / splitter so table + details visible) | #108 |
| F-07 | Non-blocking progress indicator during validate | #109 |

### P1 — High value; ship in v0.4 if Wave 1 capacity allows

| ID | Summary |
|----|---------|
| F-08 | F5 validate shortcut |
| F-09 | Reports tab validation context (stale warning) |
| F-10 | Deduplicate Manifest Gate entry point |
| F-11 | Remove Publish Preflight modal; rely on summary + status |
| F-12 | Batch risky-fix confirmation on strict profiles |
| F-13 | Single panel header above `QTabWidget` |
| F-14 | Fix-queue availability chip on Validate tab |
| F-15 | In-panel export path feedback |
| F-16 | Compact filter toolbar |
| F-17 | Remember severity/owner/view/sort per session |
| F-22 | Shelf Farm Check shortcut (with M26) |

### P2 — Defer post–v0.4.0

| ID | Summary |
|----|---------|
| F-18 | Waive from issue details |
| F-19 | Scene name + renderer in summary chrome |
| F-20 | Severity color coding in issues table |
| F-21 | Collapsible asset-class hint |

---

## Wave 1 shortlist (M28)

Implements P0 panel items from this audit. Farm work stays in M26.

### Issue #108 — Validate tab action bar + status persistence

| Audit ID | Deliverable |
|----------|-------------|
| F-01 | One toolbar row: **Primary:** Validate Scene, Validate Selection \| **Pipeline:** Publish Preflight, Manifest Gate (or overflow menu) |
| F-02 | Summary widget pinned at top of Validate tab (does not scroll with table) |
| F-03 | `Last validated: <local time>` + scan scope chip (scene / selection) |
| F-06 | `QSplitter` or reduced summary lines so issues table + details visible without scroll on 900px dock height |
| F-08 | Optional: Maya-safe F5 → Validate Scene |
| F-09 | Pass last-run metadata to Reports status label |
| F-10 | Remove Manifest Gate from Reports grid OR from Validate bar (keep one) |
| F-11 | Publish Preflight: status label only, no QMessageBox |
| F-13 | Move `build_panel_header` above tab widget (once per panel) |
| F-15 | Export actions write path into shared status label |

**Acceptance sketch:** Flow A ≤3 clicks to selected node with default dock; blocking YES/NO visible without scrolling after validate.

### Issue #109 — Issue triage speed improvements

| Audit ID | Deliverable |
|----------|-------------|
| F-05 | `itemDoubleClicked` on issues table → `_run_navigation_action(select_node)` |
| F-07 | Busy cursor or thin progress bar + `evalDeferred` validate wrapper |
| F-16 | Filters in one compact row (icon tooltips, optional collapsible) |
| F-17 | Store filter/sort prefs on `content` attrs; restore on revalidate and tab focus |

**Acceptance sketch:** Revalidate does not reset user filters; double-click selects node in viewport; UI remains interactive during scan (or shows explicit busy state).

### M26 (not M28) — Farm gap

| Audit ID | Deliverable |
|----------|-------------|
| F-04 | Farm tab: connection status, Run Farm Preflight, Submit to Farm |
| F-22 | Shelf **Shader Health Farm Check** |

---

## Parity and non-UI notes

| Topic | Status |
|-------|--------|
| GUI ↔ CLI validation | **Pass** — same `validation_pipeline` |
| `block_publish` / `block_deadline` in summary | **Pass** — `_block_status_text` |
| Deadline farm submit in panel | **Pass** — Farm tab (#101): preflight + CommandScript submit |
| Manifest gate in UI | **Pass** — but duplicated (F-10) |
| Profile change revalidate | **Pass** — `_revalidate_with_current_scope` when prior results exist |

---

## Recommended layout (Wave 1 target)

```text
+-- Maya Shader Health Inspector  v0.4.x -----------------------------------+
| [Sticky summary]  Health 78  C:2 E:5  Publish: YES  Deadline: NO        |
| Scene: char.ma   Profile: Publish Strict   Asset: Hero   Last: 14:32    |
| [Validate Scene] [Validate Selection]  |  [Publish Preflight] [Gate]   |
+-------------------------------------------------------------------------+
| Filters: [Severity v] [View v] [Owner v] [Sort v]                       |
| +---------------------------+-----------------------------------------+ |
| | Issues table              | Issue details (splitter)                | |
| | (double-click = select)   | [Select] [Hypershade] [Copy] [Reveal]   | |
| +---------------------------+-----------------------------------------+ |
| Status: Validated 42 issues (12 blocking).  [=========>    ] scanning  |
+-------------------------------------------------------------------------+
| [Validate] [Waivers] [Fixes] [Reports] [Farm]                           |
+-------------------------------------------------------------------------+
```

---

## References

- [ADR 0005 — GUI-first product philosophy](adr/0005-gui-first-product-philosophy.md)
- [ARCHITECTURE.md — UX Layer](ARCHITECTURE.md)
- [USER_GUIDE.md — GUI-first workflow](USER_GUIDE.md)
- [DEVELOPMENT_PLAN.md §19 — UI/UX Design](DEVELOPMENT_PLAN.md)
- v0.4 plan issues [#108](https://github.com/armasonix/maya-shader-health-inspector/issues/136) / [#109](https://github.com/armasonix/maya-shader-health-inspector/issues/137) / [#101](https://github.com/armasonix/maya-shader-health-inspector/issues/129)
