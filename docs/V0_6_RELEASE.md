# v0.6.0 public release checklist (local)

Manual steps for **#186** / **#232** — prepare `v0.6.0` on branch `dev`, then merge to `main`, tag, and publish GitHub Release.

**You push and publish yourself** — this doc is the copy-paste playbook.

---

## 1. Pre-flight (local)

### Git Bash

```bash
export REPO="/d/.../maya-pipeline-inspector"
cd "$REPO"

python -m pip install -e ".[dev]"
python -m pytest tests -q
python -m ruff check src tests tools
python -m mypy src/pipeline_inspector
python -m pipeline_inspector validate tests/fixtures/snapshots/vray_policy_scene.json \
  --input-kind snapshot --profile-id ci_headless \
  --report _cli_test_out/pre_release_smoke.json
echo "validate exit=$?"
```

### PowerShell

```powershell
$REPO = "D:\...\maya-pipeline-inspector"
Set-Location $REPO

python -m pip install -e ".[dev]"
python -m pytest tests -q
python -m ruff check src tests tools
python -m mypy src/pipeline_inspector
python -m pipeline_inspector validate (Join-Path $REPO "tests\fixtures\snapshots\vray_policy_scene.json") `
  --input-kind snapshot --profile-id ci_headless `
  --report (Join-Path $REPO "_cli_test_out\pre_release_smoke.json")
$LASTEXITCODE
```

**Expect:** pytest green (1306+), ruff clean, mypy clean, validate exit `0` or `1`/`2` on fixture (not `3`/`4`).

### Maya manual checklist (recommended)

Smoke in Maya before tagging:

- [ ] Panel opens; header shows **v0.6.0**
- [ ] Validate Scene on `examples/vray_policy/vray_policy_scene.ma` or `examples/arnold_policy/arnold_policy_scene.ma`
- [ ] **Readiness** tab runs configured probes
- [ ] Settings → Studio → Governance loads; risky fix / farm submit gates behave for your role
- [ ] Farm tab + optional `pipeline_inspector farm-analytics --json` against Deadline Web Service
- [ ] Check for Updates modal opens (network optional)

See also [`docs/MAYA_V02_MANUAL_CHECKLIST.md`](MAYA_V02_MANUAL_CHECKLIST.md) where still applicable.

---

## 2. What this release prep changes

| Area | Action |
|------|--------|
| Version | `0.6.0` in `version.py`, `pyproject.toml`, `test_import.py`, fallback plug-in, `native/CMakeLists.txt` |
| Docs | `CHANGELOG.md`, `README.md`, `USER_GUIDE`, `ARCHITECTURE`, `DEVELOPMENT_PLAN` §13–§14 |
| Plan | `V0_6_DEVELOPMENT_PLAN.md`, this file |

---

## 3. Commit on `dev` (local)

Review diff first:

```bash
cd "$REPO"   # or Set-Location $REPO
git status
git diff --stat
```

Suggested commit message:

```text
#186 - Prepare v0.6.0 public release

Closes #232
```

```bash
git add -A
git commit -m "#186 - Prepare v0.6.0 public release" -m "Closes #232"
```

---

## 4. Merge `dev` → `main` (manual PR or local)

**Recommended:** open PR on GitHub `dev` → `main`, wait for CI green, merge.

Example PR title: **Release v0.6.0**

After merge:

```bash
git checkout main
git pull origin main
```

---

## 5. Annotated tag `v0.6.0`

Tag **only on `main`** after merge, pointing at the merge commit that contains `0.6.0`.

### Git Bash

```bash
cd "$REPO"
git checkout main
git pull origin main

# sanity check
python -c "import pipeline_inspector; print(pipeline_inspector.__version__)"
# expect: 0.6.0

git tag -a v0.6.0 -m "Maya Pipeline Inspector v0.6.0"
git push origin v0.6.0
```

### PowerShell

```powershell
Set-Location $REPO
git checkout main
git pull origin main

python -c "import pipeline_inspector; print(pipeline_inspector.__version__)"
# expect: 0.6.0

git tag -a v0.6.0 -m "Maya Pipeline Inspector v0.6.0"
git push origin v0.6.0
```

### Verify tag

```bash
git show v0.6.0 --no-patch
git rev-parse v0.6.0
git log -1 --oneline v0.6.0
git tag -l "v0.6*"
```

**Notes:**

- Use **annotated** tag (`-a`), not lightweight — GitHub Releases pick it up cleanly.
- Tag name must match semver with **`v` prefix**: `v0.6.0` (auto-update wizard compares against this).
- If tag already exists locally from a failed attempt: `git tag -d v0.6.0` before re-creating (**only if not pushed yet**).
- Never move a published tag without team agreement (`git push --delete origin v0.6.0` is destructive).

