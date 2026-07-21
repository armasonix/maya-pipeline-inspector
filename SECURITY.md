# Security Policy

## Supported versions

| Version | Supported |
| --- | --- |
| **0.6.x** (latest release on `main`) | Yes |
| **0.5.x** and older | Best effort — upgrade to current release |
| **`dev` branch** | Unreleased; not a security support target |

Security fixes land on `main` and are tagged in [GitHub Releases](https://github.com/armasonix/maya-pipeline-inspector/releases).

## Reporting a vulnerability

**Do not** open public GitHub Issues for exploitable security problems (credentials, relay bypass, unsafe auto-fix data loss, etc.).

Instead:

1. Use [GitHub private vulnerability reporting](https://github.com/armasonix/maya-pipeline-inspector/security/advisories/new) if enabled for this repository, **or**
2. Email the maintainer with:
   - affected version / commit;
   - steps to reproduce;
   - impact (data loss, credential exposure, privilege escalation);
   - optional patch suggestion.

We aim to acknowledge within **5 business days** and share a remediation plan or fix timeline when confirmed.

## Out of scope

- Missing features or integration gaps documented in [USER_GUIDE — Known limitations](docs/USER_GUIDE.md#known-limitations--gaps)
- Studio misconfiguration (exposed PATs in `user.json`, public studio JSON with secrets)
- Third-party services (Deadline, Ftrack, Cloudflare relay) outside this repository

## Secure deployment reminders

- Keep connector secrets in **studio config on a protected share**, not in artist `user.json` ([STUDIO_OVERRIDES.md](docs/STUDIO_OVERRIDES.md))
- Run the **bug-report relay** server-side; never embed GitHub PATs in Maya ([bug_report_relay.md](docs/integrations/bug_report_relay.md))
- Treat **safe fixes** as production mutations — test on copies before batch apply ([ADR 0003](docs/adr/0003-safe-fix-reference-safety-policy.md))
