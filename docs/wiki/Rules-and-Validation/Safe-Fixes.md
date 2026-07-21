# Safe fixes

Automated remediation with guardrails — [ADR 0003](../../adr/0003-safe-fix-reference-safety-policy.md).

## Principles

1. **Preview before apply** — fix queue shows planned mutations.
2. **Reference safety** — referenced nodes skipped or fix blocked.
3. **High-risk gate** — extra confirm + role capability.
4. **Audit trail** — fix apply log JSON for postmortems.
5. **Undo** — Maya undo chunk where API allows.

## Fix plan export

Panel **Export Fix Plan** or validation output → headless:

```bash
mayapy -m pipeline_inspector apply-fixes scene.ma --fix-plan plan.json
mayapy -m pipeline_inspector apply-fixes scene.ma --fix-plan plan.json --dry-run
```

Headless policy: [ADR 0004](../../adr/0004-headless-apply-fixes-policy.md)

## What fixes cannot do

- Replace a full texture publish pipeline
- Rename assets in external databases
- Override locked studio references without policy
- Fix missing geometry topology automatically (review-only rules)

## Governance

Capability **`apply_risky_fixes`** — see [Governance](Governance).

## UI

→ [Fixes & waivers panel](Fixes-and-Waivers)