### Tag on wrong commit?

```bash
# only before push:
git tag -d v0.6.0
git tag -a v0.6.0 -m "Maya Pipeline Inspector v0.6.0" <merge-commit-sha>
git push origin v0.6.0
```

---

## 6. GitHub Release (manual UI or `gh`)

### Option A — GitHub web UI

1. **Releases → Draft a new release**
2. **Choose tag:** `v0.6.0` (create from tag if prompted)
3. **Target:** `main`
4. **Title:** `v0.6.0 — Geometry QA, Readiness, Governance & Farm Analytics`
5. **Description:** paste from [Release notes template](#release-notes-template) below
6. Attach **`maya-pipeline-inspector-0.6.0.zip`** (see §8) and optional native `.mll` if built
7. **Publish release**

### Option B — `gh` CLI

Save release body to `_cli_test_out/v0.6.0_release_notes.md`, then:

```bash
gh release create v0.6.0 \
  --title "v0.6.0 — Geometry QA, Readiness, Governance & Farm Analytics" \
  --notes-file _cli_test_out/v0.6.0_release_notes.md
```

---

## Release notes template

Copy into GitHub Release description:

```markdown
## Maya Pipeline Inspector v0.6.0

**Theme:** Geometry QA, Machine Readiness, role governance, supervisor routing, Deadline farm analytics, public MIT release.

### Highlights

- **Geometry QA** — polycount and duplicate-mesh rules with asset-class budgets; `ShapeSnapshot` enrichment ([ARCHITECTURE](docs/ARCHITECTURE.md#geometry-validation))
- **Machine Readiness** — configurable probe engine and **Readiness** panel tab before publish/farm
- **Role governance** — `PermissionResolver` capability gates ([ADR 0008](docs/adr/0008-role-based-governance-foundation.md))
- **Supervisor routing** — role-based report dispatch to Telegram/Discord/Slack ([ADR 0009](docs/adr/0009-report-to-supervisor-routing-by-role.md))
- **Farm analytics** — `pipeline_inspector farm-analytics` CLI + HTML export ([guide](docs/integrations/deadline_farm_analytics.md))
- **Demo scenes** — [`examples/vray_policy/`](examples/vray_policy/) and [`examples/arnold_policy/`](examples/arnold_policy/)
- **Community** — MIT open source, [`COMMUNITY.md`](COMMUNITY.md) contributor paths

### Install

```bash
git clone https://github.com/armasonix/maya-pipeline-inspector.git
cd maya-pipeline-inspector
git checkout v0.6.0
python -m pip install -e ".[dev]"
```

Maya module path: [docs/MAYA_INSTALL.md](docs/MAYA_INSTALL.md).

### Headless smoke

```bash
python -m pipeline_inspector validate tests/fixtures/snapshots/vray_policy_scene.json \
  --input-kind snapshot --profile-id publish_strict --report report.json

python -m pipeline_inspector farm-analytics --json
```

### Known limitations

- Geometry duplicate scans may truncate on very large scenes.
- Readiness tab is Maya-session only — no headless readiness CLI.
- Governance is a capability foundation, not full studio IAM.
- Farm analytics requires read-only Deadline 10 Web Service access.
- `.mll` binaries not in repo — build locally or use release attachments.
- User preferences are panel-only; headless loads studio config only.

### Full changelog

[CHANGELOG.md — v0.6.0](https://github.com/armasonix/maya-pipeline-inspector/blob/v0.6.0/CHANGELOG.md#060---2026-07-21)
```

---

## 7. After release

```bash
git checkout dev
git pull origin dev
git merge main
git push origin dev
```

Close Milestone 52 / v0.6 cycle issues on GitHub.

---

## 8. Release zip asset

For the auto-update wizard, attach a zip named **`maya-pipeline-inspector-0.6.0.zip`**:

```bash
git archive --format=zip --prefix=maya-pipeline-inspector-0.6.0/ v0.6.0 \
  -o maya-pipeline-inspector-0.6.0.zip

gh release upload v0.6.0 maya-pipeline-inspector-0.6.0.zip
```

Or use the packaging helper:

```powershell
python tools/build_release_package.py
```

---

## Quick reference — version locations

| File | Field |
|------|--------|
| `src/pipeline_inspector/version.py` | `__version__` |
| `pyproject.toml` | `version` |
| `tests/unit/test_import.py` | assert |
| `maya_module/plug-ins/fallback/pipeline_inspector.py` | `PLUGIN_VERSION` |
| `native/CMakeLists.txt` | `PIPELINE_INSPECTOR_PLUGIN_VERSION` |
| `CHANGELOG.md` | `[0.6.0]` section |
| `README.md` | Status line |
