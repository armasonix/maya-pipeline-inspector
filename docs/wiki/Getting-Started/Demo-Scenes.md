# Demo scenes

Shipped examples for learning, CI, and renderer policy demos. Open with **`MAYA_MODULE_PATH`** set to the repo `maya_module/`.

## Broken scene (general QA)

| Path | Purpose |
| --- | --- |
| [`examples/broken_scene/broken_scene.ma`](../../../examples/broken_scene/broken_scene.ma) | Missing textures, path issues, common rule triggers |

**Tutorial:** [First validation](../Tutorials/First-Validation-Tutorial)

## V-Ray policy demo

| Path | Purpose |
| --- | --- |
| [`examples/vray_policy/vray_policy_scene.ma`](../../../examples/vray_policy/vray_policy_scene.ma) | V-Ray-specific rules + common texture/path issues |

Requires **V-Ray** loaded in session.

**Walkthrough:** [V-Ray policy tutorial](../Tutorials/V-Ray-Policy-Walkthrough) · [`examples/vray_policy/README.md`](../../../examples/vray_policy/README.md)

## Arnold policy demo

| Path | Purpose |
| --- | --- |
| [`examples/arnold_policy/arnold_policy_scene.ma`](../../../examples/arnold_policy/arnold_policy_scene.ma) | Arnold rules, transmission depth, texture budgets, geometry metadata |

Requires **Arnold** loaded in session.

**Walkthrough:** [Arnold policy tutorial](../Tutorials/Arnold-Policy-Walkthrough) · [`examples/arnold_policy/README.md`](../../../examples/arnold_policy/README.md)

## Sample reports

Pre-generated HTML/JSON beside demo scenes — compare with your own **Reports** tab exports. Screenshot sources: [`docs/assets/`](../../assets/README.md)

## Headless validation (no UI)

```bash
mayapy -m pipeline_inspector validate examples/broken_scene/broken_scene.ma \
  --profile-id publish_strict \
  --report /tmp/report.json
```

→ [CLI reference](../Reference/CLI-Reference)
