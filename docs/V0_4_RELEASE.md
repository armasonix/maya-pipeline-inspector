# v0.4.0 public release checklist (local)

Manual steps for **#112** / **#138** — prepare `v0.4.0` on branch `dev`, then merge to `main`, tag, and publish GitHub Release.

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
python -m pipeline_inspector validate (Join-Path $REPO "tests\fixtures\snapshots\vray_policy_scene.json") `
  --input-kind snapshot --profile-id ci_headless `
  --report (Join-Path $REPO "_cli_test_out\pre_release_smoke.json")
$LASTEXITCODE
```

**Expect:** pytest green, ruff clean, validate exit `0` or `1`/`2` on fixture (not `3`/`4`).

---

## 2. What this release prep changes

| Area | Action |
|------|--------|
| Junk removed from git | fix audit, `*_fixed.ma`, manifest diff exports, deadline command aux |
| `.gitignore` | ignores local demo outputs + `_cli_test_out/` |
| Debug logging | removed from settings UI + CI helpers |
| Version | `0.4.0` in `version.py`, `pyproject.toml`, `test_import.py` |
| Docs | `CHANGELOG.md`, `README.md`, `USER_GUIDE`, `ARCHITECTURE`, `DEVELOPMENT_PLAN` |

---

## 3. Commit on `dev` (local)

Review diff first:

### Git Bash

```bash
cd "$REPO"
git status
git diff --stat
```

### PowerShell

```powershell
Set-Location $REPO
git status
git diff --stat
```

Suggested commit message:

```text
docs: Prepare v0.4 public release (ref #112)

Closes #138
```

### Git Bash

```bash
git add -A
git commit -m "docs: Prepare v0.4 public release (ref #112)" -m "Closes #138"
```

### PowerShell

```powershell
git add -A
git commit -m "docs: Prepare v0.4 public release (ref #112)" -m "Closes #138"
```

---

## 4. Merge `dev` → `main` (manual PR or local)

**Recommended:** open PR on GitHub `dev` → `main`, wait for CI green, squash/merge.

### GitHub CLI (optional)

```bash
cd "$REPO"
git push origin dev

gh pr create --base main --head dev \
  --title "Release v0.4.0" \
  --body "$(cat <<'EOF'
## Summary
- GUI-first Farm tab + Deadline 10 on-prem integration
- Studio settings (`pipeline_inspector_studio.json`) + Thinkbox Deadline connector
- Render-risk depth (displacement, .tx/optimized textures, duplicate materials)
- Native .mll Phase 1 scaffolding + Maya integration CI smoke
- Release hygiene: remove local demo junk, bump 0.4.0 docs

## Test plan
- [x] pytest 576 passed locally
- [x] ruff clean
- [x] headless validate smoke
- [x] Maya GUI smoke (Farm + Settings)

Closes #112
Closes #138
EOF
)"
```

Merge the PR on GitHub, then locally:

```bash
git checkout main
git pull origin main
```

---

## 5. Annotated tag `v0.4.0`

On **`main`** after merge:

### Git Bash

```bash
cd "$REPO"
git checkout main
git pull origin main

git tag -a v0.4.0 -m "Maya Pipeline Inspector v0.4.0"
git push origin v0.4.0
```

### PowerShell

```powershell
Set-Location $REPO
git checkout main
git pull origin main

git tag -a v0.4.0 -m "Maya Pipeline Inspector v0.4.0"
git push origin v0.4.0
```

Verify:

```bash
git show v0.4.0 --no-patch
python -c "import pipeline_inspector; print(pipeline_inspector.__version__)"
```

---

## 6. GitHub Release (manual UI or `gh`)

### Option A — GitHub web UI

1. **Releases → Draft a new release**
2. **Choose tag:** `v0.4.0`
3. **Title:** `v0.4.0 — GUI-First Farm Integration & Render Risk Depth`
4. **Description:** paste from [Release notes template](#release-notes-template) below
5. Attach optional native `.mll` zip(s) if built (`native/README.md`)
6. **Publish release**

### Option B — `gh` CLI

Save release body to a file, e.g. `_cli_test_out/v0.4.0_release_notes.md`, then:

```bash
gh release create v0.4.0 \
  --title "v0.4.0 — GUI-First Farm Integration & Render Risk Depth" \
  --notes-file _cli_test_out/v0.4.0_release_notes.md
```

---

## Release notes template

Copy into GitHub Release description:

```markdown
## Maya Pipeline Inspector v0.4.0

**Theme:** GUI-first Deadline farm integration, render-risk depth, studio settings.

### Highlights

- **Farm tab** — Deadline Web Service status, preflight, CommandScript submit
- **Settings → Connectors** — Thinkbox Deadline **Remote Farm** toggle + compact Deadline fields
- **Studio config** — `pipeline_inspector_studio.json` (Require `.tx`, Deadline connector)
- **Deadline package** — `pipeline_inspector.integrations.deadline` + [integration guide](docs/integrations/deadline_submit_preflight.md)
- **Render risk** — displacement depth, optimized texture / `.tx` rules, duplicate material/texture detection
- **Native plugin Phase 1** — CMake scaffolding + ADR 0006 (`.mll` optional; Python fallback remains)
- **UX Wave 1** — Issue Details polish, double-click issue → select node

### Install

```bash
git clone https://github.com/armasonix/maya-pipeline-inspector.git
cd maya-pipeline-inspector
git checkout v0.4.0
python -m pip install -e ".[dev]"
```

Maya module path: see [docs/MAYA_INSTALL.md](docs/MAYA_INSTALL.md).

### Headless smoke

```bash
python -m pipeline_inspector validate tests/fixtures/snapshots/vray_policy_scene.json \
  --input-kind snapshot --profile-id publish_strict --report report.json
```

### Known limitations

- Headless CLI does not yet load `pipeline_inspector_studio.json` (Maya UI only).
- `.mll` binaries are not in the repo — build locally or use release attachments.
- Maya integration CI requires self-hosted runner with `mayapy`.

### Full changelog

[CHANGELOG.md — v0.4.0](https://github.com/armasonix/maya-pipeline-inspector/blob/v0.4.0/CHANGELOG.md#040---2026-07-08)
```

---

## 7. After release

```bash
git checkout dev
git pull origin dev
git merge main
git push origin dev
```

Update any open issues/milestones for v0.4 cycle → closed.

---

## 8. Optional: attach native plugin zip

If you built Windows `.mll` per `native/README.md`:

```bash
gh release upload v0.4.0 native/build/Release/pipeline_inspector_2025.mll#pipeline_inspector-maya2025-win64.mll
```

(Adjust path/year to your build output.)

---

## Quick reference — version locations

| File | Field |
|------|--------|
| `src/pipeline_inspector/version.py` | `__version__` |
| `pyproject.toml` | `version` |
| `tests/unit/test_import.py` | assert |
| `CHANGELOG.md` | `[0.4.0]` section |
| `README.md` | Status line |
