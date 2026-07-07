# Renderer policy snapshot fixtures

JSON snapshots in this folder drive renderer policy integration tests without launching Maya.

## Files

| Snapshot | Expectations | Renderer | Purpose |
|---|---|---|---|
| `vray_policy_scene.json` | `vray_policy_scene.expectations.json` | V-Ray | Production policy failures (plugin, displacement, texture budget, trace depth) |
| `arnold_policy_scene.json` | `arnold_policy_scene.expectations.json` | Arnold | Production policy failures (plugin, displacement, transmission depth, stand-in) |
| `vray_material_policy.json` | — | V-Ray | Enrichment round-trip unit test |
| `arnold_material_policy.json` | — | Arnold | Enrichment round-trip unit test |
| `texture_freshness_outdated.json` | — | Common | Texture version freshness fail (`v001` vs latest `v003`) |
| `texture_freshness_latest.json` | — | Common | Texture version freshness pass (`v003` is latest) |
| `shader_complexity_layered_graph.json` | — | Common | Complexity profiler depth histogram and farm-cost enrichment |
| `shader_complexity_over_budget.json` | — | V-Ray | VRayBlendMtl / VRayLayeredTex expensive-node profiling |

## Adding a renderer fixture case

1. **Create the snapshot JSON** using `GraphSnapshot` schema (`docs/SNAPSHOT_SCHEMA.md`).
   - Set `renderer` to `vray` or `arnold`.
   - Include material nodes with attrs needed for enrichment (for example `rlmd` on `VRayMtl`, `transmissionDepth` on `aiStandardSurface`).
   - Omit plugin nodes when testing `*.scene.plugin_missing.error`.

2. **Create a companion expectations file** named `<snapshot_stem>.expectations.json`:

```json
{
  "profiles": {
    "supervisor_full": {
      "failed": [
        {
          "rule_id": "vray.scene.plugin_missing.error",
          "severity": "error",
          "block_publish": false,
          "block_deadline": false
        }
      ]
    },
    "publish_strict": {
      "failed": [
        {
          "rule_id": "vray.scene.plugin_missing.error",
          "severity": "error",
          "block_publish": true,
          "block_deadline": false
        }
      ]
    }
  }
}
```

3. **Register the case** in `tests/integration/test_renderer_policy_fixtures.py` by adding the snapshot stem to `POLICY_FIXTURE_CASES`.

4. **Run tests locally**:

```bash
python -m pytest tests/integration/test_renderer_policy_fixtures.py -q
```

Integration tests load the snapshot, run `run_validation()` with each profile listed in the expectations file, and assert rule id, status, severity, block flags, and optional `material` name.
