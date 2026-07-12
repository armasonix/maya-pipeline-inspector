# v0.5.0 public release checklist (local)

Manual steps for **#164** / **#198** — prepare `v0.5.0` on branch `dev`, then merge to `main`, tag, and publish GitHub Release.

**You push and publish yourself** — this doc is the copy-paste playbook.

---

## 1. Pre-flight (local)

### Git Bash

```bash
export REPO="/d/Workspace/portfolio/maya-shader-health-inspector"
cd "$REPO"

python -m pip install -e ".[dev]"
python -m pytest tests -q
python -m ruff check src tests tools
python -m mypy src
python -m shader_health validate tests/fixtures/snapshots/vray_policy_scene.json \
  --input-kind snapshot --profile-id ci_headless \
  --report _cli_test_out/pre_release_smoke.json
echo "validate exit=$?"
```

### PowerShell

```powershell
$REPO = "D:\Workspace\portfolio\maya-shader-health-inspector"
Set-Location $REPO

python -m pip install -e ".[dev]"
python -m pytest tests -q
python -m ruff check src tests tools
python -m mypy src
python -m shader_health validate (Join-Path $REPO "tests\fixtures\snapshots\vray_policy_scene.json") `
  --input-kind snapshot --profile-id ci_headless `
  --report (Join-Path $REPO "_cli_test_out\pre_release_smoke.json")
$LASTEXITCODE
```

**Expect:** pytest green (964+), ruff clean, mypy clean, validate exit `0` or `1`/`2` on fixture (not `3`/`4`).

### Maya manual checklist (recommended)

Smoke in Maya before tagging:

- [ ] Panel opens; header shows **v0.5.0**
- [ ] Settings → Basic / Advanced / Studio Environment / Connectors / Bug Report tabs load
- [ ] Validate Scene on demo scene; issue details + rule draft flow
- [ ] Farm tab still works with Deadline connector enabled
- [ ] Check for Updates modal opens (network optional)

---

## 2. What this release prep changes

| Area | Action |
|------|--------|
| Version | `0.5.0` in `version.py`, `pyproject.toml`, `test_import.py` |
| Docs | `CHANGELOG.md`, `README.md`, `USER_GUIDE`, `ARCHITECTURE`, `DEVELOPMENT_PLAN` §27 |
| Plan | `V0_5_DEVELOPMENT_PLAN.md`, this file |

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
#164 - Prepare v0.5.0 public release

Closes #198
```

```bash
git add -A
git commit -m "#164 - Prepare v0.5.0 public release" -m "Closes #198"
```

---

## 4. Merge `dev` → `main` (manual PR or local)

**Recommended:** open PR on GitHub `dev` → `main`, wait for CI green, merge.

Example PR title: **Release v0.5.0**

After merge:

```bash
git checkout main
git pull origin main
```

---

## 5. Annotated tag `v0.5.0`

Tag **only on `main`** after merge, pointing at the merge commit that contains `0.5.0`.

### Git Bash

```bash
cd "$REPO"
git checkout main
git pull origin main

# sanity check
python -c "import shader_health; print(shader_health.__version__)"
# expect: 0.5.0

git tag -a v0.5.0 -m "Maya Shader Health Inspector v0.5.0"
git push origin v0.5.0
```

### PowerShell

```powershell
Set-Location $REPO
git checkout main
git pull origin main

python -c "import shader_health; print(shader_health.__version__)"
# expect: 0.5.0

