# Deadline submit preflight example

This integration shows how to run Maya Shader Health Inspector before a Deadline
job is submitted to the farm.

v0.4 adds a shared package at `shader_health.integrations.deadline` with:

- `DeadlineConfig` — Web Service URL, profile defaults, queue/pool routing
- `DeadlineClient` — thin REST wrapper for Deadline 10 on-prem
- `run_deadline_preflight()` — headless validation gate used by examples and the Farm tab

The example script is a thin CLI wrapper around the shared module. It does not
submit a job by itself.

## Goal

- Run the headless validator through `mayapy`.
- Use a Deadline-critical validation profile.
- Write a JSON report beside the submitted scene or in a pipeline-controlled
  reports folder.
- Block submission when Shader Health returns a farm-blocking exit code.

## Configuration

Studios can load Deadline defaults from environment variables or a JSON file.

Environment variables (`SHADER_HEALTH_DEADLINE_*`):

| Variable | Purpose |
| --- | --- |
| `SHADER_HEALTH_DEADLINE_API_URL` | Web Service base URL (default `http://localhost:8081`) |
| `SHADER_HEALTH_DEADLINE_TIMEOUT` | HTTP timeout in seconds |
| `SHADER_HEALTH_DEADLINE_PROFILE_ID` | Packaged profile id (default `deadline_critical`) |
| `SHADER_HEALTH_DEADLINE_PROFILE_PATH` | Optional explicit profile JSON path |
| `SHADER_HEALTH_DEADLINE_MAYAPY` | `mayapy` executable for scene validation |
| `SHADER_HEALTH_DEADLINE_REPO_ROOT` | Working directory for validator subprocess |
| `SHADER_HEALTH_DEADLINE_QUEUE` | Default Deadline queue name |
| `SHADER_HEALTH_DEADLINE_POOL` | Default Deadline pool name |
| `SHADER_HEALTH_DEADLINE_GROUP` | Default Deadline group name |

JSON config example:

```json
{
  "api_url": "http://deadline-web:8082",
  "profile_id": "deadline_critical",
  "mayapy": "C:/Program Files/Autodesk/Maya2026/bin/mayapy.exe",
  "queue": "lookdev",
  "timeout_seconds": 30
}
```

Load in Python:

```python
from pathlib import Path

from shader_health.integrations.deadline import DeadlineConfig

config = DeadlineConfig.from_env()
# or
config = DeadlineConfig.from_json(Path("/show/config/shader_health/deadline.json"))
profile_path = config.resolved_profile_path()
```

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

The preflight helper treats the supplied profile as the critical validation
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

In a studio submitter, call the shared preflight helper before the actual
Deadline submit call:

```python
from pathlib import Path

from shader_health.integrations.deadline import DeadlineConfig, run_deadline_preflight

config = DeadlineConfig.from_env()
result = run_deadline_preflight(
    scene_path=Path(scene_path),
    report_path=Path(report_path),
    profile_path=config.resolved_profile_path(),
    mayapy=config.mayapy,
    repo_root=config.repo_root,
    extra_args=("--renderer", "vray"),
)

if not result.allowed:
    raise RuntimeError(
        "Deadline submission blocked by Shader Health. "
        f"Report: {result.report_path}"
    )

# Continue with normal Deadline submission here.
```

## REST client

`DeadlineClient` wraps the Deadline 10 on-prem Web Service for health checks and
future farm submit helpers (`#100`):

```python
from shader_health.integrations.deadline import DeadlineClient, DeadlineConfig

client = DeadlineClient(DeadlineConfig.from_env())
if not client.ping():
    raise RuntimeError("Deadline Web Service is unreachable")

job_id = client.submit_job(
    job_info={"Name": "Shader Health", "Plugin": "CommandScript", "Frames": "0"},
    plugin_info={"StartupDirectory": "/"},
)
job = client.get_job(job_id)
```

File paths in `AuxFiles` must be valid on the Web Service host, not the submitting
workstation. See the [Deadline REST overview](https://docs.thinkboxsoftware.com/products/deadline/10.4/1_User%20Manual/manual/rest-overview.html).

## Operational notes

- Keep the generated JSON report as a submit artifact.
- Use `mayapy`, not regular Python, when validating `.ma` or `.mb` scenes.
- Use snapshot JSON validation for CI or non-Maya environments.
- Do not ignore preflight error code `3`; treat it as a failed safety check.
- Tune the `deadline_critical` profile per show or facility policy.

## Validation

The integration module and example wrapper are covered by unit tests:

```bash
python -m pytest tests/unit/test_deadline_integration.py tests/unit/test_deadline_submit_preflight_example.py -v
```
