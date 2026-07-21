# Authoring rules

Extend validation without forking core code.

## Paths

| Method | Best for |
| --- | --- |
| **Rule browser + wizard** (panel) | MVP templates — missing texture, path policy, etc. |
| **Hand-edited JSON** | Advanced checks, renderer-specific logic |
| **Incident-to-rule** (panel) | Turn a failed validation into starter rule JSON |

Full schema: [`RULE_AUTHORING.md`](../../RULE_AUTHORING.md)

## Check types (shipped)

| Type | Validates |
| --- | --- |
| Field threshold | Numeric/string field vs limit |
| Path policy | Studio root compliance |
| Set membership | Enum / flag sets |
| Collection count | List sizes (UDIM tiles, etc.) |

## Fix types (shipped)

| Type | Action |
| --- | --- |
| `set_attr` | Attribute value |
| `relink_path` | File path |
| `normalize_path` | Tokenized studio path |
| `disable_feature` | Toggle risky feature |

## Contribution workflow

1. Add rule JSON under studio pack or upstream PR.
2. Add fixture snapshot or demo scene evidence.
3. Run `python -m pipeline_inspector rules validate pack/`.
4. Run `pytest` for any custom check unit tests.

→ [`CONTRIBUTING.md`](../../CONTRIBUTING.md) · [Safe fixes](Safe-Fixes)

## Renderer packs

When adding V-Ray/Arnold rules, use adapter metadata — don't hard-code vendor node names in common packs ([ADR 0002](../../adr/0002-renderer-adapter-boundary.md)).
