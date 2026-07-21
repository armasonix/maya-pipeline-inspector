# Community

Maya Pipeline Inspector is an **MIT-licensed open-source** project. We want a shared Maya material/scene QA layer that studios extend together — not another closed validator script per facility.

**Repository:** [github.com/armasonix/maya-pipeline-inspector](https://github.com/armasonix/maya-pipeline-inspector)

## Where to talk

| Channel | Use for |
| --- | --- |
| [GitHub Issues](https://github.com/armasonix/maya-pipeline-inspector/issues) | Bugs, rule requests, concrete feature asks |
| [GitHub Discussions](https://github.com/armasonix/maya-pipeline-inspector/discussions) | Design questions, rollout ideas, show-and-tell |
| Panel **Bug Report** | Plugin defects from Maya ([relay docs](docs/integrations/bug_report_relay.md)) |

## Support the project

Pipeline Inspector is MIT-licensed and maintained in spare production-engineering time. If it saves your studio debugging hours:

- **[GitHub Sponsors](https://github.com/sponsors/armasonix)** — recurring support (enable after sponsor profile approval)
- **Star / watch** the repo — helps visibility for other studios
- **Contribute** rules, adapters, or sanitized integration examples ([`CONTRIBUTING.md`](CONTRIBUTING.md))

Security issues: [`SECURITY.md`](SECURITY.md) (private report — do not use public issues for exploits).

## How to contribute

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for setup, branch workflow, and PR checklist.

| You have… | Typical path |
| --- | --- |
| A new **rule** or profile tweak | Issue + [`docs/RULE_AUTHORING.md`](docs/RULE_AUTHORING.md) + pytest fixtures |
| A **renderer adapter** change | [`src/pipeline_inspector/adapters/`](src/pipeline_inspector/adapters/) + snapshot fixtures |
| A **studio integration** pattern | Sanitized PR to `examples/` or `docs/integrations/` |
| **Documentation** fixes | README, USER_GUIDE, ARCHITECTURE, ADRs |

Demo scenes for onboarding: [`examples/vray_policy/vray_policy_scene.ma`](examples/vray_policy/vray_policy_scene.ma) · [`examples/arnold_policy/arnold_policy_scene.ma`](examples/arnold_policy/arnold_policy_scene.ma)

## Early adopters

Studios or individuals running Pipeline Inspector in production (module path, fork, or internal branch) are welcome to list themselves here via a short issue or discussion — optional, no SLA implied.

| Studio / individual | Notes |
| --- | --- |
| *(none listed yet)* | Be the first — open a Discussion titled **Early adopter** |

## Code of conduct

Be constructive and production-minded. Do not commit client names, real production paths, or secrets. See [`CONTRIBUTING.md` — Open-Source Safety](CONTRIBUTING.md#open-source-safety-and-data-privacy).
