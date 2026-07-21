# Readiness tab

**Machine Readiness** (v0.6) checks whether the **workstation** is ready for publish or farm work — before spending time on scene validation.

## When to use

| Situation | Action |
| --- | --- |
| Before publish day | **Run Machine Readiness** on a reference machine |
| Artist "it works on my box" | Compare readiness results |
| New hire workstation | Verify probes pass |

## Check categories

Configured in `pipeline_inspector_studio.json` → `readiness.checks`:

| Category | Examples |
| --- | --- |
| Maya plug-ins | V-Ray, Arnold, studio custom |
| Mapped drives | Texture / asset roots |
| Environment variables | `SHOW_ROOT`, studio tokens |
| Network paths | UNC roots from `studio_environment` |
| Installed software | Required DCC versions |

## UI flow

1. Open tab (panel or menu **Readiness Check**).
2. **Run Machine Readiness**.
3. Review pass/fail rows with actionable detail.
4. Optional: escalate to support via configured connectors.

## Limits

- Probes run **inside Maya session** — no separate readiness CLI yet ([Capability matrix](../Reference/Capability-Matrix)).
- Readiness does not replace scene validation — use **both**.

Architecture: [`ARCHITECTURE.md` — Machine Readiness](../../ARCHITECTURE.md)

→ [Studio config](../Administration/Studio-Config)