git tag -a v0.5.0 -m "Maya Shader Health Inspector v0.5.0"
git push origin v0.5.0
```

### Verify tag

```bash
git show v0.5.0 --no-patch
git rev-parse v0.5.0
git log -1 --oneline v0.5.0
```

**Notes:**

- Use **annotated** tag (`-a`), not lightweight — GitHub Releases pick it up cleanly.
- If tag already exists locally from a failed attempt: `git tag -d v0.5.0` before re-creating (only if not pushed yet).
- Never move a tag that is already published without team agreement (`git push --delete origin v0.5.0` is destructive).

---

## 6. GitHub Release (manual UI or `gh`)

### Option A — GitHub web UI

1. **Releases → Draft a new release**
2. **Choose tag:** `v0.5.0` (create from tag if prompted)
3. **Target:** `main`
4. **Title:** `v0.5.0 — Studio Settings Hub, Connectors & Rule Authoring`
5. **Description:** paste from [Release notes template](#release-notes-template) below
6. Optional: attach `maya-shader-health-inspector-0.5.0.zip` source bundle and native `.mll` if built
7. **Publish release**

### Option B — `gh` CLI

Save release body to `_cli_test_out/v0.5.0_release_notes.md`, then:

```bash
gh release create v0.5.0 \
  --title "v0.5.0 — Studio Settings Hub, Connectors & Rule Authoring" \
  --notes-file _cli_test_out/v0.5.0_release_notes.md
```

---

## Release notes template

Copy into GitHub Release description:

```markdown
## Maya Shader Health Inspector v0.5.0

**Theme:** Studio settings hub, notifications & task trackers, rule authoring, incident-to-rule, auto-update.

### Highlights

- **Settings hub** — Basic / Advanced / Studio Environment / Studio / Connectors / Bug Report ([ADR 0007](docs/adr/0007-settings-and-connectors-architecture.md))
- **Studio config 2.0** — two-layer model (studio + user prefs); headless `--studio-config`
- **Notifications** — Telegram, Discord, Slack with dispatcher routing
- **Task trackers** — Ftrack, ShotGrid, Cerebro + **Send to Tracker** from Reports
- **Bug Report** — HTTPS relay client + [studio relay spec](docs/integrations/bug_report_relay.md)
- **Check for Updates** — GitHub Releases wizard with rollback backup
- **Rule authoring** — rule browser, new rule wizard, incident-to-rule export; `shader_health rules validate`

### Install

```bash
git clone https://github.com/armasonix/maya-shader-health-inspector.git
cd maya-shader-health-inspector
git checkout v0.5.0
python -m pip install -e ".[dev]"
```

Maya module path: [docs/MAYA_INSTALL.md](docs/MAYA_INSTALL.md).

### Headless smoke

```bash
python -m shader_health validate tests/fixtures/snapshots/vray_policy_scene.json \
  --input-kind snapshot --profile-id publish_strict --report report.json

python -m shader_health rules validate src/shader_health/rules/common
```

### Known limitations

- User preferences are Maya-panel-only; headless loads studio config only.
- Bug Report and tracker connectors require studio credentials / relay endpoint.
- Rule editor is MVP — complex packs may still need JSON hand-editing.
- `.mll` binaries not in repo — build locally or use release attachments.
- Maya integration CI needs self-hosted runner with `mayapy`.

### Full changelog

[CHANGELOG.md — v0.5.0](https://github.com/armasonix/maya-shader-health-inspector/blob/v0.5.0/CHANGELOG.md#050---2026-07-12)
```

---

## 7. After release

```bash
git checkout dev
git pull origin dev
git merge main
git push origin dev
```

Close Milestone 41 / v0.5 cycle issues on GitHub.

---

## 8. Optional: release zip asset

For the auto-update wizard, attach a zip named like `maya-shader-health-inspector-0.5.0.zip`:

```bash
git archive --format=zip --prefix=maya-shader-health-inspector-0.5.0/ v0.5.0 \
  -o maya-shader-health-inspector-0.5.0.zip

gh release upload v0.5.0 maya-shader-health-inspector-0.5.0.zip
```

---

## Quick reference — version locations

| File | Field |
|------|--------|
| `src/shader_health/version.py` | `__version__` |
| `pyproject.toml` | `version` |
| `tests/unit/test_import.py` | assert |
| `CHANGELOG.md` | `[0.5.0]` section |
| `README.md` | Status line |
