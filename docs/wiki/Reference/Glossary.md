# Glossary

| Term | Definition |
| --- | --- |
| **GraphSnapshot** | Serializable scene graph state for validation |
| **Profile** | Named rule set + blocking policy (`publish_strict`, etc.) |
| **Asset class** | Overlay profile for resolution/geometry tiers |
| **Rule pack** | Directory of JSON rule definitions |
| **Issue** | Single rule failure with severity and metadata |
| **Blocking** | Failure that stops publish or farm per profile |
| **Waiver** | Approved exception in sidecar JSON |
| **Safe fix** | Rule-backed mutation with guardrails |
| **Fix plan** | JSON list of planned fixes for apply-fixes |
| **Manifest** | Shader/texture baseline (schema 1.1) |
| **Gate** | Manifest regression check |
| **Farm cost score** | Heuristic shader complexity metric |
| **Readiness probe** | Workstation prerequisite check |
| **Connector** | External integration (Deadline, Slack, etc.) |
| **Capability** | Permission flag gated by role |
| **Module path** | `MAYA_MODULE_PATH` deploy with `maya_module/` |
| **Studio config** | `pipeline_inspector_studio.json` facility policy |

## Abbreviations

| Abbr | Meaning |
| --- | --- |
| TA | Technical Artist |
| TD | Technical Director (pipeline/shader context) |
| UDIM | Udim tile texture naming (`1001`, …) |
| DCC | Digital content creation app (Maya) |

## Rule id convention

`pack.domain.name` — e.g. `common.texture.missing`, `vray.material.transmission_depth`
