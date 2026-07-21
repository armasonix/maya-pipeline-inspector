# Publish preflight

Gate asset publish with validation + optional manifest regression.

## Panel workflow

1. Set **Workflow** → `publish_strict`.
2. Set **Asset class** if production tier applies (Hero/Prop/Background).
3. **Validate Scene** — confirm **Publish Block: NO**.
4. Resolve Critical/Error issues or active waivers.
5. **Reports** → export manifest as publish baseline (first publish).
6. On updates: **Manifest Gate** or compare against approved manifest.

## Headless publish hook

```bash
mayapy -m pipeline_inspector validate "$SCENE" \
  --profile-id publish_strict \
  --studio-config "$STUDIO_JSON" \
  --report "$REPORT_JSON"

# exit code non-zero on blocking failures
```

## Manifest regression gate

```bash
mayapy -m pipeline_inspector gate "$SCENE" "$APPROVED_MANIFEST.json" \
  --profile-id publish_strict
```

## Integration doc

→ [`integrations/publish_submit_preflight.md`](../../integrations/publish_submit_preflight.md)

## Common blockers

| Issue class | Typical fix |
| --- | --- |
| Missing texture | Relink or publish texture |
| Local path | Normalize to studio token |
| UDIM gap | Fix tile sequence |
| Complexity | Simplify shader graph |
| Geometry budget | Reduce polycount or reclassify asset |

→ [Validate tab](../Panel/Validate-Tab)
