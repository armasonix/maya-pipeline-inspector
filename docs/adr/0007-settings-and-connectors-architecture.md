# ADR 0007: Settings and Connectors architecture

## Status

Accepted

## Date

2026-07-08

## Context

v0.4 ships a Settings screen with six category tabs, but only **Connectors → Deadline** and **Studio → Require .tx** are functional. Basic and Advanced tabs are placeholders. All persistent settings live in a single [`studio_config.py`](../../src/pipeline_inspector/studio_config.py) model at **schema 1.0** (`pipeline`, `connectors.deadline`, `studio_name`). Deadline connector UI is hard-coded in [`settings_panel.py`](../../src/pipeline_inspector/ui/settings_panel.py) via `_build_connectors_tab` and `_read_deadline_connector_from_view`.

v0.5 expands Settings into a **studio platform hub**: Technical Artist/TD preferences, studio pipeline policy, network path constants, notification connectors (Telegram, Discord, Slack), task trackers (Ftrack, ShotGrid, Cerebro), Bug Report via a studio HTTPS relay, and Check for Updates via GitHub Releases. ADR 0005 requires GUI-first delivery; ADR 0001 requires the validation core to stay Maya-independent and testable. Settings architecture must therefore:

- separate **studio-wide policy** from **per-user preferences** without duplicating validation logic;
- scale Connectors beyond Deadline without copy-pasting settings UI code;
- keep secrets out of user-visible files and out of the open-source plugin binary;
- let headless CLI respect studio policy (known v0.4 limitation: `PIPELINE_INSPECTOR_STUDIO_CONFIG` not wired into `pipeline_inspector validate`).

This ADR defines the v0.5 configuration model, merge semantics, connector registry, secret handling, and Bug Report relay security contract. Implementation issues #114–#118 depend on these decisions.

## Decision

Pipeline Inspector v0.5 adopts a **two-layer configuration architecture** with a **connector registry**, explicit **save/load split**, and **studio-hosted relay** for Bug Report.

### 1. Two configuration layers

| Layer | File | Discovery | Owner | Typical contents |
|---|---|---|---|---|
| **StudioConfig** | `pipeline_inspector_studio.json` | `PIPELINE_INSPECTOR_STUDIO_CONFIG` env var, then `~/.pipeline_inspector/pipeline_inspector_studio.json`, then `~/pipeline_inspector_studio.json` | Pipeline TD / studio IT | `studio_name`, `pipeline`, `studio_environment`, `connectors`, studio-locked `bug_report` relay URL, optional embedded defaults |
| **UserPreferences** | `~/.pipeline_inspector/user.json` | Fixed per-machine path | Technical Artist / local TD | `default_profile_id`, `theme`, `ui_density`, `extra_rule_paths`, `debug_logging`, `mayapy_path`, `docs_url` |

Both layers are plain JSON with `schema_version`. Studio config bumps to **2.0** in issue #114; user config starts at **1.0**.

