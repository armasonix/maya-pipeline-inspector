# User Guide

Maya Shader Health Inspector is a production-oriented material QA tool for Autodesk Maya. It is designed to help artists, Shader TDs, Pipeline TDs, and render supervisors detect material problems before publish or render farm submission.

Status: early development. This guide describes the intended user workflow for the MVP and will be updated as implementation progresses.

## What the Tool Checks

The MVP is planned to validate:

- missing texture files;
- local or unsafe texture paths;
- stale texture versions;
- broken UDIM tile sets;
- wrong color space on data maps;
- risky displacement setups;
- expensive shader graphs;
- duplicate or orphan material networks;
- basic renderer compatibility;
- Deadline preflight safety.

## Main User Roles

### Artist / Lookdev Artist

Main needs:

- validate current scene or selected assets;
- see clear red/yellow/green status;
- jump to broken nodes;
- understand why an issue matters;
- apply low-risk fixes safely;
- avoid rejected publishes or failed farm submissions.

### Shader TD / Technical Artist

Main needs:

- enforce material rules;
- inspect shader networks;
- author or tune rule packs;
- validate renderer-specific material behavior;
- keep shader libraries clean.

### Pipeline TD

Main needs:

- run validation headlessly;
- generate deterministic JSON reports;
- integrate with publish tools;
- integrate with Deadline submit flow;
- maintain project/show-specific profiles.

### Render Supervisor

Main needs:

- know if an asset or shot is safe for farm submission;
- review blocking issues;
- approve waivers if policy allows;
- inspect material health trends and reports.

## Expected Maya UI Workflow

```text
1. Open Maya scene.
2. Open Maya Shader Health Inspector panel.
3. Select profile: artist_relaxed, publish_strict, deadline_critical, or supervisor_full.
4. Click Validate Scene or Validate Selection.
5. Review health score and blocking status.
6. Filter issues by severity, owner, renderer, or auto-fix availability.
7. Select an issue.
8. Read what failed and why it matters.
9. Use Select Node, Open Attribute Editor, Copy Path, or Reveal File.
10. Apply safe fixes if available.
11. Revalidate.
12. Export JSON/HTML report if needed.
```

## Planned UI Layout

```text
+--------------------------------------------------------------------------------+
| Maya Shader Health Inspector                                                    |
| Scene: current_scene.ma   Renderer: V-Ray   Profile: Publish Strict             |
| Health: 78/100   Critical: 2   Error: 5   Warning: 17   Deadline Block: YES     |
| [Validate Scene] [Validate Selection] [Apply Safe Fixes] [Export Report]        |
+--------------------------------------------------------------------------------+
| Filters: [All severities] [Blocking only] [Auto-fixable] [Owner] [Renderer]     |
+--------------------------------------------------------------------------------+
| Sev | Material | Node | Issue | Auto-Fix | Owner | Rule ID                     |
+--------------------------------------------------------------------------------+
| Details                                                                        |
| What: Roughness texture is color-managed as ACEScg.                             |
| Why: Roughness is scalar data; color transforms alter numeric values.           |
| Current: ACEScg                                                                 |
| Expected: Raw                                                                   |
| Trace: file_roughness.outAlpha -> material.roughness                           |
| [Select Node] [Open Attr Editor] [Copy Path] [Apply Fix] [Waive]                |
+--------------------------------------------------------------------------------+
```

## Health Score

The health score is a quick summary of scene or selection quality.

Example:

```text
Health: 76 / 100
Critical: 1
Error: 2
Warning: 14
Info: 8
Publish Block: YES
Deadline Block: YES
Auto-fixable: 9
Waived: 2
```

A high score does not mean the scene is artistically correct. It means the scene has fewer detected technical material risks according to the selected profile.

## Severity Meaning

| Severity | Meaning |
|---|---|
| Info | Useful cleanup or visibility. Usually not blocking. |
| Warning | Should be reviewed. Usually not blocking. |
| Error | Should be fixed before publish. May block depending on profile. |
| Critical | High production risk. Usually blocks publish or Deadline. |

