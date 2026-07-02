# Deadline submit preflight example

This integration example shows how to run Maya Shader Health Inspector before a
Deadline job is submitted to the farm.

The example does not submit a job by itself. It is a pre-submit gate that can be
called from an existing Deadline submitter, shelf tool, launcher, or studio
pipeline hook.

## Goal

- Run the headless validator through `mayapy`.
- Use a Deadline-critical validation profile.
- Write a JSON report beside the submitted scene or in a pipeline-controlled
  reports folder.
- Block submission when Shader Health returns a farm-blocking exit code.

## Example script

```bash
mayapy examples/deadline/submit_preflight.py \
  D:/show/seq010/shot020/lighting/shot020_lighting.ma \
  --report D:/show/seq010/shot020/reports/shader_health_deadline.json \
  --profile D:/show/config/shader_health/profiles/deadline_critical.json \
  --repo-root D:/tools/maya-shader-health-inspector \
  --mayapy "C:/Program Files/Autodesk/Maya2026/bin/mayapy.exe" \
  --renderer vray
```

Arguments after the known preflight options are forwarded to the validator. This
allows the submitter to pass renderer IDs, extra rule folders, or other future
headless validation options.

## Critical mode

The preflight script treats the supplied `--profile` as the critical validation
profile for Deadline submission. A typical `deadline_critical` profile makes
farm-breaking rules set `block_deadline=true`, for example missing texture files.

The existing validation profile contract supports this with rule overrides:

```json
{
  "id": "deadline_critical",
  "display_name": "Deadline Critical",
  "rule_overrides": {
    "common.texture.missing": {
      "block_deadline": true
    }
  }
}
```

## Exit code mapping

The headless validator returns documented exit codes:

| Validator exit code | Meaning |
| --- | --- |
| `0` | No blocking issues. |
| `1` | Publish-blocking issues. |
| `2` | Deadline/farm-blocking issues. |
| `3` | Runtime/tool error. |
| `4` | Invalid config/profile/rules. |

The submit preflight maps those into submit decisions:

| Preflight exit code | Submit decision |
| --- | --- |
| `0` | Allow Deadline submission. |
| `2` | Block Deadline submission because farm-blocking issues were found. |
| `3` | Block submission because the preflight itself could not complete safely. |

## Integration pattern

In a studio submitter, call the preflight before the actual Deadline submit call:

```python
from pathlib import Path

from examples.deadline.submit_preflight import run_deadline_preflight

result = run_deadline_preflight(
    scene_path=Path(scene_path),
    report_path=Path(report_path),
    profile_path=Path(deadline_profile_path),
    mayapy=mayapy_path,
    repo_root=Path(shader_health_repo_root),
    extra_args=("--renderer", "vray"),
)

if not result.allowed:
    raise RuntimeError(
        "Deadline submission blocked by Shader Health. "
        f"Report: {result.report_path}"
    )

# Continue with normal Deadline submission here.
```

## Operational notes

- Keep the generated JSON report as a submit artifact.
- Use `mayapy`, not regular Python, when validating `.ma` or `.mb` scenes.
- Use snapshot JSON validation for CI or non-Maya environments.
- Do not ignore preflight error code `3`; treat it as a failed safety check.
- Tune the `deadline_critical` profile per show or facility policy.

## Validation

The example is covered by unit tests:

```bash
python -m pytest tests/unit/test_deadline_submit_preflight_example.py -v
```