Runtime code loads both files at panel startup (issue #117) and exposes a **MergedRuntimeConfig** dataclass to UI and integrations. Headless CLI loads **StudioConfig only** (plus optional `--studio-config`); user prefs are Maya-panel-only in v0.5.

### 2. Merge rules

When both files are present, fields resolve by **ownership**, not deep JSON merge:

| Domain | Source of truth | User override allowed? |
|---|---|---|
| Pipeline policy (`require_tx_derivatives`, waiver/manifest defaults, approved profile pins) | Studio | No |
| `studio_environment` paths and `variable_aliases` | Studio | No |
| Connector `enabled` flags and credentials | Studio | No — TDs deploy one studio file |
| Connector non-secret defaults visible to Technical Artists (e.g. `notify_on[]`) | Studio | Optional read-only display in v0.5; edits require studio file |
| UI theme, density, default profile/asset class/scan scope | User | Yes |
| `extra_rule_paths`, `debug_logging`, `max_issues_displayed`, local `mayapy_path` | User | Yes |
| `bug_report` relay URL and API key | Studio | No |
| `updates` channel / auto-check preference | User | Yes (check frequency); release repo pinned in code |

**Rule overrides:** studio `pipeline` settings continue to map to `RuleOverride` entries (as today for `.tx` rules). User `extra_rule_paths` append rule packs at validation time; they cannot disable studio-mandated rules.

**Precedence on conflict:** studio wins for locked domains; user wins for preference domains. Unknown keys in either file are ignored on load (forward compatibility).

### 3. Save and load actions

The Settings screen exposes **two explicit actions** (issue #117):

- **Save Studio Config** — writes `pipeline_inspector_studio.json` to the path shown in the status banner (or prompts for path on first save).
- **Save User Preferences** — writes `~/.pipeline_inspector/user.json`.

A single combined Save is **rejected** — it blurs rollout responsibility (studio JSON often lives on a network share deployed by IT; user JSON is per-workstation).

Load actions mirror save: **Load Studio Config** (file picker) and **Load User Preferences** (file picker, defaulting to `~/.pipeline_inspector/user.json`).

Dirty-state banner (issue #123) tracks each layer independently.

### 4. Schema 2.0 top-level sections (StudioConfig)

```json
{
  "schema_version": "2.0",
  "studio_name": "Example Studio",
  "pipeline": { "require_tx_derivatives": true },
  "studio_environment": {
    "texture_root": "\\\\farm\\textures",
    "asset_root": "\\\\farm\\assets",
    "cache_root": "\\\\farm\\cache",
    "render_root": "\\\\farm\\render",
    "variable_aliases": { "STUDIO_TEXTURE_ROOT": "\\\\farm\\textures" }
  },
  "connectors": {
    "deadline": { "enabled": false },
    "telegram": { "enabled": false, "bot_token": "", "chat_id": "" },
    "discord": { "enabled": false },
    "slack": { "enabled": false },
    "ftrack": { "enabled": false },
    "shotgrid": { "enabled": false },
    "cerebro": { "enabled": false }
  },
  "bug_report": {
    "enabled": false,
    "relay_url": "",
    "api_key": "",
    "allow_screenshot": true,
    "max_reports_per_day": 5
  }
}
```

Migration from 1.0 → 2.0 is **additive**: missing sections receive defaults; `schema_version` is rewritten on save. See issue #114 for `from_dict` implementation and tests.

`UserPreferences` schema (separate file):

```json
{
  "schema_version": "1.0",
  "default_profile_id": "lookdev",
  "default_asset_class_id": "character",
  "default_scan_scope": "scene",
  "theme": "classic",
  "ui_density": "comfortable",
  "extra_rule_paths": [],
  "debug_logging": false,
  "max_issues_displayed": 500,
  "mayapy_path": "",
  "docs_url": "https://github.com/armasonix/maya-pipeline-inspector/wiki",
  "updates": { "check_on_startup": false }
}
```

### 5. Connector registry pattern

New module [`connectors_registry.py`](../../src/pipeline_inspector/connectors_registry.py) (issue #115) defines a frozen **ConnectorDefinition** per integration:

```python
@dataclass(frozen=True)
class ConnectorDefinition:
    id: str                          # e.g. "deadline", "telegram"
    display_name: str                # Settings UI section title
    settings_dataclass: type         # frozen dataclass with from_mapping / to_dict
    resolve_fn: Callable[..., Any | None]  # StudioConfig -> runtime client or None
    settings_ui_builder: Callable[..., QWidget]  # builds Connectors tab section
    secret_field_names: frozenset[str] = frozenset()
```

**Registration:** each connector module calls `register_connector(ConnectorDefinition(...))` at import time, or a single `CONNECTORS` tuple in `connectors_registry.py` lists all definitions (preferred for testability).

**Settings panel loop:** `read_connectors_from_settings_view` and `update_settings_view` iterate `iter_connectors()` instead of Deadline-specific helpers. Deadline is refactored first; new connectors add a definition + `integrations/<name>/` package without editing the tab loop.

**Resolve semantics:** `resolve_fn(config)` returns `None` when `enabled` is false — same rule as [`resolve_deadline_config`](../../src/pipeline_inspector/studio_config.py) today (no env fallback when explicitly disabled).

**Notification fan-out:** `integrations/notify/dispatcher.py` (issue #140) queries enabled notification connectors after validation/farm events; trackers use separate explicit actions (Reports tab, issue #145).

### 6. Secret field policy

Credentials must not appear in plaintext in user-editable files beyond what studio IT already deploys. Policy:

| Rule | Detail |
|---|---|
| Schema metadata | Sensitive keys are listed in `ConnectorDefinition.secret_field_names` and documented per connector |
| UI | Secret fields use password echo mode (`QLineEdit.EchoMode.Password`); show/hide toggle optional |
| Serialization | Secrets are stored in studio JSON on disk (studio responsibility); user JSON **must not** contain connector secrets |
| Logs | Never log secret values; relay client logs relay URL host only, not API key |
| Version control | `pipeline_inspector_studio.json` with secrets stays out of git (document in `STUDIO_OVERRIDES.md`) |
| Bug Report | No GitHub PAT in Maya — relay holds GitHub App / PAT server-side |

Optional v0.5.1 enhancement (out of scope here): OS keychain storage for user-entered secrets on solo-user machines.

### 7. Bug Report — studio HTTPS relay

Bug Report uses a **studio-hosted relay** (issues #147–#151). The open-source plugin ships **client only**; each studio deploys the relay against its GitHub org.

```text
Maya panel (Bug Report form)
  -> integrations/bug_report/relay_client.py
  -> HTTPS POST multipart to studio relay_url
  -> relay validates API key, rate limits, payload size
  -> relay creates GitHub Issue (labels: bug, user-report)
  -> relay emails maintainer; returns issue URL to panel
```

**Relay security checklist (relay implementer contract):**

| Control | Requirement |
|---|---|
| Transport | HTTPS only; reject plain HTTP |
| Authentication | API key in header (`Authorization: Bearer <key>` or `X-Shader-Health-Key`); rotatable per studio |
| Rate limiting | Per API key + `machine_id`/`os_user` from payload; enforce studio `bug_report.max_reports_per_day` server-side; return **HTTP 429** with optional `Retry-After` and JSON error body when exceeded |
| Payload size | Total body cap (e.g. 3 MB); screenshot max 2 MB |
| Image types | Whitelist JPEG/PNG; reject SVG/HTML |
| SSRF | No arbitrary URL fields in payload; relay does not fetch user-supplied URLs |
| Privacy | Scene path sent as basename only; no env dump |
| GitHub scope | Optional allowlist of target repo, labels, milestones on relay |
| Abuse | Client-side throttle in `integrations/bug_report/throttle.py` mirrors `max_reports_per_day` per machine/user in `~/.pipeline_inspector/bug_report_throttle.json` before calling the relay; relay 429 responses surface as `rate_limited` in the Maya panel |

Bug Report is **disabled by default** until `bug_report.relay_url` and `api_key` are set in studio config.

### 8. Check for Updates — GitHub Releases

Per v0.5 plan decision (issues #152–#155):

- Compare [`version.py`](../../src/pipeline_inspector/version.py) against `GET /repos/{owner}/{repo}/releases/latest` tag_name (semver).
- Download release asset to a staging directory; install preserves `pipeline_inspector_studio.json` and `user.json`.
- Maya restart is **manual** — show checklist dialog; no fake auto-restart.

User-facing guide: [`docs/integrations/auto_update.md`](../integrations/auto_update.md).

User preference `updates.check_on_startup` may trigger silent check; download/install always requires explicit confirmation (GUI-first clarity).

### 9. Settings tabs — v0.5 target

| Tab | Audience | Config layer | v0.5 scope |
|---|---|---|---|
| Basic | Technical Artist | User | Profile defaults, theme, density |
| Advanced | TD | User | Rule roots, debug, perf caps, rule editor entry |
| Connectors | TD | Studio | Registry-driven integrations |
| Studio | TD | Studio | Pipeline policy, studio name |
| Studio Environment | TD | Studio | Network roots, `${VAR}` aliases |
| Bug Report | TD | Studio | Relay URL, API key, privacy notice |

Header additions (M33): Documentation button (`user.docs_url`), Check for Updates button (M37 wizard).

### 10. Headless CLI (minimal v0.5)

Issue #118 wires studio config into CLI:

- Respect `PIPELINE_INSPECTOR_STUDIO_CONFIG` and `--studio-config` on `validate`, `gate`, `manifest`.
- Apply `pipeline` rule overrides and `studio_environment` path substitution where relevant.
- User preferences are **not** loaded in headless mode in v0.5.

## Alternatives Considered

### 1. Single merged JSON file

Pros: one Save button; simpler mental model for solo Technical Artists.

Cons: studio rollout requires overwriting user theme/preferences; unsuitable for facility deployment; mixes IT-managed policy with personal prefs.

Rejected. Two files with explicit save actions.

### 2. GitHub PAT in Maya for Bug Report

Pros: no relay server; direct `POST /repos/.../issues`.

Cons: PAT in plaintext on Technical Artist workstations; unacceptable leak risk; violates studio security reviews.

Rejected. Studio relay is required.

### 3. Per-connector bespoke Settings UI (v0.4 style)

Pros: fastest for first connector; no registry abstraction.

Cons: does not scale to eight connectors; duplicate read/write/view code; regression risk.

Rejected after Deadline. Registry pattern from v0.5 onward.

### 4. Deep JSON merge (user overrides studio fields)

Pros: flexible per-user connector toggles.

Cons: Technical Artists could disable Deadline/Telegram alerts studio mandates; support nightmare.

Rejected. Ownership table with studio lock on policy/connectors.

### 5. Slack/Telegram OAuth apps in v0.5

Pros: richer Slack interactions (buttons, slash commands).

Cons: requires hosted OAuth server; scope creep.

Deferred. v0.5 uses incoming webhooks and bot tokens only.

## Consequences

### Positive

- Clear split between studio rollout (`pipeline_inspector_studio.json`) and per-machine prefs (`user.json`).
- Connector registry lets M34–M35 add integrations without rewriting `settings_panel.py`.
- Bug Report works for open-source distribution without embedding maintainer GitHub tokens.
- Secret policy and relay checklist give studios a security review starting point.
- Headless CLI parity for pipeline `.tx` overrides closes a known v0.4 gap.

### Negative / Tradeoffs

- Two files and two Save actions add TD onboarding steps (mitigated by docs in M32/M40).
- Studio JSON with secrets requires file-permission discipline at facilities.
- Studios without a relay cannot use Bug Report until they deploy one (disabled by default).
- Registry indirection adds one abstraction layer before new connectors ship.
- User preferences ignored in headless v0.5 may surprise TDs expecting `extra_rule_paths` in farm jobs (document; consider env override in v0.5.1).

## Implementation Notes

### Target modules (v0.5)

```text
src/pipeline_inspector/
├── studio_config.py       # schema 2.0, StudioConfig
├── user_config.py         # NEW — UserPreferences load/save/discover
├── connectors_registry.py # NEW — ConnectorDefinition registry
├── integrations/
│   ├── deadline/          # existing; first registry entry
│   ├── telegram/ discord/ slack/
│   ├── ftrack/ shotgrid/ cerebro/
│   ├── bug_report/        # relay_client only
│   ├── notify/            # dispatcher
│   └── update/            # github_releases
└── ui/
    ├── settings_panel.py  # registry loop, new tabs
    ├── themes/            # classic.qss, dark.qss
    ├── update_dialog.py
    └── bug_report_dialog.py
```

### ConnectorDefinition sketch (Deadline)

```python
def _resolve_deadline(config: StudioConfig) -> DeadlineConfig | None:
    return resolve_deadline_config(config)  # existing helper

DEADLINE_CONNECTOR = ConnectorDefinition(
    id="deadline",
    display_name="Thinkbox Deadline",
    settings_dataclass=DeadlineConnectorSettings,
    resolve_fn=_resolve_deadline,
    settings_ui_builder=_build_deadline_connector_section,
    secret_field_names=frozenset(),  # no secrets in v0.4 fields
)
```

### Testing expectations

| Area | Coverage |
|---|---|
| Schema 1.0 → 2.0 migration | `tests/unit/test_studio_config.py` (#114) |
| User config round-trip | `tests/unit/test_user_config.py` (#117) |
| Registry read/write | Extend `tests/unit/test_settings_panel.py` (#115) |
| Relay client | Mock HTTP; no live GitHub (#148) |
| Secret fields | UI fakes assert password echo on `bot_token`, `api_key` |

### Issue sequencing

Implement in order: **#114** schema → **#115** registry + Deadline refactor → **#116** tabs shell → **#117** user split → **#118** CLI. M31–M37 features depend on this foundation.

## Related

- Plan issue: `#113 - ADR 0007 Settings and Connectors architecture` (GitHub #147)
- Follow-on: `#114` schema 2.0 (GitHub #148), `#115` connector registry (GitHub #149), `#116`–`#118` settings core (GitHub #150–#152)
- Bug Report: `#147`–`#151` (GitHub #181–#185)
- ADR: `0001-snapshot-first-core.md`
- ADR: `0005-gui-first-product-philosophy.md`
- Module: `src/pipeline_inspector/studio_config.py`
- Module: `src/pipeline_inspector/ui/settings_panel.py`
- Document: `docs/V0_5_DEVELOPMENT_PLAN.md` (to be added)
- Document: `docs/integrations/bug_report_relay.md` (issue #150)
