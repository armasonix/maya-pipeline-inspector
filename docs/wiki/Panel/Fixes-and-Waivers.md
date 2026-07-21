# Fixes & waivers

Two tabs manage **automated remediation** and **approved exceptions**.

## Fixes tab (Safe Auto-Fix Queue)

### What is a safe fix?

A rule-backed mutation with a defined fix type ([ADR 0003](../../adr/0003-safe-fix-reference-safety-policy.md)):

| Fix type | Example |
| --- | --- |
| `set_attr` | Set color space on file node |
| `relink_path` | Point texture to studio root |
| `normalize_path` | Tokenize path to `${STUDIO_TEXTURE_ROOT}` |
| `disable_feature` | Turn off risky displacement |

### Queue workflow

1. Run validation — fixable issues populate the queue.
2. Review checkbox column — uncheck anything suspicious.
3. **Apply Safe Fixes** — mutates scene with undo chunk where possible.
4. **Fix Selected** — subset apply.
5. **Export Fix Plan** — JSON for review or headless `apply-fixes`.

### High-risk fixes

Some fixes require **extra confirmation** or role capability `apply_risky_fixes` ([Governance](Governance)).

Reference nodes and locked attributes are protected — fixes skip or fail with audit entry.

### Headless parity

```bash
mayapy -m pipeline_inspector apply-fixes scene.ma --fix-plan plan.json --dry-run
```

Policy: [ADR 0004 — Headless apply-fixes](../../adr/0004-headless-apply-fixes-policy.md)

---

## Waivers tab

Waivers record **known acceptable failures** (show policy, temp lookdev, etc.).

| Action | Purpose |
| --- | --- |
| **Make Waive** | Create waiver for selected issue pattern |
| **Refresh** | Reload waiver sidecar |
| **Revoke Selected** | Remove waiver |

Waivers live in sidecar JSON — version with scene or shot policy. They affect blocking flags per profile rules.

---

## Related

- [Safe fixes deep dive](Safe-Fixes)
- [`USER_GUIDE.md`](../../USER_GUIDE.md)
