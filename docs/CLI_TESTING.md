# Headless CLI Testing

Quick smoke commands for snapshot-only (`python`) and Maya scene (`mayapy`) validation.
Local reports go to `_cli_test_out/` or `_parity_out/` (gitignored).

## Exit codes

| Code | Meaning |
|------|---------|
| `0` | OK |
| `1` | Publish block |
| `2` | Deadline block |
| `3` | Runtime error |
| `4` | Config / input error |

## Git Bash setup (one-liners)

```bash
export REPO="/d/Workspace/portfolio/maya-pipeline-inspector"
export OUT="$REPO/_cli_test_out"
export MAYAPY="/c/Program Files/Autodesk/Maya2024/bin/mayapy.exe"
export SCENE="$REPO/examples/broken_scene/pipeline_inspector_demo_broken_headless.ma"
cd "$REPO" && mkdir -p "$OUT"
```

## Snapshot-only (`python`, no Maya)

```bash
python -m pipeline_inspector validate tests/fixtures/snapshots/vray_policy_scene.json --input-kind snapshot --profile-id publish_strict --report "$OUT/vray_publish_strict.json" && echo $?
```

```bash
python -m pipeline_inspector validate tests/fixtures/snapshots/arnold_policy_scene.json --input-kind snapshot --profile-id ci_headless --report "$OUT/arnold_ci_headless.json" && echo $?
```

```bash
python -m pipeline_inspector validate tests/fixtures/snapshots/vray_policy_scene.json --input-kind snapshot --profile-id publish_strict --asset-class-id asset_class_hero --report "$OUT/hero_resolution.json" && echo $?
```

Read a report with MSYS-safe paths:

```bash
python -c "from pipeline_inspector.util.paths import resolve_cli_path; import json; p=json.load(open(resolve_cli_path('$OUT/vray_publish_strict.json'))); print('health=',p.get('health_score'))"
```

## mayapy scene E2E

```bash
"$MAYAPY" -m pipeline_inspector validate "$SCENE" --input-kind scene --profile-id publish_strict --report "$OUT/demo_mayapy_fix.json" && echo $?
```

```bash
"$MAYAPY" -m pipeline_inspector manifest "$SCENE" --input-kind scene --profile-id publish_strict --out "$OUT/demo_manifest.json" && echo $?
```

```bash
"$MAYAPY" examples/publish/submit_preflight.py "$SCENE" --report "$OUT/publish_preflight.json" --profile "$REPO/src/pipeline_inspector/rules/profiles/publish_strict.json" --repo-root "$REPO" --mayapy "$MAYAPY" && echo $?
```

## PowerShell setup

```powershell
$REPO = "D:\Workspace\portfolio\maya-pipeline-inspector"
$OUT = Join-Path $REPO "_cli_test_out"
$MAYAPY = "C:\Program Files\Autodesk\Maya2024\bin\mayapy.exe"
$SCENE = Join-Path $REPO "examples\broken_scene\pipeline_inspector_demo_broken_headless.ma"
Set-Location $REPO; New-Item -ItemType Directory -Force -Path $OUT | Out-Null
```

```powershell
python -m pipeline_inspector validate (Join-Path $REPO "tests\fixtures\snapshots\vray_policy_scene.json") --input-kind snapshot --profile-id publish_strict --report (Join-Path $OUT "vray_publish_strict.json"); $LASTEXITCODE
```

```powershell
& $MAYAPY -m pipeline_inspector validate $SCENE --input-kind scene --profile-id publish_strict --report (Join-Path $OUT "demo_mayapy_fix.json"); $LASTEXITCODE
```

## Unit tests

```bash
python -m pytest tests/unit/test_headless_cli.py tests/unit/test_util_paths.py tests/unit/test_profile_composition.py -q
```

## GUI ↔ CLI parity

Use the same scene in Maya UI and CLI. Export GUI JSON reports to `_parity_out/`, then run CLI and compare.

```bash
mkdir -p _parity_out
export SCENE="$REPO/examples/broken_scene/pipeline_inspector_demo_broken_headless.ma"
```

**S1 — `publish_strict`, no asset class**

GUI: Validate Scene → Export JSON Report → `_parity_out/gui_s1_publish_strict.json`

```bash
"$MAYAPY" -m pipeline_inspector validate "$SCENE" --input-kind scene --profile-id publish_strict --report _parity_out/cli_s1_publish_strict.json
```

**S2 — `publish_strict` + `asset_class_hero`**

GUI: Asset class Hero → Validate → `_parity_out/gui_s2_hero.json`

```bash
"$MAYAPY" -m pipeline_inspector validate "$SCENE" --input-kind scene --profile-id publish_strict --asset-class-id asset_class_hero --report _parity_out/cli_s2_hero.json
```

**S3 — Manifest schema 1.1**

GUI: Export Shader Manifest → `_parity_out/gui_s3_manifest.json`

```bash
"$MAYAPY" -m pipeline_inspector manifest "$SCENE" --input-kind scene --profile-id publish_strict --out _parity_out/cli_s3_manifest.json
```

### Parity compare script

Save as `tools/compare_parity.py` or run inline:

```bash
python tools/compare_parity.py _parity_out/gui_s1_publish_strict.json _parity_out/cli_s1_publish_strict.json
python tools/compare_parity.py _parity_out/gui_s2_hero.json _parity_out/cli_s2_hero.json --manifest
python tools/compare_parity.py _parity_out/gui_s3_manifest.json _parity_out/cli_s3_manifest.json --manifest
```

The script compares `health_score`, block flags, failed `rule_id` lists (validate reports), or `manifest_schema_version` + material count (manifest reports). It ignores timestamps and absolute paths.