## Blocking Status

The tool separates severity from block policy.

A rule may be critical but only block publish. Another rule may be an error in UI but block Deadline in strict farm-preflight profile.

Important block flags:

- `block_publish`
- `block_deadline`

## Profiles

Profiles control strictness and runtime behavior.

Planned MVP profiles:

| Profile | Purpose |
|---|---|
| `artist_relaxed` | Interactive lookdev checks with fewer blocks. |
| `publish_strict` | Asset publish checks. Blocks serious issues. |
| `deadline_critical` | Fast farm submission preflight. Critical-only where possible. |
| `supervisor_full` | Full audit mode with all rules visible. |
| `ci_headless` | Deterministic validation for automated checks. |

## Issue Details

Every issue should explain:

- what failed;
- why it matters;
- current value;
- expected value;
- affected material/node/plug;
- owner;
- rule ID;
- graph trace;
- block flags;
- auto-fix availability.

Example:

```text
Issue: Roughness texture is color-managed as ACEScg.
Why: Roughness is scalar data. Color transforms can change numeric values and alter reflection response.
Current: ACEScg
Expected: Raw
Owner: Shader TD
Rule: common.texture.colorspace.data_raw
Auto-fix: available
```

## Safe Auto-Fix Workflow

Auto-fix is never silent.

Expected flow:

```text
1. Select issue with available fix.
2. Review before/after values.
3. Review risk level.
4. Confirm fix.
5. Tool applies fix inside Maya undo chunk.
6. Revalidate.
```

Low-risk example:

```text
file_roughness.colorSpace: ACEScg -> Raw
```

High-risk fixes should require explicit confirmation or supervisor approval depending on profile.

## Reference Safety

Referenced and locked nodes should not be modified by default.

If an issue is inside a referenced asset, the tool should:

- report the problem;
- show the reference path;
- block unsafe auto-fix by default;
- suggest opening/fixing the source asset file;
- allow waiver only if profile policy permits it.

## Waivers

Waivers are controlled exceptions for known issues.

Expected behavior:

- waiver must include reason;
- waiver must include approver;
- waiver should expire;
- waived issues remain visible in reports;
- critical farm-blocking issues are waiver-disabled by default unless profile allows it.

Example:

```text
Rule: common.texture.resolution.max
Reason: Hero close-up approved by supervisor.
Approved by: supervisor_name
Expires: 2026-07-30
```

## Reports

Planned report outputs:

- JSON report for automation;
- HTML report for review;
- Material Passport / Shader Manifest for asset state tracking;
- manifest diff report for change review.

JSON reports are intended for pipeline systems. HTML reports are intended for human review.

## Headless Usage

Target command shape:

```bash
mayapy -m shader_health validate scene.ma --profile publish_strict --report report.json
mayapy -m shader_health validate scene.ma --profile deadline_critical --critical-only
mayapy -m shader_health manifest scene.ma --out shader_manifest.json
mayapy -m shader_health diff old_manifest.json new_manifest.json --html diff.html
```

MVP implementation will add these commands gradually.

## Deadline Submit Preflight

Deadline preflight should run validation before render submission.

Expected behavior:

```text
1. Artist submits render.
2. Submit tool runs shader health validation with deadline_critical profile.
3. If block_deadline is false, submission continues.
4. If block_deadline is true, submission stops and shows summary.
5. JSON report is saved for review.
```

## Best Practices for Users

- Validate before publish, not after render failure.
- Fix critical issues before sending to farm.
- Do not waive missing textures or unsafe local paths unless policy explicitly allows it.
- Use selection validation while working on a single asset.
- Use full scene validation before publish or submission.
- Export reports for supervisor review when issues are complex.

## Current Development Status

The repository is currently in bootstrap and core architecture phase. The user-facing Maya UI is planned after the pure Python core, rule engine, and scanner contracts are stable.

See also:

- `docs/DEVELOPMENT_PLAN.md`
- `docs/ARCHITECTURE.md`
- `docs/RULE_AUTHORING.md`
