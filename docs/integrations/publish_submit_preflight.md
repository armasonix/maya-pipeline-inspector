# Publish submit preflight example

This integration example shows how to run Maya Shader Health Inspector before an
asset or shading publish is committed to the pipeline.

The example does not publish an asset by itself. It is a pre-publish gate that can
be called from an existing publish tool, shelf hook, launcher, or studio pipeline
script.

## Goal

- Run the headless validator through `mayapy`.
- Use a publish-critical validation profile such as `publish_strict`.
- Write a JSON report beside the scene or in a pipeline-controlled reports folder.
- Block publish when Shader Health returns a publish-blocking exit code.

## Example script

```bash
mayapy examples/publish/submit_preflight.py \
  D:/show/assets/char/hero/shading/hero_shading.ma \
  --report D:/show/assets/char/hero/reports/shader_health_publish.json \
  --profile D:/tools/maya-shader-health-inspector/src/shader_health/rules/profiles/publish_strict.json \
  --repo-root D:/tools/maya-shader-health-inspector \
  --mayapy "C:/Program Files/Autodesk/Maya2026/bin/mayapy.exe" \
  --renderer vray
```

Arguments after the known preflight options are forwarded to the validator. This
allows the publish tool to pass renderer IDs, extra rule folders, waiver sidecars,
or other future headless validation options.

## Publish mode

The preflight script treats the supplied `--profile` as the critical validation
profile for publish submission. A typical `publish_strict` profile makes
publish-breaking rules set `block_publish=true`, for example missing texture files
or renderer plugin gaps.

The existing validation profile contract supports this with rule overrides:

```json
{
  "id": "publish_strict",
  "display_name": "Publish Strict",
  "rule_overrides": {
    "vray.scene.plugin_missing.error": {
      "block_publish": true
    }
  }
}
```

Studios can point `--profile` at a copied or extended profile JSON while keeping
the same exit-code contract.

## Exit code mapping

The headless validator returns documented exit codes:

| Validator exit code | Meaning |
| --- | --- |
| `0` | No blocking issues. |
| `1` | Publish-blocking issues. |
| `2` | Deadline/farm-blocking issues. |
| `3` | Runtime/tool error. |
| `4` | Invalid config/profile/rules. |

The publish preflight maps those into publish decisions:

| Preflight exit code | Publish decision |
| --- | --- |
| `0` | Allow publish. |
| `1` | Block publish because publish-blocking issues were found. |
| `3` | Block publish because the preflight itself could not complete safely. |

## Integration pattern

In a studio publish tool, call the preflight before the actual publish commit:

```python
from pathlib import Path

from examples.publish.submit_preflight import run_publish_preflight

result = run_publish_preflight(
    scene_path=Path(scene_path),
    report_path=Path(report_path),
    profile_path=Path(publish_profile_path),
    mayapy=mayapy_path,
    repo_root=Path(shader_health_repo_root),
    extra_args=("--renderer", "vray"),
)

if not result.allowed:
    raise RuntimeError(
        "Publish blocked by Shader Health. "
        f"Report: {result.report_path}"
    )

# Continue with normal publish commit here.
```

## Operational notes

- Keep the generated JSON report as a publish artifact for audit and supervisor review.
- Use `mayapy`, not regular Python, when validating `.ma` or `.mb` scenes.
- Use snapshot JSON validation for CI or non-Maya environments.
- Do not ignore preflight error code `3`; treat it as a failed safety check.
- Tune the `publish_strict` profile per show or facility policy.
- Pair with waiver sidecars when policy allows supervised exceptions.

## Validation

The example is covered by unit tests:

```bash
python -m pytest tests/unit/test_publish_submit_preflight_example.py -v
```
